#!/usr/bin/env python3
"""consolidate-comments machinery: the gates, scope selector and escalation intake
for the comment consolidation pass.

Invoked by the consolidate-comments skill. One stdlib-only script; subcommands match
the gate names in SKILL.md so the procedure tables stay legible.

This is a best-effort runner. Safety does not depend on the numbers below: the skill
deletes only comments a stranger to the module could regenerate, and a human reviews
the removed lines. The caps bound review *burden*; the conservative defaults ship
labelled uncalibrated (O8). The 'controlled' tier switches on automatically when a
project configures a knowledge_graph and real caps in .consolidation.json.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

# --- conservative defaults (uncalibrated; overridable via .consolidation.json) ---
DEFAULTS = {
    "REMOVED_LINE_CAP": 200,          # removed lines per review unit
    "REMOVAL_JUDGEMENT_CAP": 30,      # distinct delete-decisions per review unit
    "SPOT_CHECK_RATE": 0.25,          # entry spot-check sampling rate
    "FUNCTIONAL_DIFF_THRESHOLD": 400, # LOC above which a realignment defers out
    "ADDED_LINE_CEILING": 200,
    "FLOOR_STALENESS_THRESHOLD_DAYS": 7,
}

OK, FAIL, ADVISORY = 0, 1, 2

# Commit-subject prefixes that mark a commit consolidation-class. `mechanical:` is slot
# MECHANICAL_REMOVAL_MARK; `consolidation:` is the general mark the design leaves implicit —
# without it the gate cannot delimit the review unit (O9) or falsify step 9's parenthood clause.
CONSOLIDATION_COMMIT_MARKS = ("consolidation:", "mechanical:")


def _norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


# Dispositions that authorize a removal: their baseline line ranges may legitimately
# disappear from the tree, and they feed the projected line half.
DELETION_AUTHORIZED = {
    _norm("regenerable → delete"),
    _norm("ruled → apply"),
    _norm("historical decision → ADR"),
    _norm("obsolete"),
}

# The countable set for the *judgement* half. Not the same set: `ruled → apply` authorizes a
# removal but costs zero judgement, because its authority is a recorded human ruling rather
# than an agent judgement (S73). Counting it would spend review budget on a decision the
# agent did not make, and force a needless split.
JUDGEMENT_COUNTABLE = {
    _norm("obsolete"),
    _norm("historical decision → ADR"),
    _norm("regenerable → delete"),
}

# The seven content-pass dispositions, all available to a `comment` pass (S54). A record
# carrying anything else is not a record the disposition table can adjudicate: an
# unrecognized string reads as non-authorizing, so a typo on a delete fails loudly but a
# typo on a retain is indistinguishable from a considered retention.
ADMISSIBLE_DISPOSITIONS = {
    _norm("ruled → apply"),
    _norm("contradicts code → suspected defect"),
    _norm("not verifiable"),
    _norm("historical decision → ADR"),
    _norm("obsolete"),
    _norm("regenerable → delete"),
    _norm("still true"),
}

# Dispositions whose *Evidence required* column is not "—" (S138). A bare disposition is
# producible without reading anything; a citation is not. Presence is mechanizable, so it is
# checked here; whether the citation is any good is the human spot-check.
EVIDENCE_REQUIRED = {
    _norm("ruled → apply"),
    _norm("contradicts code → suspected defect"),
    _norm("obsolete"),
    _norm("regenerable → delete"),
    _norm("still true"),
}

# The header fields a check would be undefined without (S137). `baseline_sha` carries both
# the verification baseline and, per slot REVIEW_UNIT_IDENTITY, the review-unit identity.
# `floor_observed` is the second half of field six — the floor's observation state — without
# which floor-staleness-check cannot know whether its own floor is sound.
# The header fields a check would be undefined without (S137). `pass_kind` is field one: a
# materialized record that does not name its pass kind cannot be read against a disposition
# set, even where this runner only ever writes one.
REQUIRED_HEADER = ("baseline_sha", "pass_kind", "floor", "floor_observed", "unit_rule",
                   "scope")

# Entry kinds this pass produces (S119). The kind is required, not decorative: the dedup
# rule at S124 switches on it.
ENTRY_KINDS = ("suspected-defect", "unverifiable-statement", "obsolete-citation")
ENTRY_STATES = ("open", "ruled", "ruled-external")

# S93 admits a narrowing for exactly two reasons. The header line opens with one of
# these names and may carry free prose after it. Accepting any non-empty string made
# the gate unfalsifiable: "narrowing_reason: I felt like it" passed the check whose
# whole job is to keep a narrowing distinguishable from evasion.
NARROWING_REASONS = ("bound-driven split", "freshness exclusion")


# --------------------------------------------------------------------------- config
# SKILL.md names the slot FLOOR_STALENESS_THRESHOLD; the default is expressed in days.
_ALIASES = {"FLOOR_STALENESS_THRESHOLD": "FLOOR_STALENESS_THRESHOLD_DAYS"}
_PROVIDER_KEYS = ("knowledge_graph", "intake_path")


def config_path():
    """`.consolidation.json` at the project root, found by walking up from cwd. A gate
    invoked from a subdirectory must not silently run on defaults and report a pass."""
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        p = d / ".consolidation.json"
        if p.exists():
            return p
        if (d / ".git").exists():
            break
    return None


def load_config():
    cfg = dict(DEFAULTS)
    p = config_path()
    if p is None:
        return cfg
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        _warn(f"could not parse {p}: {e}; using defaults")
        return cfg
    for k, v in data.items():
        key = _ALIASES.get(k, k)
        if key in DEFAULTS or key in _PROVIDER_KEYS:
            cfg[key] = v
        else:
            _warn(f"{p}: unknown key {k!r} ignored")  # a typo must not read as a default
    return cfg


def _run_provider(cmd, what):
    """Run a configured provider command. A provider that fails or prints nothing yields an
    empty target set, which every downstream check would read as 'nothing to do'."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        _die(f"{what} command failed (exit {r.returncode}): {cmd}\n{r.stderr.strip()}")
    lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    if not lines:
        _die(f"{what} command produced no output: {cmd}")
    return lines


# ----------------------------------------------------------------------------- git
def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def git_show(sha, path):
    r = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


# ----------------------------------------------------------- comment-unit extraction
# Pragmatic per-language heuristic. Not the design's closed enumeration (O2); enumerates
# pure comment lines (grouped) and /* */ block comments. Trailing/inline comments (code
# then comment on one line) and Python docstrings are NOT enumerated — extracting them
# without a real lexer false-positives on markers inside strings/URLs and would break
# coverage on valid code. The pass leaves such comments untouched rather than risk false
# units. Extensible by editing _LINE/_BLOCK.
_LINE = {}
for _pref, _exts in {
    "//": [".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".java", ".js", ".mjs",
           ".ts", ".tsx", ".jsx", ".go", ".rs", ".swift", ".kt", ".kts", ".scala",
           ".cs", ".php", ".css", ".scss", ".less", ".dart", ".groovy", ".gradle"],
    "#":  [".py", ".pyw", ".rb", ".sh", ".bash", ".zsh", ".fish", ".yaml", ".yml",
           ".toml", ".r", ".pl", ".pm", ".tcl", ".ini", ".mk", ".dockerfile"],
    "--": [".sql", ".lua", ".hs", ".lhs", ".elm", ".ada", ".adb", ".vhd", ".vhdl"],
    ";":  [".lisp", ".clj", ".cljs", ".cljc", ".el", ".scm", ".rkt", ".asm"],
}.items():
    for _e in _exts:
        _LINE[_e] = _pref

_BLOCK = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".java", ".js", ".mjs",
          ".ts", ".tsx", ".jsx", ".go", ".rs", ".swift", ".kt", ".scala", ".cs",
          ".php", ".css", ".scss", ".less", ".dart"}


def extract_units(text, ext):
    """Return [(start, end, preview)] 1-indexed line ranges for comment units in text."""
    ext = ext.lower()
    lines = text.splitlines()
    n = len(lines)
    spans = []  # (start, end)

    # /* ... */ block comments for C-family
    if ext in _BLOCK:
        i = 0
        while True:
            a = text.find("/*", i)
            if a < 0:
                break
            b = text.find("*/", a + 2)
            if b < 0:
                break
            b += 2
            spans.append((text.count("\n", 0, a) + 1, text.count("\n", 0, b) + 1))
            i = b

    # line comments: group consecutive lines whose stripped form starts with the marker
    pref = _LINE.get(ext)
    if pref:
        # A line-1 shebang shares the '#' marker but is not a comment: it is an executable
        # directive. Enumerating it forces a disposition on it, and any removal-authorizing
        # disposition then licenses deleting it.
        i = 1 if (lines and lines[0].startswith("#!")) else 0
        while i < n:
            if lines[i].strip().startswith(pref):
                j = i
                while j < n and lines[j].strip().startswith(pref):
                    j += 1
                spans.append((i + 1, j))
                i = j
            else:
                i += 1

    spans = _merge(spans)
    out = []
    for (s, e) in spans:
        preview = lines[s - 1].strip()[:60] if 0 < s <= n else ""
        out.append((s, e, preview))
    return out


def _merge(spans):
    if not spans:
        return []
    spans = sorted(spans)
    merged = [spans[0]]
    for s, e in spans[1:]:
        ls, le = merged[-1]
        if s <= le + 1:  # adjacent or overlapping
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


# ------------------------------------------------------------------ record parsing
def parse_record(path):
    """Parse the line-oriented record. Header key:value lines precede the first
    `@@unit`; each `@@unit` starts a block of key:value lines (file/lines/disposition/basis)."""
    header, units, cur = {}, [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("@@unit"):
            cur = {}
            units.append(cur)
        elif cur is not None:
            if ":" in line:
                k, _, v = line.partition(":")
                cur[k.strip()] = v.strip()
        elif ":" in line:
            k, _, v = line.partition(":")
            header[k.strip()] = v.strip()
    return header, units


def parse_lines(s):
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a), int(b)
    v = int(s)
    return v, v


def _warn(msg):
    print(f"warn: {msg}", file=sys.stderr)


def _die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(FAIL)


# -------------------------------------------------------------------- subcommands
def resolve_scope(args, cfg):
    # `is not None`, not truthiness: --scope with no values is an empty scope the caller
    # asked for. Reading it as "not given" fell through to the knowledge graph, which is a
    # silent fallback in the widening direction, and blanket scope is the named failure mode.
    if args.scope is not None:
        return args.scope
    kg = cfg.get("knowledge_graph")
    if kg:
        return _run_provider(kg, "knowledge_graph")
    _die("no scope: pass --scope FILES, or set knowledge_graph in .consolidation.json")


def cmd_target_set(args, cfg):
    scope = resolve_scope(args, cfg)
    floor = "graph" if (cfg.get("knowledge_graph") and args.scope is None) else "self-report"
    print(f"# floor: {floor}")
    print("# unit_rule: comment (pragmatic; O2 open)")
    for f in scope:
        try:
            text = Path(f).read_text(encoding="utf-8")
        except Exception as e:
            print(f"# unreadable: {f} ({e})")
            continue
        for (s, e, prev) in extract_units(text, Path(f).suffix):
            print(f"{f}\t{s}-{e}\t{prev}")
    return OK


def cmd_record_check(args, cfg):
    """Is the thing the other gates count a record at all?

    coverage-check counts entries; it does not ask whether an entry says anything admissible.
    Without this gate an inadmissible disposition — a typo, or a `retained` borrowed from the
    severance vocabulary — reads as merely non-authorizing and passes every other check, and a
    delete carrying no basis is indistinguishable from one carrying a good one (S53, S138).
    """
    header, units = parse_record(args.record)
    problems = []
    for f in REQUIRED_HEADER:
        if not header.get(f, "").strip():
            problems.append(f"header: missing field {f!r} (S137)")
    if not units:
        problems.append("record carries no entries: a pass materializing no classification "
                        "has no enforceable bound and no gate-verified coverage (S84)")
    for i, u in enumerate(units, 1):
        where = f"entry {i} ({u.get('file', '?')}:{u.get('lines', '?')})"
        raw = u.get("disposition", "")
        d = _norm(raw)
        if not d:
            problems.append(f"{where}: no disposition (S53: exactly one per classifiable unit)")
        elif d not in ADMISSIBLE_DISPOSITIONS:
            problems.append(f"{where}: disposition {raw!r} is not a member of the `comment` "
                            f"pass's disposition set (S54)")
        elif d in EVIDENCE_REQUIRED and not u.get("basis", "").strip():
            problems.append(f"{where}: {raw!r} requires evidence, and the entry carries no "
                            f"basis (S138)")
        if not u.get("file", "").strip():
            problems.append(f"{where}: no file in the unit reference")
        if not u.get("lines", "").strip():
            problems.append(f"{where}: no lines in the unit reference (S138)")
        else:
            try:
                parse_lines(u["lines"])
            except ValueError:
                problems.append(f"{where}: unparseable lines {u['lines']!r}")
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return FAIL
    print(f"ok: header complete; {len(units)} entr(ies), every disposition admissible and "
          f"carrying the evidence it requires")
    return OK


def cmd_coverage_check(args, cfg):
    header, units = parse_record(args.record)
    baseline = header.get("baseline_sha") or args.baseline
    if not baseline:
        _die("no baseline_sha in record and no --baseline given")
    scope = [s.strip() for s in header.get("scope", "").split(",") if s.strip()]
    if not scope:
        _die("record header has no scope")
    rec_count = {}
    for u in units:
        f = u.get("file", "?")
        rec_count[f] = rec_count.get(f, 0) + 1
    ok = True
    for f in scope:
        text = git_show(baseline, f)
        if text is None:
            # Skipping would let a declared scope name a file nobody examined and still pass.
            print(f"FAIL {f}: declared in scope but absent at baseline {baseline[:8]}")
            ok = False
            continue
        r = len(extract_units(text, Path(f).suffix))
        c = rec_count.get(f, 0)
        if r != c:
            print(f"FAIL {f}: recomputed {r} units, record has {c} entries")
            ok = False
        else:
            print(f"ok   {f}: {r} units == {c} entries")
    stray = sorted(set(rec_count) - set(scope))  # entries outside the declared scope (S88)
    if stray:
        print(f"FAIL: record has entries for files outside the declared scope: {stray}")
        ok = False
    return OK if ok else FAIL


def cmd_scope_cross_check(args, cfg):
    header, _ = parse_record(args.record)
    declared = {s.strip() for s in header.get("scope", "").split(",") if s.strip()}
    target = set()
    for line in Path(args.target_set).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        target.add(line.split("\t")[0])
    extra = declared - target                       # broader than the target set: blanket scope
    if extra:
        print(f"FAIL: declared scope not in target set: {sorted(extra)}")
        return FAIL
    omitted = target - declared                     # narrower: needs a recorded reason (S93)
    if omitted:
        reason = header.get("narrowing_reason", "").strip()
        if not reason:
            print(f"FAIL: declared scope narrower than target set with no recorded "
                  f"narrowing_reason; omitted: {sorted(omitted)}")
            return FAIL
        if not reason.lower().startswith(NARROWING_REASONS):
            print(f"FAIL: narrowing_reason must open with one of "
                  f"{list(NARROWING_REASONS)}; got {reason!r} (S93)")
            return FAIL
        print(f"ok: declared scope ⊂ target set, narrowed ({reason}); omitted: {sorted(omitted)}")
        return OK
    print(f"ok: declared scope ⊆ target set ({len(declared)} file(s))")
    return OK


def cmd_baseline_ancestry(args, cfg):
    head = git("rev-parse", "HEAD").strip()
    base = git("rev-parse", args.baseline).strip()
    if base == head:
        if args.unit_gate:
            print("FAIL: no commit since the baseline — the gate has no review unit to delimit")
            return FAIL
        print(f"ok: baseline {args.baseline[:8]} is the tip of the isolated tree (pre-rewrite)")
        return OK
    r = subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"])
    if r.returncode != 0:
        print(f"FAIL: baseline {args.baseline[:8]} is neither HEAD nor an ancestor of it")
        return FAIL
    print(f"ok: baseline {args.baseline[:8]} is an ancestor of HEAD (post-rewrite)")
    if args.unit_gate:
        # Step 9 asks for parenthood of the first *consolidation-class* commit as well.
        # In a linear history the baseline always parents whatever commit follows it, so the
        # clause only bites once the gate can tell a consolidation-class commit from a
        # functional one — which is what it is really guarding: no functional commit between
        # the declared baseline and the consolidation work (S91, S164).
        first = git("rev-list", f"{base}..HEAD", "--reverse").split()[0]
        subject = git("log", "-1", "--format=%s", first).strip()
        if not subject.lower().startswith(CONSOLIDATION_COMMIT_MARKS):
            print(f"FAIL: the first commit after the baseline is not consolidation-class "
                  f"({first[:8]} {subject!r}) — a functional commit intervenes, or the "
                  f"declared baseline is not the isolation point")
            return FAIL
        print(f"ok: baseline is the parent of the first consolidation-class commit {first[:8]}")
    return OK


def cmd_bound_check(args, cfg):
    header, units = parse_record(args.record)
    # Two sets, deliberately: the judgement half counts agent judgements (S73), the projected
    # line half sums every unit whose removal is authorized, including the human-ruled ones.
    judged = [u for u in units if _norm(u.get("disposition", "")) in JUDGEMENT_COUNTABLE]
    line_total = 0
    for u in units:
        if _norm(u.get("disposition", "")) in DELETION_AUTHORIZED and u.get("lines"):
            a, b = parse_lines(u["lines"])
            line_total += b - a + 1
    jcap = cfg["REMOVAL_JUDGEMENT_CAP"]
    lcap = cfg["REMOVED_LINE_CAP"]
    # No flag = the review-unit gate at step 9, which enforces both halves. The individual
    # flags are the step-five projection, where the measured half does not exist yet.
    selected = args.judgement or args.project_lines or args.measured
    do_judgement = args.judgement or not selected
    do_measured = args.measured or not selected
    print(f"floor: {header.get('floor', '?')}")
    print(f"judgements: {len(judged)} / cap {jcap}")
    # The human boundary asks for a spot-check at this rate; nothing else reads the key, so
    # the gate hands the reviewer the count rather than leaving them to compute it (S13).
    rate = cfg["SPOT_CHECK_RATE"]
    print(f"spot-check: read {math.ceil(len(units) * rate)} of {len(units)} entries "
          f"at rate {rate:g}")
    print(f"removed-line upper bound (projected from the record): {line_total} / cap {lcap}")
    status = OK
    if do_judgement and len(judged) > jcap:
        print("FAIL: judgement cap breached — split the pass across review units")
        status = FAIL
    if args.project_lines and line_total > lcap:
        print("ADVISORY: projected line cap exceeded — re-scope decision for the author")
        status = ADVISORY if status == OK else status
    if do_measured:
        baseline = header.get("baseline_sha") or args.baseline
        if not baseline:
            _die("measured line half needs baseline_sha in the record or --baseline")
        measured, exempt = _measured_removed(baseline)
        note = (f" ({exempt} exempt line(s) excluded: mechanical reflow or whitespace)"
                if exempt else "")
        print(f"removed lines measured against the tree: {measured} / cap {lcap}{note}")
        if measured > lcap:
            # Step 7's remedies are exhaustive: split across review units, or discard and
            # re-scope. Raising the cap is not among them (S81).
            print("FAIL: measured line cap breached — split across review units and re-run, "
                  "or discard and re-scope")
            status = FAIL
    return status


def _iter_removed(rev_a, rev_b="HEAD"):
    """Yield (file, baseline_line, content) for every line `git diff rev_a rev_b` removes.

    Parsed by hunk state, never by prefix alone: a removed line whose own content starts
    with '-' — a markdown bullet, a SQL or Lua '--' comment — is indistinguishable from a
    '--- a/path' header by prefix, and guessing drops it silently. A dropped removal makes
    removal-authorization-check report zero removals and pass, which is the one failure
    this gate exists to prevent.

    The baseline counter starts at the hunk's '-a' and advances on context and removed
    lines, not on added ones.
    """
    out = git("diff", "--no-color", rev_a, rev_b)
    file, cur, in_hunk = None, 0, False
    for line in out.split("\n"):
        if line.startswith("diff --git "):
            file, in_hunk = None, False
        elif line.startswith("@@"):
            m = re.search(r"@@ -(\d+)", line)
            cur, in_hunk = (int(m.group(1)) if m else 0), True
        elif not in_hunk:
            if line.startswith("--- "):
                p = line[4:].strip()
                if p.startswith('"') and p.endswith('"'):
                    p = p[1:-1]                    # git quotes paths containing spaces
                file = p[2:] if p.startswith("a/") else None   # /dev/null: no baseline side
        elif line.startswith("-"):
            if file:
                yield (file, cur, line[1:])
            cur += 1
        elif line.startswith("+") or line.startswith("\\"):
            pass  # added line, or "\ No newline at end of file" — not a baseline line
        else:
            cur += 1  # context line


def _diff_removed_lines(baseline):
    return [(f, ln) for f, ln, _ in _iter_removed(baseline)]


_BASELINE_CACHE = {}


def _baseline_line(baseline, path, lineno):
    """The content of one baseline line, for the mechanical-reflow exemption."""
    key = (baseline, path)
    if key not in _BASELINE_CACHE:
        text = git_show(baseline, path)
        _BASELINE_CACHE[key] = text.splitlines() if text is not None else []
    lines = _BASELINE_CACHE[key]
    return lines[lineno - 1] if 0 < lineno <= len(lines) else None


def _mechanical_removed_content(baseline):
    """Line content removed by commits marked MECHANICAL_REMOVAL_MARK. Mechanical reflow
    contributes zero to both caps and is exempt from removal authorization (S90).

    ponytail: matched by content, because mapping a mid-unit commit's line numbers back to
    baseline coordinates is exactly what O17 leaves open. Upgrade path: when O17 closes with
    a per-commit provenance scheme, exempt by coordinate instead. Every exemption applied is
    reported, so the hole O17 names stays visible rather than silent."""
    out = set()
    for sha in git("rev-list", f"{baseline}..HEAD").split():
        subject = git("log", "-1", "--format=%s", sha).strip().lower()
        if not subject.startswith("mechanical:"):
            continue
        for _, _, content in _iter_removed(f"{sha}^", sha):
            if content.strip():
                out.add(content.strip())
    return out


def _is_whitespace(content):
    """A whitespace-only baseline line, which is exempt from both caps and from removal
    authorization.

    Not a convenience: such a line falls in no classifiable unit, because extract_units spans
    only comment lines, and it cannot be content-matched to a mechanical commit either, because
    that set skips empty content. Without this exemption removal-authorization-check is
    unpassable for any pass that deletes a comment and the blank line orphaned beside it — no
    commit arrangement clears it. A whitespace-only line carries neither comment nor code, so
    its removal loses nothing and is no judgement (`S90`).
    """
    return content is not None and not content.strip()


def _measured_removed(baseline):
    """The measured line half (step 7): removed lines since the baseline, less what a
    mechanical commit removed and less pure whitespace."""
    mech = _mechanical_removed_content(baseline)
    total, exempt = 0, 0
    for f, ln in _diff_removed_lines(baseline):
        c = _baseline_line(baseline, f, ln)
        if _is_whitespace(c) or (c is not None and c.strip() and c.strip() in mech):
            exempt += 1
            continue
        total += 1
    return total, exempt


def cmd_removal_authorization(args, cfg):
    header, units = parse_record(args.record)
    baseline = header.get("baseline_sha") or args.baseline
    if not baseline:
        _die("no baseline_sha in record and no --baseline given")
    auth = {}
    for u in units:
        if _norm(u.get("disposition", "")) in DELETION_AUTHORIZED and u.get("lines"):
            a, b = parse_lines(u["lines"])
            auth.setdefault(u.get("file"), []).append((a, b))
    removed = _diff_removed_lines(baseline)
    mech = _mechanical_removed_content(baseline)
    bad, exempt, blank = [], 0, 0
    for (f, ln) in removed:
        if any(a <= ln <= b for (a, b) in auth.get(f, [])):
            continue
        c = _baseline_line(baseline, f, ln)
        if _is_whitespace(c):
            blank += 1
            continue
        if c is not None and c.strip() and c.strip() in mech:
            exempt += 1  # mechanical reflow, exempt per S90; the O17 hole, named
            continue
        bad.append((f, ln))
    if blank:
        print(f"note: {blank} whitespace-only removed line(s) exempted — they fall in no "
              f"classifiable unit and carry neither comment nor code")
    if exempt:
        print(f"note: {exempt} removed line(s) exempted as mechanical reflow (O17 open: "
              f"exemption matched by content, not by provenance)")
    if bad:
        sample = ", ".join(f"{f}:{ln}" for f, ln in bad[:5])
        print(f"FAIL: {len(bad)} removed line(s) not authorized by any unit (e.g. {sample})")
        return FAIL
    print(f"ok: {len(removed)} removed line(s) all fall in authorized units")
    return OK


def _commit_date(sha):
    return date.fromisoformat(git("show", "-s", "--format=%cI", sha).strip()[:10])


def _floor_observed_date(value):
    """`floor_observed` is an ISO date or a sha whose commit date is read. A graph build state
    is naturally one or the other, and demanding a single form would push the agent into
    inventing a date for a state it can only name by sha."""
    v = value.strip()
    try:
        return date.fromisoformat(v[:10])
    except ValueError:
        pass
    try:
        return _commit_date(v)
    except (RuntimeError, ValueError):
        return None


def cmd_floor_staleness(args, cfg):
    """Age the floor against the verification baseline.

    The observation state is read from the record header, which is where the procedure puts it.
    That makes it agent-transcribed like every other header field — the pre-rewrite gates read
    the author's own record and are therefore not controls (S82); at the step-nine gate the
    record is materialized inside the review unit.
    """
    header, _ = parse_record(args.record)
    floor = header.get("floor", "").strip()
    if not floor:
        print("FAIL: record header declares no floor (S137)")
        return FAIL
    if _norm(floor) == "self-report":
        # A self-report floor is authored by the pass it floors, so it cannot go stale — and it
        # cannot floor anything either. Name which, rather than reporting a pass.
        print("ADVISORY: floor is self-report — authored by this pass, so the scope cross-check "
              "has no non-agent-authored floor and staleness is undefined (S2)")
        return ADVISORY
    observed_raw = header.get("floor_observed", "").strip()
    if not observed_raw:
        print(f"FAIL: floor is {floor!r} but the header carries no floor_observed, so the "
              f"floor's age is unknown; a check depending on a floor refuses to pass rather "
              f"than passing silently (S6)")
        return FAIL
    observed = _floor_observed_date(observed_raw)
    if observed is None:
        print(f"FAIL: floor_observed {observed_raw!r} is neither an ISO date nor a resolvable sha")
        return FAIL
    baseline = header.get("baseline_sha") or args.baseline
    if not baseline:
        _die("no baseline_sha in record and no --baseline given")
    try:
        base_date = _commit_date(baseline)
    except (RuntimeError, ValueError) as e:
        _die(f"cannot read the baseline commit date for {baseline}: {e}")
    age = (base_date - observed).days
    thr = cfg["FLOOR_STALENESS_THRESHOLD_DAYS"]
    print(f"floor: {floor}; observed {observed.isoformat()}; baseline {base_date.isoformat()}; "
          f"floor predates the baseline by {age} day(s) / threshold {thr}")
    if age > thr:
        print(f"FAIL: the floor predates the verification baseline by more than {thr} day(s). "
              f"A stale floor invalidates the control it floors rather than weakening it — "
              f"rebuild the floor and re-run (S6)")
        return FAIL
    print("ok: floor is fresh relative to the verification baseline")
    return OK


# An intake line: the dated one-liner rule eleven asks for, with the S119 fields carried in a
# trailing bracket so read-before-append can parse what it is suppressing against.
_INTAKE_RE = re.compile(
    r"^- (?P<date>\S+) `(?P<ref>[^`]+)` — (?P<body>.*?)(?: \[(?P<fields>[a-z]+=[^\]]*)\])?$")
_FIELD_ORDER = ("kind", "state", "observed", "fingerprint", "context", "ruling",
                "occurrences", "latest")
PASS_CONTEXT = "consolidate-comments"


def _unit_fingerprint(path, lineno):
    """A content key for the intake, over the unit that contains `lineno`.

    `path:line` is positional: it moves when the file above it changes, and it collides when
    different content lands on the same line. Keyed on it alone, read-before-append both fails
    to suppress a genuine duplicate and falsely suppresses a new observation — the failure S123
    names. The unit is located with the same extract_units() the coverage check counts, so the
    key is the unit rule's unit and not an arbitrary window, and _norm() flattens whitespace, so
    a reflow is the same unit while a rewording is a new one (S67).

    Scoped to the file, not to the text alone: the same boilerplate comment in two files
    hashes the same, and keyed on content alone one file's entry would suppress the other's.
    A unit that moves between files is therefore a new unit, which is the conservative
    direction and matches what the displayed reference already says.

    Returns None when no fingerprint can be computed — an anchor with no line, a file that has
    gone. The caller then falls back to the reference, which is what a legacy entry carries.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    body = None
    for (a, b, _) in extract_units(text, Path(path).suffix):
        if a <= lineno <= b:
            body = "\n".join(lines[a - 1:b])
            break
    if body is None:
        if not 0 < lineno <= len(lines):
            return None
        body = lines[lineno - 1]   # no unit covers the line: key on the line itself
    keyed = Path(path).as_posix() + "\n" + body   # as_posix so a\\b and a/b are one unit
    return hashlib.sha1(_norm(keyed).encode("utf-8")).hexdigest()[:8]


def _parse_intake_line(line):
    m = _INTAKE_RE.match(line.rstrip())
    if not m:
        return None
    fields = {}
    for tok in (m.group("fields") or "").split():
        k, _, v = tok.partition("=")
        fields[k] = v
    return {"date": m.group("date"), "ref": m.group("ref"), "body": m.group("body"),
            "fields": fields, "raw": line.rstrip()}


def _render_intake(e):
    known = " ".join(f"{k}={e['fields'][k]}" for k in _FIELD_ORDER if e["fields"].get(k))
    # A field this script does not know belongs to the arbitrating human: a tag, a
    # cross-reference, a resolution note. Re-rendering a line to count an occurrence must
    # not delete it, so unknown fields are carried through in the order they were read.
    extra = " ".join(k if v == "" else f"{k}={v}"
                     for k, v in e["fields"].items() if k not in _FIELD_ORDER)
    tail = " ".join(x for x in (known, extra) if x)
    return f"- {e['date']} `{e['ref']}` — {e['body']}" + (f" [{tail}]" if tail else "")


def _head_sha():
    try:
        return git("rev-parse", "--short", "HEAD").strip()
    except RuntimeError:
        return None


def _consume_entry(e, lines, i, intake, observed, ref):
    """S125 — the pass that consumes an obsolete-citation event resolves it to `ruled`.

    Consumption is not arbitration: every other kind is ruled by a human editing the intake,
    so this refuses them. Without it the entry stays `open` after the pass that answered it
    and keeps authorizing the next one, which is the signal-versus-authorization confusion
    S140 exists to prevent.
    """
    kind = e["fields"].get("kind")
    if kind != "obsolete-citation":
        print(f"refused: a pass consumes only an obsolete-citation event; {ref} is "
              f"{kind!r}. That kind is ruled by a human editing the intake (S125).")
        return FAIL
    state = e["fields"].get("state")
    if state != "open":
        print(f"nothing to consume: {ref} is already {state!r}")
        return OK
    e["fields"].update(state="ruled", ruling=observed)
    lines[i] = _render_intake(e)
    intake.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"consumed: obsolete-citation at {ref} resolved to ruled at {observed}")
    return OK


def cmd_escalate(args, cfg):
    if args.consume:
        if args.kind or args.divergence:
            _die("--consume resolves an entry already in the intake; it takes neither "
                 "--kind nor --divergence")
    elif not (args.kind and args.divergence):
        _die("escalate needs --kind and --divergence, or --consume to resolve an "
             "obsolete-citation entry already in the intake")
    for _flag, _val in (("--observed", args.observed), ("--context", args.context)):
        if _val and any(c.isspace() for c in _val):
            _die(f"{_flag} must not contain whitespace: the intake bracket is space-delimited, "
                 f"so {_val!r} would split into separate fields and scramble the entry the "
                 f"next time a line is re-rendered")
    intake = Path(args.intake or cfg.get("intake_path")
                  or os.path.expanduser("~/.claude/escalations.md"))
    if args.line:
        ref = f"{args.file}:{args.line}"
    elif args.anchor:
        ref = f"{args.file}#{args.anchor}"
    else:
        ref = args.file
    observed = args.observed or _head_sha() or "unknown"
    fp = _unit_fingerprint(args.file, args.line) if args.line else None
    lines = intake.read_text(encoding="utf-8").splitlines() if intake.exists() else []

    # Read before append (S121) — this is what gives a pass memory, since a frozen comment
    # carries no in-file marker and a later pass re-encounters it.
    #
    # The dedup key is the churn-stable unit reference ALONE, never the pair of reference and
    # kind: keying on the pair breaks against reclassification, because a later pass observing
    # the same unit under the original kind finds no suppressing entry and appends a duplicate
    # (S122).
    for i, raw in enumerate(lines):
        e = _parse_intake_line(raw)
        if e is None:
            continue
        seen = e["fields"].get("fingerprint")
        # Two fingerprints decide it outright: equal is the same statement wherever it now
        # sits, unequal is a new statement at a reused position. Only where one side has no
        # fingerprint — an entry a human wrote, or an anchor with no line to read — does the
        # positional reference decide, which is the old behaviour and no worse than it.
        if fp and seen:
            if seen != fp:
                continue
        elif e["ref"] != ref:
            continue
        if args.consume:
            return _consume_entry(e, lines, i, intake, observed, ref)
        if e["fields"].get("kind") == "obsolete-citation" == args.kind:
            # Exempt from suppression and counted instead: suppressing the second observation
            # of the same stale statement destroys the frequency signal the observation window
            # exists to measure. A reclassification preserves the accumulated count (S124).
            n = int(e["fields"].get("occurrences") or "1") + 1
            e["fields"].update(occurrences=str(n), latest=observed)
            if fp and not seen:
                e["fields"]["fingerprint"] = fp   # upgrade a pre-fingerprint entry in place
            lines[i] = _render_intake(e)
            intake.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"counted: obsolete-citation at {ref} now at {n} occurrence(s), "
                  f"latest observation {observed}")
            return OK
        print(f"suppressed: an entry already exists for {ref}; not re-appended (S122)")
        print(f"  existing: {e['raw']}")
        print("  Request reclassification of that entry rather than appending a duplicate.")
        return OK

    if args.consume:
        print(f"nothing to consume: the intake holds no entry for {ref}")
        return FAIL

    fields = {"kind": args.kind, "state": args.state, "observed": observed,
              "context": args.context or PASS_CONTEXT}
    if fp:
        fields["fingerprint"] = fp
    if args.kind == "obsolete-citation":
        fields.update(occurrences="1", latest=observed)
    body = args.divergence + (f". {args.disposition}" if args.disposition else "")
    intake.parent.mkdir(parents=True, exist_ok=True)
    with open(intake, "a", encoding="utf-8") as fh:
        fh.write(_render_intake({"date": date.today().isoformat(), "ref": ref,
                                 "body": body, "fields": fields}) + "\n")
    print(f"escalated → {intake}")
    return OK


# ----------------------------------------------------------------------- self-test
def cmd_self_test(args, cfg):
    """Exercise the load-bearing gates against a fixture in a throwaway git repo."""
    failures = []

    def check(name, cond):
        print(f"{'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            failures.append(name)

    d = Path(tempfile.mkdtemp(prefix="cc_selftest_"))
    cwd = os.getcwd()
    try:
        os.chdir(d)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "config", "user.name", "t"], check=True)

        src = ("def add(a, b):\n"            # 1
               "    return a + b\n"          # 2
               "\n"                          # 3
               "# returns the sum\n"         # 4  regenerable: restates the code
               "def f(x):\n"                 # 5
               "    # must comply with PCI-DSS req 3.4\n"  # 6 load-bearing: external rule
               "    return x\n"              # 7
               "\n"                          # 8
               "# uses the legacy auth path\n")  # 9 obsolete
        Path("m.py").write_text(src, encoding="utf-8")
        subprocess.run(["git", "add", "m.py"], check=True)
        subprocess.run(["git", "commit", "-qm", "base"], check=True)
        baseline = git("rev-parse", "HEAD").strip()

        # target-set enumerates the three comment units
        units = extract_units(src, ".py")
        check("target-set finds 3 comment units", len(units) == 3)

        # block-comment path (/* */) is exercised separately — it's a different extractor branch
        bu = extract_units("int x; /* block note */\n", ".c")
        check("block comment (/* */) detected on line 1", len(bu) == 1 and bu[0][0] == 1)

        # a shebang is a directive, not a classifiable comment
        sh = extract_units("#!/usr/bin/env python3\n# a real comment\nx = 1\n", ".py")
        check("shebang is not enumerated as a comment unit", sh == [(2, 2, "# a real comment")])

        # record as the agent would author it
        record = d / ".consolidation" / "r.record"
        record.parent.mkdir(parents=True)
        record.write_text(
            "baseline_sha: " + baseline + "\n"
            "floor: self-report\n"
            "floor_observed: " + baseline + "\n"
            "pass_kind: comment\n"
            "unit_rule: comment\n"
            "scope: m.py\n"
            "@@unit\n"
            "file: m.py\n"
            "lines: 4\n"
            "disposition: regenerable → delete\n"
            "basis: restates the return\n"
            "@@unit\n"
            "file: m.py\n"
            "lines: 6\n"
            "disposition: not verifiable\n"
            "basis: external PCI-DSS rule, unverifiable from file\n"
            "@@unit\n"
            "file: m.py\n"
            "lines: 9\n"
            "disposition: obsolete\n"
            "basis: legacy auth path removed\n",
            encoding="utf-8")

        # coverage-check recomputes 3 units at baseline and matches the record
        cov = _run(["coverage-check", "--record", str(record)])
        check("coverage-check passes (3 == 3)", cov == OK)

        # record-check asks whether the thing coverage-check counted is admissible at all
        check("record-check passes on a complete record",
              _run(["record-check", "--record", str(record)]) == OK)
        bad_disp = d / "baddisp.record"
        bad_disp.write_text(record.read_text(encoding="utf-8").replace(
            "disposition: not verifiable", "disposition: escalates (frozen)"), encoding="utf-8")
        check("record-check fails on a disposition outside the pass's set",
              _run(["record-check", "--record", str(bad_disp)]) == FAIL)
        no_basis = d / "nobasis.record"
        no_basis.write_text(record.read_text(encoding="utf-8").replace(
            "basis: restates the return\n", ""), encoding="utf-8")
        check("record-check fails on a delete carrying no basis",
              _run(["record-check", "--record", str(no_basis)]) == FAIL)
        no_kind = d / "nokind.record"
        no_kind.write_text(record.read_text(encoding="utf-8").replace(
            "pass_kind: comment\n", ""), encoding="utf-8")
        check("record-check fails on a header with no pass_kind",
              _run(["record-check", "--record", str(no_kind)]) == FAIL)
        no_head = d / "nohead.record"
        no_head.write_text(record.read_text(encoding="utf-8").replace(
            "unit_rule: comment\n", ""), encoding="utf-8")
        check("record-check fails on a header missing a field a check needs",
              _run(["record-check", "--record", str(no_head)]) == FAIL)

        # the judgement half counts agent judgements only: `ruled → apply` authorizes a removal
        # on a recorded human ruling and contributes zero (S73)
        ruled = d / "ruled.record"
        ruled.write_text(record.read_text(encoding="utf-8").replace(
            "disposition: obsolete", "disposition: ruled → apply").replace(
            "basis: legacy auth path removed", "basis: intake entry m.py:9, ruling sha abc1234"),
            encoding="utf-8")
        (d / ".consolidation.json").write_text('{"REMOVAL_JUDGEMENT_CAP": 1}', encoding="utf-8")
        check("judgement half counts the one regenerable delete, not `ruled → apply`",
              _run(["bound-check", "--record", str(ruled), "--judgement"]) == OK)
        check("judgement half still breaches when two agent judgements are made",
              _run(["bound-check", "--record", str(record), "--judgement"]) == FAIL)
        (d / ".consolidation.json").unlink()

        # floor-staleness-check reads the floor's observation state out of the header
        check("floor-staleness is undefined, and says so, on a self-report floor",
              _run(["floor-staleness-check", "--record", str(record)]) == ADVISORY)
        graph_nofloor = d / "graph_nofloor.record"
        graph_nofloor.write_text(record.read_text(encoding="utf-8")
                                 .replace("floor: self-report\n", "floor: graph\n")
                                 .replace("floor_observed: " + baseline + "\n", ""),
                                 encoding="utf-8")
        check("floor-staleness refuses to pass a graph floor with no observation state",
              _run(["floor-staleness-check", "--record", str(graph_nofloor)]) == FAIL)
        fresh = d / "fresh.record"
        fresh.write_text(record.read_text(encoding="utf-8").replace(
            "floor: self-report\n", "floor: graph\n"), encoding="utf-8")
        check("floor-staleness passes a graph floor built at the baseline",
              _run(["floor-staleness-check", "--record", str(fresh)]) == OK)
        stale = d / "stale.record"
        old = date.fromordinal(date.today().toordinal() - 30).isoformat()
        stale.write_text(record.read_text(encoding="utf-8")
                         .replace("floor: self-report\n", "floor: graph\n")
                         .replace("floor_observed: " + baseline, "floor_observed: " + old),
                         encoding="utf-8")
        check("floor-staleness fails a graph floor older than the threshold",
              _run(["floor-staleness-check", "--record", str(stale)]) == FAIL)

        # coverage-check fails if a whole unit block is dropped from the record
        record.write_text(record.read_text(encoding="utf-8").replace(
            "@@unit\nfile: m.py\nlines: 9\n"
            "disposition: obsolete\nbasis: legacy auth path removed\n", ""),
            encoding="utf-8")
        cov2 = _run(["coverage-check", "--record", str(record)])
        check("coverage-check fails when a unit is omitted", cov2 == FAIL)

        # restore the record
        record.write_text(record.read_text(encoding="utf-8") +
                          "@@unit\nfile: m.py\nlines: 9\n"
                          "disposition: obsolete\nbasis: legacy auth path removed\n",
                          encoding="utf-8")

        # rewrite: delete the regenerable comment only, commit
        Path("m.py").write_text(src.replace("# returns the sum\n", ""), encoding="utf-8")
        subprocess.run(["git", "add", "m.py"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: m.py"], check=True)
        rem = _run(["removal-authorization-check", "--record", str(record)])
        check("removal-authorization passes (only authorized line removed)", rem == OK)

        # now remove the load-bearing line too (unauthorized) -> must fail
        Path("m.py").write_text(Path("m.py").read_text(encoding="utf-8").replace(
            "    # must comply with PCI-DSS req 3.4\n", ""), encoding="utf-8")
        subprocess.run(["git", "add", "m.py"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: m.py (bad)"], check=True)
        rem2 = _run(["removal-authorization-check", "--record", str(record)])
        check("removal-authorization fails on an unauthorized removal", rem2 == FAIL)

        # scope-cross-check fails in both directions: broader is blanket scope; narrower
        # needs a recorded narrowing_reason (S93), else it is indistinguishable from evasion
        ts = d / "target.tsv"
        ts.write_text("# floor: self-report\nm.py\t4-4\tx\nn.py\t2-2\ty\n", encoding="utf-8")
        broad = d / "broad.record"
        broad.write_text("baseline_sha: " + baseline + "\nfloor: self-report\npass_kind: comment\nunit_rule: comment\n"
                         "scope: m.py,z.py\n", encoding="utf-8")
        check("scope-cross-check fails on broader scope (z.py not in target set)",
              _run(["scope-cross-check", "--record", str(broad), "--target-set", str(ts)]) == FAIL)
        narrow = d / "narrow.record"
        narrow.write_text("baseline_sha: " + baseline + "\nfloor: self-report\npass_kind: comment\nunit_rule: comment\n"
                          "scope: m.py\n", encoding="utf-8")
        check("scope-cross-check fails on narrower scope with no narrowing_reason",
              _run(["scope-cross-check", "--record", str(narrow), "--target-set", str(ts)]) == FAIL)
        narrow_ok = d / "narrow_ok.record"
        narrow_ok.write_text("baseline_sha: " + baseline + "\nfloor: self-report\npass_kind: comment\nunit_rule: comment\n"
                             "scope: m.py\nnarrowing_reason: freshness exclusion\n", encoding="utf-8")
        check("scope-cross-check passes on narrower scope with a recorded reason",
              _run(["scope-cross-check", "--record", str(narrow_ok), "--target-set", str(ts)]) == OK)

        # Any non-empty string used to pass here, so the gate could not tell a narrowing
        # from an evasion — the one thing it exists for (S93).
        narrow_bad = d / "narrow_bad.record"
        narrow_bad.write_text("baseline_sha: " + baseline + "\nfloor: self-report\npass_kind: comment\n"
                              "unit_rule: comment\nscope: m.py\nnarrowing_reason: I felt like it\n", encoding="utf-8")
        check("scope-cross-check fails on a narrowing reason outside the two S93 admits",
              _run(["scope-cross-check", "--record", str(narrow_bad), "--target-set", str(ts)]) == FAIL)

        # An explicit but empty --scope is a scope the caller asked for. Truthiness read it
        # as absent and fell through to the graph, widening the pass in silence.
        check("an explicit empty --scope does not fall through to the knowledge graph",
              resolve_scope(argparse.Namespace(scope=[]),
                            {"knowledge_graph": "echo must-not-run"}) == [])

        # The intake bracket is space-delimited, so a value carrying a space splits into
        # separate fields and scrambles the entry the next time the line is re-rendered.
        # Refused at the boundary rather than written and discovered later.
        check("escalate refuses a whitespace-bearing field value",
              _run(["escalate", "--file", "m.py", "--kind", "suspected-defect",
                    "--divergence", "x", "--context", "round 21 audit",
                    "--intake", str(d / "guard.md")]) == FAIL
              and not (d / "guard.md").exists())

        # escalate: read-before-append against a temp intake
        intake = d / "intake.md"
        e1 = _run(["escalate", "--file", "m.py", "--line", "6", "--kind",
                   "unverifiable-statement", "--divergence", "PCI rule unverifiable",
                   "--intake", str(intake)])
        check("escalate appends once with the S119 fields",
              e1 == OK and intake.read_text(encoding="utf-8").count("PCI") == 1
              and "kind=unverifiable-statement" in intake.read_text(encoding="utf-8")
              and "state=open" in intake.read_text(encoding="utf-8"))
        # The dedup key is the unit reference ALONE. Keying on reference + divergence text — or
        # on reference + kind — lets a reworded or reclassified observation append a duplicate,
        # which is precisely the pathology S122 names.
        e2 = _run(["escalate", "--file", "m.py", "--line", "6", "--kind",
                   "unverifiable-statement", "--divergence", "PCI rule unverifiable",
                   "--intake", str(intake)])
        check("escalate suppresses an identical re-observation", e2 == OK)
        _run(["escalate", "--file", "m.py", "--line", "6", "--kind", "suspected-defect",
              "--divergence", "reworded observation, different kind", "--intake", str(intake)])
        check("escalate suppresses on the reference alone, not the reference-and-kind pair",
              len(intake.read_text(encoding="utf-8").strip().splitlines()) == 1)

        # the obsolete-citation kind is exempt from suppression and counted instead (S124)
        cite = d / "cite.md"
        _run(["escalate", "--file", "m.py", "--line", "9", "--kind", "obsolete-citation",
              "--divergence", "cites a removed helper", "--intake", str(cite)])
        _run(["escalate", "--file", "m.py", "--line", "9", "--kind", "obsolete-citation",
              "--divergence", "cites a removed helper", "--intake", str(cite)])
        _run(["escalate", "--file", "m.py", "--line", "9", "--kind", "obsolete-citation",
              "--divergence", "cites a removed helper", "--intake", str(cite)])
        cite_text = cite.read_text(encoding="utf-8")
        check("obsolete-citation is counted, not suppressed",
              len(cite_text.strip().splitlines()) == 1 and "occurrences=3" in cite_text)
        check("obsolete-citation carries a latest-observation sha", "latest=" in cite_text)

        # S125 — the pass that consumes the event resolves it, or the same event keeps
        # authorizing the next pass. Consumption is not arbitration, so it refuses every
        # other kind: those are ruled by a human editing the intake.
        check("--consume resolves the obsolete-citation event to ruled",
              _run(["escalate", "--file", "m.py", "--line", "9", "--consume",
                    "--intake", str(cite)]) == OK
              and "state=ruled" in cite.read_text(encoding="utf-8")
              and "ruling=" in cite.read_text(encoding="utf-8"))
        check("--consume keeps the accumulated occurrence count",
              "occurrences=3" in cite.read_text(encoding="utf-8"))
        check("--consume refuses a kind a human must rule",
              _run(["escalate", "--file", "m.py", "--line", "6", "--consume",
                    "--intake", str(intake)]) == FAIL
              and "state=open" in intake.read_text(encoding="utf-8"))
        check("--consume reports an intake holding no such entry",
              _run(["escalate", "--file", "nowhere.py", "--line", "1", "--consume",
                    "--intake", str(cite)]) == FAIL)

        # The dedup key is the unit's content, not its position (S123). Proven in both
        # directions, because a positional key fails in both: it appends a duplicate for a unit
        # that only moved, and suppresses a genuinely new statement at a reused line.
        fpi = d / "fp_intake.md"
        Path("fp.py").write_text("y = 0\n\n# note A\nx = 1\n", encoding="utf-8")
        _run(["escalate", "--file", "fp.py", "--line", "3", "--kind", "suspected-defect",
              "--divergence", "first observation", "--intake", str(fpi)])
        check("escalate appends the fingerprint of the unit it cites",
              "fingerprint=" in fpi.read_text(encoding="utf-8"))
        Path("fp.py").write_text("# note A\nx = 1\n", encoding="utf-8")
        _run(["escalate", "--file", "fp.py", "--line", "1", "--kind", "suspected-defect",
              "--divergence", "same statement, new position", "--intake", str(fpi)])
        check("escalate suppresses a unit that moved but did not change",
              len(fpi.read_text(encoding="utf-8").strip().splitlines()) == 1)
        Path("fp.py").write_text("y = 0\n\n# note B differs\nx = 1\n", encoding="utf-8")
        _run(["escalate", "--file", "fp.py", "--line", "3", "--kind", "suspected-defect",
              "--divergence", "a different statement at the same line", "--intake", str(fpi)])
        check("escalate appends when the cited line holds different content",
              len(fpi.read_text(encoding="utf-8").strip().splitlines()) == 2)

        # The key is (file, content). The same boilerplate comment lives in many files, and
        # keyed on the text alone the second file's escalation is suppressed and lost, which is
        # the one outcome the intake exists to prevent.
        Path("fp2.py").write_text("y = 0\n\n# note B differs\nx = 1\n", encoding="utf-8")
        _run(["escalate", "--file", "fp2.py", "--line", "3", "--kind", "suspected-defect",
              "--divergence", "the same text in another file", "--intake", str(fpi)])
        check("escalate keys on the file as well as the text",
              len(fpi.read_text(encoding="utf-8").strip().splitlines()) == 3)

        # Re-rendering a line to count an occurrence must not drop a field the arbitrating human
        # added. `k.py` does not exist, so this also exercises the no-fingerprint fallback.
        keep = d / "keep.md"
        keep.write_text("- 2026-01-01 `k.py:1` — cites a removed helper "
                        "[kind=obsolete-citation state=open observed=aaa1111 "
                        "context=x occurrences=1 latest=aaa1111 C42]\n", encoding="utf-8")
        _run(["escalate", "--file", "k.py", "--line", "1", "--kind", "obsolete-citation",
              "--divergence", "again", "--intake", str(keep)])
        kept = keep.read_text(encoding="utf-8")
        check("counting an occurrence keeps a field the script does not know",
              "occurrences=2" in kept and "C42" in kept)

        # coverage-check must not pass a scope naming a file nobody could have examined,
        # nor a record carrying entries for files outside the declared scope
        ghost = d / "ghost.record"
        ghost.write_text("baseline_sha: " + baseline + "\nfloor: self-report\npass_kind: comment\nunit_rule: comment\n"
                         "scope: m.py,absent.py\n"
                         "@@unit\nfile: m.py\nlines: 4\n"
                         "disposition: regenerable → delete\nbasis: restates the return\n"
                         "@@unit\nfile: m.py\nlines: 6\n"
                         "disposition: not verifiable\nbasis: external rule\n"
                         "@@unit\nfile: m.py\nlines: 9\n"
                         "disposition: obsolete\nbasis: legacy path\n", encoding="utf-8")
        check("coverage-check fails on a scope file absent at baseline",
              _run(["coverage-check", "--record", str(ghost)]) == FAIL)
        stray = d / "stray.record"
        stray.write_text("baseline_sha: " + baseline + "\nfloor: self-report\npass_kind: comment\nunit_rule: comment\n"
                         "scope: m.py\n"
                         "@@unit\nfile: m.py\nlines: 4\ndisposition: obsolete\nbasis: x\n"
                         "@@unit\nfile: m.py\nlines: 6\ndisposition: still true\nbasis: x\n"
                         "@@unit\nfile: m.py\nlines: 9\ndisposition: still true\nbasis: x\n"
                         "@@unit\nfile: other.py\nlines: 1\ndisposition: obsolete\nbasis: x\n",
                         encoding="utf-8")
        check("coverage-check fails on an entry outside the declared scope",
              _run(["coverage-check", "--record", str(stray)]) == FAIL)

        # The diff parser's ambiguous case: a removed line whose own content starts with '-'.
        # Prefix-guessing reads it as a '--- a/path' header and drops it, and the whole
        # authorization gate then reports zero removals and passes.
        Path("q.sql").write_text("select 1;\n-- legacy note\nselect 2;\n", encoding="utf-8")
        subprocess.run(["git", "add", "q.sql"], check=True)
        subprocess.run(["git", "commit", "-qm", "add sql"], check=True)
        sql_base = git("rev-parse", "HEAD").strip()
        Path("q.sql").write_text("select 1;\nselect 2;\n", encoding="utf-8")
        subprocess.run(["git", "add", "q.sql"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: q.sql"], check=True)
        got = _diff_removed_lines(sql_base)
        check("diff parser sees a removed '--' comment line", got == [("q.sql", 2)])
        unauth = d / "unauth.record"
        unauth.write_text("baseline_sha: " + sql_base + "\nfloor: self-report\npass_kind: comment\nunit_rule: comment\n"
                          "scope: q.sql\n"
                          "@@unit\nfile: q.sql\nlines: 2\n"
                          "disposition: still true\nbasis: retained\n", encoding="utf-8")
        check("removal-authorization fails on a '--'-leading unauthorized removal",
              _run(["removal-authorization-check", "--record", str(unauth)]) == FAIL)

        # a mechanical: commit's reflow is exempt even alongside content commits (S90)
        mech_base = git("rev-parse", "HEAD").strip()
        Path("q.sql").write_text("select 1;\nselect 2;\nselect 3;\n", encoding="utf-8")
        subprocess.run(["git", "add", "q.sql"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: q.sql grow"], check=True)
        Path("q.sql").write_text("select 1;\nselect 3;\n", encoding="utf-8")
        subprocess.run(["git", "add", "q.sql"], check=True)
        subprocess.run(["git", "commit", "-qm", "mechanical: reflow"], check=True)
        mech_rec = d / "mech.record"
        mech_rec.write_text("baseline_sha: " + mech_base + "\nfloor: self-report\n"
                            "pass_kind: comment\nunit_rule: comment\nscope: q.sql\n"
                            "@@unit\nfile: q.sql\nlines: 1\n"
                            "disposition: still true\nbasis: retained\n"
                            "@@unit\nfile: q.sql\nlines: 2\n"
                            "disposition: still true\nbasis: retained\n", encoding="utf-8")
        check("mechanical reflow is exempt beside a content commit",
              _run(["removal-authorization-check", "--record", str(mech_rec)]) == OK)

        # The ordinary rewrite takes the blank line orphaned beside a deleted comment with it.
        # A blank line falls in no comment unit and cannot be content-matched to a mechanical
        # commit, so without an explicit exemption no commit arrangement clears this gate.
        Path("b.py").write_text("x = 1\n\n# a note\n\ny = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "b.py"], check=True)
        subprocess.run(["git", "commit", "-qm", "add b"], check=True)
        blank_base = git("rev-parse", "HEAD").strip()
        Path("b.py").write_text("x = 1\n\ny = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "b.py"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: b.py"], check=True)
        blank_rec = d / "blank.record"
        blank_rec.write_text("baseline_sha: " + blank_base + "\nfloor: self-report\n"
                             "floor_observed: " + blank_base + "\npass_kind: comment\n"
                             "unit_rule: comment\n"
                             "scope: b.py\n"
                             "@@unit\nfile: b.py\nlines: 3\n"
                             "disposition: regenerable → delete\n"
                             "basis: restates the assignment above it\n", encoding="utf-8")
        check("removal-authorization passes when a comment takes its orphaned blank line",
              _run(["removal-authorization-check", "--record", str(blank_rec)]) == OK)

        # baseline-ancestry --unit-gate wants the first commit to be consolidation-class,
        # not merely descended from the baseline (step 9 / S164)
        check("unit-gate ancestry passes when the unit opens with a consolidation commit",
              _run(["baseline-ancestry-check", "--baseline", mech_base, "--unit-gate"]) == OK)
        func_base = git("rev-parse", "HEAD").strip()
        Path("q.sql").write_text("select 1;\nselect 3;\nselect 4;\n", encoding="utf-8")
        subprocess.run(["git", "add", "q.sql"], check=True)
        subprocess.run(["git", "commit", "-qm", "feat: unrelated functional change"], check=True)
        Path("q.sql").write_text("select 1;\nselect 4;\n", encoding="utf-8")
        subprocess.run(["git", "add", "q.sql"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: q.sql again"], check=True)
        check("unit-gate ancestry fails when a functional commit intervenes",
              _run(["baseline-ancestry-check", "--baseline", func_base, "--unit-gate"]) == FAIL)

        # the measured line half exists only after the rewrite (step 7)
        meas = _run(["bound-check", "--record", str(unauth), "--measured"])
        check("bound-check --measured passes under the default cap", meas == OK)
        (d / ".consolidation.json").write_text('{"REMOVED_LINE_CAP": 0}', encoding="utf-8")
        check("bound-check --measured fails when the measured half breaches the cap",
              _run(["bound-check", "--record", str(unauth), "--measured"]) == FAIL)

        # config is found at the project root, not only in cwd: a gate run from a
        # subdirectory must not silently fall back to shipped defaults
        (d / "sub").mkdir()
        os.chdir(d / "sub")
        check("config found from a subdirectory", load_config()["REMOVED_LINE_CAP"] == 0)
        os.chdir(d)
        (d / ".consolidation.json").write_text('{"REMOVED_LINE_CAP": 5, "typo_key": 1}',
                                               encoding="utf-8")
        check("unknown config key does not become a silent default",
              load_config()["REMOVED_LINE_CAP"] == 5)
    finally:
        os.chdir(cwd)

    if failures:
        print(f"\nself-test FAILED: {len(failures)} check(s): {failures}")
        return FAIL
    print("\nself-test passed")
    return OK


def _run(argv):
    """Re-invoke a subcommand in-process and return its exit code.

    `_die` and argparse both exit the process. Without catching that here, a check on an
    argument guard aborts the whole suite instead of failing one line — which is why no
    guard had a check until one was written.
    """
    try:
        args = _PARSER.parse_args(argv)
        return _DISPATCH[args.cmd](args, load_config())
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else FAIL


# --------------------------------------------------------------------------- main
def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("target-set", help="enumerate comment units in scope")
    sp.add_argument("--scope", nargs="*", help="files to scope (repo-relative)")

    sp = sub.add_parser("record-check",
                        help="header complete; every disposition admissible with its evidence")
    sp.add_argument("--record", required=True)

    sp = sub.add_parser("coverage-check", help="record entry count == recomputed unit count")
    sp.add_argument("--record", required=True)
    sp.add_argument("--baseline")

    sp = sub.add_parser("scope-cross-check", help="declared scope ⊆ target set")
    sp.add_argument("--record", required=True)
    sp.add_argument("--target-set", required=True)

    sp = sub.add_parser("baseline-ancestry-check", help="baseline is HEAD or an ancestor")
    sp.add_argument("--baseline", required=True)
    sp.add_argument("--unit-gate", action="store_true",
                    help="step 9: also require the baseline to be the parent of the unit's "
                         "first consolidation-class commit")

    sp = sub.add_parser("bound-check", help="judgement/line halves vs caps; no flag = both")
    sp.add_argument("--record", required=True)
    sp.add_argument("--baseline")
    sp.add_argument("--judgement", action="store_true")
    sp.add_argument("--project-lines", action="store_true",
                    help="step 5: line half projected from the record (advisory)")
    sp.add_argument("--measured", action="store_true",
                    help="step 7: line half measured against the tree")

    sp = sub.add_parser("removal-authorization-check",
                        help="every removed line falls in an authorized unit")
    sp.add_argument("--record", required=True)
    sp.add_argument("--baseline")

    sp = sub.add_parser("floor-staleness-check", help="floor's observation state vs baseline")
    sp.add_argument("--record", required=True)
    sp.add_argument("--baseline")

    sp = sub.add_parser("escalate", help="append a deduped, structured entry to the intake")
    sp.add_argument("--file", required=True)
    sp.add_argument("--line", type=int)
    sp.add_argument("--anchor")
    sp.add_argument("--divergence")
    sp.add_argument("--kind", choices=list(ENTRY_KINDS),
                    help="the entry kind; the dedup rule switches on it (S119, S124)")
    sp.add_argument("--consume", action="store_true",
                    help="resolve the obsolete-citation entry at this reference to "
                         "`ruled`, the pass's sha as the ruling sha (S125)")
    sp.add_argument("--state", default="open", choices=list(ENTRY_STATES))
    sp.add_argument("--observed",
                    help="sha in effect at observation, and the ruling sha "
                         "under --consume (default: short HEAD)")
    sp.add_argument("--context", help=f"originating context (default: {PASS_CONTEXT})")
    sp.add_argument("--disposition")
    sp.add_argument("--intake")

    sub.add_parser("self-test", help="run the built-in checks")
    return p


_DISPATCH = None
_PARSER = None


def main(argv=None):
    global _PARSER, _DISPATCH
    # Windows consoles default to cp1252; gate output and file previews are utf-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    _PARSER = build_parser()
    _DISPATCH = {
        "target-set": cmd_target_set,
        "record-check": cmd_record_check,
        "coverage-check": cmd_coverage_check,
        "scope-cross-check": cmd_scope_cross_check,
        "baseline-ancestry-check": cmd_baseline_ancestry,
        "bound-check": cmd_bound_check,
        "removal-authorization-check": cmd_removal_authorization,
        "floor-staleness-check": cmd_floor_staleness,
        "escalate": cmd_escalate,
        "self-test": cmd_self_test,
    }
    args = _PARSER.parse_args(argv)
    try:
        return _DISPATCH[args.cmd](args, load_config())
    except RuntimeError as e:
        _die(str(e))


if __name__ == "__main__":
    sys.exit(main())
