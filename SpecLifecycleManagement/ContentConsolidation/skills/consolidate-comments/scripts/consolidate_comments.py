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
import json
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


def _norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


# dispositions that authorize a deletion. these count against the judgement cap and
# their baseline line ranges count against the line cap.
DELETION_AUTHORIZED = {
    _norm("regenerable → delete"),
    _norm("ruled → apply"),
    _norm("historical decision → ADR"),
    _norm("obsolete"),
}


# --------------------------------------------------------------------------- config
def load_config():
    cfg = dict(DEFAULTS)
    p = Path.cwd() / ".consolidation.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            _warn(f"could not parse {p}: {e}; using defaults")
            return cfg
        for k, v in data.items():
            if k in DEFAULTS or k in ("knowledge_graph", "intake_path"):
                cfg[k] = v
    return cfg


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
        i = 0
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
    if args.scope:
        return args.scope
    kg = cfg.get("knowledge_graph")
    if kg:
        out = subprocess.run(kg, shell=True, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    _die("no scope: pass --scope FILES, or set knowledge_graph in .consolidation.json")


def cmd_target_set(args, cfg):
    scope = resolve_scope(args, cfg)
    floor = "graph" if (cfg.get("knowledge_graph") and not args.scope) else "self-report"
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
            _warn(f"{f} not found at baseline {baseline}; skipping")
            continue
        r = len(extract_units(text, Path(f).suffix))
        c = rec_count.get(f, 0)
        if r != c:
            print(f"FAIL {f}: recomputed {r} units, record has {c} entries")
            ok = False
        else:
            print(f"ok   {f}: {r} units == {c} entries")
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
        print(f"ok: declared scope ⊂ target set, narrowed ({reason}); omitted: {sorted(omitted)}")
        return OK
    print(f"ok: declared scope ⊆ target set ({len(declared)} file(s))")
    return OK


def cmd_baseline_ancestry(args, cfg):
    head = git("rev-parse", "HEAD").strip()
    if args.baseline == head:
        print(f"ok: baseline {args.baseline[:8]} is the tip of the isolated tree (pre-rewrite)")
        return OK
    r = subprocess.run(["git", "merge-base", "--is-ancestor", args.baseline, "HEAD"])
    if r.returncode == 0:
        print(f"ok: baseline {args.baseline[:8]} is an ancestor of HEAD (post-rewrite)")
        return OK
    print(f"FAIL: baseline {args.baseline[:8]} is neither HEAD nor an ancestor of it")
    return FAIL


def cmd_bound_check(args, cfg):
    header, units = parse_record(args.record)
    judged = [u for u in units if _norm(u.get("disposition", "")) in DELETION_AUTHORIZED]
    line_total = 0
    for u in judged:
        if u.get("lines"):
            a, b = parse_lines(u["lines"])
            line_total += b - a + 1
    jcap = cfg["REMOVAL_JUDGEMENT_CAP"]
    lcap = cfg["REMOVED_LINE_CAP"]
    print(f"floor: {header.get('floor', '?')}")
    print(f"judgements: {len(judged)} / cap {jcap}")
    print(f"removed-line upper bound: {line_total} / cap {lcap}")
    status = OK
    if args.judgement and len(judged) > jcap:
        print("FAIL: judgement cap breached — split the pass across review units")
        status = FAIL
    if args.project_lines and line_total > lcap:
        print("ADVISORY: line cap exceeded — re-scope decision for the author")
        status = ADVISORY if status == OK else status
    return status


def _diff_removed_lines(baseline):
    """Parse `git diff <baseline> HEAD` -> [(file, baseline_line)] for removed lines.
    Baseline line counter starts at the hunk's '-a' and advances on context and removed
    lines (not on added lines)."""
    out = git("diff", baseline, "HEAD")
    res, file, cur = [], None, 0
    for line in out.split("\n"):
        if line.startswith("--- a/"):
            file = line[6:]
        elif line.startswith("@@"):
            m = re.search(r"@@ -(\d+)", line)
            if m:
                cur = int(m.group(1))
        elif line.startswith("-") and not line.startswith("--"):
            if file:
                res.append((file, cur))
            cur += 1
        elif line.startswith("+") and not line.startswith("++"):
            pass
        elif line.startswith("\\"):
            pass  # "\ No newline at end of file" — metadata, not a baseline line
        elif line.startswith("diff --git"):
            file = None
        else:
            cur += 1  # context line
    return res


def cmd_removal_authorization(args, cfg):
    header, units = parse_record(args.record)
    baseline = header.get("baseline_sha") or args.baseline
    if not baseline:
        _die("no baseline_sha in record and no --baseline given")
    subjects = git("log", f"{baseline}..HEAD", "--format=%s").splitlines()
    if subjects and all(s.strip().lower().startswith("mechanical:") for s in subjects):
        print("ok: every commit since baseline is mechanical (reflow) — exempt")
        return OK
    auth = {}
    for u in units:
        if _norm(u.get("disposition", "")) in DELETION_AUTHORIZED and u.get("lines"):
            a, b = parse_lines(u["lines"])
            auth.setdefault(u.get("file"), []).append((a, b))
    removed = _diff_removed_lines(baseline)
    bad = []
    for (f, ln) in removed:
        if not any(a <= ln <= b for (a, b) in auth.get(f, [])):
            bad.append((f, ln))
    if bad:
        sample = ", ".join(f"{f}:{ln}" for f, ln in bad[:5])
        print(f"FAIL: {len(bad)} removed line(s) not authorized by any unit (e.g. {sample})")
        return FAIL
    print(f"ok: {len(removed)} removed line(s) all fall in authorized units")
    return OK


def cmd_floor_staleness(args, cfg):
    if not cfg.get("knowledge_graph"):
        print("ADVISORY: no knowledge_graph configured; floor is self-report, staleness n/a")
        return ADVISORY
    # ponytail: a graph's build state is provider-specific; without an introspection
    # contract we cannot check staleness generically. Advise rather than fake a pass.
    print("ADVISORY: knowledge_graph configured but build-state introspection unimplemented (O1)")
    return ADVISORY


def cmd_escalate(args, cfg):
    intake = args.intake or cfg.get("intake_path") or os.path.expanduser("~/.claude/escalations.md")
    if args.line:
        ref = f"{args.file}:{args.line}"
    elif args.anchor:
        ref = f"{args.file}#{args.anchor}"
    else:
        ref = args.file
    line = f"- {date.today().isoformat()} `{ref}` — {args.divergence}"
    if args.disposition:
        line += f". {args.disposition}"
    existing = Path(intake).read_text(encoding="utf-8") if os.path.exists(intake) else ""
    key = f"`{ref}`"
    for el in existing.splitlines():  # S121: read-before-append so passes stay idempotent
        if key in el and args.divergence in el:
            print(f"dedup: already escalated ({ref}); not re-appended")
            return OK
    Path(intake).parent.mkdir(parents=True, exist_ok=True)
    with open(intake, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
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

        # record as the agent would author it
        record = d / ".consolidation" / "r.record"
        record.parent.mkdir(parents=True)
        record.write_text(
            "baseline_sha: " + baseline + "\n"
            "floor: self-report\n"
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
            "disposition: escalates (frozen)\n"
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
        broad.write_text("baseline_sha: " + baseline + "\nfloor: self-report\nunit_rule: comment\n"
                         "scope: m.py,z.py\n", encoding="utf-8")
        check("scope-cross-check fails on broader scope (z.py not in target set)",
              _run(["scope-cross-check", "--record", str(broad), "--target-set", str(ts)]) == FAIL)
        narrow = d / "narrow.record"
        narrow.write_text("baseline_sha: " + baseline + "\nfloor: self-report\nunit_rule: comment\n"
                          "scope: m.py\n", encoding="utf-8")
        check("scope-cross-check fails on narrower scope with no narrowing_reason",
              _run(["scope-cross-check", "--record", str(narrow), "--target-set", str(ts)]) == FAIL)
        narrow_ok = d / "narrow_ok.record"
        narrow_ok.write_text("baseline_sha: " + baseline + "\nfloor: self-report\nunit_rule: comment\n"
                             "scope: m.py\nnarrowing_reason: freshness exclusion\n", encoding="utf-8")
        check("scope-cross-check passes on narrower scope with a recorded reason",
              _run(["scope-cross-check", "--record", str(narrow_ok), "--target-set", str(ts)]) == OK)

        # escalate dedup against a temp intake
        intake = d / "intake.md"
        e1 = _run(["escalate", "--file", "m.py", "--line", "6",
                   "--divergence", "PCI rule unverifiable", "--intake", str(intake)])
        e2 = _run(["escalate", "--file", "m.py", "--line", "6",
                   "--divergence", "PCI rule unverifiable", "--intake", str(intake)])
        check("escalate appends once", e1 == OK and intake.read_text().count("PCI") == 1)
        check("escalate dedups the second time", e2 == OK)
    finally:
        os.chdir(cwd)

    if failures:
        print(f"\nself-test FAILED: {len(failures)} check(s): {failures}")
        return FAIL
    print("\nself-test passed")
    return OK


def _run(argv):
    """Re-invoke a subcommand in-process and return its exit code."""
    args = _PARSER.parse_args(argv)
    return _DISPATCH[args.cmd](args, load_config())


# --------------------------------------------------------------------------- main
def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("target-set", help="enumerate comment units in scope")
    sp.add_argument("--scope", nargs="*", help="files to scope (repo-relative)")

    sp = sub.add_parser("coverage-check", help="record entry count == recomputed unit count")
    sp.add_argument("--record", required=True)
    sp.add_argument("--baseline")

    sp = sub.add_parser("scope-cross-check", help="declared scope ⊆ target set")
    sp.add_argument("--record", required=True)
    sp.add_argument("--target-set", required=True)

    sp = sub.add_parser("baseline-ancestry-check", help="baseline is HEAD or an ancestor")
    sp.add_argument("--baseline", required=True)

    sp = sub.add_parser("bound-check", help="judgement/line halves vs caps")
    sp.add_argument("--record", required=True)
    sp.add_argument("--judgement", action="store_true")
    sp.add_argument("--project-lines", action="store_true")

    sp = sub.add_parser("removal-authorization-check",
                        help="every removed line falls in an authorized unit")
    sp.add_argument("--record", required=True)
    sp.add_argument("--baseline")

    sp = sub.add_parser("floor-staleness-check", help="graph floor age vs baseline (advisory)")

    sp = sub.add_parser("escalate", help="append a deduped flag to the intake")
    sp.add_argument("--file", required=True)
    sp.add_argument("--line")
    sp.add_argument("--anchor")
    sp.add_argument("--divergence", required=True)
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
