#!/usr/bin/env python3
"""Consolidation runner: one program for the `comment`, `document` and `severance` passes.

The script owns unit identity and file edits; the agent owns only judgement.

  record-init      enumerate the units at the baseline and write the record with one stub each
  (agent)          fill disposition, basis and, where the disposition needs them, edit/claims/ruling/tbc
  record-shard     split the stubs by file for read-only workers, each with a judgement file (.j)
  record-fill      write judgement files into the record (the first classification, or a correction)
  gate --pre       record-check (identity, admissibility, evidence, edit proofs) and the pre-rewrite gates
  apply            write the files from the record; also writes the commit message
  gate --unit      replay-check, removal-authorization, code invariance, ancestry, bound, scope
  review-pack      the human's review document

The batch flow (ADR 0013) drives the same steps over many review units:

  batch-init       the master record: the whole batch scope, classified once, never applied
  gate --pre --batch   record-check and the scope checks of the master record (no bound check)
  batch-plan       cut the gated master record into review units under the caps, bottom-up
  batch-next       run the next review unit end to end; stop at the first failure
  batch-status     done and pending units, and the next command
  batch-run        batch-next until a stop, a unit that asks for the suite, or the batch end

The same file ships byte-identical in both consolidation skills. Stdlib only.
"""
import argparse
import atexit
import difflib
import hashlib
import io
import json
import math
import os
import posixpath
import re
import subprocess
import sys
import time
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lexer as LX  # noqa: E402

OK, FAIL, ADVISORY = 0, 1, 2

DEFAULTS = {
    "REMOVED_LINE_CAP": 200,
    "REMOVAL_JUDGEMENT_CAP": 30,
    "SPOT_CHECK_RATE": 0.25,
    "FUNCTIONAL_DIFF_THRESHOLD": 400,
    "ADDED_LINE_CEILING": 200,
    "FLOOR_STALENESS_THRESHOLD_DAYS": 7,
}
_ALIASES = {"FLOOR_STALENESS_THRESHOLD": "FLOOR_STALENESS_THRESHOLD_DAYS"}
_PROVIDER_KEYS = ("knowledge_graph", "intake_path", "exclusion_inventory")
# ticket ids, issue numbers, ISO and Italian dates: the stale fragments of S49, measured as facts
FRAGMENT_PATTERNS = [r"\b[A-Z][A-Z0-9]+-\d+\b", r"#\d{3,}\b", r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                     r"(?i)\b\d{1,2} (?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre"
                     r"|ottobre|novembre|dicembre) \d{4}\b"]
_OPTION_KEYS = {"directive_patterns": [], "suite_cadence": "batch", "adr_dir": "docs/adr",
                "record_channel": "commit-message", "document_exts": [".md", ".rst", ".txt", ".adoc"],
                "fragment_patterns": FRAGMENT_PATTERNS, "last_verified_at": False}

CONSOLIDATION_COMMIT_MARKS = ("consolidation:", "mechanical:")
RECORD_DIR = ".consolidation"
RECORD_BEGIN = "--- consolidation-record v3 ---"
RECORD_BEGIN_V2 = "--- consolidation-record v2 ---"   # messages written before v3: readers take both
RECORD_END = "--- end consolidation-record ---"


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# ------------------------------------------------------------------ dispositions
RULED, DEFECT, NV = "ruled → apply", "contradicts code → suspected defect", "not verifiable"
ADR, OBS, REGEN = "historical decision → ADR", "obsolete", "regenerable → delete"
COND, STRIP, STILL = "condense", "stale fragment → strip", "still true"
DUPL = "duplicate → delete"
SEV, RET = "severed", "retained"

ADMISSIBLE = {
    "comment": [RULED, DEFECT, NV, ADR, OBS, REGEN, COND, STRIP, STILL],
    "document": [RULED, DEFECT, NV, ADR, DUPL, OBS, COND, STRIP, STILL],
    "severance": [SEV, RET],
}
UNIT_RULES = {"comment": ("comment", "comment-fine"),
              "document": ("document-paragraph", "document-block"),
              "severance": ("reference-occurrence",)}
CHANGE_AUTHORIZED = {_norm(d) for d in (RULED, ADR, DUPL, OBS, REGEN, COND, STRIP, SEV)}
JUDGEMENT = {_norm(d) for d in (RULED, OBS, ADR, DUPL, REGEN, COND, STRIP, SEV)}
EVIDENCE = {_norm(d) for d in (RULED, DEFECT, NV, ADR, DUPL, OBS, REGEN, STILL, COND, STRIP, SEV, RET)}
EDIT_REQUIRED = {_norm(d) for d in (COND, STRIP)}
EDIT_ALLOWED = {_norm(d) for d in (RULED, OBS, COND, STRIP, SEV, REGEN)}
FROZEN = {_norm(d) for d in (DEFECT, NV)}
REMOVED_WHOLE = {_norm(d) for d in (ADR, DUPL, REGEN)}
REQUIRED_HEADER = ("unit_id", "baseline_sha", "pass_kind", "unit_rule", "scope", "floor", "floor_observed")
NARROWING_REASONS = ("bound-driven split", "freshness exclusion")
SCRIPT_FIELDS = ("file", "lines", "span", "fingerprint", "preview", "in_tbc", "facts")
JUDGEMENT_FIELDS = ("disposition", "basis", "edit", "claims", "ruling", "tbc", "of", "conflicts", "escalate",
                    "adr", "adr_title", "adr_text")
MULTILINE = ("edit", "claims", "adr_text")
REF_FIELDS = ("of", "conflicts")   # name another unit of the record by its record-local id (B3)
# v3 adds the script-owned `facts:` and the `adr:` judgement field (or `adr_title` + `adr_text`,
# an ADR the runner renders and writes), and counts twins on the normalized body. A v2 record
# (an earlier commit) is still judged by v2's rules, so upgrading never blocks the history walk;
# only the current version is ever written, gated before a rewrite, or applied.
RECORD_VERSION = "3"
FLOORS = ("self-report", "graph", "exclusion-inventory")
RULE_WALK_CAP = 500   # B4c: the first-parent commits record-shard reads for a remembered unit rule

ENTRY_KINDS = ("suspected-defect", "unverifiable-statement", "load-bearing-reference", "obsolete-citation")
RULABLE_KINDS = ("suspected-defect", "unverifiable-statement")   # the kinds whose ruling is `ruled → apply`


def require_current(rec, where):
    """A record about to be gated before a rewrite, or applied, is the current version: an older
    one is read only from the commit that carries it, by its own rules."""
    v = (rec.header or {}).get("record_version")
    if v != RECORD_VERSION:
        _die(f"{where}: record_version {v!r} — a record in the working tree must be version {RECORD_VERSION}; "
             f"write it again with record-init (or batch-init)")


def record_v3(rec):
    try:
        return int((rec.header or {}).get("record_version", "2")) >= 3
    except ValueError:
        return False


def canon(disp):
    """The admissible spelling of a disposition, or None."""
    n = _norm(disp)
    for d in (*ADMISSIBLE["comment"], *ADMISSIBLE["document"], SEV, RET):
        if _norm(d) == n:
            return d
    return None


# ------------------------------------------------------------------ output helpers
def _warn(msg):
    print(f"warn: {msg}", file=sys.stderr)


class Die(Exception):
    pass


def _die(msg):
    raise Die(msg)


# ------------------------------------------------------------------ config
def config_path():
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        p = d / ".consolidation.json"
        if p.exists():
            return p
        if (d / ".git").exists():
            break
    return None


_WARNED = set()


def _bound_untracked(cfg, src):
    """An untracked (or locally modified) config may tighten the gates, never loosen them: a
    cap above its default, a lower spot-check rate, a document extension the default does not
    list — each falls back to the default, and `config-bound-check` fails the gate naming it.
    Only a committed config, read from the baseline blob, carries the owner's authority
    (R-gates 5)."""
    out = []
    for k, d in DEFAULTS.items():
        v = cfg[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            out.append(f"{k}={v!r} is not a number")
        elif (v < d) if k == "SPOT_CHECK_RATE" else (v > d):
            out.append(f"{k}={v} loosens the default {d}")
        else:
            continue
        cfg[k] = d
    dflt = _OPTION_KEYS["document_exts"]
    exts = cfg["document_exts"] if isinstance(cfg["document_exts"], list) else []
    wider = [e for e in exts if str(e).lower() not in dflt]
    if wider or not isinstance(cfg["document_exts"], list):
        out.append(f"document_exts {cfg['document_exts']!r} widens the default {dflt}")
        cfg["document_exts"] = [e for e in exts if str(e).lower() in dflt] or list(dflt)
    if cfg["last_verified_at"] is not False:
        out.append("last_verified_at is the owner's word that the merge strategy keeps shas resolvable (S99)")
        cfg["last_verified_at"] = False
    for m in out:
        if (src, m) not in _WARNED:
            _WARNED.add((src, m))
            _warn(f"{src} is not the committed config: {m}; the default is in force")
    cfg["_bounded"] = out


def _config_from_text(text, src, tracked=False):
    cfg = dict(DEFAULTS)
    cfg.update({k: (list(v) if isinstance(v, list) else v) for k, v in _OPTION_KEYS.items()})
    # hashed with LF endings and without the BOM: an autocrlf worktree copy and its LF blob are
    # one config, and a BOM is an editor artifact — the same logical config with and without one
    # binds alike. A record written while the BOM was still hashed carries the BOM-included sha:
    # it stays accepted as `_config_sha_legacy`, never written into a new record
    lf = (text or "").replace("\r\n", "\n")
    cfg["_config_sha_legacy"] = hashlib.sha1(encode(lf)).hexdigest() if lf else ""
    text = (text or "").lstrip("\ufeff")
    cfg["_config_sha"] = hashlib.sha1(encode(text.replace("\r\n", "\n"))).hexdigest() if text else ""
    cfg["_tracked"] = tracked
    cfg["_bounded"] = []
    if not text:
        return cfg
    try:
        data = json.loads(text)
    except Exception as e:
        _warn(f"could not parse {src}: {e}; using defaults")
        return cfg
    for k, v in data.items():
        key = _ALIASES.get(k, k)
        if key in DEFAULTS or key in _PROVIDER_KEYS or key in _OPTION_KEYS:
            cfg[key] = v
        else:
            _warn(f"{src}: unknown key {k!r} ignored")
    if not isinstance(cfg["last_verified_at"], bool):
        _warn(f"last_verified_at {cfg['last_verified_at']!r} is not true or false; using false")
        cfg["last_verified_at"] = False
    if cfg["suite_cadence"] not in ("batch", "unit"):
        _warn(f"suite_cadence {cfg['suite_cadence']!r} is neither 'batch' nor 'unit'; using 'batch'")
        cfg["suite_cadence"] = "batch"
    if not tracked:
        _bound_untracked(cfg, src)
    return cfg


def load_config(at_sha=None):
    """The config in force. With `at_sha`: the `.consolidation.json` of that commit, when the
    repo tracks one there — the form every gate judging a record uses (A4). A worktree config
    counts as tracked only while it equals HEAD's blob; any other is bounded (R-gates 5)."""
    if at_sha:
        blob = git_show(at_sha, ".consolidation.json")
        if blob is not None:
            return _config_from_text(blob, f"{at_sha[:8]}:.consolidation.json", tracked=True)
    p = config_path()
    if p is None:
        return _config_from_text(None, "")
    try:
        text = decode(p.read_bytes())
    except OSError:
        return _config_from_text(None, str(p))
    blob = git_show("HEAD", ".consolidation.json")
    tracked = blob is not None and blob.replace("\r\n", "\n") == text.replace("\r\n", "\n")   # autocrlf
    return _config_from_text(text, str(p), tracked=tracked)


def config_for_record(rec, cfg):
    """A record is judged with the config of its own baseline when the repo tracked one there;
    an untracked config is bound by the header's config_sha, checked in record_problems (A4)."""
    sha = (rec.header or {}).get("baseline_sha") if rec is not None else None
    return load_config(at_sha=sha) if sha else cfg


def _decode_output(b):
    """Tool output: UTF-8 when it is, else the locale's code page (a Windows pipe writes cp1252)."""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        import locale
        return b.decode(locale.getpreferredencoding(False) or "utf-8", "replace")


def _run_provider(cmd, what):
    r = subprocess.run(cmd, shell=True, capture_output=True)
    if r.returncode != 0:
        _die(f"{what} command failed (exit {r.returncode}): {cmd}\n{_decode_output(r.stderr).strip()}")
    lines = [l.strip() for l in _decode_output(r.stdout).lstrip("﻿").splitlines() if l.strip()]
    if not lines:
        _die(f"{what} command produced no output: {cmd}")
    return lines


def norm_path(p):
    """A provider- or user-written repository path in the runner's form: posix, no leading './'."""
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _provider_rows(lines):
    """A provider's data lines, the path fields (first and last) normalized; `#` lines are its
    metadata (`# observed: …`)."""
    out = []
    for l in lines:
        if l.startswith("#"):
            continue
        f = l.split("\t")
        f[0], f[-1] = norm_path(f[0]), norm_path(f[-1])
        out.append("\t".join(f))
    return out


PROVIDER_FLOORS = {"graph": "knowledge_graph", "exclusion-inventory": "exclusion_inventory"}
_PROVIDER_RUNS = {}


def provider_floor(rec, cfg):
    """(target paths, observed, tracked): the floor a gate observes itself by re-running the
    record's provider from the config it is judged with — never a target set the agent hands in
    (S92, ADR 0011). `observed` is the provider's own `# observed: <ISO date or sha>` line, the
    build state `S2` asks of a floor, or None. One run per command, tree and process."""
    floor = (rec.header.get("floor") or "").strip()
    key = PROVIDER_FLOORS[floor]
    cmd = cfg.get(key)
    if not cmd:
        _die(f"the record declares floor {floor!r}, but the config sets no {key}: a floor is "
             f"observed by the gate re-running its provider, never asserted by the header")
    memo = (os.getcwd(), head_sha(), cmd)
    if memo not in _PROVIDER_RUNS:
        _PROVIDER_RUNS[memo] = _run_provider(cmd, key)
    lines = _PROVIDER_RUNS[memo]
    observed = next((m.group(1) for m in (re.match(r"#\s*observed:\s*(\S+)", l) for l in lines) if m), None)
    rows = _provider_rows(lines)
    if floor == "exclusion-inventory":
        targets = {t.strip() for t in rec.header.get("targets", "").split(",") if t.strip()}
        rows = [l for l in rows if l.split("\t")[-1].strip() in targets]
    return {l.split("\t")[0].strip() for l in rows}, observed, cfg.get("_tracked", False)


# ------------------------------------------------------------------ git, hardened
# Every diff is read with fixed options: a user's diff.noprefix, diff.external, textconv or
# core.quotepath must never change what a gate sees.
_GIT_C = ["-c", "core.quotepath=off", "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false",
          "-c", "color.ui=false"]


class _CountingSubprocess:
    """This module's `subprocess`: every git process it starts is counted for
    CONSOLIDATION_PROFILE; everything else is the stdlib module."""
    git_calls = 0

    def __getattr__(self, name):
        return getattr(_subprocess, name)

    @staticmethod
    def _count(cmd):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
            _CountingSubprocess.git_calls += 1

    def run(self, cmd, *a, **kw):
        self._count(cmd)
        return _subprocess.run(cmd, *a, **kw)

    def Popen(self, cmd, *a, **kw):
        self._count(cmd)
        return _subprocess.Popen(cmd, *a, **kw)


_subprocess = subprocess
subprocess = _CountingSubprocess()

# Memos of what a full commit sha determines. Every key starts with the working directory: one
# process (the self-test) walks many repositories whose commits can share a sha. A symbolic rev
# (HEAD, TIP, a branch, an abbreviated sha) is never memoized: commits happen mid-run.
_FULL_SHA = re.compile(r"[0-9a-f]{40}")
_MEMO = {}


def _full(*shas):
    return all(isinstance(s, str) and _FULL_SHA.fullmatch(s) is not None for s in shas)


def _memo(kind, key, fn):
    k = (kind, os.getcwd()) + key
    if k not in _MEMO:
        _MEMO[k] = fn()
    return _MEMO[k]


def git(*args, binary=False):
    r = subprocess.run(["git", *_GIT_C, *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def status_entries(*paths):
    """[(xy, path, orig)] of every path that differs from HEAD, from `git status --porcelain -z
    -uall`: names as git stores them (-z never C-quotes), each untracked file whatever
    status.showUntrackedFiles says, and a rename or copy as one entry with both sides — `orig`
    is the old one (-z writes the new side first), else None — whatever status.renames says."""
    f = git("-c", "status.renames=true", "status", "--porcelain", "-z", "-uall",
            *(("--", *paths) if paths else ())).split("\0")
    out, i = [], 0
    while i < len(f):
        e = f[i]
        i += 1
        if len(e) < 4:
            continue
        orig = None
        if "R" in e[:2] or "C" in e[:2]:
            orig = f[i] if i < len(f) else ""
            i += 1
        out.append((e[:2], e[3:], orig))
    return out


def status_line(xy, path, orig):
    """An entry as `git status --porcelain` shows it, for a report."""
    return f"{xy} {orig} -> {path}" if orig is not None else f"{xy} {path}"


def commit_message_of(sha):
    """A commit message, decoded as the record files are (surrogateescape): a record embedding a
    non-UTF-8 preview round-trips byte for byte, never through U+FFFD."""
    if _full(sha):
        return _memo("msg", (sha,), lambda: decode(git("log", "-1", "--format=%B", sha, binary=True)))
    return decode(git("log", "-1", "--format=%B", sha, binary=True))


def decode(b):
    return b.decode("utf-8", "surrogateescape")


def encode(s):
    return s.encode("utf-8", "surrogateescape")


def _git_show_proc(sha, path):
    r = subprocess.run(["git", *_GIT_C, "show", f"{sha}:{path}"], capture_output=True)
    return decode(r.stdout) if r.returncode == 0 else None


# One long-lived `git cat-file --batch` for the current directory. Only one lives at a time: a
# reader left running in a directory pins it, and the self-test removes its repositories.
_CAT = [None, None]   # [cwd, process]


def _close_cat():
    p, _CAT[:] = _CAT[1], [None, None]
    if p is not None:
        try:
            p.stdin.close()
            p.wait(timeout=5)
        except Exception:
            p.kill()


atexit.register(_close_cat)


def _cat_blob(spec):
    """(type, bytes) of `spec` from the batch reader, ('missing', None) when git has no such
    object; None when the reader failed (the caller falls back to `git show`)."""
    cwd = os.getcwd()
    try:
        if _CAT[0] != cwd or _CAT[1] is None or _CAT[1].poll() is not None:
            _close_cat()
            _CAT[:] = [cwd, subprocess.Popen(["git", *_GIT_C, "cat-file", "--batch"], stdin=_subprocess.PIPE,
                                             stdout=_subprocess.PIPE, stderr=_subprocess.DEVNULL)]
        p = _CAT[1]
        p.stdin.write(spec + b"\n")
        p.stdin.flush()
        head = p.stdout.readline()
        parts = head.rstrip(b"\n").split(b" ")
        if len(parts) == 3 and _FULL_SHA.fullmatch(parts[0].decode("ascii", "replace")) and parts[2].isdigit():
            size = int(parts[2])
            data = p.stdout.read(size)
            if len(data) != size or p.stdout.read(1) != b"\n":
                raise OSError("short read from git cat-file")
            return parts[1].decode("ascii", "replace"), data
        if head.endswith((b" missing\n", b" ambiguous\n")):
            return "missing", None
        raise OSError(f"unexpected git cat-file reply {head!r}")
    except (OSError, ValueError):
        _close_cat()
        return None


def git_show(sha, path):
    """The text of `path` at `sha`, None when it has none. A full sha's blob is read once per
    process and directory, through the batch reader, byte-identical to `git show` (neither
    applies a filter or textconv to a blob); a tree listing, a symbolic rev and a path the batch
    protocol cannot carry go through `git show`."""
    if not _full(sha) or "\n" in path or path.startswith(("./", "../")):
        return _git_show_proc(sha, path)
    key = ("show", os.getcwd(), sha, path)
    if key not in _MEMO:
        try:
            got = _cat_blob(f"{sha}:{path}".encode("utf-8"))
        except UnicodeEncodeError:
            got = None
        if got is None or got[0] not in ("blob", "missing"):
            _MEMO[key] = _git_show_proc(sha, path)
        else:
            _MEMO[key] = decode(got[1]) if got[0] == "blob" else None
    return _MEMO[key]


def read_text_file(path):
    """A file the user's shell wrote: UTF-8 with or without a BOM, or UTF-16 with its BOM (what
    Windows PowerShell 5.1 writes for `>`)."""
    b = Path(path).read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16")
    return decode(b).lstrip("﻿")


def read_worktree(path):
    try:
        return decode(Path(path).read_bytes())
    except OSError:
        return None


# The commit the unit gate judges: HEAD, except when a batch's last review unit replays every
# earlier one at its own commit, or the history walk replays a commit (ADR 0015).
TIP = "HEAD"
_GATED_UNITS = set()   # (commit, target set) of the review units this command gated and passed


def git_diff(a, b=None):
    # --text: a `binary` or `-diff` gitattribute must not turn a diff into "Binary files differ"
    # and blind every check that counts removed lines (A6).
    b = b or TIP

    def get():
        return decode(git("diff", "--text", "--no-color", "--no-ext-diff", "--no-textconv", "--no-renames",
                          "--src-prefix=a/", "--dst-prefix=b/", a, b, binary=True))
    return _memo("diff", (a, b), get) if _full(a, b) else get()


def changed_files(a, b=None):
    b = b or TIP

    def get():
        return [p for p in git("diff", "--name-only", "--no-renames", "-z", a, b).split("\0") if p]
    return list(_memo("names", (a, b), get)) if _full(a, b) else get()


def first_parent(sha):
    """`sha^`, or None for a root commit (or a rev that does not resolve)."""
    def get():
        try:
            return git("rev-parse", f"{sha}^").strip()
        except RuntimeError:
            return None
    return _memo("parent", (sha,), get) if _full(sha) else get()


def commit_log(*revs):
    """[(sha, subject, message)] of `git log revs`, newest first, from one `git log`; it fills the
    message and parent memos, so a walk over the commits pays no call per commit. `git log`
    re-encodes each message per its encoding header exactly as commit_message_of does."""
    raw = git("log", "--no-show-signature", "-z", "--format=%H%x00%P%x00%s%x00%B", *revs, "--", binary=True)
    f = raw.split(b"\0")
    out = []
    for i in range(0, len(f) - 3, 4):
        sha = f[i].decode("ascii", "replace").lstrip("\n")
        if not _full(sha):
            # the empty chunk after the last record is the stream terminator and never reaches
            # this slot; a chunk in a sha slot that is not a full sha means a commit body carried
            # a NUL byte and the field grid has slipped: fail loud — a commit silently omitted
            # here is a commit the gates never judged
            _die(f"git log output misaligned at record {i // 4 + 1}: the sha slot holds {f[i][:24]!r} — "
                 f"a commit body carries a NUL byte and the commits after it cannot be read")
        parents = f[i + 1].decode("ascii").split()
        _MEMO[("parent", os.getcwd(), sha)] = parents[0] if parents else None
        _MEMO[("msg", os.getcwd(), sha)] = msg = decode(f[i + 3] + b"\n")
        out.append((sha, f[i + 2].decode("utf-8", "replace"), msg))
    return out


def _diff_lines(a, b=None):
    """Yield (file, old_line, new_line, sign, content) for every changed line of the diff a..b.
    Parsed by hunk state, never by prefix alone, so a changed line whose own content starts with
    '-' or '+' is kept."""
    out = git_diff(a, b)
    file, old, new, in_hunk = None, 0, 0, False
    saw_header = last_changed = False
    hunk = []   # [file, old, new, sign, content, no_newline] of the current hunk

    def flush():
        # A last line that only gains or loses its newline shows as `-X`, `\ No newline`, `+X`:
        # the line itself is unchanged, so the pair is dropped (an item appended at EOF, D2).
        events = list(hunk)
        hunk.clear()
        for i, e in enumerate(events):
            if e is None or not e[5]:
                continue
            want = "+" if e[3] == "-" else "-"
            j = next((k for k, x in enumerate(events) if x is not None and k != i and x[3] == want
                      and x[4] == e[4] and x[0] == e[0] and not x[5]), None)
            if j is not None:
                events[i] = events[j] = None
        for e in events:
            if e is not None and e[0]:
                yield tuple(e[:5])

    for line in out.split("\n"):
        if line.startswith("diff --git "):
            yield from flush()
            file, in_hunk, saw_header = None, False, True
        elif line.startswith("@@"):
            yield from flush()
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
            if not m:
                _die(f"unparseable hunk header in git diff: {line!r}")
            old, new, in_hunk = int(m.group(1)), int(m.group(2)), True
        elif not in_hunk:
            if line.startswith("--- "):
                p = line[4:].strip()
                if p.startswith('"') and p.endswith('"'):
                    p = p[1:-1]
                if p != "/dev/null" and not p.startswith("a/"):
                    _die(f"unparseable diff header {line!r}: a gate refuses to read a diff it cannot parse")
                file = p[2:] if p.startswith("a/") else None
        elif line.startswith("-"):
            hunk.append([file, old, new, "-", line[1:], False])
            old += 1
            last_changed = True
        elif line.startswith("+"):
            hunk.append([file, old, new, "+", line[1:], False])
            new += 1
            last_changed = True
        elif line.startswith("\\"):
            if hunk and last_changed:   # the marker qualifies the line just before it
                hunk[-1][5] = True
        else:
            old += 1
            new += 1
            last_changed = False
    yield from flush()
    if out.strip() and not saw_header:
        _die("git diff produced output without a 'diff --git' header: refusing to read it")


def iter_removed(a, b=None):
    """Yield (file, baseline_line, content) for every line the diff a..b removes."""
    for f, old, _, sign, content in _diff_lines(a, b):
        if sign == "-":
            yield (f, old, content)


def iter_added(a, b=None):
    """Yield (file, head_line, content) for every line the diff a..b adds."""
    for f, _, new, sign, content in _diff_lines(a, b):
        if sign == "+":
            yield (f, new, content)


def repo_root():
    """The repository root of the working directory; a found root is remembered per directory."""
    key = ("root", os.getcwd())
    if key in _MEMO:
        return _MEMO[key]
    try:
        _MEMO[key] = root = git("rev-parse", "--show-toplevel").strip()
    except RuntimeError:
        return None
    return root


def head_sha(short=False):
    try:
        return git("rev-parse", *(["--short"] if short else []), "HEAD").strip()
    except RuntimeError:
        return None


ORIG_CWD = os.getcwd()


def user_path(p):
    """A path the user typed, resolved against the directory they typed it in."""
    return str(Path(p) if os.path.isabs(p) else Path(ORIG_CWD) / p)


def root_path(p):
    """A runner-chosen path (the record directory): resolved against the repository root, never
    the directory the command was typed in, so every gate's `.consolidation/` exclusion holds."""
    return str(Path(repo_root() or os.getcwd()) / p)


def show_path(p):
    """A path as the user, in the directory they typed the command in, can pass back."""
    try:   # resolved: a TEMP path in 8.3 short form must not leak `../..` into the output
        return Path(os.path.relpath(Path(user_path(p)).resolve(), Path(ORIG_CWD).resolve())).as_posix()
    except ValueError:   # another drive on Windows
        return Path(user_path(p)).as_posix()


def root_rel(p, root):
    """`p` relative to the resolved repository root, as posix; the absolute path when it lies
    on another drive or share, where no relative path exists."""
    ab = Path(p).resolve()   # resolve: 8.3 short names
    try:
        return Path(os.path.relpath(ab, root)).as_posix()
    except ValueError:
        return ab.as_posix()


def repo_rel(p):
    """A user-typed path as a repository-root-relative posix path."""
    root = repo_root() or os.getcwd()
    ab = Path(user_path(p)).resolve()
    try:
        return ab.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(p).as_posix()


# ------------------------------------------------------------------ lines
def split_lines(text):
    """(contents, eols): every line's content and its own ending, so mixed endings survive."""
    parts = text.split("\n")
    contents, eols = [], []
    for k, p in enumerate(parts):
        if k == len(parts) - 1:
            if p:
                contents.append(p)
                eols.append("")
            break
        if p.endswith("\r"):
            contents.append(p[:-1]); eols.append("\r\n")
        else:
            contents.append(p); eols.append("\n")
    return contents, eols


def join_lines(contents, eols):
    return "".join(c + e for c, e in zip(contents, eols))


def unit_body(lines, sl, el):
    """The normalized whole-line body of a unit: what its fingerprint hashes, and what identical
    units share."""
    return _norm("\n".join(lines[sl - 1:el]))


def occurrences(lines, units, v3=True):
    """The occurrence index of each unit among the file's units with the same normalized body, in
    enumeration order. Counted on the body the fingerprint hashes: two comments that differ only
    in indentation or case are one body, and must never share an index. A v2 record counted on
    the raw body, and is judged by that rule still."""
    seen, out = {}, []
    for u in units:
        b = unit_body(lines, u.sl, u.el) if v3 else "\n".join(lines[u.sl - 1:u.el])
        seen[b] = seen.get(b, 0) + 1
        out.append(seen[b])
    return out


def fingerprint(path, text, sl, el, occ=1, lines=None):
    """Content key of a unit: path + occurrence index among identical bodies + body. The index
    keeps two identical comments in one file from sharing a key, so a ruling on one never
    authorizes the other; it survives line moves, which --carry-from depends on."""
    lines = text.split("\n") if lines is None else lines
    body = "\n".join(lines[sl - 1:el])
    return hashlib.sha1(_norm(Path(path).as_posix() + "\n" + str(occ) + "\n" + body)
                        .encode("utf-8", "surrogateescape")).hexdigest()[:8]


# ------------------------------------------------------------------ scope
def parse_scope(s):
    """'a.py, docs/x.md:10-80' → [(path, (a, b) or None)]."""
    out = []
    for part in [p.strip() for p in (s or "").split(",") if p.strip()]:
        m = re.match(r"^(.*?):(\d+)-(\d+)$", part)
        out.append((m.group(1), (int(m.group(2)), int(m.group(3)))) if m else (part, None))
    return out


def render_scope(entries):
    return ", ".join(f"{p}:{r[0]}-{r[1]}" if r else p for p, r in entries)


# ------------------------------------------------------------------ enumeration
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^ {0,3}(```+|~~~+)")
_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


def doc_units(text, rule, v3=True):
    """Units of a Markdown-like document. Front matter is never a unit; a fenced block is atomic;
    an ATX heading is always its own unit. `document-block` also splits list items and table rows.
    A unit under the `## To be confirmed` heading has kind "tbc"; from v3 each of its list items
    is a unit under every rule — one item, one question, one intake entry (S65)."""
    lines, _ = split_lines(text)
    n = len(lines)
    i = 0
    if n and lines[0].lstrip("﻿").strip() == "---":   # a BOM must not expose front matter as units
        j = 1
        while j < n and lines[j].strip() not in ("---", "..."):
            j += 1
        i = j + 1
    units = []
    cur = None
    tbc = False

    def close():
        nonlocal cur
        if cur:
            units.append(tuple(cur))
        cur = None

    while i < n:
        line = lines[i].lstrip("﻿") if i == 0 else lines[i]   # a BOM never hides a heading
        ln = i + 1
        fm = _FENCE.match(line)
        if fm:
            close()
            j = i + 1
            while j < n and not lines[j].lstrip().startswith(fm.group(1)):
                j += 1
            end = min(j, n - 1)
            units.append((ln, end + 1, tbc))
            i = end + 1
            continue
        hm = _HEADING.match(line)
        if hm:
            close()
            level, title = len(hm.group(1)), hm.group(2).strip()
            if tbc and level <= 2:
                tbc = False
            units.append((ln, ln, tbc))
            if level == 2 and title.lower() == "to be confirmed":
                tbc = True
            i += 1
            continue
        if not line.strip():
            close()
            i += 1
            continue
        starts_new = False
        if rule == "document-block" or (tbc and v3):
            if _ITEM.match(line):
                starts_new = True
            elif rule == "document-block" and line.lstrip().startswith("|"):
                starts_new = re.match(r"^\s*\|?\s*:?-{2,}", line) is None
        if cur and not starts_new:
            cur[1] = ln
        else:
            close()
            cur = [ln, ln, tbc]
        i += 1
    close()
    return [LX.Unit(a, 0, b, len(lines[b - 1]), True, "tbc" if t else "block") for a, b, t in units]


def _tbc_heading_index(contents):
    """Line index of the `## To be confirmed` heading, located by doc_units' own rules: up to
    three leading spaces, never inside a fenced block (a fenced pseudo-heading is prose)."""
    k, n = 0, len(contents)
    while k < n:
        line = contents[k].lstrip("﻿") if k == 0 else contents[k]
        fm = _FENCE.match(line)
        if fm:
            k += 1
            while k < n and not contents[k].lstrip().startswith(fm.group(1)):
                k += 1
            k += 1
            continue
        hm = _HEADING.match(line)
        if hm and len(hm.group(1)) == 2 and hm.group(2).strip().lower() == "to be confirmed":
            return k
        k += 1
    return None


def _tbc_section_end(contents, h):
    """(end, last): end-exclusive index where the section stops (the next heading of level ≤ 2,
    fences skipped — never a heading inside a fence) and its last non-blank line."""
    k, n = h + 1, len(contents)
    last = h
    while k < n:
        fm = _FENCE.match(contents[k])
        if fm:
            j = k + 1
            while j < n and not contents[j].lstrip().startswith(fm.group(1)):
                j += 1
            for x in range(k, min(j + 1, n)):
                if contents[x].strip():
                    last = x
            k = j + 1
            continue
        hm = _HEADING.match(contents[k])
        if hm and len(hm.group(1)) <= 2:
            break
        if contents[k].strip():
            last = k
        k += 1
    return k, last


def _target_patterns(targets):
    """[(target, compiled)] matching each target as a whole path segment, so `auth.md` is not
    counted inside `oauth.md`."""
    out = []
    for t in targets:
        base = re.escape(Path(t).name)
        out.append((t, re.compile(r"(?<![\w.\-/])(?:[\w.\-]+/)*" + base + r"(?![\w\-]|\.\w)")))
    return out


def reference_units(text, targets):
    """One unit per occurrence of an excluded target."""
    lines, _ = split_lines(text)
    found = {}
    for t, pat in _target_patterns(targets):
        for idx, line in enumerate(lines, 1):
            for m in pat.finditer(line):
                found[(idx, m.start())] = (idx, m.start(), m.end())
    return [LX.Unit(l, a, l, b, False, "reference") for (l, a, b) in sorted(found.values())]


def enumerate_file(text, path, pass_kind, unit_rule, cfg, targets=(), v3=True):
    if pass_kind == "comment":
        matcher = LX.directive_matcher(cfg.get("directive_patterns") or ())
        return LX.comment_units(text, path, fine=(unit_rule == "comment-fine"), is_directive=matcher)
    if pass_kind == "document":
        return doc_units(text, unit_rule, v3)
    return reference_units(text, targets)


def enumerate_scope(sha, scope, pass_kind, unit_rule, cfg, targets=(), v3=True):
    """[(path, text, Unit, occurrence)] for the declared scope at `sha`. The occurrence index
    counts identical unit bodies of the whole file in enumeration order, before any range
    filter, so a narrowed scope numbers its units as the full file does. Raises Die on an
    unreadable or unsupported file: a file nobody can enumerate is never a silent zero."""
    out = []
    for path, rng in scope:
        text = git_show(sha, path)
        if text is None:
            _die(f"{path}: declared in scope but absent at {sha[:8]}")
        try:
            units = enumerate_file(text, path, pass_kind, unit_rule, cfg, targets, v3)
        except LX.UnsupportedLanguage as e:
            _die(f"{e}; narrow the scope or extend the lexer")
        lines = text.split("\n")
        for u, occ in zip(units, occurrences(lines, units, v3)):
            if rng and not (rng[0] <= u.sl <= rng[1]):
                continue
            out.append((path, text, u, occ))
    return out


# ------------------------------------------------------------------ facts (evidence, never a disposition)
# A fact is script-measured and checked like every script-owned field; the agent confirms it
# against the code before it supports a disposition (classify.md, "Facts").
_CAMEL = re.compile(r"\b(?:[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+|[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)\b")
_SNAKE = re.compile(r"\b_*[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
_DOTCALL = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+(?=\s*\()")
_BACKTICK = re.compile(r"`([A-Za-z_][\w.]*)(?:\(\))?`")
_ABSENCE_CLAIM = re.compile(r"identifier\s+`?([A-Za-z_][A-Za-z0-9_]*)`?\s+does not occur in the baseline tree", re.I)
_MARKER_HEAD = re.compile(r"^\s*(?:/\*+|\*+/?|//+|#+|--+|;+|%+|<!--|'|::|(?i:rem)\b)\s?")
_MARKER_TAIL = re.compile(r"\s*(?:\*+/|-->)\s*$")
_CODE_LINE = re.compile(r"[;{}]\s*$|^\s*[}\])]|^\s*[\w.$\[\]]+\s*(?:[-+*/%|&^]|<<|>>)?=(?!=)\s*\S"
                        r"|^\s*(?:return|import|const|let|var|function|class|if|for|while|else|try|catch|throw|new)\b"
                        r".*[(){}=;]|^\s*[\w.$]+\s*\(.*\)\s*;?\s*$")


def _fragment_res(cfg):
    pats = cfg.get("fragment_patterns")
    if not isinstance(pats, list) or not all(isinstance(p, str) for p in pats):
        _die(f"fragment_patterns must be a list of regular expressions, not {pats!r}")
    try:
        return [re.compile(p) for p in pats]
    except re.error as e:
        _die(f"fragment_patterns: {e}")


def code_identifiers(text):
    """Code-shaped names a comment or paragraph mentions, in order: backticked names, dotted
    calls (their last part), camelCase and snake_case words. Three characters or more."""
    found = [(m.start(), m.group(1).split(".")[-1]) for m in _BACKTICK.finditer(text)]
    found += [(m.start(), m.group(0).split(".")[-1]) for m in _DOTCALL.finditer(text)]
    found += [(m.start(), m.group(0)) for rx in (_CAMEL, _SNAKE) for m in rx.finditer(text)]
    out = []
    for _, w in sorted(found):
        if len(w) >= 3 and w not in out:
            out.append(w)
    return out


def code_absent(sha, idents, cfg):
    """The identifiers among `idents` that no code names at `sha`: one batched `git grep -w -F`,
    then every hit inside a comment, in a documentation file or in the record directory is
    discarded. A file the lexer cannot read counts every hit as code. At a full sha each
    identifier's answer is remembered (it depends on no other identifier: git grep tries each
    pattern on its own), and only the unknown ones are grepped."""
    idents = sorted(set(idents))
    if not idents:
        return set()
    if not _full(sha):
        return _code_absent(sha, idents, cfg)
    exts = json.dumps(cfg.get("document_exts"))

    def key(i):
        return ("absent", os.getcwd(), sha, exts, i)
    unknown = [i for i in idents if key(i) not in _MEMO]
    if unknown:
        gone = _code_absent(sha, unknown, cfg)
        for i in unknown:
            _MEMO[key(i)] = i in gone
    return {i for i in idents if _MEMO[key(i)]}


def _code_absent(sha, idents, cfg):
    import tempfile
    fd, pat = tempfile.mkstemp(suffix=".pat")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(("\n".join(idents) + "\n").encode("utf-8"))
        r = subprocess.run(["git", *_GIT_C, "grep", "-I", "-n", "--no-column", "-z", "-w", "-F", "-f", pat,
                            sha, "--", ".", f":(exclude){RECORD_DIR}"], capture_output=True)
    finally:
        os.unlink(pat)
    if r.returncode not in (0, 1):
        _die(f"git grep failed: {_decode_output(r.stderr).strip()}")
    hits = {}
    for row in decode(r.stdout).split("\n"):
        parts = row.split("\0")
        if len(parts) >= 3 and parts[1].isdigit():
            hits.setdefault(parts[0].partition(":")[2], []).append((int(parts[1]), "\0".join(parts[2:])))
    exts = tuple(e.lower() for e in cfg.get("document_exts") or [])
    word = {i: re.compile(r"(?<![A-Za-z0-9_])" + re.escape(i) + r"(?![A-Za-z0-9_])") for i in idents}
    present = set()
    for path, rows in sorted(hits.items()):
        if Path(path).suffix.lower() in exts:
            continue
        spans = None
        for ln, content in rows:
            for i in idents:
                if i in present or i not in content:
                    continue
                for m in word[i].finditer(content):
                    if spans is None:
                        spans = _comment_spans(sha, path)
                    if not _in_comment(spans, ln, m.start()):
                        present.add(i)
                        break
    return set(idents) - present


def _comment_spans(sha, path):
    """(line starts, comment spans) of a file at `sha`, or None when the lexer cannot read it;
    lexed once per full sha, path and directory (read only)."""
    if _full(sha):
        return _memo("spans", (sha, path), lambda: _comment_spans_of(sha, path))
    return _comment_spans_of(sha, path)


def _comment_spans_of(sha, path):
    text = git_show(sha, path) or ""
    try:
        _, s, _ = LX.scan(text, path)
    except LX.UnsupportedLanguage:
        return None
    starts = [0]
    for ln in text.split("\n"):
        starts.append(starts[-1] + len(ln) + 1)
    return starts, sorted((a, b) for a, b, _ in s.comments)


def _in_comment(spans, line, col):
    if spans is None or line - 1 >= len(spans[0]):
        return False
    off = spans[0][line - 1] + col
    return any(a <= off < b for a, b in spans[1])


def comment_body(text):
    """A comment's text with its markers stripped, line by line."""
    return "\n".join(_MARKER_TAIL.sub("", _MARKER_HEAD.sub("", ln)) for ln in text.split("\n")).strip("\n")


def code_like(body, path):
    """True when a comment's text reads as code in the file's language: a Python body parses
    to a statement that is more than a name or an annotation; any other body has at least half
    its lines shaped like statements."""
    lines = [l for l in body.split("\n") if l.strip()]
    if not lines:
        return False
    if LX.language_for(path) == "python":
        import ast
        import textwrap
        try:
            tree = ast.parse(textwrap.dedent("\n".join(lines)))
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            return False
        return any(not (isinstance(s, ast.AnnAssign) and s.value is None)
                   and not (isinstance(s, ast.Expr) and isinstance(s.value, (ast.Name, ast.Constant)))
                   for s in tree.body)
    return 2 * sum(1 for l in lines if _CODE_LINE.search(l)) >= len(lines)


def _fact_text(s):
    """A fact value as the record carries it: one line, no list separators, non-UTF-8 bytes
    escaped as the preview's are."""
    s = re.sub(r"[\s,;]+", " ", s).strip()
    return encode(s).decode("utf-8", "backslashreplace")


# step-narration openers (S5): a first body line that begins with one of these verbs narrates
# the step the code below already shows
NARRATION_VERBS = ("call", "create", "set", "get", "check", "load", "save", "return", "then", "now",
                   "iterate", "loop", "parse", "print", "write", "read", "open", "close", "init",
                   "fetch", "send", "update", "delete", "remove", "add", "use")
_NARRATION_RE = re.compile(r"(?i)^(?:" + "|".join(NARRATION_VERBS) + r")\b")
_TODO_RE = re.compile(r"(?i)\b(?:TODO|FIXME|XXX|HACK)\b")


def unit_facts(text, path, kind, cfg, absent):
    """The `facts:` value of one unit, from its text at the baseline: `fragment=` matches of
    fragment_patterns, `absent=` code-shaped names no code names, `code-like`, `separator`,
    `long=N` at five lines and up, `narration` and `todo` in a comment pass. `dup-of=` is
    cross-unit and is added by `stubs_for`."""
    out = []
    frags = []
    for rx in _fragment_res(cfg):
        for m in rx.finditer(text):
            f = _fact_text(m.group(0))
            if f and f not in frags:
                frags.append(f)
    if frags:
        out.append("fragment=" + ",".join(frags))
    gone = [i for i in code_identifiers(text) if i in absent]
    if gone:
        out.append("absent=" + ",".join(gone))
    body = comment_body(text) if kind == "comment" else text
    if kind == "comment" and code_like(body, path):
        out.append("code-like")
    if not re.search(r"\w", body):
        out.append("separator")
    n = len(text.split("\n"))
    if n >= 5:
        out.append(f"long={n}")
    if kind == "comment":
        first = next((ln for ln in body.split("\n") if ln.strip()), "")
        if _NARRATION_RE.match(first.lstrip()):
            out.append("narration")
        if _TODO_RE.search(text):
            out.append("todo")
    return "; ".join(out)


def _span_text(lines, u):
    if u.sl == u.el:
        return lines[u.sl - 1][u.sc:u.ec]
    return "\n".join([lines[u.sl - 1][u.sc:]] + lines[u.sl:u.el - 1] + [lines[u.el - 1][:u.ec]])


_STUB_MEMO = {}


def stubs_for(sha, header, cfg):
    """The script-owned stubs of a record header at `sha`. Memoized per process (the gates
    enumerate the same scope several times); callers get their own copies."""
    import copy
    scope = parse_scope(header.get("scope"))
    targets = [t.strip() for t in header.get("targets", "").split(",") if t.strip()]
    key = (os.getcwd(), sha, header.get("scope"), header["pass_kind"], header["unit_rule"], tuple(targets),
           tuple(cfg.get("directive_patterns") or ()), record_v3(Record(header)),
           json.dumps(cfg.get("fragment_patterns")), json.dumps(cfg.get("document_exts")))
    if key in _STUB_MEMO:
        return copy.deepcopy(_STUB_MEMO[key])
    out, texts = [], []
    split = {}
    v3 = record_v3(Record(header))
    for k, (path, text, u, occ) in enumerate(enumerate_scope(sha, scope, header["pass_kind"], header["unit_rule"],
                                                              cfg, targets, v3=v3), 1):
        lines = split.setdefault(path, text.split("\n"))
        # rstrip after the slice: the 70-char window can end in whitespace, and the record's
        # parse strips trailing whitespace (D4) — an honest preview must never depend on it
        prev = lines[u.sl - 1][u.sc:].strip()[:70].rstrip() if u.sl <= len(lines) else ""
        # bytes that are not UTF-8 (a cp1252 file) show as `\xe8`: git re-encodes a commit
        # message that is not UTF-8, so a raw byte would not survive the record's round trip
        prev = encode(prev).decode("utf-8", "backslashreplace")
        stub = {"id": str(k), "file": path, "lines": f"{u.sl}-{u.el}", "span": u.span(),
                "fingerprint": fingerprint(path, text, u.sl, u.el, occ, lines), "preview": prev}
        if u.kind == "tbc":
            stub["in_tbc"] = "yes"
        out.append(stub)
        texts.append((_span_text(lines, u), path))
    if record_v3(Record(header)) and header["pass_kind"] != "severance":
        absent = code_absent(sha, [i for t, _ in texts for i in code_identifiers(t)], cfg)
        twins = {}
        for stub, (t, path) in zip(out, texts):
            f = unit_facts(t, path, header["pass_kind"], cfg, absent)
            if f:
                stub["facts"] = f
            twins.setdefault((path, _norm(t)), []).append(stub["id"])
        # `dup-of=` is cross-unit (unit_facts sees one unit only): the ids of the other units of
        # the same file with an equal normalized body, ascending
        for stub, (t, path) in zip(out, texts):
            dup = [i for i in twins[(path, _norm(t))] if i != stub["id"]]
            if dup:
                stub["facts"] = (stub["facts"] + "; " if stub.get("facts") else "") + \
                                "dup-of=" + ",".join(sorted(dup, key=int))
    _STUB_MEMO[key] = copy.deepcopy(out)
    return out


# ------------------------------------------------------------------ record v3
class Record:
    def __init__(self, header=None, units=None, comments=None):
        self.header = header or {}
        self.units = units or []
        self.comments = comments or []
        self.problems = []


_KNOWN_UNIT = set(SCRIPT_FIELDS) | set(JUDGEMENT_FIELDS) | {"id"}


def parse_record_text(text):
    """Strict parse (D4): anything the writer would not have produced — a stray continuation
    line, an unknown key, a blank line inside a multi-line block, an unparseable line — is a
    problem the record checks report, never a silently dropped value."""
    rec = Record()
    cur = None
    ml_key = None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()   # the terminating newline, not a blank record line
    for raw in lines:
        line = raw.rstrip("\r")
        if line.startswith("@@unit"):
            cur = {"id": line[6:].strip()}
            rec.units.append(cur)
            ml_key = None
            continue
        if ml_key:
            if line.startswith("|"):
                # trailing whitespace is dropped (D4): git's commit-message cleanup strips it, so
                # the record must not depend on it — a Markdown hard break is written as `\`
                cur[ml_key].append((line[2:] if line.startswith("| ") else line[1:]).rstrip())
                continue
            if not line.strip():
                rec.problems.append(f"unit {cur.get('id')}: a blank line ends the {ml_key}: block early; "
                                    f"an empty line inside a block is written as a lone '|'")
                ml_key = None
                continue
        if line.startswith("|"):
            rec.problems.append(f"a continuation line ('| …') outside any block: {line[:50]!r}")
            continue
        ml_key = None
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            rec.problems.append(f"unparseable record line: {line[:60]!r}")
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if cur is None:
            if k in rec.header and k != "shard":
                rec.problems.append(f"header key {k!r} appears twice")
            rec.header[k] = v
            if k not in _KNOWN_HEADER:
                rec.problems.append(f"unknown header key {k!r}")
        elif k in MULTILINE and v == "":
            cur[k] = []
            ml_key = k
        else:
            cur[k] = v
            if k not in _KNOWN_UNIT:
                rec.problems.append(f"unit {cur.get('id')}: unknown key {k!r}")
    for u in rec.units:
        for k in MULTILINE:
            if isinstance(u.get(k), list):
                u[k] = "\n".join(u[k])
    return rec


def parse_record(path):
    # an editor may save the record with a BOM; it is not part of the first header key
    return parse_record_text(decode(Path(user_path(path)).read_bytes()).lstrip("﻿"))


_HEADER_ORDER = ("record_version", "unit_id", "batch_master", "batch", "baseline_sha", "pass_kind", "unit_rule",
                 "scope", "targets", "narrowing_reason", "floor", "floor_observed", "config_sha", "last_verified_at")
_KNOWN_HEADER = set(_HEADER_ORDER) | {"shard"}


def render_record(rec, guide=True):
    out = ["# consolidation record v3",
           "# Script-owned (any change fails record-check): the header, and @@unit id, file, lines, span,",
           "# fingerprint, preview, in_tbc, facts. Judgement fields: disposition, basis, and where the disposition",
           "# needs them edit / claims (multi-line, each line prefixed '| '), ruling, tbc, of, conflicts, escalate,",
           "# and adr or adr_title + adr_text (multi-line)."] if guide else []
    keys = [k for k in _HEADER_ORDER if k in rec.header] + [k for k in rec.header if k not in _HEADER_ORDER]
    out += [f"{k}: {rec.header[k]}" for k in keys]
    for u in rec.units:
        out.append(f"@@unit {u['id']}")
        for k in SCRIPT_FIELDS:
            if k in u:
                out.append(f"{k}: {u[k]}")
        for k in JUDGEMENT_FIELDS:
            v = u.get(k)
            if k in ("disposition", "basis"):
                out.append(f"{k}: {v or ''}")
            elif k in MULTILINE and v is not None:
                out.append(f"{k}:")
                out += [("| " + l) if l else "|" for l in v.split("\n")]
            elif v:
                out.append(f"{k}: {v}")
    return "\n".join(out) + "\n"


def write_record(rec, path):
    Path(user_path(path)).parent.mkdir(parents=True, exist_ok=True)
    Path(user_path(path)).write_bytes(encode(render_record(rec)))


def _commit_record_text(body):
    """A commit message's embedded record: the text between its begin and end markers. Both begin
    markers parse — commits written before the v3 wording carry the v2 marker in their messages,
    and the history walk reads them for as long as the repo lives."""
    begin = next((m for m in (RECORD_BEGIN, RECORD_BEGIN_V2) if m in body), None)
    if begin is None:
        return None
    return body.split(begin, 1)[1].split(RECORD_END, 1)[0].strip("\n")


_COMMIT_RECORDS = {}


def record_from_commit(sha):
    """The record a commit's message materializes. Parsed once per commit and process: the unit
    gate's checks each load it."""
    import copy
    full = sha if _full(sha) else git("rev-parse", sha).strip()
    key = (os.getcwd(), full)
    if key not in _COMMIT_RECORDS:
        text = _commit_record_text(commit_message_of(full))
        if text is None:
            _die(f"commit {full[:8]} carries no materialized record")
        _COMMIT_RECORDS[key] = parse_record_text(text)
    return copy.deepcopy(_COMMIT_RECORDS[key])


def load_record(args):
    if getattr(args, "record_from_commit", None):
        rec = record_from_commit(args.record_from_commit)
    elif getattr(args, "record", None):
        rec = parse_record(args.record)
        require_current(rec, show_path(args.record))
    elif getattr(args, "batch", None):
        rec = load_master(args.batch)[1]
    else:
        _die("give --record PATH or --record-from-commit SHA")
    missing = [f for f in REQUIRED_HEADER if not rec.header.get(f, "").strip()]
    if missing:
        _die(f"the record header lacks {missing}; a gate never judges a record it cannot read (D4)")
    return rec


def ulines(u):
    a, _, b = u["lines"].partition("-")
    return int(a), int(b or a)


def uspan(u):
    m = re.match(r"(\d+):(\d+)-(\d+):(\d+)$", u.get("span", ""))
    if not m:
        raise ValueError(f"bad span {u.get('span')!r}")
    return tuple(int(x) for x in m.groups())


def unit_number(uid, where):
    """The number a unit id orders by. record-init numbers the stubs and the id is script-owned:
    a hand-edited one is refused, never sorted around."""
    if not re.fullmatch(r"[1-9][0-9]*", uid):
        _die(f"unit {uid!r} of {where}: a unit id is the number record-init wrote (script-owned); "
             f"restore it from the enumeration")
    return int(uid)


# ------------------------------------------------------------------ intake
def intake_path(cfg, override=None):
    return Path(override or cfg.get("intake_path") or os.path.expanduser("~/.claude/escalations.md"))


def _lock_still_stale(lock, st):
    """True when the lock file on disk is still the one `st` was taken of (same mtime and size),
    so the stale-lock unlink may proceed. False when it is gone or has changed: another waiter
    won the O_CREAT|O_EXCL race in between, and deleting its fresh lock would strand the holder
    with a lock it can never release."""
    try:
        now = lock.stat()
    except OSError:
        return False
    return (now.st_mtime, now.st_size) == (st.st_mtime, st.st_size)


@contextmanager
def intake_lock(path, timeout=30.0):
    """Exclusive lock around a read-modify-write of the intake, which parallel sessions share."""
    lock = Path(str(path) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                st = lock.stat()
                if time.time() - st.st_mtime > 120 and _lock_still_stale(lock, st):
                    lock.unlink()   # a FileNotFoundError here is another waiter's win: retry
                    continue
            except OSError:
                pass
            if time.time() - t0 > timeout:
                _die(f"intake is locked by another session ({lock}); retry, or remove a stale lock")
            time.sleep(0.1)
    try:
        yield
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


_INTAKE_RE = re.compile(r"^- (?P<date>\S+) `(?P<ref>[^`]+)` — (?P<body>.*?)(?: \[(?P<fields>[a-z]+=[^\]]*)\])?$")
_FIELD_ORDER = ("kind", "state", "observed", "fingerprint", "context", "ruling", "id", "occurrences", "latest",
                "tbc", "applied")


def parse_intake_line(line):
    m = _INTAKE_RE.match(line.rstrip())
    if not m:
        return None
    fields = {}
    for tok in (m.group("fields") or "").split():
        k, _, v = tok.partition("=")
        fields[k] = v
    return {"date": m.group("date"), "ref": m.group("ref"), "body": m.group("body"), "fields": fields,
            "raw": line.rstrip()}


def render_intake(e):
    known = " ".join(f"{k}={e['fields'][k]}" for k in _FIELD_ORDER if e["fields"].get(k))
    extra = " ".join(k if v == "" else f"{k}={v}" for k, v in e["fields"].items() if k not in _FIELD_ORDER)
    tail = " ".join(x for x in (known, extra) if x)
    return f"- {e['date']} `{e['ref']}` — {e['body']}" + (f" [{tail}]" if tail else "")


def read_intake(path):
    return decode(path.read_bytes()).split("\n") if path.exists() else []


def write_intake(path, lines):
    while lines and lines[-1] == "":
        lines.pop()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode("\n".join(lines) + "\n"))


_INTAKE_PARSED = {}


def find_intake(lines, ref=None, fp=None, ident=None):
    """The intake entry a lookup names: by id, else by fingerprint, else by ref. An entry its
    application closed (`applied`) answers only when no live entry matches — a closed entry
    never answers a new question about a twin of its unit (ADR 0014)."""
    import copy
    closed = (None, None)
    for i, raw in enumerate(lines):
        if raw not in _INTAKE_PARSED:   # a line parses the same every time: parsed once, handed out as a copy
            if len(_INTAKE_PARSED) > 20000:
                _INTAKE_PARSED.clear()
            _INTAKE_PARSED[raw] = parse_intake_line(raw)
        e = _INTAKE_PARSED[raw]
        if e is None:
            continue
        if ident:
            if e["fields"].get("id") == ident:
                return i, copy.deepcopy(e)
            continue
        seen = e["fields"].get("fingerprint")
        if not (seen == fp if fp and seen else ref and e["ref"] == ref):
            continue
        if e["fields"].get("state") != "applied":
            return i, copy.deepcopy(e)
        if closed[1] is None:
            closed = (i, e)
    return (closed[0], copy.deepcopy(closed[1]))


# ------------------------------------------------------------------ apply engine
def _indent_of(s):
    return s[:len(s) - len(s.lstrip())]


def plan_ops(units, pass_kind):
    """[(unit, op, edit_lines)] with op in remove / replace / keep / tbc / sever."""
    ops = []
    for u in units:
        d = _norm(u.get("disposition"))
        edit = u.get("edit")
        if pass_kind == "severance":
            if d == _norm(SEV) and edit is not None:
                ops.append((u, "sever", edit.split("\n") if edit else []))
            continue
        if d in FROZEN or d == _norm(STILL) or not d:
            if pass_kind == "document" and d == _norm(NV) and u.get("in_tbc") != "yes" and u.get("tbc"):
                ops.append((u, "tbc", [u["tbc"]]))
            continue
        if d == _norm(REGEN) and edit:
            # B1: a partial regenerable keeps a subset of the unit's whole lines
            ops.append((u, "keep", edit.split("\n")))
        elif d in REMOVED_WHOLE or (d in (_norm(OBS), _norm(RULED)) and not edit):
            ops.append((u, "remove", []))
        elif d in EDIT_ALLOWED:
            ops.append((u, "replace", edit.split("\n") if edit else []))
    return ops


def tbc_item_body(t):
    """The text of a `## To be confirmed` item: one list marker stripped, never a leading '-'
    or '*' that belongs to the text (`-1 is returned`, `**Owner** must…`)."""
    return re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", t.strip()).strip()


def tbc_key(t):
    """The content key binding an item to the entry of the paragraph that raised it (S65)."""
    return hashlib.sha1(_norm(tbc_item_body(t)).encode("utf-8", "surrogateescape")).hexdigest()[:8]


def open_fence_at_end(text):
    """True when the document ends inside an unclosed code fence: an item appended there would
    be code, invisible to the next pass."""
    contents, _ = split_lines(text)
    k, n = 0, len(contents)
    while k < n:
        fm = _FENCE.match(contents[k].lstrip("﻿") if k == 0 else contents[k])
        if fm:
            j = k + 1
            while j < n and not contents[j].lstrip().startswith(fm.group(1)):
                j += 1
            if j >= n:
                return True
            k = j + 1
            continue
        k += 1
    return False


def apply_file(text, ops, pass_kind):
    """Apply one file's operations to its baseline text. Deterministic: replay-check re-runs it."""
    contents, eols = split_lines(text)
    default_eol = "\r\n" if "\r\n" in text else "\n"
    bom = contents[0].startswith("﻿") if contents else False
    tbc_items = []
    sever_lines = {}
    edits = []
    for u, op, new in ops:
        if op == "tbc":
            tbc_items.extend(new)
        elif op == "sever":
            sever_lines.setdefault(ulines(u)[0], []).append(new)
        else:
            edits.append((uspan(u), op, new))
    for line_no in sorted(sever_lines, reverse=True):
        new = sever_lines[line_no][0]
        idx = line_no - 1
        if new:
            contents[idx] = new[0]
            if bom and idx == 0 and not contents[0].startswith("﻿"):
                contents[0] = "﻿" + contents[0]   # a severed line 1 keeps the BOM
        else:
            del contents[idx]
            del eols[idx]
    for (sl, sc, el, ec), op, new in sorted(edits, key=lambda e: (e[0][0], e[0][1]), reverse=True):
        s0, e0 = sl - 1, el - 1
        before = contents[s0][:sc]
        after = contents[e0][ec:]
        # a leading BOM is not text before the unit: str.strip() keeps U+FEFF; re-added below
        whole = before.lstrip("﻿").strip() == "" and after.strip() == ""
        eol = eols[e0] if e0 < len(eols) else default_eol
        if op == "keep" and whole:
            # B1: the kept lines are the file's own, matched as record-check matched them, and
            # go back byte for byte — their indentation and endings, never the edit's
            kept, pos = [], s0
            for x in new:
                hit = next((i for i in range(pos, e0 + 1) if contents[i].lstrip("﻿").strip() == x.strip()), None)
                if hit is None:
                    break
                kept.append(hit)
                pos = hit + 1
            if kept and len(kept) == len(new):
                ke = [eols[i] if i < len(eols) else default_eol for i in kept]
                if eol == "":
                    ke[-1] = ""   # the unit ended the file without a newline: so does what is kept
                contents[s0:e0 + 1] = [contents[i] for i in kept]
                eols[s0:e0 + 1] = ke
                if bom and s0 == 0 and contents and not contents[0].startswith("﻿"):
                    contents[0] = "﻿" + contents[0]
                continue
        if op == "keep":
            op = "replace"
        if op == "replace" and new and any(x.strip() for x in new):
            if whole:
                ind = before.lstrip("﻿") if pass_kind == "comment" else ""
                repl = [(ind + x) if x.strip() else "" for x in new]
            else:
                repl = [before + new[0] + after]
            contents[s0:e0 + 1] = repl
            eols[s0:e0 + 1] = [(eols[s0] if s0 < len(eols) else default_eol) or default_eol] * (len(repl) - 1) + [eol]
            if bom and s0 == 0 and contents and not contents[0].startswith("﻿"):
                contents[0] = "﻿" + contents[0]   # D3: a replace on line 1 keeps the BOM
            continue
        if whole:
            del contents[s0:e0 + 1]
            del eols[s0:e0 + 1]
            i = s0
            if 0 < i < len(contents) and contents[i - 1].strip() == "" and contents[i].strip() == "":
                del contents[i]; del eols[i]
            elif i == 0 and contents and contents[0].strip() in ("", "﻿"):
                del contents[0]; del eols[0]
            elif i == len(contents) and i > 0 and contents[i - 1].strip() == "":
                del contents[i - 1]; del eols[i - 1]
            if bom and s0 == 0 and contents and not contents[0].startswith("﻿"):
                contents[0] = "﻿" + contents[0]
        elif sl == el:
            if after.strip() == "":
                contents[s0] = before.rstrip()
            elif before.strip() == "":
                contents[s0] = before + after.lstrip()
            else:
                contents[s0] = before.rstrip() + " " + after.lstrip()
        else:
            if before.strip() and after.strip():
                repl = [before.rstrip(), _indent_of(contents[s0]) + after.lstrip()]
            elif before.strip():
                repl = [before.rstrip()]
            else:
                repl = [before + after.lstrip()]
            contents[s0:e0 + 1] = repl
            eols[s0:e0 + 1] = [eols[s0]] * (len(repl) - 1) + [eol]
    if tbc_items:
        items, seen = [], set()
        for t in tbc_items:
            body = tbc_item_body(t)
            if body and _norm(body) not in seen:   # E1: a repeated pass adds no duplicate item
                seen.add(_norm(body))
                items.append("- " + body)
        h = _tbc_heading_index(contents)
        if h is None:
            if eols and eols[-1] == "":
                eols[-1] = default_eol
            while contents and contents[-1].strip() == "":
                contents.pop(); eols.pop()
            add = ["", "## To be confirmed", ""] + items
            contents += add
            eols += [default_eol] * len(add)
        else:
            k, last = _tbc_section_end(contents, h)
            have = {_norm(m.group(1)) for c in contents[h + 1:k]
                    for m in [re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$", c)] if m}
            items = [i for i in items if _norm(i[2:]) not in have]   # E1: the section already holds it
            if items:
                pos = last + 1
                if pos > 0 and eols[pos - 1:pos] == [""]:
                    eols[pos - 1] = default_eol   # D2: an item inserted at EOF starts on a new line
                add = ([""] if last == h else []) + items
                contents[pos:pos] = add
                eols[pos:pos] = [default_eol] * len(add)
    return join_lines(contents, eols)


def expected_texts(rec, sha=None):
    """{path: (baseline_text, expected_text)} for every file in the record's scope, with the
    `last-verified-at` front matter the record's header names (S98)."""
    sha = sha or rec.header["baseline_sha"]
    lva_sha, lva_files = lva_spec(rec)
    by_file = {}
    for u in rec.units:
        by_file.setdefault(u["file"], []).append(u)
    out = {}
    for path, _ in parse_scope(rec.header.get("scope")):
        if path in out:
            continue
        base = git_show(sha, path)
        if base is None:
            _die(f"{path}: absent at baseline {sha[:8]}")
        new = apply_file(base, plan_ops(by_file.get(path, []), rec.header["pass_kind"]), rec.header["pass_kind"])
        out[path] = (base, set_lva(new, lva_sha) if path in lva_files else new)
    return out


def _scope_overlap_problems(scope):
    """A file is declared once, with one range or none: two entries for one path — duplicate or
    overlapping — make one unit carry two dispositions, and only the applied one is seen (A5)."""
    probs = []
    seen = {}
    for p, rng in scope:
        if p in seen:
            probs.append(f"{p}: declared twice in the scope; a file appears once, with one range or none")
        seen.setdefault(p, []).append(rng)
    for p, rngs in seen.items():
        ranged = [r for r in rngs if r]
        if len(rngs) > 1 and len(ranged) < len(rngs):
            probs.append(f"{p}: declared both whole and as a range in the scope")
        for i, a in enumerate(ranged):
            for b in ranged[i + 1:]:
                if a[0] <= b[1] and b[0] <= a[1]:
                    probs.append(f"{p}: overlapping ranges {sorted(ranged)} in the scope")
    return probs


def _scope_type_problems(scope, kind, cfg):
    """A document or severance pass owns documentation files only: prose units and reference
    occurrences are not code-invariant, so a code file in such a scope skips every proof the
    comment passes rely on (A3)."""
    if kind not in ("document", "severance"):
        return []
    exts = tuple(e.lower() for e in cfg.get("document_exts") or [])
    return [f"{p}: a {kind} pass covers documentation files {list(exts)}; this is not one — "
            f"narrow the scope or run a comment pass" for p, _ in scope
            if Path(p).suffix.lower() not in exts]


# ------------------------------------------------------------------ record validation
def _words(s):
    return re.findall(r"\w+", s.lower())


def _is_subsequence(small, big):
    it = iter(big)
    return all(w in it for w in small)


_SPLITS = {}


def _split_once(text):
    """text.split("\n"), shared by every unit of one file (read only): a few recent texts by
    identity, each held so its id cannot be reused."""
    got = _SPLITS.get(id(text))
    if got is None or got[0] is not text:
        if len(_SPLITS) >= 16:
            _SPLITS.clear()
        got = _SPLITS[id(text)] = (text, text.split("\n"))
    return got[1]


def _unit_text(base_text, u):
    sl, sc, el, ec = uspan(u)
    lines = _split_once(base_text)
    if sl == el:
        return lines[sl - 1][sc:ec]
    return "\n".join([lines[sl - 1][sc:]] + lines[sl:el - 1] + [lines[el - 1][:ec]])


def identity_problems(rec, cfg):
    """C1: the record's stubs must equal a fresh enumeration at the baseline, field for field.
    A count is not enough: one omission plus one duplicate has the right count."""
    h = rec.header
    try:
        expected = stubs_for(h["baseline_sha"], h, cfg)
    except Die as e:
        return [str(e)]
    probs = []
    got = {u.get("id"): u for u in rec.units}
    if len(got) != len(rec.units):
        probs.append("duplicate @@unit ids")
    spans = set()
    for u in rec.units:
        key = (u.get("file"), u.get("span"))
        if key in spans:
            probs.append(f"two units share the span {u.get('file')}:{u.get('span')}")
        spans.add(key)
    exp_ids = {s["id"] for s in expected}
    for s in expected:
        u = got.get(s["id"])
        if u is None:
            probs.append(f"unit {s['id']} ({s['file']}:{s['lines']}) is missing from the record")
            continue
        for k in ("file", "lines", "span", "fingerprint", "preview") + (("facts",) if record_v3(rec) else ()):
            if (u.get(k) or "") != (s.get(k) or ""):
                probs.append(f"unit {s['id']}: script-owned field {k!r} is {u.get(k)!r}, enumeration says {s.get(k)!r}")
        if (u.get("in_tbc") == "yes") != (s.get("in_tbc") == "yes"):
            probs.append(f"unit {s['id']}: script-owned field 'in_tbc' differs from the enumeration")
    for uid in got:
        if uid not in exp_ids:
            probs.append(f"unit {uid}: not a unit of the declared scope at the baseline")
    return probs


def _sha_resolves(sha):
    # only a full sha that resolves is remembered: an abbreviated one can turn ambiguous later
    key = ("resolves", os.getcwd(), sha)
    if key in _MEMO:
        return True
    ok = subprocess.run(["git", *_GIT_C, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
                        capture_output=True).returncode == 0
    if ok and _full(sha):
        _MEMO[key] = True
    return ok


def _intake_inside_repo(ipath):
    root = repo_root()
    if not root:
        return False
    try:
        return Path(root).resolve() in Path(ipath).resolve().parents
    except OSError:
        return False


def _ruling_sha_problem(where, ruling, rsha, ipath):
    """The ruling sha must name a commit here — checked when the intake lives inside the repo,
    the only place its shas are this repo's (owner-approved deviation 3)."""
    if re.fullmatch(r"[0-9a-f]{7,40}", rsha or "") and _intake_inside_repo(ipath) and not _sha_resolves(rsha):
        return [f"{where}: ruling {ruling!r} was recorded at sha {rsha!r}, which is no commit here"]
    return []


# The marker only `escalate --rule` writes; `units=` carries the digest of the covered list.
_RULED_MARK = re.compile(r" — RULED \d{4}-\d{2}-\d{2} \(owner(?:, units=(?P<digest>[0-9a-f]{8}))?\): ")


def _units_digest(own_fp, covered):
    """Binds an entry's explicit unit list to the entry: a `units=` added or extended by hand
    no longer matches the digest the panel flow wrote (R-gates 3)."""
    return hashlib.sha1(((own_fp or "") + "\n" + ",".join(sorted(covered))).encode()).hexdigest()[:8]


def parse_applied(field):
    """{(fingerprint, unit_id, baseline7)} from an entry's `applied=fp:U-3@abc1234,…`."""
    out = set()
    for tok in (field or "").split(","):
        m = re.fullmatch(r"([0-9a-f]{8}):([A-Za-z0-9._-]+)@([0-9a-f]{7,40})", tok)
        if m:
            out.add((m.group(1), m.group(2), m.group(3)[:7]))
    return out


def _ruling_binding_problems(u, ruling, ipath, intake, ctx=None):
    """A `ruling:` must cite an intake entry that is this unit's own: an owner ruling — a
    suspected-defect or unverifiable-statement entry in state `ruled`, carrying the marker
    `escalate --rule` writes — bound to the unit by fingerprint, by reference (file, and line
    inside the unit), or by the entry's digest-bound unit list. A ruling on another unit, a
    consumed obsolete-citation event, an entry minted `ruled` or a forged standing ruling
    authorizes nothing (A1, R-gates 1–3). A ruling binds once: the unit that applied it is
    written on the entry (`applied=`), and a later unit that inherits the same fingerprint — an
    identical comment whose occurrence index shifted — is refused (ADR 0014). A `## To be
    confirmed` item binds to the entry of the paragraph that raised it, by its text (S65).
    `ctx`: {"unit_id", "baseline"} of the record, and "text" — the unit's file at the baseline."""
    ctx = ctx or {}
    where = f"unit {u['id']} ({u['file']}:{u['lines']})"
    d = _norm(u.get("disposition"))
    if d == _norm(COND):
        _, e = find_intake(intake, ident=ruling)
        if not e or e["fields"].get("kind") != "standing-ruling" or e["fields"].get("state") != "ruled":
            return [f"{where}: ruling {ruling!r} is not a ruled standing ruling in the intake"]
        probs = []
        want = "SR-" + hashlib.sha1(_norm(e["body"]).encode()).hexdigest()[:8]
        if e["fields"].get("id") != want:
            probs.append(f"{where}: standing ruling {ruling!r} fails its id check (the id must be "
                         f"SR- + sha1 of the ruling text); record it with `escalate --standing`")
        return probs + _ruling_sha_problem(where, ruling, e["fields"].get("ruling"), ipath)
    _, e = find_intake(intake, ref=ruling, fp=ruling if re.fullmatch(r"[0-9a-f]{8}", ruling) else None)
    state = e["fields"].get("state") if e else None
    item_key = (tbc_key(_unit_text(ctx["text"], u)) if u.get("in_tbc") == "yes" and ctx.get("text") is not None
                else None)
    as_item = bool(e and item_key and e["fields"].get("tbc") == item_key
                   and state in ("ruled", "ruled-external", "applied"))
    applied = parse_applied(e["fields"].get("applied")) if e else set()
    me = (u.get("fingerprint"), ctx.get("unit_id"), (ctx.get("baseline") or "")[:7])
    if e and not as_item:
        by = [a for a in applied if a[0] == u.get("fingerprint")]
        if by and me not in applied:
            return [f"{where}: ruling {ruling!r} was already applied to a unit with this fingerprint by "
                    f"{by[0][1]} at {by[0][2]}; a ruling binds once — escalate this unit afresh"]
        if state == "applied" and me not in applied:
            return [f"{where}: ruling {ruling!r} is applied and closed (state applied)"]
    if not e or (state not in ("ruled", "applied") and not as_item):
        return [f"{where}: ruling {ruling!r} names no intake entry in state ruled"]
    kind = e["fields"].get("kind")
    if kind == "obsolete-citation":
        return [f"{where}: ruling {ruling!r} cites a consumed obsolete-citation event, not an owner "
                f"ruling on this unit"]
    if kind == "standing-ruling":
        return [f"{where}: a standing ruling authorizes {canon(COND)!r} only; cite a ruling on this unit"]
    if kind not in RULABLE_KINDS:
        return [f"{where}: ruling {ruling!r} cites an entry of kind {kind!r}; only an owner ruling on a "
                f"{' or '.join(RULABLE_KINDS)} entry authorizes {canon(RULED)!r}"]
    mark = _RULED_MARK.search(e["body"])
    if not mark:
        return [f"{where}: ruling {ruling!r} cites an entry with no owner ruling on it — an entry "
                f"is ruled only by `escalate --rule` on the owner's answer"]
    probs = _ruling_sha_problem(where, ruling, e["fields"].get("ruling"), ipath)
    a, b = ulines(u)
    ref = e["ref"].split("#", 1)[0]
    rfile, _, rline = ref.partition(":")
    if as_item:
        if rfile != u["file"]:
            probs.append(f"{where}: ruling {ruling!r} raised an item of {e['ref']!r}, not of this unit's file")
        return probs
    efp = e["fields"].get("fingerprint")
    covered = {x for x in (e["fields"].get("units") or "").split(",") if x}
    if (covered or mark.group("digest")) and mark.group("digest") != _units_digest(efp, covered):
        return probs + [f"{where}: ruling {ruling!r} carries a unit list its ruling marker does not "
                        f"bind — the list is written by `escalate --rule --also-fingerprint` only"]
    # E8: a ruling that directs edits beyond its own unit (a True ruling writing the sentence into
    # the body) names every unit it covers, all in the entry's own file.
    if u.get("fingerprint") in covered:
        if rfile != u["file"]:
            probs.append(f"{where}: ruling {ruling!r} lists this unit, but the entry is of {e['ref']!r}; "
                         f"a ruling covers units of its own file only")
        return probs
    if rfile != u["file"]:
        probs.append(f"{where}: ruling {ruling!r} cites an entry of {e['ref']!r}, not of this unit's file")
    elif efp and efp != u.get("fingerprint"):
        probs.append(f"{where}: ruling {ruling!r} cites an entry fingerprinted {efp!r}; this unit "
                     f"is {u.get('fingerprint')!r}")
    elif not efp and (not rline or not (a <= int(rline) <= b)):
        # Without a content key the entry cannot follow its text, so the reference itself must
        # point inside the unit; a fingerprinted entry binds by content wherever the text moved.
        probs.append(f"{where}: ruling {ruling!r} cites {e['ref']!r}, which is not inside the unit's "
                     f"lines {a}-{b} and carries no matching fingerprint")
    return probs


def record_problems(rec, cfg, check_intake=True, check_identity=True):
    h = rec.header
    probs = list(getattr(rec, "problems", []))
    for f in REQUIRED_HEADER:
        if not h.get(f, "").strip():
            probs.append(f"header: missing field {f!r} (S137)")
    if probs:
        return probs
    kind = h["pass_kind"]
    if kind not in ADMISSIBLE:
        return [f"header: pass_kind {kind!r} is not one of {list(ADMISSIBLE)}"]
    if h["unit_rule"] not in UNIT_RULES[kind]:
        probs.append(f"header: unit_rule {h['unit_rule']!r} is not a rule of a {kind} pass {UNIT_RULES[kind]}")
    probs += _scope_type_problems(parse_scope(h.get("scope")), kind, cfg)
    probs += _scope_overlap_problems(parse_scope(h.get("scope")))
    if "config_sha" not in h:
        probs.append("header: missing config_sha — the record binds the config it was built on")
    elif h["config_sha"] not in (cfg.get("_config_sha"), cfg.get("_config_sha_legacy")):
        probs.append(f"header: config_sha {h['config_sha']!r} does not match the config in force "
                     f"({cfg.get('_config_sha')!r}); the record was built on a different config")
    if kind == "severance" and not h.get("targets"):
        probs.append("header: a severance record names its excluded targets")
    probs += _lva_problems(rec, cfg)
    if not rec.units:
        probs.append("record carries no entries (S84)")
    if check_identity and not probs:
        probs += identity_problems(rec, cfg)
    if probs:
        return probs
    admissible = {_norm(d) for d in ADMISSIBLE[kind]}
    ipath = intake_path(cfg)
    intake = read_intake(ipath) if check_intake else None
    base_texts = {}
    v3 = record_v3(rec)
    for u in rec.units:
        where = f"unit {u['id']} ({u['file']}:{u['lines']})"
        d = _norm(u.get("disposition"))
        if not d:
            probs.append(f"{where}: no disposition (S53)")
            continue
        if d not in admissible:
            extra = "; the regenerability test is scoped to comments (S46)" if d == _norm(REGEN) else ""
            probs.append(f"{where}: {u.get('disposition')!r} is not a disposition of a {kind} pass{extra}")
            continue
        if d in EVIDENCE and not (u.get("basis") or "").strip():
            probs.append(f"{where}: {canon(d)!r} requires a basis (S138)")
        if d in EDIT_REQUIRED and u.get("edit") is None:
            probs.append(f"{where}: {canon(d)!r} requires an edit block")
        if u.get("edit") is not None and d not in EDIT_ALLOWED:
            probs.append(f"{where}: {canon(d)!r} takes no edit; only {sorted(canon(x) for x in EDIT_ALLOWED)} do")
        if d == _norm(COND) and not (u.get("claims") or "").strip():
            probs.append(f"{where}: condense requires a claims ledger: every invariant, why and id the text keeps")
        if kind == "document" and d == _norm(NV) and u.get("in_tbc") != "yes" and not (u.get("tbc") or "").strip():
            # E1: a fingerprint the intake already holds open (or ruled-external) was asked in an
            # earlier panel; requiring the item again would duplicate it in the section.
            _, seen = find_intake(intake, fp=u.get("fingerprint")) if intake is not None else (None, None)
            if not (seen and seen["fields"].get("state") in ("open", "ruled-external")):
                probs.append(f"{where}: not verifiable in a document pass requires the `tbc:` item text (S51 inverse)")
        if d in (_norm(RULED), _norm(COND)):
            ruling = (u.get("ruling") or "").strip()
            if not ruling:
                probs.append(f"{where}: {canon(d)!r} requires `ruling:` naming the intake entry that authorizes it")
            elif intake is not None:
                base = base_texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
                probs += _ruling_binding_problems(u, ruling, ipath, intake,
                                                  {"unit_id": h["unit_id"], "baseline": h["baseline_sha"],
                                                   "text": base})
        of = (u.get("of") or "").strip()
        if of and kind != "document":
            probs.append(f"{where}: `of:` belongs to a {canon(DUPL)!r} unit of a document pass only")
        if of and d != _norm(DUPL):
            probs.append(f"{where}: `of:` belongs to {canon(DUPL)!r} only")
        if d == _norm(DUPL) and not of:
            probs.append(f"{where}: {canon(DUPL)!r} requires `of:` — the id of the kept unit it duplicates")
        if (u.get("conflicts") or "").strip() and (d not in FROZEN or kind != "document"):
            probs.append(f"{where}: `conflicts:` belongs to a frozen unit ({canon(DEFECT)!r}, {canon(NV)!r}) "
                         f"of a document pass only")
        rendered = u.get("adr_title") is not None or u.get("adr_text") is not None
        if v3 and d == _norm(ADR):
            adr = (u.get("adr") or "").strip().replace("\\", "/")
            adr_dir = cfg["adr_dir"].rstrip("/") + "/"
            if rendered:
                # the runner writes the ADR and derives its path: a hand-named path beside it is a second truth
                if adr:
                    probs.append(f"{where}: `adr:` and `adr_title` + `adr_text` exclude each other — with "
                                 f"`adr_text` the runner writes the ADR and derives its path")
                if not adr_slug(u.get("adr_title")):
                    probs.append(f"{where}: `adr_text` requires `adr_title:` with at least one letter or digit")
                if not (u.get("adr_text") or "").strip():
                    probs.append(f"{where}: `adr_title` requires `adr_text:` — the ADR body "
                                 f"(## Context, ## Decision, ## Consequences)")
            elif not adr:
                probs.append(f"{where}: {canon(ADR)!r} requires `adr:` — the path of the ADR file the "
                             f"single writer adds under {cfg['adr_dir']} in this unit — or `adr_title` + "
                             f"`adr_text`, which the runner writes")
            elif not adr.startswith(adr_dir) or not adr.lower().endswith(".md") or ".." in adr.split("/"):
                probs.append(f"{where}: adr {adr!r} is not a Markdown file under {cfg['adr_dir']}")
        else:
            if u.get("adr"):
                probs.append(f"{where}: `adr:` belongs to {canon(ADR)!r} only")
            if rendered:
                probs.append(f"{where}: `adr_title` and `adr_text` belong to {canon(ADR)!r} in a "
                             f"version-{RECORD_VERSION} record only")
        if u.get("edit") is not None and d in (_norm(STRIP), _norm(COND)):
            base = base_texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
            old = _unit_text(base, u)
            new = u["edit"]
            if d == _norm(STRIP):
                if not _words(new):
                    probs.append(f"{where}: strip left no words: dispose the unit {canon(REGEN) if kind == 'comment' else canon(OBS)!r} instead")
                elif not _is_subsequence(_words(new), _words(old)):
                    probs.append(f"{where}: strip may only delete words; the new text adds or reorders words")
                elif len(_words(new)) == len(_words(old)):
                    probs.append(f"{where}: strip removed no word")
            elif not _words(new):
                probs.append(f"{where}: condense left no text: a removal is a different disposition")
            elif len(_norm(new)) >= len(_norm(old)):
                probs.append(f"{where}: condense did not shorten the unit")
            elif kind == "comment":
                # B2: each condensed pointer names a spec file (a blob, never a directory) at the
                # baseline, and the claims ledger cites it
                for ln in new.split("\n"):
                    for m in re.finditer(r"(?i)\bsee\s+(\S+?)[,;:]?\s*§", ln):
                        p = m.group(1)
                        try:
                            blob = git("cat-file", "-t", f"{h['baseline_sha']}:{p}").strip() == "blob"
                        except RuntimeError:
                            blob = False
                        if not blob:
                            probs.append(f"{where}: the pointer names {p!r}, which is not a file at "
                                         f"the baseline {h['baseline_sha'][:7]}")
                        if p not in (u.get("claims") or ""):
                            probs.append(f"{where}: a pointer condense cites the spec path in its "
                                         f"claims ledger: {p!r}")
        if kind == "comment" and d == _norm(REGEN) and u.get("edit") is not None:
            # B1: a partial regenerable keeps a subset of the unit's whole lines, byte for byte
            # modulo leading and trailing whitespace, in order, at least one line dropped
            base = base_texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
            whole = _unit_text(base, u).split("\n")
            e_lines = u["edit"].split("\n")
            if not any(ln.strip() for ln in e_lines):
                probs.append(f"{where}: an edit of {canon(REGEN)!r} with no lines is refused: "
                             f"without an edit the unit is removed whole")
            else:
                pos, hits = 0, []
                for ln in e_lines:
                    hit = next((i for i in range(pos, len(whole)) if whole[i].strip() == ln.strip()), None)
                    if hit is None:
                        break
                    hits.append(hit)
                    pos = hit + 1
                if len(hits) != len(e_lines):
                    probs.append(f"{where}: a partial {canon(REGEN)!r} edit keeps only the unit's own "
                                 f"whole lines, unchanged and in order")
                elif len(hits) == len(whole):
                    probs.append(f"{where}: a partial {canon(REGEN)!r} edit must drop at least one line")
        if u.get("edit") and kind == "comment":
            sl, sc, el, ec = uspan(u)
            base = base_texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
            lines = _split_once(base)
            whole = (lines[sl - 1][:sc].lstrip("﻿").strip() == ""
                     and lines[el - 1][ec:].rstrip("\r").strip() == "")
            if not whole and "\n" in u["edit"]:
                probs.append(f"{where}: a comment sharing a line with code takes a one-line edit")
            matcher = LX.directive_matcher(cfg.get("directive_patterns") or ())
            for ln in u["edit"].split("\n"):
                body = re.sub(r"^[\s/*#!;'<>%{-]+", "", ln)
                if body and matcher(body) is not None:
                    probs.append(f"{where}: an edit never introduces a directive or licence marker "
                                 f"({matcher(body)}): {ln.strip()[:60]!r} (C3)")
            if LX.language_for(u["file"]) == "java" and re.search(r"\\u[0-9a-fA-F]{4}", u["edit"]):
                probs.append(f"{where}: a Java edit may not carry a \\uXXXX escape — Java decodes it "
                             f"before lexing, so it can end the comment and inject a line (B4)")
    if kind == "document":
        # `of:` and `conflicts:` name another unit of the same record and the same file (B3)
        for f in sorted({u["file"] for u in rec.units}):
            fus = [u for u in rec.units if u["file"] == f]
            op = {(x["lines"], x["span"]): o for x, o, _ in plan_ops(fus, kind)}
            by_id = {x["id"]: x for x in fus}
            for u in fus:
                where = f"unit {u['id']} ({u['file']}:{u['lines']})"
                of = (u.get("of") or "").strip()
                t = by_id.get(of)
                if of and (t is None or t is u):
                    probs.append(f"{where}: `of: {of}` names no other unit of {f} in this record")
                elif of and op.get((t["lines"], t["span"])) == "remove":
                    probs.append(f"{where}: `of: {of}` names unit {t['id']}, whose disposition removes it: "
                                 f"the kept unit must be one this record retains")
                cf = (u.get("conflicts") or "").strip()
                t = by_id.get(cf)
                if cf and (t is None or t is u):
                    probs.append(f"{where}: `conflicts: {cf}` names no other unit of {f} in this record")
                elif cf and (t.get("conflicts") or "").strip():
                    probs.append(f"{where}: `conflicts: {cf}` — unit {t['id']} carries its own `conflicts:`: "
                                 f"one direction per pair")
    if v3:
        # one ADR file, one writer: a hand-written `adr:` never names the path another unit
        # renders, however spelled (`./`). A part record's paths rank in its master, whose own
        # gate runs this check
        hand = {posixpath.normpath((u.get("adr") or "").strip().replace("\\", "/")): u for u in rec.units
                if _norm(u.get("disposition")) == _norm(ADR) and (u.get("adr") or "").strip()}
        if hand and not h.get("batch") and any(_adr_text_unit(u) for u in rec.units):
            try:
                rendered = adr_files(rec, cfg)
            except Die as e:
                rendered = {}
                probs.append(str(e))
            for uid, (p, _) in sorted(rendered.items(), key=lambda kv: kv[1][0]):
                if p in hand:
                    u = hand[p]
                    probs.append(f"unit {u['id']} ({u['file']}:{u['lines']}): `adr: {u['adr'].strip()}` names {p}, "
                                 f"the ADR unit {uid} renders from `adr_title` + `adr_text` — name a file this unit adds itself, "
                                 f"or give it its own `adr_title` + `adr_text`")
        claims = [(u, m.group(1)) for u in rec.units for m in _ABSENCE_CLAIM.finditer(u.get("basis") or "")]
        if claims:
            absent = code_absent(h["baseline_sha"], [c for _, c in claims], cfg)
            for u, c in claims:
                if c not in absent:
                    probs.append(f"unit {u['id']} ({u['file']}:{u['lines']}): the basis says identifier {c} does "
                                 f"not occur in the baseline tree, but code at the baseline names it (git grep -w)")
    if kind == "severance":
        per_line = {}
        for u in rec.units:
            per_line.setdefault((u["file"], ulines(u)[0]), []).append(u)
        pats = _target_patterns([t.strip() for t in h.get("targets", "").split(",") if t.strip()])
        for (f, ln), us in sorted(per_line.items()):
            where = f"{f}:{ln}"
            severed = [u for u in us if _norm(u.get("disposition")) == _norm(SEV)]
            if not severed:
                continue
            editors = [u for u in severed if u.get("edit") is not None]
            if len(editors) != 1:
                probs.append(f"{where}: exactly one severed entry per line carries the line's new text in `edit`")
                continue
            new = editors[0]["edit"]
            if "\n" in new:
                probs.append(f"{where}: a severed line's new text is one line")
                continue
            base = base_texts.setdefault(f, git_show(h["baseline_sha"], f) or "")
            kept = {}
            for u in us:
                if _norm(u.get("disposition")) == _norm(RET):
                    for t, pat in pats:
                        if pat.search(_unit_text(base, u)):
                            kept[t] = kept.get(t, 0) + 1
            for t, pat in pats:
                got = len(pat.findall(new))
                if got != kept.get(t, 0):
                    probs.append(f"{where}: the target {t} must be gone from the new line "
                                 f"({got} occurrence(s), {kept.get(t, 0)} retained entr(ies) to keep)")
    if kind == "document":
        for f in sorted({u["file"] for u in rec.units if _norm(u.get("disposition")) == _norm(NV)
                         and u.get("in_tbc") != "yes" and (u.get("tbc") or "").strip()}):
            base = base_texts.setdefault(f, git_show(h["baseline_sha"], f) or "")
            if open_fence_at_end(base):
                probs.append(f"{f}: the document ends inside an unclosed code fence — a `## To be confirmed` "
                             f"item appended there would be code; close the fence in a functional commit")
    if not probs:
        probs += edit_proof_problems(rec, cfg)
    return probs


def edit_proof_problems(rec, cfg):
    """Simulate apply. In a comment pass the result must keep every code token (no edit can carry
    code) and a Python file must still compile."""
    if rec.header["pass_kind"] != "comment":
        return []
    probs = []
    fine = rec.header["unit_rule"] == "comment-fine"
    for path, (base, new) in expected_texts(rec).items():
        if base == new:
            continue
        t0, _ = LX.code_tokens(base, path, fine)
        t1, _ = LX.code_tokens(new, path, fine)
        if t0 != t1:
            for u in [x for x in rec.units if x["file"] == path and x.get("edit")]:
                one = apply_file(base, plan_ops([u], "comment"), "comment")
                if LX.code_tokens(one, path, fine)[0] != t0:
                    probs.append(f"unit {u['id']} ({path}:{u['lines']}): the edit changes code tokens — an edit carries comment text only")
            if not probs:
                probs.append(f"{path}: applying the record changes code tokens")
        if LX.language_for(path) == "python" and _compiles(base, path) is None:
            # bytes, so the BOM (D3, R-gates 4) and a coding cookie are honoured as Python reads them
            err = _compiles(new, path)
            if err:
                probs.append(f"{path}: the applied file does not compile ({err})")
    return probs


def _compiles(text, path):
    """None when the Python source compiles, else the error. A file that did not compile at the
    baseline is no proof obligation of the pass."""
    try:
        compile(encode(text), path, "exec")
        return None
    except (SyntaxError, ValueError, UnicodeError) as e:
        return f"{getattr(e, 'msg', e)}, line {getattr(e, 'lineno', '?')}"


# ------------------------------------------------------------------ subcommands: scope and record
def cmd_target_set(args, cfg):
    kind = args.pass_kind
    if kind == "severance":
        if args.scope is not None:
            _die("--scope is not accepted for a severance pass: the exclusion inventory names the documents (E5)")
        inv = cfg.get("exclusion_inventory")
        if not inv:
            print("severance DISABLED: no exclusion_inventory configured (S107).")
            return ADVISORY
        print("# floor: exclusion-inventory\n# pass_kind: severance")
        for r in _run_provider(inv, "exclusion_inventory"):
            print(r)
        return OK
    rule = args.unit_rule or UNIT_RULES[kind][0]
    meta = []
    if args.scope is not None:
        scope = [repo_rel(s) for s in args.scope]
        floor = "self-report"
    elif cfg.get("knowledge_graph"):
        lines = _run_provider(cfg["knowledge_graph"], "knowledge_graph")
        scope, meta = _provider_rows(lines), [l for l in lines if l.startswith("#")]
        floor = "graph"
    else:
        _die("no scope: pass --scope FILES, or set knowledge_graph in .consolidation.json")
    print(f"# floor: {floor}\n# pass_kind: {kind}\n# unit_rule: {rule}")
    for m in meta:
        print(m)
    status = OK
    for f in scope:
        text = read_worktree(f)
        if text is None:
            print(f"# unreadable: {f}")
            status = FAIL
            continue
        try:
            units = enumerate_file(text, f, kind, rule, cfg)
        except LX.UnsupportedLanguage as e:
            print(f"# unsupported: {e}")
            status = FAIL
            continue
        print(f"{f}\t{len(units)}")
    return status


_UNIT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _body_groups(text, path, kind, rule, cfg, targets=()):
    """{normalized body: number of units of the whole file with that body}."""
    try:
        units = enumerate_file(text, path, kind, rule, cfg, targets)
    except LX.UnsupportedLanguage:
        return {}
    lines = text.split("\n")
    out = {}
    for u in units:
        b = unit_body(lines, u.sl, u.el)
        out[b] = out.get(b, 0) + 1
    return out


def carry_judgement(rec, src, cfg):
    """Copy judgement from an earlier record `src` onto the identical units of `rec`. The key is
    file and fingerprint, never position: a later unit is enumerated after an earlier unit's
    commit moved its lines. A fingerprint carries an occurrence index, which an earlier deletion
    of an identical comment shifts; so a unit whose body group changed size since `src`'s
    baseline is carried only when every member of the old group had one and the same judgement.
    Returns the ids left uncarried."""
    old_base = src.header.get("baseline_sha", "")
    new_base = rec.header["baseline_sha"]
    kind, rule = rec.header["pass_kind"], rec.header["unit_rule"]
    targets = [t.strip() for t in rec.header.get("targets", "").split(",") if t.strip()]
    by_fp = {(u.get("file"), u.get("fingerprint")): u for u in src.units}
    texts, groups = {}, {}

    def text_of(sha, path):
        if (sha, path) not in texts:
            texts[(sha, path)] = git_show(sha, path) if sha else None
        return texts[(sha, path)]

    def group(sha, path):
        if (sha, path) not in groups:
            t = text_of(sha, path)
            groups[(sha, path)] = _body_groups(t, path, kind, rule, cfg, targets) if t is not None else None
        return groups[(sha, path)]

    def judgement(u):
        return tuple((k, u.get(k)) for k in JUDGEMENT_FIELDS)

    uncarried, carried = [], []
    for u in rec.units:
        s = by_fp.get((u["file"], u["fingerprint"]))
        if not s or not _norm(s.get("disposition")):
            if not _norm(u.get("disposition")):
                uncarried.append(u["id"])
            continue
        new_text = text_of(new_base, u["file"])
        a, b = ulines(u)
        body = unit_body(new_text.split("\n"), a, b)
        g_old, g_new = group(old_base, u["file"]), group(new_base, u["file"])
        if g_old is None or g_old.get(body) != g_new.get(body):
            old_text = text_of(old_base, u["file"])
            olines = old_text.split("\n") if old_text is not None else []
            members = [x for x in src.units if x.get("file") == u["file"]
                       and unit_body(olines, *ulines(x)) == body] if olines else []
            if g_old is None or len(members) != g_old.get(body) or len({judgement(x) for x in members}) != 1:
                uncarried.append(u["id"])
                continue
        u.update({k: s[k] for k in JUDGEMENT_FIELDS if s.get(k) is not None})
        carried.append(u)
    # an `of:` / `conflicts:` id is record-local: a carried one names the same unit by this
    # record's id; a unit whose named unit this record does not hold is left uncarried
    sid = {x["id"]: x for x in src.units}
    rid = {(x["file"], x["fingerprint"]): x["id"] for x in rec.units}
    for u in carried:
        for f in REF_FIELDS:
            v = (u.get(f) or "").strip()
            t = sid.get(v) if v else None
            new = rid.get((t["file"], t["fingerprint"])) if t is not None and t["file"] == u["file"] else None
            if v and new is None:
                for k in JUDGEMENT_FIELDS:
                    u.pop(k, None)
                uncarried.append(u["id"])
                break
            if v:
                u[f] = new
    return uncarried


def _scope_args(entries):
    scope = []
    for s in entries:
        if "," in s:
            _die(f"{s!r}: a scope entry holds no comma — the record's scope line is comma-separated; "
                 f"rename the file or leave it out of scope")
        m = re.match(r"^(.*?):(\d+)-(\d+)$", s)
        scope.append((repo_rel(m.group(1)), (int(m.group(2)), int(m.group(3)))) if m else (repo_rel(s), None))
    return scope


def cmd_record_init(args, cfg):
    kind = args.pass_kind
    rule = args.unit_rule or UNIT_RULES[kind][0]
    if rule not in UNIT_RULES[kind]:
        _die(f"unit rule {rule!r} is not a rule of a {kind} pass {UNIT_RULES[kind]}")
    unit_id = getattr(args, "batch_id", None) or args.unit_id
    if not _UNIT_ID.match(unit_id or ""):
        _die(f"id {unit_id!r}: letters, digits, '.', '_' and '-' only (it names files and intake entries)")
    sha = head_sha()
    if not sha:
        _die("no HEAD: record-init runs inside a git repository with at least one commit")
    hist = _history_record_problems(cfg)
    if hist:
        _die("consolidation commits at the tip carry no passing record — gate or discard them first "
             "(a failed attempt is never buried under a new baseline):\n" + "\n".join(hist[:5]))
    scope = _scope_args(args.scope)
    dirty = [status_line(*e) for e in status_entries(*[p for p, _ in scope])]
    if dirty:
        _die("scope files differ from HEAD; commit the functional work first (S101):\n" + "\n".join(dirty))
    cfg_blob = git_show(sha, ".consolidation.json")
    wt = read_worktree(".consolidation.json")
    if cfg_blob is not None and (wt or "").replace("\r\n", "\n") != cfg_blob.replace("\r\n", "\n"):
        _die(".consolidation.json differs from HEAD: commit or restore it before taking the baseline "
             "(gates judge with the config of the baseline)")
    if any(p == cfg["adr_dir"] or p.startswith(cfg["adr_dir"].rstrip("/") + "/") for p, _ in scope):
        _die(f"the ADR directory ({cfg['adr_dir']}) is an output directory, never a scope")
    type_probs = _scope_type_problems(scope, kind, cfg) + _scope_overlap_problems(scope)
    if type_probs:
        _die("; ".join(type_probs))
    targets = []
    if kind == "severance":
        if args.target:
            targets = [repo_rel(t) for t in args.target]
        elif cfg.get("exclusion_inventory"):
            targets = sorted({l.split("\t")[-1].strip() for l in _provider_rows(
                _run_provider(cfg["exclusion_inventory"], "exclusion_inventory"))})
        else:
            _die("severance is disabled without an exclusion_inventory or --target (S107)")
    master = bool(getattr(args, "batch_id", None))
    header = {"record_version": RECORD_VERSION, "unit_id": unit_id, "baseline_sha": sha, "pass_kind": kind,
              "unit_rule": rule, "scope": render_scope(scope)}
    if master:
        header["batch_master"] = "yes"
    if targets:
        header["targets"] = ", ".join(targets)
    if args.narrowing_reason:
        header["narrowing_reason"] = args.narrowing_reason
    # targets typed with --target are the agent's, not the inventory's: that floor is self-report
    header["floor"] = args.floor or ("exclusion-inventory" if kind == "severance" and not args.target
                                     else "self-report")
    header["floor_observed"] = args.floor_observed or sha
    header["config_sha"] = cfg.get("_config_sha", "")
    whole = [p for p, rng in scope if rng is None]
    if kind == "document" and not master and cfg.get("last_verified_at") and whole:
        header["last_verified_at"] = f"{sha} {', '.join(whole)}"
    rec = Record(header, stubs_for(sha, header, cfg))
    uncarried = []
    if getattr(args, "carry_from", None):
        src = parse_record(args.carry_from)
        uncarried = carry_judgement(rec, src, cfg)
        print(f"carried the judgement of {len(rec.units) - len(uncarried)} of {len(rec.units)} unit(s) "
              f"from {show_path(args.carry_from)}")
        if uncarried:
            print(f"uncarried (classify these): unit(s) {', '.join(uncarried)}")
    ext = ".batch" if master else ".record"
    out = args.out or root_path(f"{RECORD_DIR}/{unit_id}-{sha[:7]}{ext}")
    if Path(user_path(out)).exists() and not args.force:
        _die(f"{show_path(out)} exists; pass --force to overwrite")
    write_record(rec, out)
    files = len({u["file"] for u in rec.units})
    print(f"record: {show_path(out)}\nbaseline: {sha}\n{len(rec.units)} unit(s) in {files} file(s); "
          f"fill disposition and basis for each (reference/classify.md)")
    if not rec.units:
        print("note: no classifiable unit in this scope — choose another scope; an empty record fails record-check")
    args._out, args._uncarried = out, uncarried
    return OK


def tree_snapshot(record=None):
    """{path: content hash} of every path that differs from HEAD, outside the record directory
    and — with `record` — outside the record's own shards and snapshot, wherever the record
    lives. Worker isolation is judged against the tree as it was when the shards were cut. A
    rename counts by both sides: its old side hashes as deleted, so moving a file into the
    record directory still shows."""
    snap = {}
    excl = [RECORD_DIR + "/"]
    if record:
        excl.append(repo_rel(record))   # the record itself, its shards, snapshot and commit message
    for path in [p for _, new, old in status_entries() for p in (new, old) if p]:
        if any(path == e or path.startswith(e) for e in excl):
            continue
        b = Path(path).read_bytes() if Path(path).is_file() else None
        snap[path] = hashlib.sha1(b).hexdigest() if b is not None else "deleted"
    return snap


def cmd_record_shard(args, cfg):
    """`R.shard-k` is a worker's read-only brief; `R.shard-k.j` its judgement file, one
    `@@ <id> <fingerprint>` block per unit, which `record-fill` writes back into the record."""
    if args.shards < 1:
        _die(f"--shards {args.shards}: a shard count is 1 or more, one worker per shard")
    args.record = record_file(args.record)
    rec = parse_record(args.record)
    by_file = {}
    for u in rec.units:
        by_file.setdefault(u["file"], []).append(u)
    n = max(1, min(args.shards, len(by_file)))
    if args.shards > 6:
        _warn(f"{args.shards} shards: beyond 6, each worker's fixed cost (the rubric, the precedents) outweighs its share")
    bins = [[0, []] for _ in range(n)]
    weight = lambda us: sum(ulines(u)[1] - ulines(u)[0] + 1 for u in us) + 3 * len(us)
    for f, us in sorted(by_file.items(), key=lambda kv: -weight(kv[1])):
        b = min(bins, key=lambda x: x[0])
        b[0] += weight(us)
        b[1].append(f)
    for k, (w, files) in enumerate(bins, 1):
        sub = Record(dict(rec.header, shard=f"{k}/{n}"), [u for u in rec.units if u["file"] in files])
        p = f"{args.record}.shard-{k}"
        write_record(sub, p)
        Path(user_path(p + ".j")).write_bytes(encode("".join(f"@@ {u['id']} {u['fingerprint']}\n" for u in sub.units)))
        print(f"{show_path(p)}\t{len(sub.units)} unit(s)\t{', '.join(files)}\tjudgement file: {show_path(p + '.j')}")
    # B4c: the unit rule each scoped file was last consolidated under, remembered from the
    # nearest committed document record below the baseline (first-parent walk, nearest commit
    # wins). Only a document pass has a document rule to compare
    base, rule = rec.header.get("baseline_sha", ""), rec.header.get("unit_rule", "")
    left = {p for p, _ in parse_scope(rec.header.get("scope"))}
    sha = base if _full(base) and rec.header.get("pass_kind") == "document" else None
    if sha and left:
        commit_log("--first-parent", f"-n{RULE_WALK_CAP}", sha)   # one call fills the walk's memos
    walked = 0
    while sha and left:
        if walked == RULE_WALK_CAP:
            print(f"note: no document record found within {walked} commits for {len(left)} file(s)")
            break
        walked += 1
        for r in _materialized_records(sha):
            if r.header.get("pass_kind") != "document":
                continue
            for f in sorted(left & {p for p, _ in parse_scope(r.header.get("scope"))}):
                got = r.header.get("unit_rule", "")
                print(f"{'warn: ' if got != rule else ''}{f}: unit rule {got} from record "
                      f"{r.header.get('unit_id')} ({sha[:7]})")
                left.discard(f)
            if not left:
                break
        sha = first_parent(sha)
    snap = tree_snapshot(args.record)
    snap["_record"] = hashlib.sha1(Path(user_path(args.record)).read_bytes()).hexdigest()
    Path(user_path(args.record + ".snapshot.json")).write_text(json.dumps(snap, indent=1), encoding="utf-8")
    return OK


def cmd_record_merge(args, cfg):
    rec = parse_record(args.record)
    # exactly the files record-shard wrote: a stray `.shard-1.bak` is no shard
    shards = sorted(p for p in Path(user_path(args.record)).parent.glob(Path(args.record).name + ".shard-*")
                    if re.fullmatch(r"\.shard-\d+", p.name[len(Path(args.record).name):]))
    if not shards:
        _die("no shard files to merge")
    by_id = {u["id"]: u for u in rec.units}
    seen = {}
    probs = []
    for sp in shards:
        sub = parse_record(str(sp))
        h = {k: v for k, v in sub.header.items() if k != "shard"}
        if h != rec.header:
            probs.append(f"{sp.name}: header differs from the record's (script-owned)")
        for u in sub.units:
            base = by_id.get(u.get("id"))
            if base is None:
                probs.append(f"{sp.name}: unit {u.get('id')} is not in the record")
                continue
            if u["id"] in seen:
                probs.append(f"unit {u['id']} appears in {seen[u['id']]} and {sp.name}")
            seen[u["id"]] = sp.name
            for k in SCRIPT_FIELDS:
                if (u.get(k) or "") != (base.get(k) or ""):
                    probs.append(f"{sp.name}: unit {u['id']} script-owned field {k!r} changed")
            if not _norm(u.get("disposition")):
                probs.append(f"{sp.name}: unit {u['id']} has no disposition")
            # A shard carries its unit's whole judgement: a field the worker deleted is deleted,
            # never silently kept from the main record (A9).
            for k in JUDGEMENT_FIELDS:
                if u.get(k) is not None:
                    base[k] = u[k]
                else:
                    base.pop(k, None)
    missing = sorted(set(by_id) - set(seen), key=lambda i: unit_number(i, show_path(args.record)))
    if missing:
        probs.append(f"units not covered by any shard: {missing}")
    snap_path = Path(user_path(args.record + ".snapshot.json"))
    before = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
    stamped = before.pop("_record", None)
    if stamped is not None and stamped != hashlib.sha1(Path(user_path(args.record)).read_bytes()).hexdigest():
        probs.append("the main record changed after the shards were cut — re-cut the shards (A9)")
    now = tree_snapshot(args.record)
    dirty = sorted(p for p in set(before) | set(now) if before.get(p) != now.get(p))
    if dirty:
        probs.append("worker isolation broken — files changed since the shards were cut: " + ", ".join(dirty))
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    write_record(rec, args.record)
    for sp in shards:
        sp.unlink()
    if snap_path.exists():
        snap_path.unlink()
    print(f"ok: merged {len(shards)} shard(s), {len(rec.units)} unit(s) into {args.record}")
    return OK


_J_HEAD = re.compile(r"^@@\s+(\S+)\s+(\S+)\s*$")


def parse_judgement_file(text, name):
    """([(id, fingerprint, {judgement field: value})], problems) of a judgement file: blocks
    `@@ <id> <fingerprint>`, each followed by judgement fields in the record's own syntax."""
    blocks, probs, cur = [], [], None
    for raw in text.lstrip("﻿").split("\n"):
        line = raw.rstrip("\r")
        if line.startswith("@@"):
            cur = (line, [])
            blocks.append(cur)
        elif cur is not None:
            cur[1].append(line)
        elif line.strip() and not line.startswith("#"):
            probs.append(f"{name}: a line before the first `@@ <id> <fingerprint>` block: {line[:60]!r}")
    out = []
    for head, body in blocks:
        m = _J_HEAD.match(head)
        if not m:
            probs.append(f"{name}: {head[:60]!r} is no block header `@@ <id> <fingerprint>`")
            continue
        uid, fp = m.groups()
        while body and not body[-1].strip():
            body.pop()   # the blank lines between blocks
        keys = [l.partition(":")[0].strip() for l in body if ":" in l and not l.startswith(("|", "#"))]
        owned = [k for k in keys if k in SCRIPT_FIELDS or k == "id"]
        if owned:
            probs.append(f"{name}: unit {uid}: script-owned field(s) {', '.join(owned)} — a judgement file "
                         f"carries judgement fields only")
            continue
        sub = parse_record_text("\n".join([f"@@unit {uid}", *body]) + "\n")
        probs += [f"{name}: {p}" for p in sub.problems]
        out.append((uid, fp, {k: v for k, v in sub.units[0].items() if k in JUDGEMENT_FIELDS}))
    return out, probs


def cmd_record_fill(args, cfg):
    """Write the judgement of the J files into the units they name, replacing those units' judgement
    fields; every other unit is left as it is. All or nothing: any problem writes nothing."""
    path = record_file(args.record)
    rec = parse_record(path)
    require_current(rec, show_path(path))
    if rec.problems:
        _die(f"{show_path(path)} does not parse: " + "; ".join(rec.problems[:5]))
    by_id = {u["id"]: u for u in rec.units}
    probs, seen, fills = [], {}, []
    for j in args.sources:
        name = show_path(j)
        try:
            text = decode(Path(user_path(j)).read_bytes())
        except OSError as e:
            probs.append(f"{name}: cannot read it ({e.strerror})")
            continue
        blocks, p = parse_judgement_file(text, name)
        probs += p
        for uid, fp, fields in blocks:
            u = by_id.get(uid)
            if u is None:
                probs.append(f"{name}: unit {uid} is not in the record")
            elif fp != u.get("fingerprint"):
                probs.append(f"{name}: unit {uid}: fingerprint {fp} differs from the record's {u.get('fingerprint')}")
            elif uid in seen:
                probs.append(f"unit {uid} appears in {seen[uid]} and {name}")
            else:
                seen[uid] = name
                fills.append((u, fields))
    inputs = {repo_rel(j) for j in args.sources}
    # an untracked config is the owner's, bound by config_sha (ADR 0012), as preflight treats it
    if any(xy == "??" for xy, _, _ in status_entries(".consolidation.json")):
        inputs.add(".consolidation.json")
    dirty = sorted(p for p in tree_snapshot(path) if p not in inputs)
    if dirty:
        probs.append("the working tree changed outside the record directory (a worker writes only its judgement "
                     "file): " + ", ".join(dirty[:10]))
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        print("record-fill refused: nothing written")
        return FAIL
    for u, fields in fills:
        for k in JUDGEMENT_FIELDS:
            if k in fields:
                u[k] = fields[k]
            else:
                u.pop(k, None)
    write_record(rec, path)
    empty = sum(1 for u in rec.units if not _norm(u.get("disposition")))
    print(f"ok: filled {len(fills)} unit(s) of {show_path(path)} from {len(args.sources)} file(s); "
          f"{empty} unit(s) still empty")
    return OK


def cmd_record_check(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    probs = record_problems(rec, cfg, check_intake=not args.no_intake)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    print(f"ok: header complete; {len(rec.units)} unit(s) identical to the enumeration at the baseline; "
          f"every disposition admissible with its evidence; edits proven")
    return OK


def cmd_coverage_check(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    probs = identity_problems(rec, cfg)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    print(f"ok: {len(rec.units)} entr(ies) == the {len(rec.units)} unit(s) enumerated at the baseline, one to one")
    return OK


def cmd_scope_cross_check(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    scope = parse_scope(rec.header.get("scope"))
    declared = {p for p, _ in scope}
    declared_floor = (rec.header.get("floor") or "").strip()
    status = OK
    if declared_floor in PROVIDER_FLOORS:
        # the gate observes the floor itself (S92, ADR 0011): a target set handed in floors nothing
        target, _, tracked = provider_floor(rec, cfg)
        print(f"floor {declared_floor}: the target set is {PROVIDER_FLOORS[declared_floor]}, re-run by the gate"
              + (" (--target-set ignored)" if getattr(args, "target_set", None) else ""))
        if not tracked:
            print(f"ADVISORY: {PROVIDER_FLOORS[declared_floor]} comes from an uncommitted .consolidation.json — "
                  f"an agent-authored command floors nothing; commit the config (R-gates 5)")
            status = ADVISORY
    elif _norm(declared_floor) == "self-report":
        if not getattr(args, "target_set", None):
            print("n/a: a self-report floor and no --target-set — nothing to cross-check")
            return ADVISORY
        target = set()
        floor = None
        for line in read_text_file(user_path(args.target_set)).splitlines():
            if line.startswith("# floor:"):
                floor = line.split(":", 1)[1].strip()
            if line.strip() and not line.startswith("#"):
                target.add(line.split("\t")[0])
        if floor is not None and floor != declared_floor:
            print(f"FAIL: the record declares floor {declared_floor!r}; the target set was built on floor "
                  f"{floor!r} — a {floor} floor is declared in the header and observed by the gate (A4)")
            return FAIL
    else:
        print(f"FAIL: floor {declared_floor!r} is none of {['self-report', *PROVIDER_FLOORS]}")
        return FAIL
    extra = declared - target
    if extra:
        print(f"FAIL: declared scope not in the target set: {sorted(extra)}")
        return FAIL
    omitted = target - declared
    ranged = [p for p, r in scope if r]
    if omitted or ranged:
        reason = rec.header.get("narrowing_reason", "").strip()
        if not reason:
            print(f"FAIL: declared scope narrower than the target set with no narrowing_reason; "
                  f"omitted {sorted(omitted)}, subset of {ranged}")
            return FAIL
        if not reason.lower().startswith(NARROWING_REASONS):
            print(f"FAIL: narrowing_reason must open with one of {list(NARROWING_REASONS)}; got {reason!r} (S93)")
            return FAIL
        print(f"ok: declared scope narrower than the target set ({reason})")
        return status
    print(f"ok: declared scope == target set ({len(declared)} file(s))")
    return status


def cmd_baseline_ancestry(args, cfg):
    base_arg = args.baseline or (load_record(args).header.get("baseline_sha")
                                 if (args.record or args.record_from_commit or getattr(args, "batch", None)) else None)
    if not base_arg:
        _die("give --baseline SHA or --record")
    head = TIP if _full(TIP) else git("rev-parse", TIP).strip()
    base = base_arg if _full(base_arg) else git("rev-parse", base_arg).strip()
    if base == head:
        if args.unit_gate:
            print("FAIL: no commit since the baseline — the gate has no review unit to delimit")
            return FAIL
        print(f"ok: baseline {base[:8]} is the tip of the isolated tree (pre-rewrite)")
        return OK
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, head]).returncode != 0:
        print(f"FAIL: baseline {base[:8]} is neither HEAD nor an ancestor of it")
        return FAIL
    if not args.unit_gate:
        print(f"FAIL: pre-rewrite, the baseline must be HEAD; {base[:8]} is an older ancestor")
        return FAIL
    unit = commit_log(f"{base}..{head}")   # newest first, as rev-list lists them
    first, subject = unit[-1][0], unit[-1][1].strip()
    if not subject.lower().startswith(CONSOLIDATION_COMMIT_MARKS):
        print(f"FAIL: the first commit after the baseline is not consolidation-class ({first[:8]} {subject!r})")
        return FAIL
    for sha, s, _ in unit:
        s = s.strip()
        if not s.lower().startswith(CONSOLIDATION_COMMIT_MARKS):
            print(f"FAIL: a functional commit sits inside the review unit ({sha[:8]} {s!r}) (S164)")
            return FAIL
    print(f"ok: baseline {base[:8]} parents the unit's first consolidation-class commit {first[:8]}")
    return OK


def _materialized_records(sha):
    """Every record materialized in one commit: embedded in its message, or committed as a
    record file under .consolidation/. Parsed once per commit and directory; callers get copies."""
    import copy
    if _full(sha):
        return copy.deepcopy(_memo("records", (sha,), lambda: _materialized_records_of(sha)))
    return _materialized_records_of(sha)


def _materialized_records_of(sha):
    out = []
    body = commit_message_of(sha)
    text = _commit_record_text(body)
    if text is not None:
        out.append(parse_record_text(text))
    parent = first_parent(sha)
    if parent:
        for f in changed_files(parent, sha):
            if f.startswith(RECORD_DIR + "/") and f.endswith(".record"):
                t = git_show(sha, f)
                if t is not None:
                    out.append(parse_record_text(t))
    return out


def cmd_record_provenance(args, cfg):
    """The unit gate judges the record the review unit materialized — the commit's own message
    or a committed record file — never a record handed in from the side (A8)."""
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    base = rec.header.get("baseline_sha", "")
    probs = []
    listed = {}

    def _unit_commits(base):
        if "unit" not in listed:
            listed["unit"] = git("rev-list", f"{base}..{TIP}").split()
            if listed["unit"]:
                commit_log(f"{base}..{TIP}")   # one call fills every message and parent memo
        return listed["unit"]
    if getattr(args, "record_from_commit", None):
        sha = args.record_from_commit
        sha = sha if _full(sha) else git("rev-parse", sha).strip()
        if base and sha not in _unit_commits(base):
            probs.append(f"commit {sha[:8]} is outside {base[:8]}..HEAD — the gate judges a commit of this review unit")
    if base and not probs:
        canon = render_record(rec, guide=False).strip()
        known = []
        for sha in _unit_commits(base):
            known += _materialized_records(sha)
        for f in changed_files(base):
            if f.startswith(RECORD_DIR + "/") and f.endswith(".record"):
                t = git_show(TIP, f)
                if t is not None:
                    known.append(parse_record_text(t))
        if not any(render_record(r, guide=False).strip() == canon for r in known):
            probs.append("the gated record is not one this review unit materialized (in a commit message "
                         "or as a committed record file)")
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    print("ok: the gated record is the one the review unit materialized")
    return OK


def _dirty_outside_records():
    """The status lines of every change outside the record directory — a rename by both its
    sides, so a record-dir new side never hides the old side's deletion — except an untracked
    `.consolidation.json`, the owner's config bound by config_sha (ADR 0012)."""
    return [status_line(*e) for e in status_entries()
            if not all(p.startswith(RECORD_DIR + "/") for p in e[1:] if p is not None)
            and e[:2] != ("??", ".consolidation.json")]


def cmd_unit_tree_check(args, cfg):
    dirty = _dirty_outside_records()
    if dirty:
        print("FAIL: uncommitted changes in the tree — the unit gate judges committed work only (A8):")
        print("\n".join("  " + d for d in dirty[:20]))
        return FAIL
    print("ok: working tree clean outside the record directory")
    return OK


_ADR_STATUS_LINE = re.compile(r"^\s*(\*\*)?status(\*\*)?\s*:", re.I)


def _mechanical_change_only(sha, cfg):
    """True when the commit's whole diff vs its parent stays inside the mechanical allowances:
    the last-verified-at front matter (what _strip_lva drops, marker-only block included), ADR
    status lines, and the record directory. A `mechanical:` subject alone bypasses nothing
    (review round 2, R-runner 2)."""
    parent = first_parent(sha)
    if parent is None:
        return False
    adr = cfg["adr_dir"].rstrip("/") + "/"
    exts = tuple(e.lower() for e in cfg.get("document_exts") or [])
    for f in changed_files(parent, sha):
        if f.startswith(RECORD_DIR + "/"):
            continue
        if f.startswith(adr) and git_show(parent, f) is not None:
            lines = [l for ff, _, l in list(iter_removed(parent, sha)) + list(iter_added(parent, sha)) if ff == f]
            if not all(_ADR_STATUS_LINE.match(l) for l in lines):
                return False
            continue
        new, old = git_show(sha, f) or "", git_show(parent, f) or ""
        if _strip_lva(new) != _strip_lva(old) or (new != old and Path(f).suffix.lower() not in exts):
            return False   # last-verified-at is a document's front matter, never a code file's
    return True


def _rev_list(a, b):
    """`git rev-list a..b`; memoized when both ends are full shas (the range is then fixed)."""
    def get():
        return git("rev-list", f"{a}..{b}").split()
    return list(_memo("revlist", (a, b), get)) if _full(a, b) else get()


def _history_record_problems(cfg):
    """Every consolidation-class commit at the tip, back to the first functional commit, must
    carry a record that passes its own gate: a failed earlier attempt is never buried under a
    new baseline (A8). The walk has no cap — a check that stops early never passes (ADR 0015).
    A record-carrying commit is replayed at itself, and covers every commit of its unit, from
    its baseline: the content commit of the committed-file channel (S24, E2) and any mechanical
    commit inside it. Any other mechanical commit must stay inside the mechanical allowances."""
    probs = []
    verified = _verified_commits()
    covered = set()
    walk = git("log", "--first-parent", "--format=%H %s").splitlines()
    k = next((i for i, line in enumerate(walk)
              if not line.partition(" ")[2].strip().lower().startswith(CONSOLIDATION_COMMIT_MARKS)), len(walk))
    if k:
        commit_log("--first-parent", f"-n{k}")   # one call fills the walk's message and parent memos
    for line in walk:
        sha, _, subject = line.partition(" ")
        low = subject.strip().lower()
        if not low.startswith(CONSOLIDATION_COMMIT_MARKS):
            break
        if sha in covered:
            continue
        if _REVERT_SUBJECT.fullmatch(subject.strip()) and not _materialized_records(sha):
            continue   # B5: the revert batch-revert printed carries no record of its own, and buries
            # nothing: the units it reverts stay on the line below, each replayed at its own commit.
            # A record-carrying commit is never skipped, whatever its subject; the walk cannot check
            # the batch id or the bounds (it holds no batch context) — runner.md states this limit
        what = f"{sha[:8]} ({subject.strip()!r})"
        if low.startswith("mechanical:"):
            if not _mechanical_change_only(sha, cfg):
                probs.append(f"{what}: a mechanical commit whose diff exceeds the allowances (a document's "
                             f"last-verified-at front matter, an ADR status line, the record directory)")
            continue
        recs = _materialized_records(sha)
        if not recs:
            probs.append(f"{what}: a consolidation commit that materializes no record")
            continue
        for r in recs:
            try:
                covered.update(_rev_list(r.header.get('baseline_sha', ''), sha))
            except RuntimeError:
                pass
        if sha in verified:
            continue
        ok = True
        for r in recs:
            rcfg = config_for_record(r, cfg)
            rp = record_problems(r, rcfg) or batch_carry_problems(r, sha) or _replay_at(r, rcfg, sha)
            if rp:
                ok = False
                probs.append(f"{what}: {rp[0]}")
        if ok:
            _remember_verified(sha)
    return probs


def _runner_hash():
    here = Path(__file__).resolve().parent
    return hashlib.sha1(b"".join((here / f).read_bytes() for f in ("consolidate.py", "lexer.py"))).hexdigest()[:12]


def _verified_path():
    try:
        return Path(git("rev-parse", "--git-common-dir").strip()).resolve() / "consolidation-verified"
    except RuntimeError:
        return None


def _verified_commits():
    """Commits whose materialized records already passed the history check under this runner.
    Kept in the git directory, outside the tree; a miss re-runs the full check, so the cache
    only saves time — the walk was quadratic over a batch."""
    p = _verified_path()
    if p is None or not p.exists():
        return set()
    h = _runner_hash()
    return {l.split()[0] for l in p.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(l.split()) == 2 and l.split()[1] == h}


def _remember_verified(sha):
    p = _verified_path()
    if p is None:
        return
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{sha} {_runner_hash()}\n")
    except OSError:
        pass


# ------------------------------------------------------------------ subcommands: post-rewrite gates
def _is_output(path, cfg):
    return path.startswith(RECORD_DIR + "/") or path.startswith(cfg["adr_dir"].rstrip("/") + "/")


def _strip_lva(text):
    """Drop a front-matter `last-verified-at:` line, which a mechanical commit may rewrite (S162).
    A block that held only the marker goes entirely: step 8 may add both on a document with no
    front matter of its own (E4). A leading BOM does not hide the front matter (R-runner 4a)."""
    lines = text.split("\n")
    if not lines or lines[0].lstrip("﻿").strip() != "---":
        return text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return text
    body = lines[1:end]
    if not any(l.startswith("last-verified-at:") for l in body):
        return text
    kept = [l for l in body if not l.startswith("last-verified-at:")]
    if all(not l.strip() for l in kept):
        rest = lines[end + 1:]
        if rest and lines[0].startswith("﻿") and not rest[0].startswith("﻿"):
            rest[0] = "﻿" + rest[0]   # dropping the block must not drop the BOM with it
        return "\n".join(rest)
    at = next(i for i, l in enumerate(body) if l.startswith("last-verified-at:"))
    return "\n".join(lines[:1 + at] + lines[2 + at:])


def lva_spec(rec):
    """(sha, [files]) of the header `last_verified_at: <sha> <file>, …`, or (None, [])."""
    v = (rec.header.get("last_verified_at") or "").strip()
    sha, _, files = v.partition(" ")
    return (sha or None), [f.strip() for f in files.split(",") if f.strip()]


def set_lva(text, sha):
    """`text` with the front-matter line `last-verified-at: <sha>`: replaced where the front
    matter holds one, added to it otherwise, or a front-matter block of its own put first (the
    inverse of _strip_lva). A BOM stays first; the line ending is the file's own."""
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    contents, eols = split_lines(text[len(bom):])
    nl = "\r\n" if "\r\n" in eols else "\n"
    line = f"last-verified-at: {sha}"
    if contents and contents[0].strip() == "---":
        end = next((i for i in range(1, len(contents)) if contents[i].strip() == "---"), None)
        if end is not None:
            at = next((i for i in range(1, end) if contents[i].startswith("last-verified-at:")), None)
            if at is not None:
                contents[at] = line
            else:
                contents.insert(end, line)
                eols.insert(end, nl)
            return bom + join_lines(contents, eols)
    return bom + "---" + nl + line + nl + "---" + nl + join_lines(contents, eols)


def _lva_problems(rec, cfg):
    """The `last_verified_at` header is the runner's, under S98–S100: a document pass, the
    committed config's `last_verified_at: true` (S99), the record's baseline — in a batch, the
    master record's, an ancestor of it — and whole documents only; a batch's top range of a
    whole document counts, since its lower ranges ran first."""
    sha, files = lva_spec(rec)
    h = rec.header
    if not sha and not files:
        return []
    where = "header: last_verified_at"
    if h["pass_kind"] != "document":
        return [f"{where} is written by a document pass only (S100)"]
    if not cfg.get("last_verified_at"):
        return [f"{where} needs `last_verified_at: true` in the committed .consolidation.json — the owner's "
                f"word that the merge strategy keeps the sha resolvable (S99)"]
    if not files or not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        return [f"{where} must read '<full sha> <file>, …'"]
    probs = []
    if not h.get("batch") and sha != h["baseline_sha"]:
        probs.append(f"{where}: {sha[:8]} is not the record's baseline (S98)")
    elif subprocess.run(["git", "merge-base", "--is-ancestor", sha, h["baseline_sha"]], capture_output=True).returncode:
        probs.append(f"{where}: {sha[:8]} is not an ancestor of the baseline (S98)")
    scope = dict(parse_scope(h.get("scope")))
    for f in files:
        if f not in scope:
            probs.append(f"{where}: {f} is not in the scope")
        elif scope[f] is not None and not (h.get("batch") and scope[f][0] == 1):
            probs.append(f"{where}: {f} is declared as a range; only a whole document is verified (S100)")
    return probs


def _git_mode(sha, path):
    def get():
        out = git("ls-tree", sha, "--", path).strip()
        return out.split()[0] if out else None
    return _memo("mode", (sha, path), get) if _full(sha) else get()


def replay_problems(rec, cfg):
    """The primary gate: the judged commit (TIP) must equal apply(baseline, record) in scope, and
    nothing else may change except declared outputs. Every change is therefore authorized by an
    entry. From v3 the comparison is exact — the record names its last-verified-at too; a v2
    record tolerated a later mechanical marker."""
    base = rec.header["baseline_sha"]
    probs = []
    exp = expected_texts(rec)
    for path, (b, want) in exp.items():
        got = git_show(TIP, path)
        if got is None:
            probs.append(f"{path}: deleted at HEAD")
            continue
        if (got != want) if record_v3(rec) else (_strip_lva(got) != _strip_lva(want)):
            a, c = want.split("\n"), got.split("\n")
            ln = next((i + 1 for i, (x, y) in enumerate(zip(a, c)) if x != y), min(len(a), len(c)) + 1)
            probs.append(f"{path}: HEAD differs from apply(baseline, record) at line {ln}")
    adr = cfg["adr_dir"].rstrip("/") + "/"
    for path in changed_files(base):
        if path in exp:
            continue
        if path.startswith(RECORD_DIR + "/"):
            continue
        if path.startswith(adr):
            old = git_show(base, path)
            if old is None:
                if not path.lower().endswith(".md"):
                    probs.append(f"{path}: a new file under the ADR directory ({cfg['adr_dir']}) must be "
                                 f"an ADR — a Markdown file")
            else:
                bad = [l for f, _, l in iter_removed(base) if f == path and not _ADR_STATUS_LINE.match(l)]
                bad += [l for f, _, l in iter_added(base) if f == path and not _ADR_STATUS_LINE.match(l)]
                if bad:
                    probs.append(f"{path}: an existing ADR changed beyond its status line (S32)")
            continue
        probs.append(f"{path}: changed outside the declared scope and the declared outputs")
    for path in exp:   # A7: a mode change on a scope file is invisible to every content check
        if _git_mode(base, path) != _git_mode(TIP, path):
            probs.append(f"{path}: file mode changed between the baseline and HEAD")
    # a unit removed as `historical decision → ADR` names the ADR its decision moved to; the unit
    # adds it, or the decision would be lost silently (v3)
    if record_v3(rec):
        for u in rec.units:
            adr_file = (u.get("adr") or "").strip().replace("\\", "/")
            if _norm(u.get("disposition")) == _norm(ADR) and adr_file:
                if git_show(base, adr_file) is not None or git_show(TIP, adr_file) is None:
                    probs.append(f"unit {u['id']} ({u['file']}:{u['lines']}): the ADR {adr_file} is not "
                                 f"added by this review unit — write it and commit it with the unit")
        try:
            rendered = adr_files(rec, cfg, at=TIP)
        except Die as e:
            rendered = {}
            probs.append(str(e))
        for uid, (path, text) in sorted(rendered.items()):
            got = git_show(TIP, path)
            if git_show(base, path) is not None or got is None:
                probs.append(f"unit {uid}: the ADR {path} the runner renders is not added by this review unit")
            elif got != text:
                probs.append(f"unit {uid}: the ADR {path} differs from the text the record renders (adr_title, "
                             f"adr_text) — it is written by apply only")
    return probs


@contextmanager
def _at_tip(sha):
    """`sha` is the judged commit inside the block; the one judged before is restored after it,
    so a nested call never re-points an outer gate."""
    global TIP
    old, TIP = TIP, sha
    try:
        yield
    finally:
        TIP = old


def _replay_at(rec, cfg, sha):
    """replay_problems with `sha` as the judged commit."""
    with _at_tip(sha):
        try:
            return replay_problems(rec, cfg)
        except Die as e:
            return [str(e)]


def cmd_replay_check(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    probs = replay_problems(rec, cfg)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    n = len({p for p, _ in parse_scope(rec.header.get("scope"))})
    print(f"ok: HEAD == apply(baseline, record) for {n} file(s); no change outside scope and outputs")
    return OK


def cmd_removal_authorization(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    probs = identity_problems(rec, cfg)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    base = rec.header["baseline_sha"]
    auth = {}
    for u in rec.units:
        if _norm(u.get("disposition")) in CHANGE_AUTHORIZED:
            a, b = ulines(u)
            auth.setdefault(u["file"], []).append((a, b))
    bad, blank, total = [], 0, 0
    for f, ln, content in iter_removed(base):
        total += 1
        if any(a <= ln <= b for a, b in auth.get(f, [])):
            continue
        if not content.strip():
            blank += 1
            continue
        if _is_output(f, cfg) or content.startswith("last-verified-at:"):
            continue
        bad.append(f"{f}:{ln}")
    if blank:
        print(f"note: {blank} whitespace-only removed line(s) exempt")
    if bad:
        print(f"FAIL: {len(bad)} removed line(s) fall in no unit whose entry authorizes a change (e.g. {', '.join(bad[:5])})")
        return FAIL
    print(f"ok: {total} removed line(s), every one inside an authorized enumerated unit or exempt")
    return OK


def invariance(rec, rev="HEAD"):
    """{path: 'proven' | 'equal-uncertain' | 'differs' | 'unsupported'}"""
    fine = rec.header["unit_rule"] == "comment-fine"
    out = {}
    for path, _ in parse_scope(rec.header.get("scope")):
        a = git_show(rec.header["baseline_sha"], path)
        b = git_show(rev, path) if rev else read_worktree(path)
        try:
            ta, ca = LX.code_tokens(a or "", path, fine)
            tb, cb = LX.code_tokens(b or "", path, fine)
        except LX.UnsupportedLanguage:
            out[path] = "unsupported"
            continue
        out[path] = "differs" if ta != tb else ("proven" if ca and cb else "equal-uncertain")
    return out


def cmd_code_invariance(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    if rec.header["pass_kind"] != "comment":
        print("n/a: code invariance applies to comment passes")
        return OK
    res = invariance(rec, None if args.worktree else TIP)
    status = OK
    for p, r in res.items():
        print(f"{r:16} {p}")
        if r in ("differs", "unsupported"):
            status = FAIL
    unproven = [p for p, r in res.items() if r == "equal-uncertain"]
    if status == OK and unproven:
        print(f"cannot prove: {len(unproven)} file(s) lexed heuristically — run the suite for this unit")
        return ADVISORY
    if status == OK:
        print("ok: non-comment tokens identical in every file of the scope")
    return status


def measured_removed(rec, cfg):
    base = rec.header["baseline_sha"]
    total = exempt = 0
    for f, _, content in iter_removed(base):
        if not content.strip() or _is_output(f, cfg) or content.startswith("last-verified-at:"):
            exempt += 1
            continue
        total += 1
    return total, exempt


def cmd_bound_check(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    units = rec.units
    judged = [u for u in units if _norm(u.get("disposition")) in JUDGEMENT]
    line_total = sum(ulines(u)[1] - ulines(u)[0] + 1 for u in units if _norm(u.get("disposition")) in CHANGE_AUTHORIZED)
    jcap, lcap, rate = cfg["REMOVAL_JUDGEMENT_CAP"], cfg["REMOVED_LINE_CAP"], cfg["SPOT_CHECK_RATE"]
    selected = args.judgement or args.project_lines or args.measured
    print(f"judgements: {len(judged)} / cap {jcap}")
    print(f"spot-check: read {math.ceil(len(units) * rate)} of {len(units)} entries at rate {rate:g}")
    print(f"projected changed lines (upper bound from the record): {line_total} / cap {lcap}")
    status = OK
    if (args.judgement or not selected) and len(judged) > jcap:
        print("FAIL: judgement cap breached — split the pass across review units (S81)")
        status = FAIL
    if args.project_lines and line_total > lcap:
        print("ADVISORY: projected line cap exceeded — a re-scope decision for the author (S80)")
        status = ADVISORY if status == OK else status
    if args.measured or not selected:
        measured, exempt = measured_removed(rec, cfg)
        print(f"removed lines measured against the tree: {measured} / cap {lcap}" + (f" ({exempt} exempt)" if exempt else ""))
        if measured > lcap:
            print("FAIL: measured line cap breached — split across review units and re-run, or discard and re-scope (S81)")
            status = FAIL
    return status


def _commit_date(sha):
    return date.fromisoformat(git("show", "-s", "--format=%cI", sha).strip()[:10])


def cmd_floor_staleness(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    floor = rec.header.get("floor", "").strip()
    if not floor:
        print("FAIL: record header declares no floor (S137)")
        return FAIL
    if _norm(floor) == "self-report":
        print("ADVISORY: floor is self-report — authored by this pass, so the scope cross-check has no "
              "non-agent-authored floor and staleness is undefined (S2)")
        return ADVISORY
    if floor not in PROVIDER_FLOORS:
        print(f"FAIL: floor {floor!r} is none of {['self-report', *PROVIDER_FLOORS]}")
        return FAIL
    # the observation state is the provider's own, never the header's floor_observed (ADR 0011)
    _, raw, _ = provider_floor(rec, cfg)
    if not raw:
        print(f"ADVISORY: {PROVIDER_FLOORS[floor]} reports no `# observed: <ISO date or sha>` line — "
              f"its build state is not observable, so staleness cannot be judged (S2, S6)")
        return ADVISORY
    try:
        observed = date.fromisoformat(raw[:10])
    except ValueError:
        try:
            observed = _commit_date(raw)
        except (RuntimeError, ValueError):
            print(f"FAIL: the provider's observed {raw!r} is neither an ISO date nor a resolvable sha")
            return FAIL
    base = _commit_date(rec.header["baseline_sha"])
    age = (base - observed).days
    thr = cfg["FLOOR_STALENESS_THRESHOLD_DAYS"]
    print(f"floor: {floor}; observed {observed}; baseline {base}; age {age} day(s) / threshold {thr}")
    if age > thr:
        print("FAIL: a stale floor invalidates the control it floors — rebuild it and re-run (S6)")
        return FAIL
    print("ok: floor is fresh")
    return OK


# ------------------------------------------------------------------ aggregate gates
def _sub(name, fn, args, cfg, **over):
    ns = argparse.Namespace(**{**vars(args), "judgement": False, "project_lines": False, "measured": False,
                               "unit_gate": False, "baseline": None, "worktree": False, "no_intake": False, **over})
    print(f"── {name}")
    try:
        r = fn(ns, cfg)
    except Die as e:
        print(f"FAIL {e}")
        r = FAIL
    except Exception as e:   # D4: a malformed record fails the gate, it never crashes it
        print(f"FAIL {type(e).__name__}: {e}")
        r = FAIL
    return r


def cmd_config_bound_check(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    if cfg.get("_bounded"):
        for m in cfg["_bounded"]:
            print(f"FAIL the config in force is not the committed one, and {m}")
        print("an uncommitted .consolidation.json may only tighten the gates — commit it to loosen one (R-gates 5)")
        return FAIL
    print("ok: the config in force is committed, or only tightens the defaults")
    return OK


def cmd_gate(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    kind = rec.header.get("pass_kind")
    # a master record is never a review unit: no bound (batch-plan cuts it under the caps) and
    # no unit gate (each of its review units has its own) — ADR 0013
    master = rec.header.get("batch_master") == "yes"
    if master and not args.pre:
        _die("a batch master record is never gated --unit: batch-next gates each of its review units")
    cross = bool(args.target_set) or (rec.header.get("floor") or "").strip() in PROVIDER_FLOORS
    results = [("config-bound-check", _sub("config-bound-check", cmd_config_bound_check, args, cfg))]
    if args.pre:
        results.append(("record-check", _sub("record-check (identity, admissibility, evidence, edit proofs)", cmd_record_check, args, cfg)))
        if cross:
            results.append(("scope-cross-check", _sub("scope-cross-check", cmd_scope_cross_check, args, cfg)))
        results.append(("floor-staleness-check", _sub("floor-staleness-check", cmd_floor_staleness, args, cfg)))
        results.append(("baseline-ancestry-check", _sub("baseline-ancestry-check (pre-rewrite)", cmd_baseline_ancestry, args, cfg)))
        if not master:
            results.append(("bound-check", _sub("bound-check --judgement --project-lines", cmd_bound_check, args, cfg,
                                                judgement=True, project_lines=True)))
    else:
        # The unit gate never skips the intake: a `ruled → apply` whose entry cannot be
        # verified — missing, evolved or bound to another unit — fails the gate (A1).
        results.append(("record-check", _sub("record-check", cmd_record_check, args, cfg)))
        results.append(("record-provenance-check", _sub("record-provenance-check", cmd_record_provenance, args, cfg)))
        # a done unit re-gated at its own commit (batch-next): the working tree belongs to the next
        # unit, and batch-next checks it itself, its outputs allowed
        if not getattr(args, "at_commit", False):
            results.append(("unit-tree-check", _sub("unit-tree-check", cmd_unit_tree_check, args, cfg)))
        results.append(("replay-check", _sub("replay-check", cmd_replay_check, args, cfg)))
        if rec.header.get("batch"):
            results.append(("batch-carry-check", _sub("batch-carry-check", cmd_batch_carry_check, args, cfg)))
        results.append(("removal-authorization-check", _sub("removal-authorization-check", cmd_removal_authorization, args, cfg)))
        if kind == "comment":
            results.append(("code-invariance-check", _sub("code-invariance-check", cmd_code_invariance, args, cfg)))
        results.append(("baseline-ancestry-check", _sub("baseline-ancestry-check --unit-gate", cmd_baseline_ancestry, args, cfg, unit_gate=True)))
        if cross:
            results.append(("scope-cross-check", _sub("scope-cross-check", cmd_scope_cross_check, args, cfg)))
        results.append(("floor-staleness-check", _sub("floor-staleness-check", cmd_floor_staleness, args, cfg)))
        results.append(("bound-check", _sub("bound-check", cmd_bound_check, args, cfg)))
    print("══ gate", "--pre --batch" if master else "--pre" if args.pre else "--unit")
    failed = [n for n, r in results if r == FAIL]
    advisory = [n for n, r in results if r == ADVISORY]
    for n, r in results:
        print(f"  {('FAIL' if r == FAIL else 'advisory' if r == ADVISORY else 'ok'):9} {n}")
    if master:
        print("  note      bound-check not run: a master record is cut into review units under the caps (batch-plan)")
    if not cross:
        print("  note      scope-cross-check not run: a self-report floor is cross-checked only against "
              "--target-set FILE (the target-set output)")
    if not args.pre and kind == "comment" and not failed:
        unproven = "code-invariance-check" in advisory
        if unproven:
            print("SUITE: run the test suite now, for this unit — code invariance could not be proven for every file")
        elif cfg["suite_cadence"] == "unit":
            print("SUITE: run the test suite now, for this unit (suite_cadence=unit)")
        else:
            print("SUITE: deferred to the batch run (suite_cadence=batch); code invariance proven")
    if failed:
        print(f"GATE FAILED: {', '.join(failed)} — stop; a reviewer is never asked to substitute attention for a control (S163)")
        return FAIL
    print("GATE PASSED" + (" (advisories: " + ", ".join(advisory) + ")" if advisory else ""))
    return OK


# ------------------------------------------------------------------ apply
def _stripped_fragments(old, new):
    ow, nw = re.findall(r"\S+", old), re.findall(r"\S+", new)
    sm = difflib.SequenceMatcher(a=[_norm(w) for w in ow], b=[_norm(w) for w in nw], autojunk=False)
    frags = [" ".join(ow[i1:i2]) for tag, i1, i2, _, _ in sm.get_opcodes() if tag in ("delete", "replace")]
    return [f for f in frags if re.search(r"\w", f)]


def commit_message(rec, embed_record=True):
    """The unit's commit message. With `embed_record=False` (the content commit of the committed
    -file channel) it carries the summary and the relocated fragments but not the record itself,
    which rides as a file in the record commit that follows it (S24, S169, E2)."""
    h = rec.header
    counts = {}
    for u in rec.units:
        d = canon(u.get("disposition")) or "?"
        counts[d] = counts.get(d, 0) + 1
    summary = ", ".join(f"{n} {d}" for d, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    lines = [f"consolidation: {h['unit_id']} {h['pass_kind']} pass — {len(rec.units)} units", "", summary]
    reloc = []
    base_texts = {}
    for u in rec.units:
        if _norm(u.get("disposition")) == _norm(STRIP) and u.get("edit") is not None:
            base = base_texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
            frags = _stripped_fragments(_unit_text(base, u), u["edit"])
            if frags:
                reloc.append(f"- {u['file']}:{ulines(u)[0]}: " + "; ".join(f'"{f}"' for f in frags))
    if reloc:
        lines += ["", "Relocated from comments (stale fragment → strip, S49):"] + reloc
    if embed_record:
        lines += ["", RECORD_BEGIN, render_record(rec, guide=False).rstrip("\n"), RECORD_END]
    return "\n".join(lines).rstrip("\n") + "\n"


def _q(p):
    """A path quoted for Git Bash and PowerShell alike when it needs it."""
    return p if re.fullmatch(r"[A-Za-z0-9._/:@+=-]+", p) else '"' + p.replace('"', '\\"') + '"'


def apply_plan(rec, cfg):
    """(changed paths, {path: text to write}) for a record. Every file is checked before any is
    written, so a refusal never leaves a half-applied tree."""
    h = rec.header
    if h.get("batch_master") == "yes":
        _die("a batch master record is never applied: `batch-plan` cuts it into review units")
    if head_sha() != h.get("baseline_sha"):
        _die("apply runs once, on the baseline: HEAD is not the record's baseline_sha")
    exp = expected_texts(rec)
    writes = {}
    for path, (base, new) in exp.items():
        # D1: "unchanged" is judged through git's filters, so core.autocrlf=true (worktree CRLF,
        # blob LF) is not a spurious difference; the write keeps the worktree's own endings.
        if subprocess.run(["git", *_GIT_C, "diff", "--quiet", h["baseline_sha"], "--", path],
                          capture_output=True).returncode != 0:
            _die(f"{path}: the working tree differs from the baseline; apply writes onto the baseline only")
        if new != base:
            cur = read_worktree(path)
            writes[path] = new.replace("\n", "\r\n") if cur and "\r\n" in cur and "\r\n" not in new else new
    for uid, (path, text) in sorted(adr_files(rec, cfg).items()):
        if git_show(h["baseline_sha"], path) is not None:
            _die(f"{path}: the ADR unit {uid} renders exists at the baseline")
        cur = read_worktree(path)
        if cur is not None and cur != text:
            _die(f"{path}: a file with other content is in the way of the ADR unit {uid} renders; delete it")
        writes[path] = text
    return list(writes), writes


def write_unit(rec, record_path, cfg, writes):
    """Write the files and the commit message(s). Returns (message path, content-message path)."""
    stem = re.sub(r"\.record$", "", user_path(record_path))
    msg_path, content_path = stem + ".commit-msg", stem + ".content-msg"
    for path, text in writes.items():
        Path(path).parent.mkdir(parents=True, exist_ok=True)   # a rendered ADR may open adr_dir
        Path(path).write_bytes(encode(text))
    Path(msg_path).write_bytes(encode(commit_message(rec)))
    if cfg["record_channel"] == "file":
        Path(content_path).write_bytes(encode(commit_message(rec, embed_record=False)))
    return msg_path, content_path


def unit_adrs(rec):
    """The hand-written ADR files the record names (`adr:`); the runner renders the `adr_text` ones."""
    return sorted({(u.get("adr") or "").strip().replace("\\", "/") for u in rec.units
                   if _norm(u.get("disposition")) == _norm(ADR) and (u.get("adr") or "").strip()})


_ADR_NUMBER = re.compile(r"(\d{4})(?!\d)")


def adr_slug(title):
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:60].strip("-")


def _adr_text_unit(u):
    return _norm(u.get("disposition")) == _norm(ADR) and u.get("adr_text") is not None


def adr_rank_source(rec, at=None):
    """The record whose `adr_text` units number the ADRs the runner writes: for a part record of a
    batch, the master record it names — committed with the unit at `at`, else the working tree's —
    so a batch numbers its ADRs once; for any other record, the record itself."""
    name = rec.header.get("batch")
    if not name:
        return rec
    text = git_show(at, name) if at else read_worktree(root_path(name))
    if text is None:
        _die(f"the master record {name} is not " + (f"committed at {at[:8]}" if at else "in the working tree")
             + ": the ADR numbers of this part record are its")
    return _parsed_once(text.lstrip("﻿"))


def adr_path_for(src, u, cfg):
    """(path, rendered text) of the ADR the runner writes for the `adr_text` unit `u`. `src` is
    adr_rank_source's record: NNNN = 1 + the highest four-digit number in adr_dir at its baseline +
    the unit's rank among its `adr_text` units in unit-id order; the date is that baseline's
    committer date. Deterministic, so replay-check recomputes exactly what apply wrote."""
    ranked = sorted((m for m in src.units if _adr_text_unit(m)),
                    key=lambda m: unit_number(m["id"], f"record {src.header.get('unit_id')}"))
    rank = next((i for i, m in enumerate(ranked) if _ukey(m) == _ukey(u)), None)
    if rank is None:
        _die(f"unit {u['id']} ({u['file']}:{u['lines']}): no `adr_text` unit of {src.header.get('unit_id')} matches it")
    base = src.header["baseline_sha"]
    d = cfg["adr_dir"].replace("\\", "/").strip("/")
    names = git("ls-tree", "--name-only", base, "--", d + "/").splitlines()
    nums = [_ADR_NUMBER.match(n.rsplit("/", 1)[-1]) for n in names]
    num = f"{max((int(m.group(1)) for m in nums if m), default=0) + 1 + rank:04d}"
    title = (u.get("adr_title") or "").strip()
    text = (f"# {num} — {title}\n\nStatus: accepted\nDate: {_commit_date(base).isoformat()}\n\n"
            f"{u['adr_text']}\n")
    return f"{d}/{num}-{adr_slug(title)}.md", text


def adr_files(rec, cfg, at=None):
    """{unit id: (path, text)} of the ADRs the runner writes for `rec`'s `adr_text` units."""
    units = [u for u in rec.units if _adr_text_unit(u)]
    if not units:
        return {}
    src = adr_rank_source(rec, at)
    return {u["id"]: adr_path_for(src, u, cfg) for u in units}


def cmd_apply(args, cfg):
    rec = parse_record(args.record)
    require_current(rec, show_path(args.record))
    probs = record_problems(rec, cfg)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        print("apply refused: run gate --pre and fix the record first")
        return FAIL
    changed, writes = apply_plan(rec, cfg)
    print(("would change" if args.dry_run else "changed") + f" {len(changed)} file(s): " + ", ".join(changed))
    if args.dry_run:
        return OK
    msg_path, content_path = write_unit(rec, args.record, cfg, writes)
    # printed with `git -C <root>` and root-relative paths: the lines work from any directory
    root = Path(repo_root() or os.getcwd()).resolve()
    g = f"git -C {_q(root.as_posix())}"
    rel = lambda p: root_rel(p, root)
    adrs = unit_adrs(rec)
    add = " ".join(_q(p) for p in changed + adrs)
    rec_rel = _q(rel(user_path(args.record)))
    if changed:
        # E2: every unit's last commit carries the record in its message (-F), so the gate reads
        # the record from the record-carrying commit in every channel.
        if cfg["record_channel"] == "file":
            print(f"next: {g} add -- {add} && {g} commit -F {_q(rel(content_path))}\n"
                  f"      then {g} add -f -- {rec_rel} && {g} commit -F {_q(rel(msg_path))}")
            n = 2
        else:
            print(f"next: {g} add -- {add} && {g} commit -F {_q(rel(msg_path))}")
            n = 1
        if adrs:
            print(f"      the ADR file(s) {', '.join(adrs)} must exist before the commit")
        print("then: gate --unit --record-from-commit <the record-carrying commit: HEAD after these commits>")
        restore = [p for p in changed if not _is_output(p, cfg)]   # a rendered ADR is new: nothing to restore
        print(f"undo: {g} reset --mixed HEAD~{n} && {g} restore -- {' '.join(_q(p) for p in restore)}\n"
              f"      (the ADR and the record stay on disk; extend ~{n} by every mechanical commit that followed)")
    else:
        print(f"nothing removed: commit the record itself (S169): {g} add -f -- {rec_rel} "
              f"&& {g} commit -F {_q(rel(msg_path))}")
        print(f"undo: {g} reset --mixed HEAD~1  (the record stays on disk)")
    return OK


# ------------------------------------------------------------------ review pack
def _fenced(text):
    """A code block that the text cannot close: the fence is longer than its longest backtick run."""
    run = max((len(m) for m in re.findall(r"`+", text or "")), default=0)
    f = "`" * max(3, run + 1)
    return [f, text, f]


def spot_sample(rec, rate):
    """The deterministic spot-check sample (S13): drawn from the entries that change nothing —
    the retained and the frozen — because every changed entry is read in full anyway."""
    h = rec.header
    pool = [u for u in rec.units if _norm(u.get("disposition")) not in CHANGE_AUTHORIZED]
    k = min(len(pool), math.ceil(len(rec.units) * rate))
    key = lambda u: hashlib.sha1(f"{h.get('baseline_sha', '')}:{h['unit_id']}:{u['id']}".encode()).hexdigest()
    return {u["id"] for u in sorted(pool, key=key)[:k]}


def review_pack(rec, cfg, path, verdict=None, at=None):
    """Write the pack; returns (spot-check entries, the problem that kept the rendered ADR paths
    out of it, or None). The pack renders a record its gate refuses too, so a refusal is written
    into it, never dropped."""
    h = rec.header
    base_texts = {}
    adr_problem = None
    try:   # `at`: the commit the part record's master is read from (the working tree's without it)
        rendered = adr_files(rec, cfg, at)
    except Die as e:
        rendered, adr_problem = {}, str(e)
    sample = spot_sample(rec, cfg["SPOT_CHECK_RATE"])
    out = [f"# Review — {h['unit_id']} ({h['pass_kind']} pass)", "",
           f"Baseline `{h['baseline_sha'][:10]}` · scope: {h['scope']} · {len(rec.units)} entries", "",
           f"Gate: {verdict}" if verdict else "Gate: not run here — run `gate --unit` and stop on any FAIL", "",
           "Read in order: 1) the gate result (stop on any FAIL); 2) every changed unit below, removed text "
           "against its basis; 3) the spot-check entries marked ★.", ""]
    counts = {}
    for u in rec.units:
        counts[canon(u.get("disposition")) or "?"] = counts.get(canon(u.get("disposition")) or "?", 0) + 1
    out += ["| disposition | entries |", "|---|---|"] + [f"| {d} | {n} |" for d, n in sorted(counts.items())] + [""]
    out.append("## Changed units")
    for u in rec.units:
        d = _norm(u.get("disposition"))
        if d not in CHANGE_AUTHORIZED:
            continue
        base = base_texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
        out += ["", f"### {u['file']}:{u['lines']} — {canon(d)}", f"basis: {u.get('basis', '')}"]
        if u.get("ruling"):
            out.append(f"ruling: {u['ruling']}")
        if u.get("adr"):
            out.append(f"ADR: {u['adr']}")
        if u["id"] in rendered:
            out += [f"ADR: {rendered[u['id']][0]} (written by apply from adr_title + adr_text)", "", "ADR text:"]
            out += _fenced(rendered[u["id"]][1].rstrip("\n"))
        if h["pass_kind"] == "severance":
            # the line as a whole: a severed line's new text is judged against all of the old one
            a = ulines(u)[0]
            out += ["", "line at the baseline:"] + _fenced(base.split("\n")[a - 1].rstrip("\r"))
        else:
            out += ["", "removed:"] + _fenced(_unit_text(base, u))
        if u.get("edit") is not None:
            out += ["new:"] + _fenced(u["edit"])
        if u.get("claims"):
            out += ["claims kept:", u["claims"]]
    # the gates refuse an `adr:` naming the path another unit renders, but the pack also renders
    # a refused record: one path is listed once
    adrs = list(dict.fromkeys(unit_adrs(rec) + sorted(p for p, _ in rendered.values())))
    if adrs or adr_problem:
        out += ["", "## ADR files added", ""] + [f"- {a}" for a in adrs]
        if adr_problem:
            out.append(f"- FAIL: the ADR files the runner renders cannot be listed: {adr_problem}")
    frozen = [u for u in rec.units if _norm(u.get("disposition")) in FROZEN]
    if frozen:
        out += ["", "## Frozen and escalated"]
        for u in frozen:
            star = " ★" if u["id"] in sample else ""
            out.append(f"- {u['file']}:{u['lines']} — {canon(u['disposition'])}: {u.get('basis', '')}{star}")
            if (u.get("tbc") or "").strip() and u.get("in_tbc") != "yes":
                out.append(f"  - added to `## To be confirmed`: {tbc_item_body(u['tbc'])}")
    spot = [u for u in rec.units if u["id"] in sample and _norm(u.get("disposition")) not in FROZEN]
    if spot:
        out += ["", "## Spot-check (retained) ★"]
        out += [f"- {u['file']}:{u['lines']} `{u.get('preview', '')}` — {canon(u.get('disposition'))}: "
                f"{u.get('basis', '')}" for u in spot]
    Path(user_path(path)).parent.mkdir(parents=True, exist_ok=True)
    Path(user_path(path)).write_bytes(encode("\n".join(out) + "\n"))
    return len(sample), adr_problem


def cmd_review_pack(args, cfg):
    rec = load_record(args)
    cfg = config_for_record(rec, cfg)
    h = rec.header
    verdict = None
    if args.record_from_commit and not args.no_gate:
        buf = __import__("io").StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            gate_args = argparse.Namespace(**{**vars(args), "pre": False, "unit": True, "target_set": args.target_set})
            cmd_gate(gate_args, load_config())
        verdict = next((l for l in reversed(buf.getvalue().splitlines()) if l.startswith("GATE ")), None)
    path = args.out or (re.sub(r"\.record$", "", args.record) + ".review.md" if args.record
                        else root_path(f"{RECORD_DIR}/{h['unit_id']}.review.md"))
    k, adr_problem = review_pack(rec, cfg, path, verdict, at=args.record_from_commit)
    print(f"review pack: {show_path(path)} ({k} spot-check entries)" + (f" — {verdict}" if verdict else ""))
    if adr_problem:
        print(f"FAIL the pack lists no rendered ADR file: {adr_problem}")
        return FAIL
    return OK


# ------------------------------------------------------------------ preflight
def cmd_preflight(args, cfg):
    status = OK
    if repo_root() is None:
        _die("not inside a git repository")
    dirty = _dirty_outside_records()
    if dirty:
        print("FAIL: working tree not clean — commit the functional work first, never stash it (S101):")
        print("\n".join("  " + d for d in dirty[:20]))
        status = FAIL
    else:
        print("ok: working tree clean")
    hist = _history_record_problems(cfg)
    if hist:
        print("FAIL: consolidation commits at the tip carry no passing record (A8):")
        print("\n".join("  " + h for h in hist[:5]))
        status = FAIL
    try:
        up = git("rev-parse", "--abbrev-ref", "@{u}").strip()
        ahead, behind = (int(x) for x in git("rev-list", "--left-right", "--count", "HEAD...@{u}").split())
        if behind:
            print(f"FAIL: {behind} commit(s) on {up} are not in HEAD — pull before taking a baseline")
            status = FAIL
        print(f"note: {ahead} local commit(s) not on {up}; commits already on {up} are never amended")
    except RuntimeError:
        print("note: no upstream branch")
    me = git("config", "user.name").strip() if subprocess.run(["git", "config", "user.name"], capture_output=True).returncode == 0 else ""
    last = git("log", "-200", "--format=%H\x1f%an\x1f%s").splitlines()
    foreign = []
    for line in last:
        sha, author, subj = line.split("\x1f", 2)
        if subj.lower().startswith(CONSOLIDATION_COMMIT_MARKS):
            break
        if me and author != me:
            foreign.append(f"{sha[:8]} {author}: {subj}")
    if foreign:
        print("note: commits by other authors since the last consolidation commit — read them before taking the baseline:")
        print("\n".join("  " + f for f in foreign[:10]))
    print(f"baseline candidate: {head_sha()}")
    return status


# ------------------------------------------------------------------ escalate
def cmd_escalate(args, cfg):
    intake = intake_path(cfg, args.intake and user_path(args.intake))
    for flag, val in (("--observed", args.observed), ("--context", args.context), ("--ruling", args.ruling)):
        if val and any(c.isspace() for c in val):
            _die(f"{flag} must not contain whitespace: the intake bracket is space-delimited")
    with intake_lock(intake):
        lines = read_intake(intake)
        if args.close_applied:
            return _escalate_close_applied(args, cfg, intake, lines)
        if args.from_record:
            return _escalate_from_record(args, cfg, intake, lines)
        if args.standing:
            return _escalate_standing(args, intake, lines)
        if not args.file:
            _die("--file is required")
        rel = repo_rel(args.file)   # D6: the ref is the repo-relative path, however it was typed
        ref = f"{rel}:{args.line}" if args.line else (f"{rel}#{args.anchor}" if args.anchor else rel)
        fp = None
        if args.line:
            sha = args.baseline or head_sha()
            text = git_show(sha, repo_rel(args.file)) if sha else None
            if text is None:
                text = read_worktree(user_path(args.file))
                if text is not None:
                    _warn("fingerprint taken from the working tree: pass --baseline SHA to key on the baseline unit")
            fp = _fingerprint_at(text, args.file, args.line, cfg) if text is not None else None
            if text is None:
                # absent at the baseline, at HEAD and in the worktree: the entry is appended all
                # the same, but with no fingerprint it binds by line alone — say so, loud
                _warn(f"{rel} is absent at the baseline and in the working tree: the entry carries no "
                      "fingerprint and binds by line only")
        if args.fingerprint:
            fp = args.fingerprint
        observed = args.observed or head_sha(short=True) or "unknown"
        if args.rule:
            return _escalate_rule(args, cfg, intake, lines, ref, fp)
        if args.consume:
            if args.kind or args.divergence:
                _die("--consume takes neither --kind nor --divergence")
        elif not (args.kind and args.divergence):
            _die("escalate needs --kind and --divergence, or --consume, --rule, --standing or --from-record")
        # an entry is always created open: only `--rule`, on the owner's answer, rules it (R-gates 1)
        return _append_or_count(intake, lines, ref, fp, args.kind, args.divergence, observed,
                                args.context or "consolidation", "open", consume=args.consume)


def _unit_fingerprints(text, rel, cfg):
    """The fingerprints of the file's units under every comment and document unit rule."""
    out = set()
    for kind, rules in UNIT_RULES.items():
        if kind == "severance":
            continue
        for rule in rules:
            try:
                units = enumerate_file(text, rel, kind, rule, cfg)
            except LX.UnsupportedLanguage:
                continue
            lines = text.split("\n")
            for u, occ in zip(units, occurrences(lines, units)):
                out.add(fingerprint(rel, text, u.sl, u.el, occ, lines))
    return out


def _fingerprint_at(text, path, line, cfg):
    rel = repo_rel(path)
    for kind, rule in (("comment", "comment"), ("document", "document-paragraph")):
        try:
            units = enumerate_file(text, rel, kind, rule, cfg)
        except LX.UnsupportedLanguage:
            continue
        lines = text.split("\n")
        for u, occ in zip(units, occurrences(lines, units)):
            if u.sl <= line <= u.el:
                return fingerprint(rel, text, u.sl, u.el, occ, lines)
        if units or LX.language_for(rel):
            break
    if 0 < line <= len(text.split("\n")):
        return fingerprint(rel, text, line, line)
    return None


def _append_or_count(intake, lines, ref, fp, kind, divergence, observed, context, state, consume=False,
                     tbc=None):
    i, e = find_intake(lines, ref=ref, fp=fp)
    if e is not None and e["fields"].get("state") == "applied" and not consume:
        e = None   # the ruling was applied and closed: this unit is a new question (ADR 0014)
    if e is not None:
        if consume:
            if e["fields"].get("kind") != "obsolete-citation":
                print(f"refused: a pass consumes only an obsolete-citation event; {ref} is {e['fields'].get('kind')!r} (S125)")
                return FAIL
            if e["fields"].get("state") != "open":
                print(f"nothing to consume: {ref} is already {e['fields'].get('state')!r}")
                return OK
            e["fields"].update(state="ruled", ruling=observed)
            lines[i] = render_intake(e)
            write_intake(intake, lines)
            print(f"consumed: obsolete-citation at {ref} resolved to ruled at {observed}")
            return OK
        if e["fields"].get("kind") == "obsolete-citation" == kind:
            n = int(e["fields"].get("occurrences") or "1") + 1
            e["fields"].update(occurrences=str(n), latest=observed)
            if fp and not e["fields"].get("fingerprint"):
                e["fields"]["fingerprint"] = fp
            lines[i] = render_intake(e)
            write_intake(intake, lines)
            print(f"counted: obsolete-citation at {ref} now at {n} occurrence(s)")
            return OK
        if tbc and not e["fields"].get("tbc") and e["fields"].get("state") == "open":
            e["fields"]["tbc"] = tbc   # an open entry from before items were keyed learns its item
            lines[i] = render_intake(e)
            write_intake(intake, lines)
        print(f"suppressed: an entry already exists for {ref} (S122)\n  existing: {e['raw']}")
        if e["fields"].get("state") == "ruled" and e["fields"].get("kind") in RULABLE_KINDS:
            print(f"  it is ruled: when the ruling directs an edit, set this unit to `ruled → apply` "
                  f"with `ruling: {e['fields'].get('fingerprint') or ref}`")
        return OK
    if consume:
        print(f"nothing to consume: the intake holds no entry for {ref}")
        return FAIL
    fields = {"kind": kind, "state": state, "observed": observed, "context": context}
    if fp:
        fields["fingerprint"] = fp
    if tbc:
        fields["tbc"] = tbc
    if kind == "obsolete-citation":
        fields.update(occurrences="1", latest=observed)
    lines.append(render_intake({"date": date.today().isoformat(), "ref": ref,
                                "body": divergence.replace("\n", " "), "fields": fields}))
    write_intake(intake, lines)
    print(f"escalated {ref} → {intake}")
    return OK


def _escalate_from_record(args, cfg, intake, lines):
    rec = parse_record(record_file(args.from_record))
    h = rec.header
    kind_of = {_norm(DEFECT): "suspected-defect", _norm(NV): "unverifiable-statement"}
    ctx = f"consolidate-{h['pass_kind']}-{h['unit_id']}".replace(" ", "_")
    observed = h["baseline_sha"][:7]
    raised = {(e["ref"].split("#", 1)[0].partition(":")[0], e["fields"]["tbc"])
              for e in map(parse_intake_line, lines) if e and e["fields"].get("tbc")}
    # B3: a `conflicts:` pair is one panel question, raised by the carrier with both texts; the
    # partner's own entry is suppressed, whichever unit comes first
    partner = {}
    for u in rec.units:
        c = (u.get("conflicts") or "").strip()
        if c and any(x["id"] == c and x["file"] == u["file"] for x in rec.units):
            partner[(u["file"], c)] = u["id"]
    texts = {}
    n = 0
    for u in rec.units:
        kind = u.get("escalate") or kind_of.get(_norm(u.get("disposition")))
        if not kind:
            continue
        if kind not in ENTRY_KINDS:
            _die(f"unit {u['id']}: escalate kind {kind!r} is not one of {ENTRY_KINDS}")
        if (u["file"], u["id"]) in partner:
            print(f"unit {u['id']}: suppressed: the conflict partner of unit "
                  f"{partner[(u['file'], u['id'])]} carries the question")
            n += 1
            continue
        if u.get("in_tbc") == "yes":
            # an item of `## To be confirmed` was raised by its paragraph's entry; asking it again
            # is the loop S66 forbids
            base = texts.setdefault(u["file"], git_show(h["baseline_sha"], u["file"]) or "")
            if (u["file"], tbc_key(_unit_text(base, u))) in raised:
                print(f"unit {u['id']}: suppressed: the item is the open question of its paragraph's entry (S66)")
                n += 1
                continue
        text = (u.get("basis") or u.get("tbc") or u.get("preview") or "").strip()
        if _norm(u.get("disposition")) in FROZEN:
            text += " (frozen unit, byte-for-byte)"
        c = (u.get("conflicts") or "").strip()
        if c:
            t = next((x for x in rec.units if x["id"] == c and x["file"] == u["file"]), None)
            if t is not None:
                text += (f" | conflicts with unit {c} ({t['file']}:{t['lines']}): "
                         f"{(t.get('basis') or t.get('preview') or '').strip()}")
        ref = f"{u['file']}:{ulines(u)[0]}"
        item = tbc_key(u["tbc"]) if (u.get("tbc") or "").strip() and u.get("in_tbc") != "yes" else None
        print(f"unit {u['id']}: ", end="")
        if _append_or_count(intake, lines, ref, u.get("fingerprint"), kind, text, observed, ctx, "open",
                            tbc=item) == OK:
            n += 1
    # B4b: long units that no standing ruling covered — ask the panel once, stdout only
    longs = [int(m.group(1)) for u in rec.units
             for m in [re.search(r"\blong=(\d+)", u.get("facts") or "")]
             if m and _norm(u.get("disposition")) != _norm(COND)]
    if longs:
        print(f'question: {len(longs)} long unit(s) (max {max(longs)} lines) that no standing ruling '
              f'covered; to record one: escalate --standing --ruling-text "<the class and its keep-rules>"')
    print(f"ok: {n} escalation(s) processed from {args.from_record}")
    return OK


def close_applied(rec, lines):
    """Write on each ruling the units this record applied it to (`applied=fp:unit@baseline`); an
    entry whose own unit and every listed unit are applied is closed (`state=applied`). Returns
    the number of entries touched. Run after `gate --unit` passed (ADR 0014)."""
    h = rec.header
    me_unit, me_base = h["unit_id"], h["baseline_sha"][:7]
    touched = set()
    for u in rec.units:
        ruling = (u.get("ruling") or "").strip()
        if _norm(u.get("disposition")) != _norm(RULED) or not ruling:
            continue
        i, e = find_intake(lines, ref=ruling, fp=ruling if re.fullmatch(r"[0-9a-f]{8}", ruling) else None)
        if e is None or e["fields"].get("kind") not in RULABLE_KINDS:
            continue
        applied = parse_applied(e["fields"].get("applied"))
        applied.add((u["fingerprint"], me_unit, me_base))
        e["fields"]["applied"] = ",".join(f"{a}:{b}@{c}" for a, b, c in sorted(applied))
        efp = e["fields"].get("fingerprint")
        covered = {x for x in (e["fields"].get("units") or "").split(",") if x} | ({efp} if efp else set())
        # an entry with no content key binds by line, which another unit may occupy next: closed at once
        if e["fields"].get("state") == "ruled" and (not covered or covered <= {a[0] for a in applied}):
            e["fields"]["state"] = "applied"
        lines[i] = render_intake(e)
        touched.add(i)
    return len(touched)


def _escalate_close_applied(args, cfg, intake, lines):
    if not args.record_from_commit:
        _die("--close-applied takes --record-from-commit: the unit's record-carrying commit, after its gate passed")
    rec = record_from_commit(args.record_from_commit)
    n = close_applied(rec, lines)
    if n:
        write_intake(intake, lines)
    print(f"ok: {n} ruling(s) marked applied by {rec.header['unit_id']}")
    return OK


def _escalate_rule(args, cfg, intake, lines, ref, fp):
    if not args.ruling_text:
        _die("--rule needs --ruling-text: the owner's decision, as stated in the panel")
    i, e = find_intake(lines, ref=ref, fp=fp)
    if e is None:
        print(f"nothing to rule: the intake holds no entry for {ref}")
        return FAIL
    kind = e["fields"].get("kind")
    if kind == "obsolete-citation":
        print("refused: an obsolete-citation event is resolved by the consuming pass (--consume), not ruled")
        return FAIL
    if e["fields"].get("state") != "open":
        print(f"already {e['fields'].get('state')!r}: {e['raw']}")
        return OK
    if args.external and kind != "unverifiable-statement":
        _die("ruled-external is admissible only for the unverifiable-statement kind (S125)")
    if args.external and args.also_fingerprint:
        _die("--external records a pure keep, which directs no edit; an answer that rewrites further "
             "units is a ruling (`--rule` without --external) — ruled-external authorizes no `ruled → apply`")
    extra = sorted(set(args.also_fingerprint or []))
    for x in extra:
        if not re.fullmatch(r"[0-9a-f]{8}", x):
            _die(f"--also-fingerprint takes an 8-hex unit fingerprint, not {x!r}")
    if extra:
        # E8: the explicit unit list — the units, beyond the entry's own, that this ruling
        # covers; each one a unit of the entry's own file
        rfile = e["ref"].split("#", 1)[0].partition(":")[0]
        sha = args.baseline or head_sha()
        text = (git_show(sha, rfile) if sha else None) or read_worktree(rfile)
        known = _unit_fingerprints(text, rfile, cfg) if text is not None else set()
        stray = [x for x in extra if x not in known]
        if stray:
            _die(f"--also-fingerprint {', '.join(stray)}: not a unit of {rfile} at "
                 f"{(sha or 'the working tree')[:8]}; a ruling covers units of its own file only")
        e["fields"]["units"] = ",".join(extra)
    ruling = args.ruling or head_sha(short=True) or "unknown"
    e["fields"].update(state="ruled-external" if args.external else "ruled", ruling=ruling)
    owner = f"owner, units={_units_digest(e['fields'].get('fingerprint'), extra)}" if extra else "owner"
    e["body"] += f" — RULED {date.today().isoformat()} ({owner}): {args.ruling_text.replace(chr(10), ' ')}"
    lines[i] = render_intake(e)
    write_intake(intake, lines)
    print(f"ruled: {ref} → {e['fields']['state']} at {ruling}; cite it as `ruling: {e['fields'].get('fingerprint') or ref}`")
    return OK


def _escalate_standing(args, intake, lines):
    if not args.ruling_text:
        _die("--standing needs --ruling-text: the class of edit the owner authorizes, and its keep-rules")
    ident = "SR-" + hashlib.sha1(_norm(args.ruling_text).encode()).hexdigest()[:8]
    _, e = find_intake(lines, ident=ident)
    if e is not None:
        print(f"exists: {ident}\n  {e['raw']}")
        return OK
    ruling = args.ruling or head_sha(short=True) or "unknown"
    lines.append(render_intake({"date": date.today().isoformat(), "ref": f"standing-ruling:{ident}",
                                "body": args.ruling_text.replace("\n", " "),
                                "fields": {"kind": "standing-ruling", "state": "ruled", "ruling": ruling,
                                           "id": ident, "context": args.context or "owner-panel"}}))
    write_intake(intake, lines)
    print(f"standing ruling recorded: {ident} — cite it as `ruling: {ident}` on condense entries")
    return OK


def cmd_standing(args, cfg):
    intake = intake_path(cfg, args.intake and user_path(args.intake))
    n = 0
    for raw in read_intake(intake):
        e = parse_intake_line(raw)
        if e and e["fields"].get("kind") == "standing-ruling" and e["fields"].get("state") == "ruled":
            print(f"{e['fields'].get('id')}: {e['body']}")
            n += 1
    if not n:
        print("no standing rulings: condense is unavailable until the owner rules one")
    return OK


# ------------------------------------------------------------------ batch flow (ADR 0013)
def record_file(arg):
    """A record path as typed, or the master record of the batch id `arg`."""
    p = Path(user_path(arg))
    if p.is_file():
        return str(p)
    if not _UNIT_ID.match(arg or ""):
        _die(f"{arg!r}: no such record file, and not a batch id")
    pat = re.compile(re.escape(arg) + r"-[0-9a-f]{7}\.batch")
    found = sorted(f for f in Path(root_path(RECORD_DIR)).glob(f"{arg}-*.batch") if pat.fullmatch(f.name))
    if not found:
        _die(f"{arg!r}: no such record file, and no master record {RECORD_DIR}/{arg}-<sha7>.batch "
             f"(batch-init writes it)")
    if len(found) > 1:
        _die(f"batch {arg!r} has {len(found)} master records ({', '.join(f.name for f in found)}): name the file")
    return str(found[0])


def load_master(arg):
    path = record_file(arg)
    rec = parse_record(path)
    if rec.header.get("batch_master") != "yes":
        _die(f"{show_path(path)} is not a batch master record (batch-init writes one)")
    require_current(rec, show_path(path))
    missing = [f for f in REQUIRED_HEADER if not rec.header.get(f, "").strip()]
    if missing:
        _die(f"the master record header lacks {missing}")
    if not _UNIT_ID.fullmatch(rec.header["unit_id"]):
        # the batch id names files and is printed inside quoted shell lines
        _die(f"{show_path(path)}: unit_id {rec.header['unit_id']!r} is not a batch id — letters, digits, "
             f"'.', '_' and '-' only, as batch-init writes it; restore it")
    return path, rec


def _plan_path(master_path):
    return re.sub(r"\.batch$", "", master_path) + ".plan"


def _master_rel(mpath):
    """The master record's repository path. It lives under the record directory, where every
    review unit commits it (ADR 0015)."""
    rel = repo_rel(mpath)
    if not rel.startswith(RECORD_DIR + "/"):
        _die(f"{show_path(mpath)}: a master record lives under {RECORD_DIR}/, where every review unit commits it")
    return rel


def _unit_weight(u):
    """(judgements, projected changed lines) of one entry, as bound-check counts them."""
    d = _norm(u.get("disposition"))
    a, b = ulines(u)
    return (1 if d in JUDGEMENT else 0), (b - a + 1 if d in CHANGE_AUTHORIZED else 0)


def _cut_file(path, units, lo, hi, jcap, lcap, floor_line=None):
    """Contiguous `path:A-B` ranges of one file under both caps, bottom-up: the run order. A
    later range lies wholly above every earlier one, so the lines and occurrence indices of the
    ranges still to run never move. A cut never falls inside a unit, and the lower range keeps
    the lines between two units: removing its first unit (and a blank line beside it) touches no
    line above. `floor_line`: no cut below it — the `## To be confirmed` heading, where every
    later range's items land. No cut falls inside the line span of a unit and the unit its `of:`
    or `conflicts:` names: the part record checks the pair, so the span is one block — over a cap,
    it overflows as one unit does. Returns [((path, (A, B)), judgements, lines)]."""
    us = sorted(units, key=lambda u: (ulines(u)[0], uspan(u)))
    maxel, m = [], 0
    for u in us:
        m = max(m, ulines(u)[1])
        maxel.append(m)
    by_id = {u.get("id"): u for u in us}
    pairs = [(min(ulines(u)[0], ulines(t)[0]), max(ulines(u)[1], ulines(t)[1]))
             for u in us for f in REF_FIELDS for t in [by_id.get((u.get(f) or "").strip())] if t not in (None, u)]
    blocks = []   # [first, last] indices into us; a cut falls only between two blocks
    for i in range(len(us)):
        if blocks and any(s < maxel[i - 1] + 1 <= e for s, e in pairs):
            blocks[-1][1] = i
        else:
            blocks.append([i, i])
    out = []
    end, j, l, n = hi, 0, 0, 0
    for first, last in reversed(blocks):
        uj, ul = (sum(w) for w in zip(*(_unit_weight(us[x]) for x in range(first, last + 1))))
        if n and (j + uj > jcap or l + ul > lcap):
            cut = maxel[last] + 1
            if cut <= ulines(us[last + 1])[0] and (floor_line is None or cut <= floor_line):
                out.append(((path, (cut, end)), j, l))
                end, j, l, n = cut - 1, 0, 0, 0
        j, l, n = j + uj, l + ul, n + 1
    out.append(((path, (lo, end)), j, l))
    return out


def batch_plan(rec, cfg):
    """(parts, nil, empty) for a master record. `parts`: [[scope entries, judgements, lines]] in
    run order — whole files packed greedily under REMOVAL_JUDGEMENT_CAP and the projected
    REMOVED_LINE_CAP, a file over a cap cut by `_cut_file`. `nil`: the scope entries whose files
    the batch leaves unchanged — one final unit that commits only its record (S169). `empty`:
    scope files with no unit, in no part. Deterministic: the same record plans the same units."""
    h = rec.header
    jcap, lcap = cfg["REMOVAL_JUDGEMENT_CAP"], cfg["REMOVED_LINE_CAP"]
    by_file = {}
    for u in rec.units:
        by_file.setdefault(u["file"], []).append(u)
    exp = expected_texts(rec)
    items, nil, empty = [], [], []
    for path, rng in parse_scope(h["scope"]):
        us = by_file.get(path, [])
        base, new = exp[path]
        if not us:
            empty.append(path)
            continue
        if base == new:
            nil.append((path, rng))
            continue
        j, l = (sum(w) for w in zip(*map(_unit_weight, us)))
        if j <= jcap and l <= lcap:
            items.append(([(path, rng)], j, l))
            continue
        contents = split_lines(base)[0]
        floor = None
        if h["pass_kind"] == "document" and any(_norm(u.get("disposition")) == _norm(NV) and (u.get("tbc") or "").strip()
                                                and u.get("in_tbc") != "yes" for u in us):
            k = _tbc_heading_index(contents)
            floor = k + 1 if k is not None else None
        lo, hi = rng or (1, len(contents))
        for entry, cj, cl in _cut_file(path, us, lo, hi, jcap, lcap, floor):
            if cj > jcap or cl > lcap:
                _die(f"{path}:{entry[1][0]}-{entry[1][1]} holds {cj} judgement(s) and {cl} projected line(s) "
                     f"and admits no cut under the caps ({jcap}, {lcap}): a unit longer than the line cap, "
                     f"units sharing lines, or the tail from the `## To be confirmed` heading — narrow the "
                     f"batch scope (S81)")
            items.append(([entry], cj, cl))
    parts = []
    for scope, j, l in items:
        last = parts[-1] if parts else None
        if (last and last[1] + j <= jcap and last[2] + l <= lcap
                and not {p for p, _ in scope} & {p for p, _ in last[0]}):
            last[0] += scope
            last[1] += j
            last[2] += l
        else:
            parts.append([list(scope), j, l])
    return parts, nil, empty


def _ukey(u):
    return u["file"], u["fingerprint"], u["lines"], u["span"]


def _judged(u, f, by_id):
    """A judgement field as two records of one batch compare it: an `of:` or `conflicts:` id is
    record-local, so it compares as the key of the unit it names."""
    v = (u.get(f) or "").strip()
    t = by_id.get(v) if f in REF_FIELDS and v else None
    return _ukey(t) if t is not None and t["file"] == u["file"] else v


_PARSED = {}


def _parsed_once(text):
    """parse_record_text(text), shared and read only: a master record committed with every
    review unit is one text, parsed once."""
    key = hashlib.sha1(encode(text)).hexdigest()
    if key not in _PARSED:
        if len(_PARSED) >= 32:
            _PARSED.clear()
        _PARSED[key] = parse_record_text(text)
    return _PARSED[key]


def _is_ancestor(a, b):
    """`git merge-base --is-ancestor a b`; remembered when both are full shas."""
    def get():
        return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], capture_output=True).returncode == 0
    return _memo("ancestor", (a, b), get) if _full(a, b) else get()


def batch_carry_problems(rec, at):
    """A review unit of a batch carries the master record's judgement, unit for unit (ADR 0015):
    the master record committed with it, at `at`, holds exactly the units of its scope — the
    file, or the range of a cut file — with the same judgement, and the last-verified-at the
    master's baseline gives. A part record is derived, never edited."""
    name = rec.header.get("batch")
    if not name:
        return []
    text = git_show(at, name)
    if text is None:
        return [f"batch: the master record {name} is not committed with this review unit"]
    m = _parsed_once(text)
    mh = m.header
    if m.problems or mh.get("batch_master") != "yes":
        return [f"batch: {name} is not a readable master record"]
    probs = [f"batch: {k} {rec.header.get(k)!r} differs from the master record's {mh.get(k)!r}"
             for k in ("pass_kind", "unit_rule", "record_version") if rec.header.get(k) != mh.get(k)]
    if not _is_ancestor(mh.get("baseline_sha", ""), rec.header["baseline_sha"]):
        probs.append("batch: the master record's baseline is not an ancestor of this unit's baseline")
    mscope = dict(parse_scope(mh.get("scope")))
    want = {}
    for path, rng in parse_scope(rec.header.get("scope")):
        if path not in mscope:
            probs.append(f"batch: {path} is not in the batch scope")
        for u in m.units:
            if u["file"] == path and (rng is None or rng[0] <= ulines(u)[0] <= rng[1]):
                want[_ukey(u)] = u
    got = {_ukey(u): u for u in rec.units}
    gid, mid = {u["id"]: u for u in rec.units}, {u["id"]: u for u in m.units}
    for k in sorted(want.keys() - got.keys()):
        probs.append(f"batch: master unit {want[k]['id']} ({k[0]}:{k[2]}) is missing from this review unit")
    for k in sorted(got.keys() - want.keys()):
        probs.append(f"batch: unit {got[k]['id']} ({k[0]}:{k[2]}) is no unit the master record gives this scope")
    for k in sorted(got.keys() & want.keys()):
        diff = [f for f in JUDGEMENT_FIELDS if _judged(got[k], f, gid) != _judged(want[k], f, mid)]
        if diff:
            probs.append(f"batch: unit {got[k]['id']} ({k[0]}:{k[2]}): {', '.join(diff)} differ from the master "
                         f"record's unit {want[k]['id']} — correct the master record, never a part record")
    sha, files = lva_spec(rec)
    if files and sha != mh.get("baseline_sha"):
        probs.append("batch: last_verified_at must name the master record's baseline (S98)")
    probs += [f"batch: last_verified_at names {f}, which the master record scopes as a range (S100)"
              for f in files if mscope.get(f, ()) is not None]
    return probs


def cmd_batch_carry_check(args, cfg):
    rec = load_record(args)
    probs = batch_carry_problems(rec, args.record_from_commit or TIP)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        return FAIL
    print(f"ok: every unit carries the judgement of the master record {rec.header['batch']}")
    return OK


def _one_record(recs):
    """The record a commit materializes — one, though it may sit in the message and as a file."""
    texts = {render_record(r, guide=False).strip() for r in recs}
    return recs[0] if len(texts) == 1 else None


_REVERT_SUBJECT = re.compile(r"consolidation: revert batch (\S+) units (\d+)\.\.(\d+)")


def batch_chain(master, mrel):
    """The batch's review units done, read from git, never from a file the agent can edit
    (ADR 0015). Every commit on the first-parent line from the batch baseline to HEAD is one
    batch-next made: a record-carrying commit per unit — in the committed-file channel, a
    content commit and then its record commit — whose record names this batch, the id `B.k` and,
    as its baseline, the commit that ended unit k-1. A `consolidation: revert batch <bid> units
    <k>..<n>` commit (the line batch-revert prints) is neither a unit nor pending: the next
    unit's baseline names it. The batch ends at the review unit after which no unit of the master
    record remains: the commits after it are the owner's, reported and never judged. Returns
    ([{"k", "commit", "content", "record"}], pending, later) — `content` is the unit's content
    commit in the committed-file channel, else None — `pending` is a last content commit whose
    record commit is missing; `later` is None while the batch is open, else the commits after
    its last review unit."""
    bid, base0 = master.header["unit_id"], master.header["baseline_sha"]
    head = git("rev-parse", "HEAD").strip()
    if head != base0 and subprocess.run(["git", "merge-base", "--is-ancestor", base0, head],
                                        capture_output=True).returncode:
        _die(f"the batch baseline {base0[:8]} is not an ancestor of HEAD {head[:8]}")
    done, expect, pending = [], base0, None
    log = [l.partition(" ")[::2] for l in
           git("log", "--reverse", "--first-parent", "--format=%H %s", f"{base0}..{head}").splitlines() if l]
    for i, (c, subject) in enumerate(log):
        if not batch_remaining(master, done).units:
            return done, None, [x for x, _ in log[i:]]
        recs = _materialized_records(c)
        k = len(done) + 1
        subject = subject.strip()
        rv = _REVERT_SUBJECT.fullmatch(subject)
        # a revert that also touches the record directory is a forgotten `git checkout HEAD --
        # .consolidation` before the commit: it would silently discard the master's corrections to
        # units still to run, so the revert condition declines it and the commit falls through to
        # pending below — batch-next stops on it as a content commit whose record commit is missing
        if rv and not recs and pending is None and rv.group(1) == bid \
                and 1 <= int(rv.group(2)) <= int(rv.group(3)) <= len(done) \
                and not any(f == RECORD_DIR or f.startswith(RECORD_DIR + "/")
                            for f in changed_files(f"{c}^", c)):
            expect, pending = c, None   # B5: the revert of units k..n; the next unit's baseline names it
            continue
        if not recs and pending is None and not subject.lower().startswith("mechanical:"):
            pending = c
            continue
        r = _one_record(recs) if recs else None
        h = r.header if r else {}
        if (h.get("unit_id"), h.get("baseline_sha"), h.get("batch")) != (f"{bid}.{k}", expect, mrel):
            _die(f"commit {c[:8]} ({subject!r}) is not review unit {bid}.{k}: from the batch baseline to HEAD "
                 f"only the commits batch-next makes may sit (ADR 0015) — reset to {expect[:8]}, then "
                 f"batch-next --batch {bid}")
        done.append({"k": k, "commit": c, "content": pending, "record": r})
        expect, pending = c, None
    return done, pending, (None if pending or batch_remaining(master, done).units else [])


def batch_remaining(master, done):
    """The master record restricted to what no done review unit covers. A cut file's ranges run
    bottom-up, so what remains of it is one range at its top."""
    cover = {}
    for d in done:
        for path, rng in parse_scope(d["record"].header["scope"]):
            cover.setdefault(path, []).append(rng)
    base = master.header["baseline_sha"]
    scope = []
    for path, rng in parse_scope(master.header["scope"]):
        rs = cover.get(path)
        if not rs:
            scope.append((path, rng))
            continue
        if None in rs:
            continue
        lo, hi = rng or (1, len(split_lines(git_show(base, path) or "")[0]))
        rs = sorted(rs)
        if any(x[1] + 1 != y[0] for x, y in zip(rs, rs[1:])) or rs[-1][1] != hi or rs[0][0] < lo:
            _die(f"{path}: the done review units cover {render_scope([(path, r) for r in rs])}, which is not the "
                 f"bottom of its batch range {lo}-{hi}")
        if rs[0][0] > lo:
            scope.append((path, (lo, rs[0][0] - 1)))

    def inside(u):
        return any(u["file"] == p and (r is None or r[0] <= ulines(u)[0] <= r[1]) for p, r in scope)
    return Record(dict(master.header, scope=render_scope(scope)), [u for u in master.units if inside(u)])


def _next_part(master, done, cfg):
    """(scope entries, nil, units left) of the next review unit — the first of the plan cut from
    what remains, so a correction of units not yet applied re-plans only those — or (None, …)."""
    parts, nil, _ = batch_plan(batch_remaining(master, done), cfg)
    left = len(parts) + (1 if nil else 0)
    if parts:
        return parts[0][0], False, left
    return (nil, True, left) if nil else (None, False, 0)


def _master_problems(master, mrel, done, cfg):
    """The master record passes its gate, and a correction made after a review unit ran
    touches no unit a done review unit applied (ADR 0015): its header is the one committed with
    every done unit, and each unit keeps the judgement the part record that applied it carries —
    what was applied, not a master copy a hand-made unit commit could carry changed. Once a unit
    is done, the intake is left to each review unit's own gate: the rulings the done units applied
    are closed, and the master record never binds a ruling itself."""
    probs = record_problems(master, cfg, check_intake=not done)
    if probs or not done:
        return probs
    for d in done:
        text = git_show(d["commit"], mrel)
        if text is None:
            return [f"{mrel} is not committed with review unit {d['record'].header['unit_id']}"]
        if _parsed_once(text).header != master.header:
            return ["the master record's header changed after a review unit ran: start a new batch for the rest"]
    now = {_ukey(u): u for u in master.units}
    mid = {u["id"]: u for u in master.units}
    moved = []
    for d in done:
        did = {u["id"]: u for u in d["record"].units}
        for u in d["record"].units:
            m = now.get(_ukey(u), {})
            if any(_judged(u, f, did) != _judged(m, f, mid) for f in JUDGEMENT_FIELDS):
                moved.append(m.get("id") or f"{u['file']}:{u['lines']}")
    if moved:
        return [f"master unit(s) {', '.join(moved)} changed after a done review unit applied them: a correction "
                f"touches only units not yet applied — restore them"]
    # an ADR's number is its rank among the master's adr_text units: a correction that adds or drops
    # one before an applied ADR would number a later ADR onto an applied one
    for d in done:
        was = adr_files(d["record"], cfg, at=d["commit"])
        now_files = adr_files(d["record"], cfg)
        if was != now_files:
            return [f"a correction renumbers the ADR(s) review unit {d['record'].header['unit_id']} wrote "
                    f"({', '.join(p for p, _ in sorted(was.values()))}): an `adr_text` unit is added or dropped only "
                    f"after every applied one"]
    return []


def _quiet(fn, ns, cfg):
    """Run a subcommand with its output captured: (exit code, output)."""
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        try:
            r = fn(ns, cfg)
        except Die as e:
            print(f"FAIL {e}")
            r = FAIL
    return r, buf.getvalue()


def _gate_ns(**kw):
    return argparse.Namespace(**{"record": None, "record_from_commit": None, "batch": None, "pre": False,
                                 "unit": False, "target_set": None, "no_intake": False, **kw})


def _master_files(bid):
    pat = re.compile(re.escape(bid) + r"-[0-9a-f]{7}\.batch")
    return sorted(f.name for f in Path(root_path(RECORD_DIR)).glob(f"{bid}-*.batch") if pat.fullmatch(f.name))


def _next_free_batch_id():
    used = [int(m.group(1)) for f in Path(root_path(RECORD_DIR)).glob("B-*.batch")
            for m in [re.fullmatch(r"B-(\d+)-[0-9a-f]{7}\.batch", f.name)] if m]
    return f"B-{max(used, default=0) + 1}"


def cmd_batch_init(args, cfg):
    """The master record. A batch id names one batch: an id that already has a master record, at
    any baseline, is refused without --force. --carry-from copies an earlier record's judgement
    (a path or a batch id) onto the units equal in file and fingerprint, as record-init does."""
    bid = args.batch_id
    if getattr(args, "out", None) and not repo_rel(args.out).startswith(RECORD_DIR + "/"):
        _die(f"{show_path(args.out)}: a master record lives under {RECORD_DIR}/, where every review unit commits it")
    used = _master_files(bid)
    if used and not args.force:
        _die(f"batch id {bid!r} already has a master record ({', '.join(used)}): a new batch takes a new id — "
             f"the next free one is {_next_free_batch_id()} (--force overwrites)")
    carry = record_file(args.carry_from) if args.carry_from else None
    ns = argparse.Namespace(**{**vars(args), "unit_id": bid, "carry_from": carry})
    r = cmd_record_init(ns, cfg)
    if getattr(ns, "_uncarried", None):
        print(f"next: classify the {len(ns._uncarried)} uncarried stub(s) (record-shard / record-fill for workers), "
              f"then gate --pre --batch {bid}")
    elif carry:
        print(f"next: gate --pre --batch {bid}")
    else:
        print(f"next: classify every stub (record-shard / record-fill for workers), then gate --pre --batch {bid}")
    return r


def cmd_batch_run(args, cfg):
    """batch-next, again and again, in this process: it stops at the first stop (exit 1), right
    after a review unit that asks for the test suite before the batch end, and at the batch end.
    Every unit's output is printed as it ends."""
    global TIP
    n = 0
    while True:
        cwd, tip, head = os.getcwd(), TIP, head_sha()
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            try:
                r = cmd_batch_next(args, cfg)
            except (Die, RuntimeError) as e:
                print(f"error: {e}")
                r = FAIL
        os.chdir(cwd)
        TIP = tip
        out = buf.getvalue()
        print(out.rstrip(), flush=True)
        if r != OK:
            print(f"batch-run: stopped after {n} review unit(s) — do what the STOP says, then batch-run again")
            return r
        if re.search(r"^batch \S+ complete", out, re.M):
            return OK
        if head_sha() == head:
            print("batch-run: batch-next committed nothing and did not end the batch — stopped")
            return FAIL
        n += 1
        if any(l.startswith("SUITE: run the test suite now") and "the batch end" not in l for l in out.splitlines()):
            print(f"batch-run: stopped after {n} review unit(s) — run the test suite now, then batch-run again")
            return OK


def cmd_batch_plan(args, cfg):
    """Print the review units in run order: those done (read from git) and the plan cut from
    what remains. The `.plan` file is a display copy; batch-next never reads it."""
    mpath, master = load_master(args.batch)
    mrel = _master_rel(mpath)
    bid = master.header["unit_id"]
    mcfg = config_for_record(master, cfg)
    done = batch_chain(master, mrel)[0]
    probs = _master_problems(master, mrel, done, mcfg)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        print(f"batch-plan refused: gate --pre --batch {bid} must pass first")
        return FAIL
    parts, nil, empty = batch_plan(batch_remaining(master, done), mcfg)
    m = len(done) + len(parts) + (1 if nil else 0)
    out = ["# consolidation batch plan — a display copy: batch-next recomputes it from the master record and git",
           f"batch: {bid}", f"master: {mrel}", f"baseline_sha: {master.header['baseline_sha']}"]
    out += [f"part {d['k']}/{m}: {bid}.{d['k']} | done {d['commit'][:8]} | scope: {d['record'].header['scope']}"
            for d in done]
    out += [f"part {k}/{m}: {bid}.{k} | judgements {j} | lines {l} | scope: {render_scope(sc)}"
            for k, (sc, j, l) in enumerate(parts, len(done) + 1)]
    if nil:
        out.append(f"part {m}/{m}: {bid}.{m} | nil | scope: {render_scope(nil)}")
    if empty:
        out.append("# no unit, in no part: " + ", ".join(empty))
    plan_path = _plan_path(mpath)
    Path(plan_path).write_bytes(encode("\n".join(out) + "\n"))
    print("\n".join(out[4:]))
    print(f"plan: {show_path(plan_path)} — {m} review unit(s) under the caps "
          f"({mcfg['REMOVAL_JUDGEMENT_CAP']} judgements, {mcfg['REMOVED_LINE_CAP']} lines)")
    print(f"next: batch-next --batch {bid}")
    return OK


def _batch_part_init(master, mrel, k, scope, base, cfg, root):
    """Write review unit k's record at `base`, derived from the master record: the master's
    judgement on every unit, the batch's name, and the last-verified-at of each whole document
    whose last range this is (S100). The carry is exact, never a guess: the unit's lines — the
    whole file, or lines 1..B of a range — must be byte-identical to the batch baseline (earlier
    units changed only lines below them), so every unit keeps its lines, span and fingerprint.
    Returns (record path, record)."""
    h = master.header
    old, bid = h["baseline_sha"], h["unit_id"]
    for path, rng in scope:
        a, b = git_show(old, path), git_show(base, path)
        keep = rng[1] if rng else None
        if a is None or b is None or a.split("\n")[:keep] != b.split("\n")[:keep]:
            _die(f"{path}: {f'lines 1-{keep}' if keep else 'the file'} changed since the batch baseline "
                 f"{old[:8]}, so the plan no longer holds for review unit {bid}.{k}; finish the batch by hand "
                 f"from the master record (runner.md, `--carry-from`)")
    targets = [t.strip() for t in h.get("targets", "").split(",") if t.strip()]
    observed = h.get("floor_observed")
    ns = argparse.Namespace(
        pass_kind=h["pass_kind"], unit_id=f"{bid}.{k}", batch_id=None, unit_rule=h["unit_rule"],
        scope=[(root / p).as_posix() + (f":{r[0]}-{r[1]}" if r else "") for p, r in scope],
        narrowing_reason=f"bound-driven split: batch {bid} review unit {k}",
        target=[(root / t).as_posix() for t in targets] or None, floor=h.get("floor"),
        floor_observed=None if observed == old else observed, out=None, force=True, carry_from=None)
    r, out = _quiet(cmd_record_init, ns, cfg)
    if r != OK:
        print(out.rstrip())
        _die(f"record-init failed for review unit {bid}.{k}")
    rec = parse_record(ns._out)
    by_key = {_ukey(u): u for u in master.units}
    lost = []
    for u in rec.units:
        s = by_key.get(_ukey(u))
        if not s or not _norm(s.get("disposition")):
            lost.append(u["id"])
            continue
        for f in JUDGEMENT_FIELDS:
            u.pop(f, None)
            if s.get(f) is not None:
                u[f] = s[f]
    if lost:
        _die(f"unit(s) {', '.join(lost)} of review unit {bid}.{k} match no classified unit of the master record: "
             f"the plan no longer holds")
    # an `of:` / `conflicts:` id is record-local: name the same unit by this record's id (the cut
    # keeps both units of a pair in one review unit)
    mby, pid = {u["id"]: u for u in master.units}, {_ukey(u): u["id"] for u in rec.units}
    for u in rec.units:
        for f in REF_FIELDS:
            v = (u.get(f) or "").strip()
            t = mby.get(v) if v else None
            if v and (t is None or t["file"] != u["file"] or _ukey(t) not in pid):
                _die(f"unit {u['id']} of review unit {bid}.{k}: `{f}: {v}` names a master unit this review unit "
                     f"does not hold: the plan no longer holds")
            if v:
                u[f] = pid[_ukey(t)]
    rec.header["batch"] = mrel
    rec.header.pop("last_verified_at", None)
    mscope = dict(parse_scope(h["scope"]))
    lva = [p for p, rg in scope if mscope.get(p, ()) is None and (rg is None or rg[0] == 1)]
    if h["pass_kind"] == "document" and cfg.get("last_verified_at") and lva:
        rec.header["last_verified_at"] = f"{old} {', '.join(lva)}"
    write_record(rec, ns._out)
    return ns._out, rec


def _git_step(*args):
    r = subprocess.run(["git", *args], capture_output=True)
    return r.returncode, _decode_output(r.stdout + r.stderr).strip()


def _undo(g, base, changed, bid, cfg):
    """The lines that return the tree to `base`: every file a runner step or a hook changed. An
    ADR the baseline lacks is never listed for deletion: the agent wrote it for this unit, and
    the next run needs it again."""
    out = git("diff", "--name-only", "--no-renames", "-z", base)
    files = sorted({*changed, *(f for f in out.split("\0") if f and not f.startswith(RECORD_DIR + "/"))})
    keep = [f for f in files if git_show(base, f) is not None]
    adr = cfg["adr_dir"].rstrip("/") + "/"
    extra = [f for f in files if f not in keep and not f.startswith(adr)]
    return (f"undo: {g} reset --mixed {base[:8]}" + (f" && {g} restore -- {' '.join(_q(p) for p in keep)}" if keep else "")
            + (f"\n      and delete what the baseline lacks: {', '.join(extra)}" if extra else "")
            + f"\n      then batch-next --batch {bid}")


def _batch_verify(done, args, cfg):
    """Gate each done review unit at its own commit with the unit gate's commit checks: every run
    re-gates the last one, so no unit is stacked on one that failed its gate, and the batch end
    re-gates them all, so an earlier unit amended and the chain rebuilt on it is caught before
    the batch is complete. A unit this command already gated is not gated again."""
    for d in done:
        if (d["commit"], args.target_set) in _GATED_UNITS:
            continue
        with _at_tip(d["commit"]):
            r, out = _quiet(cmd_gate, _gate_ns(record_from_commit=d["commit"], unit=True, at_commit=True,
                                               target_set=args.target_set), cfg)
        if r == FAIL:
            return d, out
        _GATED_UNITS.add((d["commit"], args.target_set))
    return None, ""


def cmd_batch_next(args, cfg):
    """Run the batch's next review unit end to end: derive its record from the master record,
    gate --pre, apply, commit it with the master record (the hooks run), gate --unit, close the
    rulings it applied, write its review pack. Every run reads where the batch stands from git
    (ADR 0015); a stop prints what to do, then batch-next runs again. When no unit remains it
    replays every unit at its own commit before it reports the batch complete; the commits after
    a complete batch's last unit are reported, never judged or undone."""
    mpath, master = load_master(args.batch)
    mrel = _master_rel(mpath)
    bid = master.header["unit_id"]
    mcfg = config_for_record(master, cfg)
    root = Path(repo_root() or os.getcwd()).resolve()
    g = f"git -C {_q(root.as_posix())}"
    rel = lambda p: root_rel(p, root)
    done, pending, later = batch_chain(master, mrel)
    base = done[-1]["commit"] if done else master.header["baseline_sha"]
    if pending:
        print(f"STOP: {pending[:8]} is a content commit whose record commit is missing (a failed commit?)")
        print(_undo(g, base, [], bid, mcfg))
        return FAIL
    if later is not None:
        probs = _master_problems(master, mrel, done, mcfg)
        if probs:
            for p in probs:
                print(f"FAIL {p}")
            print(f"STOP: the master record {show_path(mpath)} differs from the one the batch ran: restore it")
            return FAIL
        return _batch_end(master, done, args, cfg, later)
    if done:
        last = done[-1]
        lrec = last["record"]
        bad, out = _batch_verify([last], args, cfg)
        if bad:
            print(out.rstrip())
            prev = done[-2]["commit"] if len(done) > 1 else master.header["baseline_sha"]
            print(f"STOP: review unit {lrec.header['unit_id']} ({last['commit'][:8]}) does not pass its gate")
            print(_undo(g, prev, [], bid, mcfg))
            return FAIL
    # a rename by both its sides, never an `a -> b` composite that names no path anyone can act on
    dirty = [p for xy, new, old in status_entries() if (xy, new) != ("??", ".consolidation.json")
             for p in (new, old) if p and not _is_output(p, mcfg)]
    if dirty:
        print(f"STOP: the tree differs from {base[:8]} outside the outputs: {', '.join(dirty[:10])}")
        print(_undo(g, base, [], bid, mcfg))
        return FAIL
    probs = _master_problems(master, mrel, done, mcfg)
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        print(f"STOP: correct the master record {show_path(mpath)}, run gate --pre --batch {bid}, then batch-next --batch {bid}")
        return FAIL
    scope, nil, left = _next_part(master, done, mcfg)
    if scope is None:
        return _batch_end(master, done, args, cfg, [])
    k, m = len(done) + 1, len(done) + left
    tag = f"part {k}/{m} ({bid}.{k})"
    rec_path, rec = _batch_part_init(master, mrel, k, scope, base, mcfg, root)
    print(f"{tag}: record {rel(rec_path)}, {len(rec.units)} unit(s), scope {render_scope(scope)}")
    r, out = _quiet(cmd_gate, _gate_ns(record=rec_path, pre=True, target_set=args.target_set), cfg)
    if r == FAIL:
        print(out.rstrip())
        print(f"STOP: {tag}: gate --pre failed — the record is the master record's judgement: correct the master "
              f"record, run gate --pre --batch {bid}, then batch-next --batch {bid}")
        return FAIL
    print(f"{tag}: gate --pre passed")
    rcfg = config_for_record(rec, cfg)
    adrs = unit_adrs(rec)
    missing = [a for a in adrs if not (root / a).is_file()]
    if missing:
        print(f"STOP: write the ADR file(s) {', '.join(missing)} (each at the `adr:` path its unit names), then batch-next --batch {bid}")
        return FAIL
    changed, writes = apply_plan(rec, rcfg)
    msg_path, content_path = write_unit(rec, rec_path, rcfg, writes)
    if not changed:
        steps = [("add", "-f", "--", rec_path, mpath), ("commit", "-F", msg_path)]
    elif rcfg["record_channel"] == "file":
        steps = [("add", "--", *changed, *adrs), ("commit", "-F", content_path),
                 ("add", "-f", "--", rec_path, mpath), ("commit", "-F", msg_path)]
    else:
        steps = [("add", "--", *changed, *adrs), ("add", "-f", "--", mpath), ("commit", "-F", msg_path)]
    for s in steps:
        code, out = _git_step(*s)
        if code:
            print(out)
            print(f"STOP: {tag}: git {s[0]} failed (a hook?)")
            print(_undo(g, base, changed, bid, mcfg))
            return FAIL
    commit = git("rev-parse", "HEAD").strip()
    print(f"{tag}: committed {commit[:8]}" + (f" ({len(changed)} file(s))" if changed else " (record only)"))
    rewritten = _hook_rewrites(commit, changed, writes)
    if rewritten:
        print(f"STOP: {tag}: {', '.join(rewritten)} at {commit[:8]} differ from what apply wrote: a commit hook "
              f"rewrote them — a review unit commits only the runner's edits")
        print(_undo(g, base, changed, bid, mcfg))
        return FAIL
    r, out = _quiet(cmd_gate, _gate_ns(record_from_commit=commit, unit=True, target_set=args.target_set), cfg)
    verdict = next((l for l in reversed(out.splitlines()) if l.startswith("GATE ")), "GATE FAILED")
    if r == FAIL:
        print(out.rstrip())
        print(f"STOP: {tag}: gate --unit failed — a reviewer never substitutes for a control (S163)")
        print(_undo(g, base, changed, bid, mcfg))
        return FAIL
    rec = record_from_commit(commit)
    _GATED_UNITS.add((commit, args.target_set))
    gated = render_record(rec, guide=False).strip()
    recs = _materialized_records(commit)
    if recs and all(render_record(x, guide=False).strip() == gated for x in recs):
        _remember_verified(commit)   # the history walk's checks are part of the gate just passed (ADR 0016)
    rcfg = config_for_record(rec, cfg)
    n = 0
    if any(_norm(u.get("disposition")) == _norm(RULED) for u in rec.units):
        ipath = intake_path(rcfg)
        with intake_lock(ipath):
            lines = read_intake(ipath)
            n = close_applied(rec, lines)
            if n:
                write_intake(ipath, lines)
    pack = re.sub(r"\.record$", "", rec_path) + ".review.md"
    review_pack(rec, rcfg, pack, verdict)   # the gate just passed derived the same ADR paths
    print(f"{tag}: {verdict} — commit {commit[:8]}" + (f"; {n} ruling(s) marked applied" if n else ""))
    print(f"review pack: {rel(pack)}")
    suite = next((l for l in out.splitlines() if l.startswith("SUITE:")), None)
    if suite:
        print(suite)
    done, _, later = batch_chain(master, mrel)
    if later is None:
        print(f"next: batch-next --batch {bid}")
        return OK
    return _batch_end(master, done, args, cfg, later)


def _hook_rewrites(commit, changed, writes):
    """The files whose blob at `commit` is not what apply wrote, through git's own filters."""
    paths = [p for p in changed if p in writes]
    if not paths:
        return []
    tree = {}
    for l in git("ls-tree", "-z", "--full-name", commit, "--", *paths).split("\0"):
        meta, _, path = l.partition("\t")
        if path:
            tree[path] = meta.split()[2]
    out = []
    for p in paths:
        r = subprocess.run(["git", "hash-object", f"--path={p}", "--stdin"], input=encode(writes[p]),
                           capture_output=True)
        if tree.get(p) != _decode_output(r.stdout).strip():
            out.append(p)
    return out


def _pack_of(d):
    h = d["record"].header
    return f"{RECORD_DIR}/{h['unit_id']}-{h['baseline_sha'][:7]}.review.md"


def _batch_end(master, done, args, cfg, later):
    bid = master.header["unit_id"]
    bad, out = _batch_verify(done, args, cfg)
    if bad:
        print(out.rstrip())
        print(f"STOP: review unit {bad['record'].header['unit_id']} ({bad['commit'][:8]}) fails its gate at its own "
              f"commit: reset to the commit before it, then batch-next --batch {bid}")
        return FAIL
    print(f"batch {bid} complete: {len(done)} review unit(s), each replayed at its own commit")
    if later:
        print(_later_line(master, done, later))
    if master.header["pass_kind"] == "comment" and config_for_record(master, cfg)["suite_cadence"] == "batch":
        print("SUITE: run the test suite now — the batch end (suite_cadence=batch)")
    print("review packs, in order: " + ", ".join(_pack_of(d) for d in done))
    return OK


def _later_line(master, done, later):
    end = done[-1]["commit"] if done else master.header["baseline_sha"]
    return f"batch {master.header['unit_id']} complete; {len(later)} later commit(s) after {end[:7]}"


def cmd_batch_status(args, cfg):
    """Where the batch stands, read from git and the master record — and the next command."""
    mpath, master = load_master(args.batch)
    mrel = _master_rel(mpath)
    bid = master.header["unit_id"]
    mcfg = config_for_record(master, cfg)
    print(f"batch {bid}: master {show_path(mpath)}, baseline {master.header['baseline_sha'][:8]}, "
          f"{len(master.units)} unit(s)")
    done, pending, later = batch_chain(master, mrel)
    probs = _master_problems(master, mrel, done, mcfg)
    parts, nil = ([], []) if probs else batch_plan(batch_remaining(master, done), mcfg)[:2]
    m = len(done) + len(parts) + (1 if nil else 0)
    for d in done:
        print(f"  {d['k']}/{m} {bid}.{d['k']}  done     {d['commit'][:8]}  pack {_pack_of(d)}  — "
              f"{d['record'].header['scope']}")
    for k, (sc, _, _) in enumerate(parts, len(done) + 1):
        print(f"  {k}/{m} {bid}.{k}  pending  — {render_scope(sc)}")
    if nil:
        print(f"  {m}/{m} {bid}.{m}  pending  — nil, {render_scope(nil)}")
    if pending:
        print(f"FAIL: {pending[:8]} is a content commit whose record commit is missing — batch-next prints the undo")
        return FAIL
    if probs:
        for p in probs:
            print(f"FAIL {p}")
        print(f"next: correct the master record, gate --pre --batch {bid}, then batch-next --batch {bid}")
        return FAIL
    if later:
        print(_later_line(master, done, later))
    elif not parts and not nil:
        print(f"every review unit is done: batch-next --batch {bid} replays them all and lists the review packs")
    else:
        print(f"next: batch-next --batch {bid}")
    return OK


def cmd_batch_revert(args, cfg):
    """The red suite found its culprit unit k (git bisect run over the unit commits): print the
    git line that reverts units k..n and re-open the rulings those units applied — the mirror of
    close_applied, their triples out of `applied=`. An applied entry returns to `ruled` only when
    a fingerprint it covers (its own, or one in `units=`) has no still-applied unit left; an entry
    closed at once, with no content key, never re-opens. The runner never runs destructive git:
    the owner runs the printed line (B5)."""
    mpath, master = load_master(args.batch)
    bid = master.header["unit_id"]
    done, pending, later = batch_chain(master, _master_rel(mpath))
    if pending:
        # the chain refuses a revert between a content commit and its record commit
        _die(f"{pending[:8]} is a content commit whose record commit is missing — batch-next --batch {bid} "
             f"prints the undo; run batch-revert after it")
    n = len(done)
    if not n:
        _die(f"batch {bid} has no done review unit to revert")
    if not re.fullmatch(r"0|[1-9]\d*", args.from_unit or ""):
        _die(f"--from takes an integer unit number in 1..{n}, not {args.from_unit!r}")
    k = int(args.from_unit)
    if not 1 <= k <= n:
        _die(f"--from {k} is out of 1..{n}: batch {bid} has {n} done review unit(s)")
    # the record directory must equal HEAD: the revert rewrites the master's committed lines and
    # the restore step resets every tracked record file to HEAD, so an uncommitted correction
    # cannot survive either — the correction and the bookkeeping are lines of one file, which no
    # path-spec can tell apart, and only the owner can (the next unit's commit carries a
    # correction; a stashed one survives). Untracked files are the normal mid-batch state and no
    # revert or checkout touches them
    dirty = [status_line(*e) for e in status_entries(RECORD_DIR) if e[0] != "??"]
    if dirty:
        _die(f"the record directory differs from HEAD ({'; '.join(d.split(' ', 1)[1] for d in dirty[:3])}): "
             f"the revert would discard it — commit it (the next unit does) or stash it aside, "
             f"then batch-revert again")
    z = done[n - 1]["commit"]
    head = git("rev-parse", "HEAD").strip()
    if head != z:
        above = git("rev-list", "--count", "--first-parent", f"{z}..{head}").strip()
        print(f"warn: HEAD {head[:8]} is not unit {n}'s commit {z[:8]}: the revert lands above {above} later commit(s)")
    root = Path(repo_root() or os.getcwd()).resolve()
    g = f"git -C {_q(root.as_posix())}"
    # the line names each unit's own commits — its content commit and its record commit in the
    # committed-file channel, its single record-carrying commit otherwise — never a range A..Z:
    # a range would also revert a revert commit the chain holds between two units, re-applying
    # units outside k..n. Printed with `git -C <root>` and root-relative paths, like every line
    # the runner prints: it works from any directory
    # the revert stages the deletion of the .consolidation/ files the units added: mid-batch the
    # chain refuses a revert that changes one, and under the file channel the unit record files
    # go too. HEAD must hold the directory, or the checkout dies on its pathspec — mid-batch it
    # does, every unit commit carrying the master record
    file_channel = config_for_record(master, cfg)["record_channel"] == "file"
    restore = (f" && {g} checkout HEAD -- {RECORD_DIR}"
               if (later is None or file_channel) and git("ls-tree", "--name-only", "HEAD", "--", RECORD_DIR).strip()
               else "")
    commits = " ".join(c for d in done[k - 1:] for c in ((d["content"],) if d["content"] else ()) + (d["commit"],))
    print(f'{g} revert --no-commit {commits}{restore} && {g} commit -m '
          f'"consolidation: revert batch {bid} units {k}..{n}"')
    ipath = intake_path(config_for_record(master, cfg))
    x, touched = 0, set()
    with intake_lock(ipath):
        lines = read_intake(ipath)
        for d in done[k - 1:]:
            h = d["record"].header
            for u in d["record"].units:
                ruling = (u.get("ruling") or "").strip()
                if _norm(u.get("disposition")) != _norm(RULED) or not ruling:
                    continue
                i, e = find_intake(lines, ref=ruling, fp=ruling if re.fullmatch(r"[0-9a-f]{8}", ruling) else None)
                if e is None or e["fields"].get("kind") not in RULABLE_KINDS:
                    continue
                applied = parse_applied(e["fields"].get("applied"))
                me = (u["fingerprint"], h["unit_id"], h["baseline_sha"][:7])
                if me not in applied:
                    continue
                applied.discard(me)
                e["fields"]["applied"] = ",".join(f"{p}:{q}@{r}" for p, q, r in sorted(applied))
                efp = e["fields"].get("fingerprint")
                covered = {t for t in (e["fields"].get("units") or "").split(",") if t} | ({efp} if efp else set())
                if e["fields"].get("state") == "applied" and covered and not covered <= {p[0] for p in applied}:
                    e["fields"]["state"] = "ruled"
                lines[i] = render_intake(e)
                touched.add(i)
                x += 1
        if touched:
            write_intake(ipath, lines)
    if x:
        print(f"re-opened {x} ruling(s) on {len(touched)} entry/entries")
    else:
        print(f"no applied rulings among units {k}..{n}")
    return OK


# ------------------------------------------------------------------ CLI
def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def rec_args(sp, required=True, batch=False):
        g = sp.add_mutually_exclusive_group(required=required)
        g.add_argument("--record")
        g.add_argument("--record-from-commit", metavar="SHA")
        if batch:
            g.add_argument("--batch", metavar="B", help="a batch id or its master record file (ADR 0013)")

    sp = sub.add_parser("preflight", help="clean tree, upstream, foreign commits; prints the baseline candidate")

    sp = sub.add_parser("target-set", help="files and unit counts of a candidate scope")
    sp.add_argument("--pass-kind", choices=list(ADMISSIBLE), required=True)
    sp.add_argument("--scope", nargs="*")
    sp.add_argument("--unit-rule")

    sp = sub.add_parser("record-init", help="write the record: header + one stub per unit at HEAD")
    sp.add_argument("--pass-kind", choices=list(ADMISSIBLE), required=True)
    sp.add_argument("--unit-id", required=True)
    sp.add_argument("--scope", nargs="+", required=True, help="files, or file:A-B for a subset (S26)")
    sp.add_argument("--unit-rule")
    sp.add_argument("--narrowing-reason")
    sp.add_argument("--target", nargs="*", help="severance: excluded target paths")
    sp.add_argument("--floor", choices=list(FLOORS))
    sp.add_argument("--floor-observed")
    sp.add_argument("--out")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--carry-from", metavar="RECORD",
                    help="copy judgement onto identical units of an earlier record (a bound-driven split)")

    sp = sub.add_parser("record-shard", help="split the stubs by file for N read-only workers; writes each "
                                             "shard's brief and its judgement file (.j)")
    sp.add_argument("--record", required=True, help="the record path or a batch id")
    sp.add_argument("--shards", type=int, required=True)

    sp = sub.add_parser("record-fill", help="write the judgement of judgement files (@@ <id> <fingerprint> "
                                            "blocks) into the units they name; every other unit is untouched")
    sp.add_argument("--record", required=True, help="the record path or a batch id")
    sp.add_argument("--from", dest="sources", nargs="+", required=True, metavar="J")

    sp = sub.add_parser("record-merge", help="merge filled shards back; verifies stubs and worker isolation")
    sp.add_argument("--record", required=True)

    sp = sub.add_parser("record-check", help="identity, admissibility, evidence and edit proofs")
    rec_args(sp)
    sp.add_argument("--no-intake", action="store_true", help="skip ruling lookups in the intake")

    sp = sub.add_parser("coverage-check", help="entries == units enumerated at the baseline, one to one")
    rec_args(sp)

    sp = sub.add_parser("scope-cross-check", help="declared scope against the target set the floor gives")
    rec_args(sp)
    sp.add_argument("--target-set", help="the target-set output; a graph or inventory floor is re-run instead")

    sp = sub.add_parser("config-bound-check", help="an uncommitted config only tightens the gates")
    rec_args(sp)

    sp = sub.add_parser("baseline-ancestry-check", help="baseline is HEAD (pre) / parents the unit (--unit-gate)")
    rec_args(sp, required=False)
    sp.add_argument("--baseline")
    sp.add_argument("--unit-gate", action="store_true")

    sp = sub.add_parser("bound-check", help="judgement and line halves against the caps")
    rec_args(sp)
    sp.add_argument("--judgement", action="store_true")
    sp.add_argument("--project-lines", action="store_true")
    sp.add_argument("--measured", action="store_true")

    sp = sub.add_parser("floor-staleness-check", help="floor's observation state against the baseline")
    rec_args(sp)

    sp = sub.add_parser("apply", help="write the files from the record (on the baseline only)")
    sp.add_argument("--record", required=True)
    sp.add_argument("--dry-run", action="store_true")

    sp = sub.add_parser("record-provenance-check", help="the gated record is the one the unit materialized")
    rec_args(sp)

    sp = sub.add_parser("unit-tree-check", help="no uncommitted changes outside .consolidation/")

    sp = sub.add_parser("replay-check", help="HEAD == apply(baseline, record); nothing else changed")
    rec_args(sp)

    sp = sub.add_parser("removal-authorization-check", help="every removed line inside an authorized unit")
    rec_args(sp)

    sp = sub.add_parser("code-invariance-check", help="non-comment tokens identical, baseline vs HEAD")
    rec_args(sp)
    sp.add_argument("--worktree", action="store_true", help="compare against the working tree, not HEAD")

    sp = sub.add_parser("gate", help="all checks of one stage in one call")
    rec_args(sp, batch=True)
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--pre", action="store_true", help="step M5: before apply")
    g.add_argument("--unit", action="store_true", help="step M8: after the commit")
    sp.add_argument("--target-set")

    sp = sub.add_parser("review-pack", help="markdown for the human review")
    rec_args(sp)
    sp.add_argument("--out")
    sp.add_argument("--target-set", help="passed to the gate the pack reports")
    sp.add_argument("--no-gate", action="store_true", help="do not run gate --unit for the pack's verdict line")

    sp = sub.add_parser("escalate", help="intake: append, count, consume, rule, standing, from-record")
    sp.add_argument("--file")
    sp.add_argument("--line", type=int)
    sp.add_argument("--anchor")
    sp.add_argument("--baseline", help="sha whose unit is fingerprinted (default HEAD)")
    sp.add_argument("--fingerprint", help="key on this unit fingerprint (from the record stub)")
    sp.add_argument("--divergence")
    sp.add_argument("--kind", choices=list(ENTRY_KINDS))
    sp.add_argument("--observed")
    sp.add_argument("--context")
    sp.add_argument("--intake")
    sp.add_argument("--consume", action="store_true", help="resolve an obsolete-citation event (S125)")
    sp.add_argument("--rule", action="store_true", help="record the owner's ruling on an open entry")
    sp.add_argument("--also-fingerprint", action="append", metavar="FP",
                    help="with --rule: a further unit fingerprint this ruling covers (repeatable; E8)")
    sp.add_argument("--external", action="store_true", help="with --rule: ruled-external (unverifiable only)")
    sp.add_argument("--standing", action="store_true", help="record an owner's standing (class) ruling")
    sp.add_argument("--ruling-text")
    sp.add_argument("--ruling", help="ruling sha (default: short HEAD)")
    sp.add_argument("--from-record", metavar="RECORD", help="escalate every frozen entry of a record (or a batch id)")
    sp.add_argument("--close-applied", action="store_true",
                    help="after gate --unit: mark the rulings the unit applied (with --record-from-commit)")
    sp.add_argument("--record-from-commit", metavar="SHA")

    sp = sub.add_parser("standing-rulings", help="list the owner's standing rulings")
    sp.add_argument("--intake")

    sp = sub.add_parser("batch-init", help="write a batch's master record: classified once, never applied")
    sp.add_argument("--pass-kind", choices=list(ADMISSIBLE), required=True)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--scope", nargs="+", required=True, help="files, or file:A-B for a subset (S26)")
    sp.add_argument("--unit-rule")
    sp.add_argument("--narrowing-reason")
    sp.add_argument("--target", nargs="*", help="severance: excluded target paths")
    sp.add_argument("--floor", choices=list(FLOORS))
    sp.add_argument("--floor-observed")
    sp.add_argument("--out")
    sp.add_argument("--force", action="store_true", help="overwrite, or reuse a batch id that has a master record")
    sp.add_argument("--carry-from", metavar="OLD",
                    help="copy judgement from an earlier record (a path or a batch id) onto equal units")

    sp = sub.add_parser("batch-plan", help="cut the gated master record into review units under the caps")
    sp.add_argument("--batch", required=True, metavar="B", help="the batch id or its master record file")

    sp = sub.add_parser("batch-next", help="run the batch's next review unit end to end")
    sp.add_argument("--batch", required=True, metavar="B")
    sp.add_argument("--target-set", help="passed to both gates of the unit (a self-report floor)")

    sp = sub.add_parser("batch-status", help="done and pending review units of a batch, and the next command")
    sp.add_argument("--batch", required=True, metavar="B")

    sp = sub.add_parser("batch-run", help="batch-next until a stop, a unit that asks for the suite, or the batch end")
    sp.add_argument("--batch", required=True, metavar="B")
    sp.add_argument("--target-set", help="passed to both gates of every unit (a self-report floor)")

    sp = sub.add_parser("batch-revert", help="print the git line that reverts review units K..n, and re-open their rulings")
    sp.add_argument("--batch", required=True, metavar="B", help="the batch id or its master record file")
    sp.add_argument("--from", dest="from_unit", required=True, metavar="K",
                    help="the first review unit to revert, in 1..(done units)")

    sub.add_parser("self-test", help="run the built-in checks")
    return p


DISPATCH = {
    "preflight": cmd_preflight, "target-set": cmd_target_set, "record-init": cmd_record_init,
    "record-shard": cmd_record_shard, "record-fill": cmd_record_fill, "record-merge": cmd_record_merge, "record-check": cmd_record_check,
    "coverage-check": cmd_coverage_check, "scope-cross-check": cmd_scope_cross_check,
    "config-bound-check": cmd_config_bound_check,
    "baseline-ancestry-check": cmd_baseline_ancestry, "bound-check": cmd_bound_check,
    "floor-staleness-check": cmd_floor_staleness, "apply": cmd_apply, "replay-check": cmd_replay_check,
    "record-provenance-check": cmd_record_provenance, "unit-tree-check": cmd_unit_tree_check,
    "removal-authorization-check": cmd_removal_authorization, "code-invariance-check": cmd_code_invariance,
    "gate": cmd_gate, "review-pack": cmd_review_pack, "escalate": cmd_escalate,
    "standing-rulings": cmd_standing, "batch-init": cmd_batch_init, "batch-plan": cmd_batch_plan,
    "batch-next": cmd_batch_next, "batch-status": cmd_batch_status, "batch-run": cmd_batch_run,
    "batch-revert": cmd_batch_revert,
}


def run(argv):
    """Parse and dispatch one invocation; returns the exit code. Used by main and the self-test."""
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else FAIL
    if args.cmd == "self-test":
        import selftest
        return selftest.main()
    _GATED_UNITS.clear()
    try:
        return DISPATCH[args.cmd](args, load_config())
    except Die as e:
        print(f"error: {e}", file=sys.stderr)
        return FAIL
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return FAIL
    except Exception as e:   # a malformed record fails cleanly, never a traceback (R-runner 3)
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return FAIL


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    argv = sys.argv[1:] if argv is None else argv
    t0 = time.monotonic()
    try:
        root = repo_root()
        if root:
            os.chdir(root)
        return run(argv)
    finally:
        if os.environ.get("CONSOLIDATION_PROFILE") == "1":
            _close_cat()
            # the self-test imports this file again as `consolidate`: its calls count too
            other = sys.modules.get("consolidate")
            n = _CountingSubprocess.git_calls
            if other is not None and other is not sys.modules[__name__]:
                n += other._CountingSubprocess.git_calls
            print(f"profile: {argv[0] if argv else '-'} {time.monotonic() - t0:.1f}s, {n} git calls", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
