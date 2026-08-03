#!/usr/bin/env python3
"""consolidate-specs machinery: the gates, scope selector and escalation intake
for the spec/design-doc consolidation pass.

Invoked by the consolidate-specs skill. One stdlib-only script; subcommands match the
gate names in SKILL.md.

Two pass kinds:
  document  — realign a doc to the code; relocate rationale to an ADR; hand the
              unresolvable to a person via a `## To be confirmed` section.
  severance — cut inbound references to a doc being excluded from retrieval.
              DISABLED unless an exclusion_inventory is configured (O14).

Best-effort runner: safety comes from conservative deletion plus a human-reviewed diff,
not from the numbers. Caps bound review burden; defaults ship labelled uncalibrated (O8).
The 'controlled' tier switches on when a project configures a knowledge_graph and real caps.
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

DEFAULTS = {
    "REMOVED_LINE_CAP": 200,
    "REMOVAL_JUDGEMENT_CAP": 30,
    "SPOT_CHECK_RATE": 0.25,
    "FUNCTIONAL_DIFF_THRESHOLD": 400,
    "ADDED_LINE_CEILING": 200,
    "FLOOR_STALENESS_THRESHOLD_DAYS": 7,
}

OK, FAIL, ADVISORY = 0, 1, 2


def _norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


# regenerable → delete is unavailable to the document pass; severance uses `severed`.
DELETION_AUTHORIZED_DOCUMENT = {
    _norm("ruled → apply"),
    _norm("historical decision → ADR"),
    _norm("obsolete"),
}
DELETION_AUTHORIZED_SEVERANCE = {
    _norm("severed"),
}


def auth_set_for(pass_kind):
    return DELETION_AUTHORIZED_SEVERANCE if "severance" in _norm(pass_kind) else DELETION_AUTHORIZED_DOCUMENT


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
            if k in DEFAULTS or k in ("knowledge_graph", "intake_path", "exclusion_inventory"):
                cfg[k] = v
    return cfg


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def git_show(sha, path):
    r = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


# --------------------------------------------------------------- doc-unit extraction
def extract_units(text, ext):
    """Doc units = paragraphs (blocks separated by blank lines). Pragmatic unit rule (O2):
    coarse but stable and countable. A pass may split a paragraph into finer statements
    during rewrite; coverage counts the paragraph floor."""
    lines = text.splitlines()
    n = len(lines)
    units = []
    i = 0
    while i < n:
        while i < n and not lines[i].strip():
            i += 1
        if i >= n:
            break
        start = i + 1
        while i < n and lines[i].strip():
            i += 1
        end = i
        preview = lines[start - 1].strip()[:60]
        units.append((start, end, preview))
    return units


# ------------------------------------------------------------------ record parsing
def parse_record(path):
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
        out = subprocess.run(kg, shell=True, capture_output=True, text=True)
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    _die("no scope: pass --scope FILES, or set knowledge_graph in .consolidation.json")


def cmd_target_set(args, cfg):
    if args.pass_kind == "severance":
        inv = cfg.get("exclusion_inventory")
        if not inv:
            print("severance DISABLED: no exclusion_inventory configured (O14).")
            print("Run a 'document' pass, or set exclusion_inventory in .consolidation.json "
                  "to the command that enumerates inbound references.")
            return ADVISORY
        out = subprocess.run(inv, shell=True, capture_output=True, text=True)
        refs = [l.strip() for l in out.stdout.splitlines() if l.strip()]
        print("# floor: exclusion-inventory")
        print("# pass_kind: severance")
        for r in refs:
            print(r)
        return OK

    scope = resolve_scope(args, cfg)
    floor = "graph" if (cfg.get("knowledge_graph") and not args.scope) else "self-report"
    print(f"# floor: {floor}")
    print("# unit_rule: document-paragraph (pragmatic; O2 open)")
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
    extra = declared - target
    if extra:
        print(f"FAIL: declared scope not in target set: {sorted(extra)}")
        return FAIL
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
    aset = auth_set_for(header.get("pass_kind", "document"))
    judged = [u for u in units if _norm(u.get("disposition", "")) in aset]
    line_total = 0
    for u in judged:
        if u.get("lines"):
            a, b = parse_lines(u["lines"])
            line_total += b - a + 1
    jcap = cfg["REMOVAL_JUDGEMENT_CAP"]
    lcap = cfg["REMOVED_LINE_CAP"]
    print(f"pass_kind: {header.get('pass_kind', 'document')}")
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
        elif line.startswith("diff --git"):
            file = None
        else:
            cur += 1
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
    aset = auth_set_for(header.get("pass_kind", "document"))
    auth = {}
    for u in units:
        if _norm(u.get("disposition", "")) in aset and u.get("lines"):
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
    for el in existing.splitlines():  # S121: read-before-append, idempotent passes
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
    failures = []

    def check(name, cond):
        print(f"{'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            failures.append(name)

    d = Path(tempfile.mkdtemp(prefix="cs_selftest_"))
    cwd = os.getcwd()
    try:
        os.chdir(d)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "config", "user.name", "t"], check=True)

        doc = ("# Auth service\n"                              # 1
               "\n"                                            # 2
               "The service uses the legacy HMAC path.\n"      # 3  obsolete
               "\n"                                            # 4
               "Tokens expire after 15 minutes.\n"             # 5  still true / retained
               "\n"                                            # 6
               "Retention must satisfy GDPR Art. 5.\n")        # 7  external truth → To be confirmed
        Path("auth.md").write_text(doc, encoding="utf-8")
        subprocess.run(["git", "add", "auth.md"], check=True)
        subprocess.run(["git", "commit", "-qm", "base"], check=True)
        baseline = git("rev-parse", "HEAD").strip()

        units = extract_units(doc, ".md")
        check("target-set finds 4 doc units (header + 3 paragraphs)", len(units) == 4)

        record = d / ".consolidation" / "r.record"
        record.parent.mkdir(parents=True)
        record.write_text(
            "baseline_sha: " + baseline + "\n"
            "floor: self-report\n"
            "pass_kind: document\n"
            "unit_rule: document-paragraph\n"
            "scope: auth.md\n"
            "@@unit\nfile: auth.md\nlines: 1\n"
            "disposition: retained\nbasis: structural header\n"
            "@@unit\nfile: auth.md\nlines: 3\n"
            "disposition: obsolete\nbasis: legacy HMAC path removed\n"
            "@@unit\nfile: auth.md\nlines: 5\n"
            "disposition: retained\nbasis: still true\n"
            "@@unit\nfile: auth.md\nlines: 7\n"
            "disposition: escalates (To be confirmed)\nbasis: external GDPR rule\n",
            encoding="utf-8")

        cov = _run(["coverage-check", "--record", str(record)])
        check("coverage-check passes (3 == 3)", cov == OK)

        # rewrite: delete the obsolete paragraph only
        Path("auth.md").write_text(doc.replace("The service uses the legacy HMAC path.\n", ""),
                                   encoding="utf-8")
        subprocess.run(["git", "add", "auth.md"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: auth.md"], check=True)
        rem = _run(["removal-authorization-check", "--record", str(record)])
        check("removal-authorization passes (only obsolete paragraph removed)", rem == OK)

        # unauthorized removal of the retained paragraph -> fail
        Path("auth.md").write_text(Path("auth.md").read_text(encoding="utf-8").replace(
            "Tokens expire after 15 minutes.\n", ""), encoding="utf-8")
        subprocess.run(["git", "add", "auth.md"], check=True)
        subprocess.run(["git", "commit", "-qm", "consolidation: auth.md (bad)"], check=True)
        rem2 = _run(["removal-authorization-check", "--record", str(record)])
        check("removal-authorization fails on an unauthorized removal", rem2 == FAIL)

        # severance disabled with no exclusion_inventory
        sev = _run(["target-set", "--pass-kind", "severance"])
        check("severance disabled when no exclusion_inventory configured", sev == ADVISORY)
    finally:
        os.chdir(cwd)

    if failures:
        print(f"\nself-test FAILED: {len(failures)} check(s): {failures}")
        return FAIL
    print("\nself-test passed")
    return OK


def _run(argv):
    args = _PARSER.parse_args(argv)
    return _DISPATCH[args.cmd](args, load_config())


# --------------------------------------------------------------------------- main
def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("target-set", help="enumerate doc units (document) or inbound refs (severance)")
    sp.add_argument("--scope", nargs="*", help="docs to scope (repo-relative)")
    sp.add_argument("--pass-kind", choices=["document", "severance"], default="document")

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
