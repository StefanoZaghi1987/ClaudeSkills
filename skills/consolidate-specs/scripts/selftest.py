"""Self-test for the consolidation runner: the whole pipeline in throwaway git repositories,
plus a regression test for every defect the v2 redesign closed."""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import consolidate as C
import lexer as LX

FAILURES = []


def check(name, cond):
    print(f"{'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        FAILURES.append(name)


def run(*argv):
    """Run a subcommand in-process, silently. Returns (exit_code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = C.run(list(argv))
    return code, buf.getvalue()


def sh(*cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def commit(msg, *files):
    sh("git", "add", *(files or ["-A"]))
    sh("git", "commit", "-qm", msg)
    return C.head_sha()


def write(path, text, crlf=False):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def read(path):
    return Path(path).read_bytes().decode("utf-8")


def fill(record, decide):
    """Fill judgement fields: decide(unit) -> dict of fields, or None to leave the stub empty."""
    rec = C.parse_record(record)
    for u in rec.units:
        d = decide(u)
        if d:
            u.update(d)
    C.write_record(rec, record)
    return rec


def new_repo(prefix):
    d = Path(tempfile.mkdtemp(prefix=prefix))
    os.chdir(d)
    C.ORIG_CWD = str(d)
    sh("git", "init", "-q")
    sh("git", "config", "user.email", "t@t")
    sh("git", "config", "user.name", "t")
    sh("git", "config", "core.autocrlf", "false")
    # the user's global git config must not change what `git status` reports in a test repo
    sh("git", "config", "status.renames", "true")
    sh("git", "config", "diff.renames", "true")
    sh("git", "config", "status.showUntrackedFiles", "normal")
    return d


def _rmtree(d):
    """Remove a test repository and never raise: git writes its objects read-only, and Windows
    unlinks a read-only file only once its write bit is set."""
    def retry(fn, path, _):
        try:
            os.chmod(path, stat.S_IWRITE)
            fn(path)
        except OSError:
            pass
    try:
        shutil.rmtree(d, **({"onexc": retry} if sys.version_info >= (3, 12) else {"onerror": retry}))
    except OSError:
        pass


PY = ("#!/usr/bin/env python3\n"                       # 1 shebang: never a unit
      "import os  # noqa: F401\n"                      # 2 trailing directive
      "\n"                                             # 3
      "# returns the sum of a and b\n"                 # 4 regenerable
      "def add(a, b):\n"                               # 5
      "    return a + b\n"                             # 6
      "\n"                                             # 7
      "# TASK-0014.02 (2026-10-01): flush before close because the driver buffers\n"  # 8 strip
      "def f(x):\n"                                    # 9
      "    # must comply with PCI-DSS req 3.4\n"       # 10 not verifiable
      "    s = \"# not a comment\"\n"                  # 11
      "    return x  # trailing note\n"                # 12 trailing: no unit under `comment`
      "\n"                                             # 13
      "# uses the legacy auth path\n"                  # 14 obsolete
      "y = 1\n")                                       # 15

JS = ('const p = "src/*.js";\n'                        # 1 glob in a string: no unit
      "// eslint-disable-next-line no-eval\n"          # 2 directive: no unit
      "eval(p);\n"                                     # 3
      "// step 1: call the thing\n"                    # 4 regenerable
      "call();\n"                                      # 5
      "const q = \"*/\";\n")                           # 6

DOC = ("# Auth\n"                                      # 1 heading unit
       "\n"
       "Tokens are signed with HMAC.\n"                # 3 obsolete -> rewritten
       "\n"
       "Retention follows GDPR Art. 5.\n"              # 5 not verifiable -> TBC
       "\n"
       "See TASK-0099 for the history of the cache.\n"  # 7 strip
       "\n"
       "## Usage\n"                                    # 9
       "\n"
       "Call login() then fetch().\n")                 # 11 still true


def main():
    cwd = os.getcwd()
    orig = C.ORIG_CWD
    dirs = []
    try:
        _lexer_tests()
        _lexer2_tests()
        dirs.append(new_repo("cons_selftest_"))
        _pipeline_tests()
        dirs.append(new_repo("cons_selftest_rul_"))
        _ruling_tests()
        dirs.append(new_repo("cons_selftest_cfg_"))
        _config_tests(dirs)
        dirs.append(new_repo("cons_selftest_gate2_"))
        _gate2_tests()
        dirs.append(new_repo("cons_selftest_int_"))
        _integrity_tests()
        _autocrlf_tests(dirs)
        _data_tests(dirs)
        _record_channel_tests(dirs)
        dirs.append(new_repo("cons_selftest_doc_"))
        _document_tests()
        dirs.append(new_repo("cons_selftest_sev_"))
        _severance_tests()
        dirs.append(new_repo("cons_selftest_misc_"))
        _misc_tests()
        _v21_tests(dirs)
        _v22_r1_tests(dirs)
        _v22_r2_tests(dirs)
        _v22_r3_tests(dirs)
        _v22_b1_tests(dirs)
        _v22_b2_tests(dirs)
        _v23_lexer_tests()
        _v23_lexpin_tests()
        _v23_runner_tests(dirs)
        _v23_wave1_tests(dirs)
        _v23_cover_tests(dirs)
        _v23_review_tests(dirs)
    finally:
        os.chdir(cwd)
        C.ORIG_CWD = orig
        # the long-lived `git cat-file --batch` holds its repository open on Windows
        C._close_cat()
        for d in dirs:
            _rmtree(d)
    if FAILURES:
        print(f"\nself-test FAILED: {len(FAILURES)} check(s): {FAILURES}")
        return C.FAIL
    print("\nself-test passed")
    return C.OK


def _lexer_tests():
    U = LX.comment_units
    check("C4: '/*' inside a string makes no unit", U('const p = "src/*.js";\nconst x = 1;\nconst q = "*/";\n', "a.js") == [])
    check("C4: '#' inside a Python string makes no unit", U('s = """\n# not\n"""\n', "a.py") == [])
    check("C4: a regex literal hides no comment", len(U("const r = /[/*]/g;\n// real\n", "a.js")) == 1)
    check("C4: a shell heredoc hides no comment", len(U("cat <<EOF\n# in heredoc\nEOF\n# real\n", "a.sh")) == 1)
    check("C5: tool directives are not units",
          U("// eslint-disable-next-line x\n// @ts-ignore\n# noqa\n", "a.ts") == [])
    check("C5: a directive splits its group",
          [(u.sl, u.el) for u in U("// a\n// eslint-disable-next-line x\n// b\nx();\n", "a.js")] == [(1, 1), (3, 3)])
    check("C5: a license header is excluded whole, and every group before the first code line",
          U("// Copyright 2020 X\n\n// GPL body\n\n// real\nx();\n", "a.js") == []
          and [(u.sl, u.el) for u in U("// Copyright 2020 X\n\nx();\n// real\ny();\n", "a.js")] == [(4, 4)])
    check("shebang and encoding cookie are not units",
          [(u.sl, u.el) for u in U("#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n# real\n", "a.py")] == [(3, 3)])
    check("H4: HTML comments and inline-script comments are units",
          len(U("<!-- a -->\n<script>\n// b\n</script>\n", "a.html")) == 2)
    check("H4: SQL block comments are units", len(U("/* a */\nselect 1;\n", "a.sql")) == 1)
    check("H4: PHP '#' comments are units, PHP 8 attributes are not",
          len(U("<?php\n# a\n#[Attr]\n$x = 1;\n", "a.php")) == 1)
    check("H4: extensionless Dockerfile is enumerated", len(U("# a\nFROM x\n", "Dockerfile")) == 1)
    try:
        LX.scan("x", "a.unknownext")
        check("H4: an unsupported file type raises, never a silent zero", False)
    except LX.UnsupportedLanguage:
        check("H4: an unsupported file type raises, never a silent zero", True)
    check("comment-fine enumerates trailing comments", len(U("x = 1  # t\n", "a.py", fine=True)) == 1)
    t0, c0 = LX.code_tokens("a();\n// c\n\nb(); // t\n", "a.js")
    t1, _ = LX.code_tokens("a();\n\nb();\n", "a.js")
    check("code tokens ignore comments and blank lines", t0 == t1 and c0)
    check("code tokens see a changed token", LX.code_tokens("a();\n", "a.js")[0] != LX.code_tokens("b();\n", "a.js")[0])


def _pipeline_tests():
    write("m.py", PY)
    write("a.js", JS)
    write("b.js", "// retries are capped because the upstream API rate-limits\nretry(3);\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    base = commit("base")

    code, out = run("preflight")
    check("preflight passes on a clean tree", code == C.OK and base in out)

    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "U1", "--scope", "m.py", "a.js",
                    "--out", ".consolidation/u1.record")
    check("record-init writes the record", code == C.OK)
    rec = C.parse_record(".consolidation/u1.record")
    check("record-init: 4 units in m.py, 1 in a.js (shebang, directives, strings, trailing excluded)",
          [u["lines"] for u in rec.units if u["file"] == "m.py"] == ["4-4", "8-8", "10-10", "14-14"]
          and [u["lines"] for u in rec.units if u["file"] == "a.js"] == ["4-4"])
    check("record-check fails while dispositions are empty",
          run("record-check", "--record", ".consolidation/u1.record")[0] == C.FAIL)

    decisions = {
        ("m.py", "4-4"): {"disposition": C.REGEN, "basis": "restates def add(a, b): return a + b"},
        ("m.py", "8-8"): {"disposition": C.STRIP, "basis": "ticket id and date are history",
                          "edit": "# flush before close because the driver buffers"},
        ("m.py", "10-10"): {"disposition": C.NV, "basis": "external PCI-DSS rule, unverifiable from file"},
        ("m.py", "14-14"): {"disposition": C.OBS, "basis": "no legacy auth path exists in the tree"},
        ("a.js", "4-4"): {"disposition": C.REGEN, "basis": "restates call()"},
    }
    fill(".consolidation/u1.record", lambda u: decisions[(u["file"], u["lines"])])
    code, out = run("record-check", "--record", ".consolidation/u1.record")
    check("record-check passes a complete record", code == C.OK)

    # --- tampering: every one of these passed the v1 gates
    def tampered(fn):
        rec = C.parse_record(".consolidation/u1.record")
        fn(rec)
        C.write_record(rec, ".consolidation/t.record")
        return run("record-check", "--record", ".consolidation/t.record")[0]

    check("C1: an over-wide range fails (script-owned lines)",
          tampered(lambda r: r.units[0].update(lines="1-15")) == C.FAIL)
    check("C1: an omitted unit plus a duplicate fails though the count matches",
          tampered(lambda r: r.units.__setitem__(1, dict(r.units[0]))) == C.FAIL)
    check("strip that adds a word fails",
          tampered(lambda r: r.units[1].update(edit="# always flush before close")) == C.FAIL)
    check("strip that removes nothing fails",
          tampered(lambda r: r.units[1].update(
              edit="# TASK-0014.02 (2026-10-01): flush before close because the driver buffers")) == C.FAIL)
    check("an edit carrying code fails the token proof",
          tampered(lambda r: r.units[3].update(disposition=C.OBS, edit="import os")) == C.FAIL)
    check("C3: an edit may not introduce a tool directive",
          tampered(lambda r: r.units[0].update(disposition=C.OBS, edit="//go:build ignore")) == C.FAIL
          and tampered(lambda r: r.units[0].update(disposition=C.OBS, edit="/* eslint-disable */")) == C.FAIL)
    check("C3: an edit may not introduce a licence marker",
          tampered(lambda r: r.units[0].update(disposition=C.OBS, edit="# Copyright 2026 Acme")) == C.FAIL)
    check("condense without a standing ruling fails",
          tampered(lambda r: r.units[1].update(disposition=C.COND, edit="# flush first", claims="driver buffers")) == C.FAIL)
    check("a disposition outside the pass kind fails",
          tampered(lambda r: r.units[0].update(disposition=C.SEV)) == C.FAIL)
    check("a removal without basis fails", tampered(lambda r: r.units[0].update(basis="")) == C.FAIL)

    code, out = run("escalate", "--standing", "--ruling-text", "condense comment units of 12+ lines; keep every invariant")
    check("escalate --standing records a standing ruling", code == C.OK and "SR-" in out)
    sr = out.split("standing ruling recorded: ")[1].split()[0]
    check("condense under a standing ruling with claims passes",
          tampered(lambda r: r.units[1].update(disposition=C.COND, edit="# flush first: the driver buffers",
                                               claims="flush before close; driver buffers", ruling=sr)) == C.OK)

    code, out = run("gate", "--pre", "--record", ".consolidation/u1.record")
    check("gate --pre passes (self-report floor is advisory, never blocking)", code == C.OK and "GATE PASSED" in out)

    code, out = run("escalate", "--from-record", ".consolidation/u1.record")
    intake = read("intake.md")
    check("escalate --from-record escalates the frozen unit with its baseline fingerprint",
          code == C.OK and "m.py:10" in intake and "fingerprint=" in intake and "kind=unverifiable-statement" in intake)
    run("escalate", "--from-record", ".consolidation/u1.record")
    check("escalate --from-record is idempotent", read("intake.md").count("m.py:10") == 1)
    check("H5: the intake lock is released", not Path("intake.md.lock").exists())

    code, out = run("apply", "--record", ".consolidation/u1.record")
    check("apply writes the files", code == C.OK and "changed 2 file(s)" in out)
    m = read("m.py")
    check("apply: regenerable, obsolete removed; strip applied; frozen and trailing kept byte-for-byte",
          "returns the sum" not in m and "legacy auth" not in m and "TASK-0014" not in m
          and "# flush before close because the driver buffers" in m
          and "    # must comply with PCI-DSS req 3.4\n" in m and "# trailing note" in m and "# noqa" in m)
    check("apply leaves no double blank line", "\n\n\n" not in m)
    msg = read(".consolidation/u1.commit-msg")
    check("commit message relocates the stripped references (S49) and embeds the record",
          "TASK-0014.02" in msg and C.RECORD_BEGIN in msg)
    sh("git", "add", "m.py", "a.js")
    sh("git", "commit", "-q", "-F", ".consolidation/u1.commit-msg")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("gate --unit passes on the applied commit", code == C.OK and "GATE PASSED" in out)
    check("gate --unit defers the suite when invariance is proven", "deferred to the batch" in out)
    code, out = run("review-pack", "--record", ".consolidation/u1.record")
    check("review-pack writes the review document", code == C.OK and Path(".consolidation/u1.review.md").exists())

    # --- C2: an added code line in a consolidation commit
    write("m.py", read("m.py").replace("y = 1\n", "y = 1\nimport shutil\n"))
    commit("consolidation: sneak", "m.py")
    code, out = run("gate", "--unit", "--record", ".consolidation/u1.record")
    check("C2: an added code line fails replay-check and the gate", code == C.FAIL and "replay-check" in out)
    check("C2: code-invariance-check also sees it",
          run("code-invariance-check", "--record", ".consolidation/u1.record")[0] == C.FAIL)

    # --- C3: diff.noprefix must not blind the gate
    sh("git", "config", "diff.noprefix", "true")
    code, out = run("removal-authorization-check", "--record", ".consolidation/u1.record")
    check("C3: diff.noprefix=true does not blind removal-authorization", code == C.OK and "removed line(s)" in out
          and "0 removed" not in out)
    write("m.py", read("m.py").replace("    return a + b\n", ""))
    commit("consolidation: delete code", "m.py")
    check("C3: an unauthorized code removal fails even with diff.noprefix=true",
          run("removal-authorization-check", "--record", ".consolidation/u1.record")[0] == C.FAIL)
    sh("git", "config", "--unset", "diff.noprefix")
    sh("git", "reset", "-q", "--hard", "HEAD~2")

    # --- S164: a functional commit inside the unit
    write("a.js", read("a.js") + "more();\n")
    commit("feat: unrelated", "a.js")
    check("ancestry --unit-gate fails when a functional commit sits inside the unit",
          run("baseline-ancestry-check", "--record", ".consolidation/u1.record", "--unit-gate")[0] == C.FAIL)
    sh("git", "reset", "-q", "--hard", "HEAD~1")

    # --- the in-session panel: a ruling, then a later unit applies it
    code, out = run("escalate", "--rule", "--file", "m.py", "--line", "10", "--baseline", base,
                    "--ruling-text", "the PCI rule is obsolete; delete it")
    check("escalate --rule resolves the open entry to ruled", code == C.OK and "state=ruled" in read("intake.md"))
    fp = [u for u in rec.units if u["lines"] == "10-10"][0]["fingerprint"]
    head = C.head_sha()
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "U2", "--scope", "m.py",
                    "--out", ".consolidation/u2.record")
    fill(".consolidation/u2.record", lambda u: {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp}
         if "PCI" in u["preview"] else {"disposition": C.STILL, "basis": "states a non-obvious reason"})
    check("ruled → apply cites the intake entry by fingerprint",
          run("record-check", "--record", ".consolidation/u2.record")[0] == C.OK)
    fill(".consolidation/u2.record", lambda u: {"ruling": "deadbeef"} if "PCI" in u["preview"] else None)
    check("ruled → apply citing no ruled entry fails",
          run("record-check", "--record", ".consolidation/u2.record")[0] == C.FAIL)
    check("record-init took HEAD as baseline", C.parse_record(".consolidation/u2.record").header["baseline_sha"] == head)
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "U2b", "--scope", "m.py:1-9",
                    "--narrowing-reason", "bound-driven split: first half", "--carry-from", ".consolidation/u2.record",
                    "--out", ".consolidation/u2b.record")
    sub = C.parse_record(".consolidation/u2b.record")
    check("--carry-from copies judgement onto the identical units of a split",
          code == C.OK and sub.units and all(u.get("disposition") for u in sub.units)
          and all(C.ulines(u)[0] <= 9 for u in sub.units))

    # --- read-parallel: shard, fill, merge
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "U3", "--scope", "m.py", "b.js",
                    "--out", ".consolidation/u3.record", "--force")
    write("notes-untracked.txt", "present before the shards were cut\n")
    run("record-shard", "--record", ".consolidation/u3.record", "--shards", "2")
    shards = sorted(Path(".consolidation").glob("u3.record.shard-[0-9]"))
    check("record-shard splits by file", len(shards) == 2)
    for sp in shards:
        fill(str(sp), lambda u: {"disposition": C.STILL, "basis": "carries a reason the code cannot state"})
    bad = C.parse_record(str(shards[0]))
    bad.units[0]["lines"] = "1-99"
    C.write_record(bad, str(shards[0]) + ".bak")
    shutil.copy(str(shards[0]), str(shards[0]) + ".orig")
    shutil.copy(str(shards[0]) + ".bak", str(shards[0]))
    check("record-merge refuses a shard whose stub a worker edited",
          run("record-merge", "--record", ".consolidation/u3.record")[0] == C.FAIL)
    shutil.copy(str(shards[0]) + ".orig", str(shards[0]))
    for extra in Path(".consolidation").glob("u3.record.shard-*.*"):
        extra.unlink()
    write("a.js", read("a.js") + "// worker wrote this\n")
    check("record-merge refuses when a worker touched a source file",
          run("record-merge", "--record", ".consolidation/u3.record")[0] == C.FAIL)
    sh("git", "checkout", "--", "a.js")
    code, out = run("record-merge", "--record", ".consolidation/u3.record")
    check("record-merge joins clean shards into one record", code == C.OK
          and run("record-check", "--record", ".consolidation/u3.record")[0] == C.OK)

    # --- H1: invoked from a subdirectory
    Path("sub").mkdir(exist_ok=True)
    os.chdir("sub")
    C.ORIG_CWD = os.getcwd()
    root = C.repo_root()
    os.chdir(root)
    check("H1: a path typed in a subdirectory resolves to a root-relative path", C.repo_rel("../m.py") == "m.py")
    C.ORIG_CWD = root


def _ruling_tests():
    write("a.py", "# must comply with PCI-DSS req 3.4\nx = 1\n# must comply with PCI-DSS req 3.4\ny = 2\n")
    write("other.py", "# uses the legacy path\nz = 3\n")
    write("d.md", "see old.md\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "A1", "--scope", "a.py", "--out", ".consolidation/a1.record")
    rec = C.parse_record(".consolidation/a1.record")
    check("A1: two identical comments carry distinct fingerprints",
          len(rec.units) == 2 and len({u["fingerprint"] for u in rec.units}) == 2)

    run("escalate", "--file", "other.py", "--line", "1", "--kind", "suspected-defect", "--divergence", "legacy")
    run("escalate", "--rule", "--file", "other.py", "--line", "1", "--ruling-text", "delete the legacy note")
    run("escalate", "--file", "a.py", "--line", "1", "--kind", "suspected-defect", "--divergence", "PCI")
    run("escalate", "--rule", "--file", "a.py", "--line", "1", "--ruling-text", "delete the PCI note")
    fp1 = [u for u in rec.units if C.ulines(u) == (1, 1)][0]["fingerprint"]
    check("A1: escalate --rule keys the entry to the unit's own fingerprint", f"fingerprint={fp1}" in read("intake.md"))

    fill(".consolidation/a1.record", lambda u: {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1})
    check("A1: one ruling authorizes one unit, not its identical sibling",
          run("record-check", "--record", ".consolidation/a1.record")[0] == C.FAIL)
    fill(".consolidation/a1.record",
         lambda u: ({"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1} if u["id"] == "1"
                    else {"disposition": C.RULED, "basis": "owner ruling", "ruling": "other.py:1"}))
    check("A1: a ruling on another file's entry authorizes nothing",
          run("record-check", "--record", ".consolidation/a1.record")[0] == C.FAIL)

    # a consumed obsolete-citation event (state=ruled) is not an owner ruling
    run("escalate", "--file", "d.md", "--line", "1", "--kind", "obsolete-citation", "--divergence", "old.md gone")
    run("escalate", "--file", "d.md", "--line", "1", "--consume")
    fill(".consolidation/a1.record",
         lambda u: ({"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1} if u["id"] == "1"
                    else {"disposition": C.RULED, "basis": "consumed event", "ruling": "d.md:1"}))
    check("A1: a consumed obsolete-citation event authorizes no ruled → apply",
          run("record-check", "--record", ".consolidation/a1.record")[0] == C.FAIL)

    # a hand-written standing-ruling line with a forged id authorizes no condense
    with open("intake.md", "a", encoding="utf-8") as f:
        f.write("- 2026-10-06 `standing-ruling:SR-00000000` — anything [kind=standing-ruling state=ruled id=SR-00000000]\n")
    fill(".consolidation/a1.record",
         lambda u: ({"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1} if u["id"] == "1"
                    else {"disposition": C.COND, "basis": "long", "edit": "# comply with PCI",
                          "claims": "PCI", "ruling": "SR-00000000"}))
    check("A1: a standing ruling whose id does not match its text authorizes nothing",
          run("record-check", "--record", ".consolidation/a1.record")[0] == C.FAIL)

    # ruled → apply counts toward the judgement cap (S73)
    fill(".consolidation/a1.record",
         lambda u: ({"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1} if u["id"] == "1"
                    else {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1}))
    code, out = run("bound-check", "--record", ".consolidation/a1.record", "--judgement")
    check("A1: ruled → apply counts toward the judgement cap", code == C.FAIL and "judgement cap" in out)

    # the fabricated ruling: apply refuses; a hand-built commit must still fail the unit gate
    fill(".consolidation/a1.record",
         lambda u: ({"disposition": C.RULED, "basis": "owner said so", "ruling": "deadbeef"} if u["id"] == "1"
                    else {"disposition": C.NV, "basis": "external rule"}))
    check("A1: apply refuses a fabricated ruling",
          run("apply", "--record", ".consolidation/a1.record")[0] == C.FAIL)
    write("a.py", "x = 1\ny = 2\n")
    rec = C.parse_record(".consolidation/a1.record")
    Path(".consolidation/a1.commit-msg").write_bytes(C.encode(C.commit_message(rec)))
    sh("git", "add", "a.py")
    sh("git", "commit", "-q", "-F", ".consolidation/a1.commit-msg")
    check("A1: gate --unit consults the intake and refuses the fabricated ruling",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.FAIL)

    # the honest record passes end to end (1 judgement == cap 1, so the gate passes)
    sh("git", "reset", "-q", "--hard", "HEAD~1")
    fill(".consolidation/a1.record",
         lambda u: ({"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1} if u["id"] == "1"
                    else {"disposition": C.NV, "basis": "external rule",
                          "edit": None, "claims": None, "ruling": None}))
    run("apply", "--record", ".consolidation/a1.record")
    sh("git", "add", "a.py")
    sh("git", "commit", "-q", "-F", ".consolidation/a1.commit-msg")
    check("A1: a bound ruling passes gate --unit",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)

    # E8: a ruling may name the further units it covers (the explicit unit list)
    write("e.py", "# external constraint applies\nw = 1\n# second note\nv = 2\n")
    commit("feat: e", "e.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "A5", "--scope", "e.py",
        "--out", ".consolidation/a5.record")
    rec5 = C.parse_record(".consolidation/a5.record")
    fp_a, fp_b = rec5.units[0]["fingerprint"], rec5.units[1]["fingerprint"]
    run("escalate", "--file", "e.py", "--line", "1", "--kind", "unverifiable-statement", "--divergence", "constraint")
    run("escalate", "--rule", "--file", "e.py", "--line", "1", "--fingerprint", fp_a,
        "--ruling-text", "true; the second note is rewritten too", "--also-fingerprint", fp_b)
    check("E8: --also-fingerprint writes the explicit unit list on the entry",
          f"units={fp_b}" in read("intake.md"))
    fill(".consolidation/a5.record", lambda u: (
        {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp_a} if u["id"] == "1" else
        {"disposition": C.RULED, "basis": "owner ruling; the entry's unit list names this unit",
         "ruling": fp_a, "edit": "# second note, rewritten"}))
    check("E8: a unit listed in the ruling's unit list cites the ruling",
          run("record-check", "--record", ".consolidation/a5.record")[0] == C.OK)

    # R-gates 1-3: an intake entry is an owner ruling only when `escalate --rule` made it one
    code, _ = run("escalate", "--file", "e.py", "--line", "3", "--kind", "suspected-defect",
                  "--state", "ruled", "--divergence", "agent says fine")
    check("R-gates 1: escalate takes no --state: an entry is never minted ruled",
          code != C.OK and "agent says fine" not in read("intake.md"))
    honest = read("intake.md")
    head = C.head_sha(short=True)

    def cite(fp, line, instead_of=None):
        write("intake.md", honest.replace(instead_of, line) if instead_of else honest + line + "\n")
        fill(".consolidation/a5.record", lambda u: (
            {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp, "edit": None} if u["id"] == "2"
            else {"disposition": C.STILL, "basis": "carries a reason", "ruling": None, "edit": None}))
        return run("record-check", "--record", ".consolidation/a5.record")[0]

    entry = "- 2026-10-06 `e.py:3` — agent says fine{mark} [{kind}state=ruled fingerprint=" + fp_b + " ruling={sha}]"
    mark = " — RULED 2026-10-06 (owner): delete it"
    check("R-gates control: a well-formed owner ruling on the unit passes",
          cite(fp_b, entry.format(mark=mark, kind="kind=suspected-defect ", sha=head)) == C.OK)
    check("R-gates 1: a ruled entry without the owner's RULED marker authorizes nothing",
          cite(fp_b, entry.format(mark="", kind="kind=suspected-defect ", sha=head)) == C.FAIL)
    check("R-gates 1: a plain ruling's sha must resolve when the intake is in the repo",
          cite(fp_b, entry.format(mark=mark, kind="kind=suspected-defect ", sha="0badc0de")) == C.FAIL)
    check("R-gates 2: a ruled entry of the wrong, an unknown or no kind authorizes nothing",
          all(cite(fp_b, entry.format(mark=mark, kind=k, sha=head)) == C.FAIL
              for k in ("kind=load-bearing-reference ", "kind=totally-fake ", "")))
    fp_line = next(l for l in honest.split("\n") if f"fingerprint={fp_a}" in l)
    check("R-gates 3: a unit list without its marker digest binds nothing",
          cite(fp_a, re.sub(r"\(owner, units=\w+\)", "(owner)", fp_line), fp_line) == C.FAIL)
    check("R-gates 3: a unit list extended by hand no longer matches its digest",
          cite(fp_a, fp_line.replace(f"units={fp_b}", f"units={fp_b},deadbeef"), fp_line) == C.FAIL)
    check("R-gates 3 control: the untouched digest-bound list passes", cite(fp_a, fp_line, fp_line) == C.OK)
    write("intake.md", honest)
    run("escalate", "--file", "e.py", "--line", "3", "--kind", "unverifiable-statement", "--divergence", "note")
    other_fp = C._fingerprint_at(read("other.py"), "other.py", 1, C.load_config())
    code, _ = run("escalate", "--rule", "--file", "e.py", "--line", "3", "--ruling-text", "rewrite both",
                  "--also-fingerprint", other_fp)
    check("R-gates 3: --also-fingerprint refuses a unit of another file",
          code == C.FAIL and "RULED" not in read("intake.md").split("`e.py:3`")[-1])
    write("intake.md", honest)
    fill(".consolidation/a5.record", lambda u: (
        {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp_a} if u["id"] == "1" else
        {"disposition": C.RULED, "basis": "owner ruling; the entry's unit list names this unit",
         "ruling": fp_a, "edit": "# second note, rewritten"}))


def _config_tests(dirs):
    # tracked config: judged from the baseline blob, not the worktree
    write("m.py", "".join(f"# note {i}\nx{i} = {i}\n\n" for i in range(3)))
    write("docs/adr/keep.md", "# ADR\n\nStatus: accepted\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "C1", "--scope", "m.py", "--out", ".consolidation/c1.record")
    fill(".consolidation/c1.record", lambda u: {"disposition": C.REGEN, "basis": "restates the assignment"})
    check("A4: record-init stamps the config digest", "config_sha" in C.parse_record(".consolidation/c1.record").header)
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1000}')
    code, out = run("gate", "--pre", "--record", ".consolidation/c1.record")
    check("A4: a cap raised in the worktree after the baseline never reaches the gate",
          code == C.FAIL and "judgement cap" in out)
    check("A4: record-init refuses a tracked config that differs from HEAD",
          run("record-init", "--pass-kind", "comment", "--unit-id", "C2", "--scope", "m.py",
              "--out", ".consolidation/c2.record")[0] == C.FAIL)
    sh("git", "checkout", "--", ".consolidation.json")
    check("A4: the ADR directory is an output, never a scope",
          run("record-init", "--pass-kind", "comment", "--unit-id", "C3", "--scope", "docs/adr/keep.md",
              "--out", ".consolidation/c3.record")[0] == C.FAIL)

    # untracked config: bound by the header's config_sha
    dirs.append(new_repo("cons_selftest_cfg2_"))
    write("m.py", "# note\nx = 1\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n.consolidation.json\n")
    cfg2 = '{"intake_path": "intake.md", "REMOVED_LINE_CAP": 150}'
    write(".consolidation.json", cfg2)
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "U", "--scope", "m.py", "--out", ".consolidation/u.record")
    fill(".consolidation/u.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    run("apply", "--record", ".consolidation/u.record")
    sh("git", "commit", "-q", "--allow-empty", "-F", ".consolidation/u.commit-msg")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("A4: a nil pass over an untracked config passes its gate",
          code == C.OK and "ok        config-bound-check" in out)

    # R-gates 5: an untracked config may tighten the gates (REMOVED_LINE_CAP above), never loosen them
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 9999, '
                                 '"SPOT_CHECK_RATE": 0.01, "document_exts": [".md", ".py"]}')
    cfg = C.load_config()
    check("R-gates 5: an untracked config cannot raise a cap, lower the spot-check rate or widen document_exts",
          cfg["REMOVAL_JUDGEMENT_CAP"] == 30 and cfg["SPOT_CHECK_RATE"] == 0.25
          and ".py" not in cfg["document_exts"] and len(cfg["_bounded"]) == 3)
    check("R-gates 5: a document pass over code stays refused under a widened untracked config",
          C._scope_type_problems([("m.py", None)], "document", cfg) != [])
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("R-gates 5: the gate fails on an untracked config that loosens, naming the value",
          code == C.FAIL and "config-bound-check" in out.split("GATE FAILED:")[-1]
          and "REMOVAL_JUDGEMENT_CAP=9999" in out)
    write(".consolidation.json", cfg2)
    write("ts.txt", "# floor: graph\n# pass_kind: comment\nm.py\t1\n")
    code, out = run("scope-cross-check", "--record", ".consolidation/u.record", "--target-set", "ts.txt")
    check("A4: the floor is taken from the target-set output, never asserted",
          code == C.FAIL and "floor" in out)
    os.remove("ts.txt")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVED_LINE_CAP": 5}')
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("A4: an untracked config changed after record-init fails the gate",
          code == C.FAIL and "config_sha" in out)
    write(".consolidation.json", cfg2)
    write("docs/adr/0001-notes.txt", "not an ADR\n")
    sh("git", "add", "docs")
    sh("git", "commit", "-q", "-m", "consolidation: U adr")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD~1")
    check("A4: a new non-Markdown file under the ADR directory fails replay",
          code == C.FAIL and "must be" in out and "ADR" in out)

    # R-gates 7: a provider floor is observed by the gate re-running the provider (ADR 0011)
    dirs.append(new_repo("cons_selftest_floor_"))
    write("m.py", "# note m\nx = 1\n")
    write("n.py", "# note n\ny = 2\n")
    write("graph.py", "import sys\nif len(sys.argv) > 1:\n    print('# observed: ' + sys.argv[1])\nprint('m.py')\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")

    def graph_cfg(*observed):
        return json.dumps({"intake_path": "intake.md",
                           "knowledge_graph": " ".join([f'"{sys.executable}"', "graph.py", *observed])})

    def pre(unit, *scope, target_set=None):
        run("record-init", "--pass-kind", "comment", "--unit-id", unit, "--scope", *scope, "--floor", "graph",
            "--out", f".consolidation/{unit}.record")
        fill(f".consolidation/{unit}.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
        return run("gate", "--pre", "--record", f".consolidation/{unit}.record",
                   *(["--target-set", target_set] if target_set else []))

    write(".consolidation.json", graph_cfg("HEAD"))
    commit("base")
    code, out = pre("G1", "m.py")
    check("R-gates 7: a graph floor is cross-checked by re-running the provider, no --target-set needed",
          code == C.OK and "re-run by the gate" in out and "ok        scope-cross-check" in out
          and "ok        floor-staleness-check" in out)
    write(".consolidation/forged.targets", "# floor: graph\n# pass_kind: comment\nm.py\t1\nn.py\t1\n")
    code, out = pre("G2", "m.py", "n.py", target_set=".consolidation/forged.targets")
    check("R-gates 7: a hand-written target set agreeing with a wider scope floors nothing",
          code == C.FAIL and "declared scope not in the target set" in out and "--target-set ignored" in out)
    write(".consolidation.json", graph_cfg("2000-01-01"))
    commit("feat: stale graph", ".consolidation.json")
    code, out = pre("G3", "m.py")
    check("R-gates 7: staleness comes from the provider's own observed line, not the header",
          code == C.FAIL and "stale floor" in out
          and C.parse_record(".consolidation/G3.record").header["floor_observed"] == C.head_sha())
    write(".consolidation.json", graph_cfg())
    commit("feat: graph without observation", ".consolidation.json")
    code, out = pre("G4", "m.py")
    check("R-gates 7: a provider with no observed line leaves staleness advisory, never ok",
          code == C.OK and "advisory  floor-staleness-check" in out)
    write(".consolidation.json", json.dumps({"intake_path": "intake.md"}))
    commit("feat: no graph", ".consolidation.json")
    code, out = pre("G5", "m.py")
    check("R-gates 7: a graph floor with no provider configured fails",
          code == C.FAIL and "sets no knowledge_graph" in out)
    sh("git", "rm", "-q", "--cached", ".consolidation.json")
    write(".gitignore", "intake.md\n.consolidation.json\n")
    commit("feat: untrack the config", ".gitignore")
    write(".consolidation.json", graph_cfg("HEAD"))
    code, out = pre("G6", "m.py")
    check("R-gates 7: a provider from an uncommitted config floors nothing (advisory)",
          code == C.OK and "advisory  scope-cross-check" in out and "uncommitted" in out)


def _gate2_tests():
    write("m.py", "x = 1\n# note a\n# note b\n# note c\ny = 2\n")
    write("run.sh", "echo hi\n")
    write("docs/adr/0001-db.md", "# ADR 1\nStatus: accepted\n\nDecision: use Postgres.\n")
    write(".gitattributes", "* -diff\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVED_LINE_CAP": 2}')
    commit("base")
    check("A5: a file declared twice in the scope is refused",
          run("record-init", "--pass-kind", "comment", "--unit-id", "G2", "--scope", "m.py", "m.py",
              "--out", ".consolidation/g2.record")[0] == C.FAIL)
    check("A5: overlapping ranges on one file are refused",
          run("record-init", "--pass-kind", "comment", "--unit-id", "G2", "--scope", "m.py:1-2", "m.py:2-3",
              "--out", ".consolidation/g2.record")[0] == C.FAIL)
    run("record-init", "--pass-kind", "comment", "--unit-id", "G2", "--scope", "m.py", "run.sh",
        "--out", ".consolidation/g2.record")
    fill(".consolidation/g2.record", lambda u: {"disposition": C.REGEN, "basis": "restates the assignment"})
    run("apply", "--record", ".consolidation/g2.record")
    sh("git", "add", "m.py")
    sh("git", "commit", "-q", "-F", ".consolidation/g2.commit-msg")
    code, out = run("gate", "--unit", "--record", ".consolidation/g2.record")
    check("A6: a -diff gitattribute does not hide removed lines from the line cap",
          code == C.FAIL and "measured line cap breached" in out and "GATE FAILED: bound-check" in out)
    sh("git", "update-index", "--chmod=+x", "run.sh")
    sh("git", "commit", "-q", "-m", "mechanical: chmod")
    code, out = run("gate", "--unit", "--record", ".consolidation/g2.record")
    check("A7: a mode change on an in-scope file fails replay", code == C.FAIL and "mode changed" in out)
    sh("git", "update-index", "--chmod=-x", "run.sh")
    sh("git", "commit", "-q", "-m", "mechanical: unchmod")
    write("docs/adr/0001-db.md", "# ADR 1\nStatus: accepted\n\nDecision: use Postgres.\n\nAmendment: MongoDB now.\n")
    sh("git", "add", "docs")
    sh("git", "commit", "-q", "-m", "mechanical: adr note")
    code, out = run("gate", "--unit", "--record", ".consolidation/g2.record")
    check("A7: lines added to an existing ADR beyond its status line fail replay",
          code == C.FAIL and "beyond its status line" in out)


def _integrity_tests():
    write("m.py", "# returns the sum\ndef add(a, b):\n    return a + b\n")
    write("b.js", "// note b\nq();\n")
    write("c.js", "// note c\nr();\n")
    write("other.py", "x = 1\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "I1", "--scope", "m.py", "--out", ".consolidation/i1.record")
    fill(".consolidation/i1.record", lambda u: {"disposition": C.REGEN, "basis": "restates add"})
    run("apply", "--record", ".consolidation/i1.record")
    sh("git", "add", "m.py")
    sh("git", "commit", "-q", "-F", ".consolidation/i1.commit-msg")
    check("A8 control: a clean unit passes the new checks",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)

    # a record file that differs from what the unit materialized
    honest = C.head_sha()
    perm = C.parse_record(".consolidation/i1.record")
    perm.units[0]["basis"] = "tampered"
    C.write_record(perm, ".consolidation/t.record")
    code, out = run("gate", "--unit", "--record", ".consolidation/t.record")
    check("A8: the unit gate refuses a record the unit did not materialize",
          code == C.FAIL and "materialized" in out)

    # a side commit carrying the permissive record, never on the branch
    Path(".consolidation/perm.msg").write_bytes(C.encode(C.commit_message(perm)))
    sh("git", "commit", "-q", "--amend", "-F", ".consolidation/perm.msg")
    side = C.head_sha()
    sh("git", "reset", "-q", "--hard", honest)
    code, out = run("gate", "--unit", "--record-from-commit", side)
    check("A8: a record-from-commit outside base..HEAD is refused",
          code == C.FAIL and "outside" in out)

    # uncommitted changes at the unit gate
    write("other.py", "x = 2\n")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("A8: the unit gate refuses uncommitted changes in the tree",
          code == C.FAIL and "uncommitted" in out)
    sh("git", "checkout", "--", "other.py")

    # an ungated consolidation commit at the tip refuses a new baseline
    write("m.py", "def add(a, b):\n    return a + b\nz = 0\n")
    sh("git", "add", "m.py")
    sh("git", "commit", "-q", "-m", "consolidation: I1 first attempt")
    check("A8: record-init refuses an ungated consolidation commit at the tip",
          run("record-init", "--pass-kind", "comment", "--unit-id", "I2", "--scope", "m.py",
              "--out", ".consolidation/i2.record")[0] == C.FAIL)
    check("A8: preflight fails on an ungated consolidation commit at the tip",
          run("preflight")[0] == C.FAIL)
    sh("git", "reset", "-q", "--hard", honest)

    # --- A9: a shard's judgement replaces the whole set
    run("record-init", "--pass-kind", "comment", "--unit-id", "I3", "--scope", "b.js", "c.js",
        "--out", ".consolidation/i3.record")
    fill(".consolidation/i3.record", lambda u: {"disposition": C.OBS, "basis": "gone",
                                                "edit": "// replaced"})
    run("record-shard", "--record", ".consolidation/i3.record", "--shards", "2")
    for sp in sorted(Path(".consolidation").glob("i3.record.shard-[0-9]")):
        rec = C.parse_record(str(sp))
        for u in rec.units:
            u.pop("edit", None)
            u["basis"] = "worker: delete the note entirely"
        C.write_record(rec, str(sp))
    check("A9: a field the worker deleted stays deleted",
          run("record-merge", "--record", ".consolidation/i3.record")[0] == C.OK
          and all("edit" not in u for u in C.parse_record(".consolidation/i3.record").units))

    # the main record hashed in the snapshot
    run("record-shard", "--record", ".consolidation/i3.record", "--shards", "2")
    for sp in sorted(Path(".consolidation").glob("i3.record.shard-[0-9]")):
        fill(str(sp), lambda u: {"disposition": C.STILL, "basis": "ok"})
    rec = C.parse_record(".consolidation/i3.record")
    rec.units[0]["basis"] = "edited on the main record while the workers ran"
    C.write_record(rec, ".consolidation/i3.record")
    code, out = run("record-merge", "--record", ".consolidation/i3.record")
    check("A9: record-merge refuses a main record edited after the shards were cut",
          code == C.FAIL and "main record changed" in out)
    rec.units[0]["basis"] = "gone"
    C.write_record(rec, ".consolidation/i3.record")
    run("record-merge", "--record", ".consolidation/i3.record")

    # a record outside .consolidation/
    Path("work").mkdir(exist_ok=True)
    run("record-init", "--pass-kind", "comment", "--unit-id", "I4", "--scope", "b.js",
        "--out", "work/i4.record")
    run("record-shard", "--record", "work/i4.record", "--shards", "1")
    fill("work/i4.record.shard-1", lambda u: {"disposition": C.STILL, "basis": "ok"})
    check("A9: a record outside .consolidation/ shards and merges cleanly",
          run("record-merge", "--record", "work/i4.record")[0] == C.OK)


def _autocrlf_tests(dirs):
    dirs.append(new_repo("cons_selftest_crlf_"))
    sh("git", "config", "core.autocrlf", "true")
    Path("a.py").write_bytes(b"x = 1\n# restates x\ny = 2\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    commit("base")
    os.remove("a.py")
    sh("git", "checkout", "--", "a.py")
    check("D1: a real checkout under autocrlf=true is CRLF on disk", Path("a.py").read_bytes() == b"x = 1\r\n# restates x\r\ny = 2\r\n")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "W1", "--scope", "a.py",
                    "--out", ".consolidation/w1.record")
    check("D1: record-init accepts a CRLF worktree over an LF blob", code == C.OK)
    fill(".consolidation/w1.record", lambda u: {"disposition": C.REGEN, "basis": "restates the assignment"})
    code, out = run("apply", "--record", ".consolidation/w1.record")
    check("D1: apply writes onto an autocrlf=true worktree", code == C.OK)
    check("D1: the write keeps the worktree's CRLF", Path("a.py").read_bytes() == b"x = 1\r\ny = 2\r\n")
    sh("git", "add", "a.py")
    sh("git", "commit", "-q", "-F", ".consolidation/w1.commit-msg")
    check("D1: the pass gates under autocrlf=true",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)


def _lexer2_tests():
    """One regression check per Critical/Required lexer finding of the fresh review (B/C)."""
    U = LX.comment_units
    T = LX.code_tokens

    def spans(text, path, fine=False):
        return [(u.sl, u.el) for u in U(text, path, fine=fine)]

    # --- B1: whitespace is significant; a comment is a transparent separator
    check("B1: x = - -y is not x = --y", T("x = - -y;\n", "a.js")[0] != T("x = --y;\n", "a.js")[0])
    check("B1: r = a + ++b is not r = a++ + b", T("r = a + ++b;\n", "a.c")[0] != T("r = a++ + b;\n", "a.c")[0])
    check("B1: css a .b is not a.b", T("a .b { }", "a.css")[0] != T("a.b { }", "a.css")[0])
    check("B1: html text spacing is visible", T("<p>foo<b>x</b></p>", "a.html")[0] != T("<p>foo <b>x</b></p>", "a.html")[0])
    check("B1: ini value spacing is visible", T("k = a  b\n", "a.ini")[0] != T("k = a b\n", "a.ini")[0])
    check("B1: a comment separates what it stands between",
          T("a(); /* x */ b();\n", "a.js")[0] == T("a(); b();\n", "a.js")[0])
    check("B1: a comment with code on both sides is never a unit, not even under comment-fine",
          U("f(a /* why */ b);\ng();\n", "a.js", fine=True) == [])

    # --- B2: mapping errors
    check("B2: a groovy single-quoted URL yields no unit", U("maven { url 'https://jitpack.io' }\n", "build.gradle") == [])
    check("B2: .s is gas, where ';' separates statements", U("movl $1, %eax; movl $2\n", "a.s", fine=True) == [])

    # --- B3: java block comments do not nest
    check("B3: a java block comment does not nest over code",
          spans("/* com/x/*.class */\nint a = 1;\n", "A.java") == [(1, 1)])

    # --- B4: line endings, escapes, splices
    check("B4: a lone CR ends a line comment", U("// c\rdoWork();\r", "a.js") == [])
    check("B4: a spliced C comment covers its continuation line",
          spans("// path C:\\dir\\\nint live = 1;\n", "w.c") == [(1, 2)])
    check("B4: an escaped CRLF keeps the string open", U('var s = "a \\\r\n// inside\r\nend";\r\n', "a.js") == [])
    check("B4: a C char literal of a backslashed quote", U("char c = '\\'';\n", "a.c", fine=True) == [])

    # --- B5: heredocs and continuations in line lexers
    check("B5: a Dockerfile heredoc body is opaque",
          U("RUN <<EOF\n#!/bin/sh\n# install\nEOF\nCOPY <<CONF /etc/app.ini\n# keep me\nx=1\nCONF\n", "Dockerfile") == [])
    check("B5: a .properties continuation line is part of the value",
          U("key = first \\\n  # still part of value\nother = 2\n", "a.properties") == [])
    check("B5: a fortran sentinel comment is a directive, never a unit",
          U("program p\n!$omp parallel do\n!DIR$ IVDEP\nend program\n", "p.f90") == []
          and U("      program p\nC$OMP PARALLEL DO\n      end\n", "p.f") == [])
    check("B5: a fixed-form column-6 ! is a continuation", U("      x = 1 +\n     !    2\n", "p.f") == [])

    # --- B6: SQL dialects
    check("B6: a T-SQL block comment nests over code", spans("/* a /* b */\nDROP TABLE x;\n*/\n", "q.sql") == [(1, 3)])
    check("B6: a mysql exec comment and a hint are directives",
          U("/*!40101 SET NAMES */;\n", "dump.sql") == [] and U("SELECT /*+ hint */ 1;\n", "q.sql", True) == [])
    check("B6: 5--1 is arithmetic, not a comment", U("SELECT 5--1;\n", "q.sql", fine=True) == [])
    check("B6: a mysql backslash escape ends certainty", T("SELECT 'it\\'s -- here';\n", "q.sql")[1] is False)

    # --- B7: interpolation holes are scanned as code
    check("B7: a C# interpolated string hides its nested URLs",
          U('var s = $"{u ?? "http://x"}";\nFoo();\n', "A.cs", fine=True) == [])
    # R-lexer 1: the scan starts at the quote, never at the $/@ prefix
    cs = ['var s = $"http://x/{a}";\nFoo();\n',
          'var s = $@"line one\n// string text, not a comment\nline three";\nFoo();\n',
          'var s = @$"a /* not */ b {x}";\nFoo();\n',
          'var s = $@"C:\\dir\\"" // still text";\nFoo();\n',
          'var s = $"""\n  // raw text {x}\n  """;\nFoo();\n',
          'var s = $$"""\n  /* raw */ {{x}}\n  """;\nFoo();\n']
    check("R-lexer 1: no C# interpolated-string form yields a comment unit",
          all(U(t, "A.cs", fine=True) == [] for t in cs))
    check("R-lexer 1: deleting the would-be comment text changes code tokens",
          T('var s = $"http://x/{a}";\n', "A.cs")[0] != T('var s = $"http:\n', "A.cs")[0])
    check("R-lexer 1: a real comment after an interpolated string is still a unit",
          spans('var s = $@"a\nb";\n// real\nFoo();\n', "A.cs") == [(3, 3)])
    check("B7: a kotlin template hole hides its strings",
          U('val s = "${if (a) "//" else ""}"\n', "a.kt", fine=True) == [])
    check("B7: a swift \\( hole hides its strings",
          U('let s = "a \\(b) c"\n', "a.swift", fine=True) == [])

    # --- B8: HTML/Vue/PHP embedding
    check("B8: a template script is opaque, never JS",
          U('<script type="text/x-kendo-template">\n  // literal\n</script>\n', "a.html") == [])
    check("B8: <ScriptEditor> is not a script tag",
          U('<template>\n<ScriptEditor />\n<p>\n// a\nhttps://x.y\n</p>\n</template>\n'
            '<script>\nexport default {}\n</script>\n', "a.vue") == [])
    check("B8: server code inside a script region stays server code",
          U('<script>\nvar x = <?php echo 1; // note ?>;\n</script>\n', "a.php", fine=True) == [])
    check("B8: a textarea holds RCDATA, not comments", U('<textarea><!-- literal --></textarea>\n', "a.html") == [])
    check("B8: style lang is honoured", spans('<style lang="scss">\n// c\n.a{}\n</style>\n', "a.vue") == [(2, 2)])

    # --- B9: JSX text children
    check("B9: JSX text children are not comments",
          U('const x = (\n  <p>\n    // shown literally\n  </p>\n);\n', "a.tsx") == [])
    check("B9: a URL inside JSX text is not a comment",
          U('<a href={u}>https://example.com</a>\n', "a.jsx", fine=True) == [])

    # --- R-lexer 2: javac decodes \uXXXX before lexing
    jv = "class A {\n  // done \\u000a  deleteDatabase();\n  // plain note\n  int x;\n}\n"
    check("R-lexer 2: a Java comment carrying \\u000a is no unit; its neighbour still is",
          spans(jv, "A.java") == [(3, 3)] and spans(jv, "A.java", fine=True) == [(3, 3)])
    check("R-lexer 2: a Java block comment closed by \\u002a\\u002f is no unit",
          U("class A {\n  /* x \\u002a\\u002f int y; /* */\n}\n", "A.java", fine=True) == [])
    check("R-lexer 2: a Java file with a structural \\uXXXX escape is never certain",
          T(jv, "A.java")[1] is False and T("class A { int x; }\n", "A.java")[1] is True)

    # --- B10: unterminated constructs
    check("B10: an unterminated block comment is no unit and ends certainty",
          U("x = 1;\n/* abc", "a.js") == [] and T("x = 1;\n/* abc", "a.js")[1] is False)

    # --- B11: false units in the hash family and friends
    check("B11: a ruby heredoc body is opaque", U("sql = <<~SQL\n  # heading\n  select 1\nSQL\n", "a.rb") == [])
    check("B11: a yaml multiline quoted scalar hides no comment",
          U('key: "line one\n  # not a comment\n  end"\n', "a.yaml") == [])
    check("B11: a yaml anchored block scalar is opaque", U("script: &s |\n  # step\n  make\n", "a.yml") == [])
    check("B11: a nix multiline string is opaque", U("buildPhase = ''\n  # compile\n  make\n'';\n", "a.nix") == [])
    check("B11: a lisp escaped semicolon is no comment", U("(char= c #\\;) (foo)\n", "a.lisp", fine=True) == [])
    check("B11: haskell --> is an operator", U("x = a --> b\n", "M.hs", fine=True) == [])

    # --- C1: the directive list
    m = LX.directive_matcher()
    miss = [x for x in ("tslint:disable-next-line", "biome-ignore lint: x", "NOSONAR", "NOLINTBEGIN",
                        "LCOV_EXCL_LINE", "cppcheck-suppress nullPointer", "IWYU pragma: keep",
                        "<reference types=\"node\" />", "CHECKSTYLE:OFF", "NOPMD", "swiftlint:disable all",
                        "$omp parallel do", "SBATCH --nodes=2", "PBS -l nodes=1", "compdef git",
                        "liquibase formatted sql", "+goose Up", "name: GetUser :one", "migrate:up",
                        "<auto-generated />", "@ORM\\Entity", "@codingStandardsIgnoreStart",
                        "Output:  42", "Code generated by protoc-gen-go. DO NOT EDIT.",
                        "fall through", "FALLTHRU", "ignore_for_file: x", "ignore: unused_import",
                        "format: off", "purgecss start ignore", "ko if: x", "endbuild", "#include virtual=\"x\"",
                        "@jest-environment jsdom", "$FlowFixMe", "type:ignore", "pyre-ignore", "yapf: disable")
            if m(x) != "tool"]
    check("C1: the review's missed directives are all matched", miss == [])

    # --- R-lexer 4: directives match the tool's syntax, not ordinary prose
    prose = ("+---------+", "+ added index on users", "++ fixed", "exported functions live in api.js",
             "changeset is the unit of change", "output: the result", "ignore: this is temporary",
             "lint: fix later", "we never use noqa here")
    tools = ("+kubebuilder:validation:Required", "+optional", "+k8s:deepcopy-gen=package", "+migrate Up",
             "exported foo, bar", "changeset alice:1", "Unordered output: 1", "lint -e715", "noqa: E501",
             "type: ignore # noqa")
    check("R-lexer 4: prose that looks like a directive is no directive",
          [x for x in prose if m(x) is not None] == [])
    check("R-lexer 4: the real directives the narrowed patterns cover still match",
          [x for x in tools if m(x) != "tool"] == [])
    check("R-lexer 4: an ASCII banner comment is a unit again", spans("x();\n// +---------+\ny();\n", "a.js") == [(2, 2)])

    # --- R-lexer 3: licence notices in their common forms
    notices = ("Copyright Acme, Inc. 2024", "(c) 2024 Acme Corp.", "(c) Acme Corp 2024", "© Acme 2024",
               "SPDX-FileCopyrightText: 2024 Acme", "SPDX-License-Identifier: MIT",
               "Released under the MIT License.", "MIT License",
               "Apache License, Version 2.0", "BSD 3-Clause License")
    check("R-lexer 3: every common licence notice form is matched",
          [x for x in notices if m(x) != "license"] == [])
    check("R-lexer 3: a licence header in any of these forms yields no unit",
          all(U(f"# {x}\n\n# body text\nx = 1\n", "a.py") == [] for x in notices))

    # --- C2: licences
    check("C2: a licence docstring is no unit under comment-fine",
          U('"""Copyright 2024 Acme Corp. Licensed under Apache 2.0."""\nx = 1\n', "a.py", fine=True) == [])
    check("C2: a GPL body separated from its Copyright line is protected",
          U("# Copyright (C) 2024 Acme\n\n# This program is free software\nx = 1\n", "a.py") == [])

    # --- C4: runtime-read doc comments
    check("C4: a rust doc comment is a unit only under comment-fine",
          U("/// Adds.\npub fn add() {}\n", "lib.rs") == []
          and [u.kind for u in U("/// Adds.\npub fn add() {}\n", "lib.rs", True)] == ["doc"])
    check("C4: a php docblock is a unit only under comment-fine",
          U("<?php\n/** @var Foo $x */\nclass U {}\n", "a.php") == [])

    # --- the narrowed CERTAIN set (owner decision: narrow + strengthen)
    check("CERTAIN holds exactly the eight tested languages",
          LX.CERTAIN == {"python", "js", "c", "java", "csharp", "css", "sql", "php"})


def _data_tests(dirs):
    # D2/D3: apply_file in memory
    us = LX.comment_units("x = 1\n# old comment", "a.py")
    op = {"lines": f"{us[0].sl}-{us[0].el}", "span": us[0].span(), "disposition": C.OBS,
          "edit": "# line one\n# line two"}
    check("D2: a multi-line replace at EOF-without-newline separates its lines",
          C.apply_file("x = 1\n# old comment", C.plan_ops([op], "comment"), "comment")
          == "x = 1\n# line one\n# line two")
    d = C.doc_units("# T\n\nPara one.\n\n## To be confirmed\n\n- existing item", "document-paragraph")
    u = {"lines": "3-3", "span": d[1].span(), "disposition": C.NV, "tbc": "Confirm X."}
    check("D2: a TBC item appended to an EOF section starts on a new line",
          C.apply_file("# T\n\nPara one.\n\n## To be confirmed\n\n- existing item",
                       C.plan_ops([u], "document"), "document")
          == "# T\n\nPara one.\n\n## To be confirmed\n\n- existing item\n- Confirm X.\n")
    check("D3: a BOM line-1 comment is a unit",
          [(x.sl, x.el) for x in LX.comment_units("﻿# header comment\nx = 1\n", "a.py")] == [(1, 1)])
    dus = C.doc_units("﻿First para.\n\nSecond.", "document-paragraph")
    u2 = {"lines": "1-1", "span": dus[0].span(), "disposition": C.OBS, "edit": "New first."}
    check("D3: a replace on a BOM file's first line keeps the BOM",
          C.apply_file("﻿First para.\n\nSecond.", C.plan_ops([u2], "document"), "document")
          == "﻿New first.\n\nSecond.")

    # D4/D6: in a repo
    dirs.append(new_repo("cons_selftest_data_"))
    write("A.java", "class A {\n  void f() {\n    // retry once\n    g();\n  }\n}\n")
    write("a.py", "x = 1\n# TASK-1: flush before close\ny = 2\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "DD", "--scope", "a.py",
        "--out", ".consolidation/dd.record")
    run("record-init", "--pass-kind", "comment", "--unit-id", "DJ", "--scope", "A.java",
        "--out", ".consolidation/j.record")
    fill(".consolidation/j.record", lambda u: {"disposition": C.OBS, "basis": "no retry",
                                               "edit": "// note \\u000a Runtime.getRuntime();"})
    check("B4: a Java edit may not carry a \\uXXXX escape",
          run("record-check", "--record", ".consolidation/j.record")[0] == C.FAIL)
    fill(".consolidation/dd.record", lambda u: {"disposition": C.STRIP, "basis": "ticket is history",
                                                "edit": "# flush before close  "})
    check("D4: trailing whitespace in an edit is stripped on parse",
          run("record-check", "--record", ".consolidation/dd.record")[0] == C.OK)
    run("apply", "--record", ".consolidation/dd.record")
    sh("git", "add", "a.py")
    sh("git", "commit", "-q", "-F", ".consolidation/dd.commit-msg")
    check("D4: a trailing-whitespace edit gates clean after the commit-message round trip",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)

    rec = C.parse_record(".consolidation/dd.record")
    txt = C.render_record(rec)
    Path(".consolidation/m1.record").write_bytes(
        C.encode(txt.replace("edit:\n| # flush before close", "edit:\n| # first\n\n| # second")))
    code, out = run("record-check", "--record", ".consolidation/m1.record")
    check("D4: a blank line inside an edit block fails record-check",
          code == C.FAIL and "blank line" in out)
    Path(".consolidation/m2.record").write_bytes(C.encode(txt.replace("basis:", "basis2:", 1)))
    code, out = run("record-check", "--record", ".consolidation/m2.record")
    check("D4: an unknown key fails record-check", code == C.FAIL and "unknown key" in out)
    Path(".consolidation/m3.record").write_bytes(C.encode(re.sub(r"baseline_sha: \w+\n", "", txt)))
    check("D4: a header without baseline_sha fails every command, crashing none",
          all(run(*cmd, "--record", ".consolidation/m3.record")[0] == C.FAIL
              for cmd in (("gate", "--pre"), ("gate", "--unit"), ("record-check",),
                          ("bound-check",), ("review-pack",))))
    rec.units[0]["preview"] = "harmless TODO"
    C.write_record(rec, ".consolidation/m4.record")
    check("D4: a tampered preview fails identity",
          run("record-check", "--record", ".consolidation/m4.record")[0] == C.FAIL)

    Path("sub").mkdir()
    os.chdir("sub")
    C.ORIG_CWD = os.getcwd()
    run("escalate", "--file", "../a.py", "--line", "2", "--kind", "suspected-defect", "--divergence", "x")
    os.chdir("..")
    C.ORIG_CWD = os.getcwd()
    run("escalate", "--file", "a.py", "--line", "2", "--kind", "suspected-defect", "--divergence", "x")
    check("D6: the escalate ref is the repo-relative path however it was typed",
          read("intake.md").count("`a.py:2`") == 1)


def _record_channel_tests(dirs):
    dirs.append(new_repo("cons_selftest_chan_"))
    write("m.py", "# note\nx = 1\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n.consolidation.json\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "record_channel": "file"}')
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "F1", "--scope", "m.py",
        "--out", ".consolidation/f1.record")
    fill(".consolidation/f1.record", lambda u: {"disposition": C.REGEN, "basis": "restates x = 1"})
    code, out = run("apply", "--record", ".consolidation/f1.record")
    check("E2: the file channel prints a content commit and a record commit, both -F",
          len(re.findall(r"git -C \S+ commit -F", out)) == 2 and ".content-msg" in out and "reset --mixed HEAD~2" in out)
    check("E2: the content message carries the summary but not the record",
          C.RECORD_BEGIN not in read(".consolidation/f1.content-msg")
          and C.RECORD_BEGIN in read(".consolidation/f1.commit-msg"))
    sh("git", "add", "m.py")
    sh("git", "commit", "-q", "-F", ".consolidation/f1.content-msg")
    sh("git", "add", "-f", ".consolidation/f1.record")
    sh("git", "commit", "-q", "-F", ".consolidation/f1.commit-msg")
    check("E2: gate --unit --record-from-commit HEAD works through the file channel",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    check("E2: the next record-init accepts the two-commit tip (S24: the record commit answers for its content commit)",
          run("record-init", "--pass-kind", "comment", "--unit-id", "F2", "--scope", "m.py",
              "--out", ".consolidation/f2.record")[0] == C.OK)

    # a nil pass commits its record with -F, so --record-from-commit HEAD works there too
    write("m2.py", "# must comply with PCI-DSS req 3.4\nq = 1\n")
    sh("git", "add", "m2.py")
    sh("git", "commit", "-q", "-m", "feat: add m2")
    run("record-init", "--pass-kind", "comment", "--unit-id", "F3", "--scope", "m2.py",
        "--out", ".consolidation/f3.record")
    fill(".consolidation/f3.record", lambda u: {"disposition": C.NV, "basis": "PCI-DSS is external"})
    code, out = run("apply", "--record", ".consolidation/f3.record")
    check("E2: a nil pass tells -F, never -m", re.search(r"git -C \S+ commit -F", out) and "commit -m" not in out)
    sh("git", "add", "-f", ".consolidation/f3.record")
    sh("git", "commit", "-q", "-F", ".consolidation/f3.commit-msg")
    check("E2: a nil pass passes gate --unit --record-from-commit HEAD",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)

    # R-runner 2: a mechanical: subject alone bypasses nothing
    write("m2.py", "# must comply with PCI-DSS req 3.4\nq = 1\nimport shutil\n")
    sh("git", "add", "m2.py")
    sh("git", "commit", "-q", "-m", "mechanical: touch up")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "F4", "--scope", "m2.py",
                    "--out", ".consolidation/f4.record")
    check("a mechanical commit whose diff exceeds the allowances fails the history gate",
          code == C.FAIL and "mechanical" in out)
    sh("git", "reset", "-q", "--hard", "HEAD~1")
    write("d.md", "---\nlast-verified-at: old\n---\n# T\n")
    sh("git", "add", "d.md")
    sh("git", "commit", "-q", "-m", "feat: doc")
    write("d.md", "---\nlast-verified-at: new\n---\n# T\n")
    sh("git", "add", "d.md")
    sh("git", "commit", "-q", "-m", "mechanical: lva refresh")
    check("an lva-only mechanical commit is tolerated by the history gate",
          run("record-init", "--pass-kind", "comment", "--unit-id", "F5", "--scope", "m2.py",
              "--out", ".consolidation/f5.record")[0] == C.OK)


def _document_tests():
    write("app.py", "import os\n")
    write("doc.md", DOC)
    write("intake.md", "")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "D1", "--scope", "doc.md", "--out", ".consolidation/d1.record")
    rec = C.parse_record(".consolidation/d1.record")
    check("document units: headings separate, paragraphs blank-line delimited",
          [u["lines"] for u in rec.units] == ["1-1", "3-3", "5-5", "7-7", "9-9", "11-11"])
    dec = {"3-3": {"disposition": C.OBS, "basis": "HMAC path removed; auth/sign.js uses Ed25519",
                   "edit": "Tokens are signed with Ed25519."},
           "5-5": {"disposition": C.NV, "basis": "GDPR is external", "tbc": "Confirm the retention period against GDPR Art. 5."},
           "7-7": {"disposition": C.STRIP, "basis": "ticket id is history", "edit": "See for the history of the cache."}}
    fill(".consolidation/d1.record", lambda u: dec.get(u["lines"], {"disposition": C.STILL, "basis": "verified"}))
    check("document record-check passes", run("record-check", "--record", ".consolidation/d1.record")[0] == C.OK)
    rec = C.parse_record(".consolidation/d1.record")
    rec.units[3]["disposition"] = C.REGEN
    C.write_record(rec, ".consolidation/t.record")
    check("regenerable → delete is refused in a document pass (S46)",
          run("record-check", "--record", ".consolidation/t.record")[0] == C.FAIL)
    run("apply", "--record", ".consolidation/d1.record")
    d = read("doc.md")
    check("document apply: sentence edited, TBC section written, strip applied",
          "Ed25519" in d and "HMAC" not in d and "## To be confirmed\n\n- Confirm the retention" in d
          and "TASK-0099" not in d and "Retention follows GDPR" in d)
    sh("git", "add", "doc.md")
    sh("git", "commit", "-q", "-F", ".consolidation/d1.commit-msg")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("document gate --unit passes", code == C.OK)
    run("record-init", "--pass-kind", "document", "--unit-id", "D2", "--scope", "doc.md:9-20",
        "--out", ".consolidation/d2.record")
    rec = C.parse_record(".consolidation/d2.record")
    check("H3: a subset scope enumerates only units starting inside the range",
          rec.header["scope"] == "doc.md:9-20" and all(9 <= C.ulines(u)[0] <= 20 for u in rec.units) and rec.units)
    tbc = [u for u in rec.units if u.get("in_tbc") == "yes"]
    check("items under ## To be confirmed are units marked in_tbc", len(tbc) == 1)

    # --- A3: a document or severance pass never covers a code file
    check("A3: record-init refuses a document pass over a code file",
          run("record-init", "--pass-kind", "document", "--unit-id", "D3", "--scope", "app.py",
              "--out", ".consolidation/d3.record")[0] == C.FAIL)
    rec = C.parse_record(".consolidation/d1.record")
    rec.header["scope"] = "app.py"
    C.write_record(rec, ".consolidation/t.record")
    code, out = run("record-check", "--record", ".consolidation/t.record")
    check("A3: record-check refuses a document record over a code file",
          code == C.FAIL and "documentation files" in out)

    # --- E1: a second document pass over an open TBC item neither fails nor duplicates it
    run("escalate", "--from-record", ".consolidation/d1.record")
    run("record-init", "--pass-kind", "document", "--unit-id", "D4", "--scope", "doc.md",
        "--out", ".consolidation/d4.record")
    rec = C.parse_record(".consolidation/d4.record")
    body = [u for u in rec.units if "Retention follows GDPR" in u.get("preview", "")]
    check("E1: pass 2 sees the body paragraph and the section item as separate units",
          len(body) == 1 and body[0].get("in_tbc") != "yes"
          and len([u for u in rec.units if u.get("in_tbc") == "yes"]) == 1)
    fill(".consolidation/d4.record", lambda u: (
        {"disposition": C.NV, "basis": "GDPR is external"} if "Retention follows GDPR" in u.get("preview", "")
        else {"disposition": C.STILL, "basis": "verified"}))
    check("E1: an open intake entry on the fingerprint exempts the unit from tbc:",
          run("record-check", "--record", ".consolidation/d4.record")[0] == C.OK)
    write("intake.md", "")
    check("E1: without the intake entry the tbc: item text is required again",
          run("record-check", "--record", ".consolidation/d4.record")[0] == C.FAIL)
    run("escalate", "--from-record", ".consolidation/d4.record")
    # this repo's intake is tracked (the real one lives outside the repo or ignored): restore it,
    # as the unit's commit may not carry it; the record now carries its own tbc: item text
    sh("git", "checkout", "--", "intake.md")
    fill(".consolidation/d4.record", lambda u: (
        {"disposition": C.NV, "basis": "GDPR is external",
         "tbc": "Confirm the retention period against GDPR Art. 5."}
        if "Retention follows GDPR" in u.get("preview", "")
        else {"disposition": C.STILL, "basis": "verified"}))
    code, out = run("apply", "--record", ".consolidation/d4.record")
    check("E1: apply adds no duplicate of an item the section already holds",
          read("doc.md").count("- Confirm the retention period") == 1)
    check("E2: a nil pass prints the -F record commit and the mixed-reset undo",
          "commit -F" in out and "reset --mixed HEAD~1" in out and "git commit -m" not in out)
    sh("git", "add", "-f", ".consolidation/d4.record")
    sh("git", "commit", "-q", "-F", ".consolidation/d4.commit-msg")
    check("E1/E2: the nil second pass passes gate --unit through the commit message",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)

    # --- R-runner 1: the TBC locator follows doc_units' rules; R4/5: BOMs
    write("doc2.md", "# T\n\nExternal rule applies.\n\n  ## To be confirmed\n\n- existing item\n\n"
                     "## Next\n\nBody text.\n")
    commit("feat: doc2", "doc2.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "D5", "--scope", "doc2.md",
        "--out", ".consolidation/d5.record")
    fill(".consolidation/d5.record", lambda u: (
        {"disposition": C.NV, "basis": "external rule", "tbc": "External rule applies, confirm?"}
        if u.get("preview", "").startswith("External rule applies.")
        else {"disposition": C.STILL, "basis": "verified"}))
    run("apply", "--record", ".consolidation/d5.record")
    d2 = read("doc2.md")
    check("an indented ## To be confirmed section is found, no second one appended",
          d2.count("## To be confirmed") == 1 and "- External rule applies, confirm?" in d2
          and d2.index("- existing item") < d2.index("confirm?"))
    write("doc3.md", "# T\n\nExternal fact.\n\n```text\n## To be confirmed\n```\n\nBody text.\n")
    commit("feat: doc3", "doc3.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "D6", "--scope", "doc3.md",
        "--out", ".consolidation/d6.record")
    fill(".consolidation/d6.record", lambda u: (
        {"disposition": C.NV, "basis": "external fact", "tbc": "Confirm the fact?"}
        if u.get("preview", "").startswith("External fact.")
        else {"disposition": C.STILL, "basis": "verified"}))
    run("apply", "--record", ".consolidation/d6.record")
    d3 = read("doc3.md")
    check("a fenced pseudo-heading never becomes the section; the real one lands at EOF",
          d3.count("## To be confirmed") == 2 and "```text\n## To be confirmed\n```" in d3
          and d3.rstrip().endswith("- Confirm the fact?"))
    write("bom.md", "﻿---\ntitle: x\n---\n\n# H\n\nBody text.\n")
    commit("feat: bom", "bom.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "D7", "--scope", "bom.md",
        "--out", ".consolidation/d7.record")
    rec = C.parse_record(".consolidation/d7.record")
    check("a BOM must not expose front matter as units", rec.units and min(C.ulines(u)[0] for u in rec.units) >= 5)
    with open(".consolidation/d1t.targets", "wb") as f:
        f.write(b"\xef\xbb\xbf# floor: self-report\n# pass_kind: document\ndoc.md\t6\n")
    check("a BOM'd target-set file parses (the first line is not a file)",
          run("scope-cross-check", "--record", ".consolidation/d4.record",
              "--target-set", ".consolidation/d1t.targets")[0] == C.OK)


def _severance_tests():
    write("guide.md", "See docs/auth.md and auth.md, not oauth.md.\nKeep auth.md here.\n")
    write("intake.md", "")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    commit("base")
    run("record-init", "--pass-kind", "severance", "--unit-id", "S1", "--scope", "guide.md",
        "--target", "docs/auth.md", "--out", ".consolidation/s1.record")
    rec = C.parse_record(".consolidation/s1.record")
    check("M1: severance counts path-segment occurrences, not oauth.md", len(rec.units) == 3)
    fill(".consolidation/s1.record", lambda u: (
        {"disposition": C.SEV, "basis": "inventory entry docs/auth.md", "edit": "See the auth section."}
        if u["id"] == "1" else
        {"disposition": C.SEV, "basis": "inventory entry docs/auth.md"} if u["id"] == "2" else
        {"disposition": C.RET, "basis": "load-bearing", "escalate": "load-bearing-reference"}))
    check("severance record-check passes", run("record-check", "--record", ".consolidation/s1.record")[0] == C.OK)
    run("apply", "--record", ".consolidation/s1.record")
    check("severance apply rewrites the line and keeps the retained one",
          read("guide.md") == "See the auth section.\nKeep auth.md here.\n")

    # --- A3: severance edit proofs
    def sev_case(name, mutate):
        rec = C.parse_record(".consolidation/s1.record")
        mutate(rec)
        C.write_record(rec, ".consolidation/t.record")
        return run("record-check", "--record", ".consolidation/t.record")[0]

    check("A3: a severed edit may not keep the target",
          sev_case("keeps", lambda r: r.units[0].update(edit="See docs/auth.md for keys.")) == C.FAIL)
    check("A3: a severed edit is one line",
          sev_case("two lines", lambda r: r.units[0].update(edit="See the auth section.\nSECOND LINE")) == C.FAIL)
    check("A3: a severed edit drops no retained occurrence on its line",
          sev_case("drops retained", lambda r: r.units[1].update(disposition=C.RET, basis="load-bearing"))
          == C.FAIL)
    write("load.py", "cfg = load('settings.json')\n")
    commit("sev base", "load.py")
    check("A3: record-init refuses a severance pass over a code file",
          run("record-init", "--pass-kind", "severance", "--unit-id", "S2", "--scope", "load.py",
              "--target", "settings.json", "--out", ".consolidation/s2.record")[0] == C.FAIL)
    check("E5: target-set refuses --scope for a severance pass (the inventory names the documents)",
          run("target-set", "--pass-kind", "severance", "--scope", "guide.md")[0] == C.FAIL)

    # R4c: a severed line 1 keeps the BOM
    rec = C.parse_record(".consolidation/s1.record")
    out = C.apply_file("﻿See docs/auth.md now.\n", [(rec.units[0], "sever", ["See nothing here."])], "severance")
    check("a severed line 1 keeps the BOM", out == "﻿See nothing here.\n")


def _v21_tests(dirs):
    """Regression checks for the v2.1 analysis findings (plan Phase 1, items 1–32)."""
    dirs.append(new_repo("cons_selftest_v21_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("ind.py", "def f():\n    # drop the cached value\n    x = 1\n# drop the cached value\ny = 2\n")
    write("dup.js", "// end of block\na();\n// end of block\nb();\n")
    commit("base")

    # 1: the occurrence index is counted on the normalized body the fingerprint hashes
    run("record-init", "--pass-kind", "comment", "--unit-id", "V1", "--scope", "ind.py",
        "--out", ".consolidation/v1.record")
    rec = C.parse_record(".consolidation/v1.record")
    check("v2.1-1: comments differing only in indentation get distinct fingerprints",
          len(rec.units) == 2 and len({u["fingerprint"] for u in rec.units}) == 2)

    # 2: carry-from leaves a unit uncarried when its body group shrank and the judgements differed
    run("record-init", "--pass-kind", "comment", "--unit-id", "M1", "--scope", "dup.js",
        "--out", ".consolidation/m1.record")
    fill(".consolidation/m1.record", lambda u: (
        {"disposition": C.REGEN, "basis": "restates a()"} if u["lines"] == "1-1"
        else {"disposition": C.STILL, "basis": "marks the end of the retry block for the reader"}))
    write("dup.js", "a();\n// end of block\nb();\n")
    commit("feat: a() block ends itself", "dup.js")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "M2", "--scope", "dup.js",
                    "--carry-from", ".consolidation/m1.record", "--out", ".consolidation/m2.record")
    rec = C.parse_record(".consolidation/m2.record")
    check("v2.1-2: a shifted occurrence index never carries the deleted twin's judgement",
          code == C.OK and len(rec.units) == 1 and not rec.units[0].get("disposition") and "uncarried" in out)
    fill(".consolidation/m1.record", lambda u: {"disposition": C.STILL, "basis": "marks the end of the block"})
    run("record-init", "--pass-kind", "comment", "--unit-id", "M3", "--scope", "dup.js",
        "--carry-from", ".consolidation/m1.record", "--out", ".consolidation/m3.record")
    check("v2.1-2: a shrunk group whose members shared one judgement still carries",
          C.parse_record(".consolidation/m3.record").units[0].get("disposition") == C.STILL)

    # 3: a ruling binds once — the twin that inherits the fingerprint is refused
    write("tw.py", "# legacy flush note\nx = 1\n# legacy flush note\ny = 2\n")
    commit("feat: tw", "tw.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "R1", "--scope", "tw.py",
        "--out", ".consolidation/r1.record")
    r1 = C.parse_record(".consolidation/r1.record")
    fp1 = r1.units[0]["fingerprint"]
    run("escalate", "--file", "tw.py", "--line", "1", "--kind", "suspected-defect", "--divergence", "legacy")
    run("escalate", "--rule", "--file", "tw.py", "--line", "1", "--ruling-text", "delete the first note")
    fill(".consolidation/r1.record", lambda u: (
        {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1} if u["id"] == "1"
        else {"disposition": C.STILL, "basis": "the second note stays per the owner"}))
    run("apply", "--record", ".consolidation/r1.record")
    sh("git", "add", "tw.py")
    sh("git", "commit", "-q", "-F", ".consolidation/r1.commit-msg")
    check("v2.1-3: the unit applying the ruling passes gate --unit",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    code, out = run("escalate", "--close-applied", "--record-from-commit", "HEAD")
    check("v2.1-3: --close-applied writes applied= and closes the entry",
          code == C.OK and "state=applied" in read("intake.md") and f"applied={fp1}:R1@" in read("intake.md"))
    check("v2.1-3: the applying unit still passes gate --unit after the close",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    run("record-init", "--pass-kind", "comment", "--unit-id", "R2", "--scope", "tw.py",
        "--out", ".consolidation/r2.record")
    r2 = C.parse_record(".consolidation/r2.record")
    check("v2.1-3 premise: the surviving twin now carries the applied fingerprint", r2.units[0]["fingerprint"] == fp1)
    fill(".consolidation/r2.record", lambda u: {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp1})
    code, out = run("record-check", "--record", ".consolidation/r2.record")
    check("v2.1-3: an applied ruling never binds the twin that inherited its fingerprint",
          code == C.FAIL and "already applied" in out)
    # review C: the closed entry never suppresses the twin's escalation; a fresh ruling binds it
    code, out = run("escalate", "--file", "tw.py", "--line", "1", "--fingerprint", fp1,
                    "--kind", "suspected-defect", "--divergence", "legacy (twin)")
    check("review C: escalating the twin of an applied ruling opens a fresh entry (never suppressed)",
          code == C.OK and "suppressed" not in out and read("intake.md").count(f"fingerprint={fp1}") == 2)
    code, out = run("record-check", "--record", ".consolidation/r2.record")
    check("review C: the old ruling still does not bind the twin while its fresh entry is open",
          code == C.FAIL)
    run("escalate", "--rule", "--file", "tw.py", "--line", "1", "--fingerprint", fp1,
        "--ruling-text", "delete the second note too")
    check("review C: the owner's fresh ruling binds the twin",
          run("record-check", "--record", ".consolidation/r2.record")[0] == C.OK)
    lines = read("intake.md").split("\n")
    check("review C: a lookup by fingerprint prefers the live entry over the applied one",
          C.find_intake(lines, fp=fp1)[1]["fields"].get("state") == "ruled")

    # 4: ruled-external is a pure keep
    write("ex.py", "# PCI-DSS req 3.4 applies\nx = 1\n# card data is masked\ny = 2\n")
    commit("feat: ex", "ex.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "X1", "--scope", "ex.py",
        "--out", ".consolidation/x1.record")
    xr = C.parse_record(".consolidation/x1.record")
    run("escalate", "--file", "ex.py", "--line", "1", "--kind", "unverifiable-statement", "--divergence", "PCI")
    code, _ = run("escalate", "--rule", "--external", "--file", "ex.py", "--line", "1", "--ruling-text", "true",
                  "--also-fingerprint", xr.units[1]["fingerprint"])
    check("v2.1-4: --external with --also-fingerprint is refused", code == C.FAIL and "RULED" not in read("intake.md").split("`ex.py:1`")[-1])

    # 6: a CRLF config under core.autocrlf=true is the committed config
    sh("git", "config", "core.autocrlf", "true")
    write(".consolidation.json", '{\n  "intake_path": "intake.md"\n}\n', crlf=True)
    commit("chore: config", ".consolidation.json")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "CR", "--scope", "ex.py",
                    "--out", ".consolidation/cr.record")
    fill(".consolidation/cr.record", lambda u: {"disposition": C.STILL, "basis": "a reason"})
    check("v2.1-6: a CRLF worktree config with an LF blob passes record-init and record-check",
          code == C.OK and run("record-check", "--record", ".consolidation/cr.record")[0] == C.OK)
    sh("git", "config", "core.autocrlf", "false")

    # 7: a cp1252 source file round-trips through the commit message
    Path("lat.js").write_bytes(b"// il valore \xe8 fisso\nx = 1;\n")
    commit("feat: lat", "lat.js")
    run("record-init", "--pass-kind", "comment", "--unit-id", "L1", "--scope", "lat.js",
        "--out", ".consolidation/l1.record")
    fill(".consolidation/l1.record", lambda u: {"disposition": C.REGEN, "basis": "restates x = 1"})
    run("apply", "--record", ".consolidation/l1.record")
    sh("git", "add", "lat.js")
    sh("git", "commit", "-q", "-F", ".consolidation/l1.commit-msg")
    check("v2.1-7: a non-UTF-8 preview survives the commit-message round trip (gate --unit)",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    check("v2.1-32: a gated unit's commit is remembered by the history walk",
          run("preflight")[0] == C.OK and C.head_sha() in (C._verified_commits()))

    # 8: the default record path is the repository root's, wherever the command is typed
    Path("sub").mkdir(exist_ok=True)
    root = os.getcwd()
    C.ORIG_CWD = str(Path(root) / "sub")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "SUBDIR", "--scope", "../ex.py")
    C.ORIG_CWD = root
    check("v2.1-8: record-init from a subdirectory writes under the root's .consolidation/",
          code == C.OK and list(Path(".consolidation").glob("SUBDIR-*.record"))
          and not Path("sub/.consolidation").exists())
    check("v2.1-12: an unusual id is refused (it names files and intake entries)",
          run("record-init", "--pass-kind", "comment", "--unit-id", "U 1", "--scope", "ex.py")[0] == C.FAIL)
    check("v2.1-28: a comma in a scope path is refused clearly",
          "comma" in run("record-init", "--pass-kind", "comment", "--unit-id", "CM", "--scope", "a,b.py")[1])
    check("v2.1-24: a floor outside the three is refused at record-init",
          run("record-init", "--pass-kind", "comment", "--unit-id", "FL", "--scope", "ex.py",
              "--floor", "grpah")[0] != C.OK)

    # 9: a record saved with a BOM parses
    raw = Path(".consolidation/cr.record").read_bytes()
    Path(".consolidation/bom.record").write_bytes(b"\xef\xbb\xbf" + raw)
    check("v2.1-9: a BOM'd record parses", not C.parse_record(".consolidation/bom.record").problems)
    Path(".consolidation/u16.targets").write_bytes("# floor: self-report\nex.py\t2\n".encode("utf-16"))
    check("v2.1-9: a UTF-16 target-set file (PowerShell 5.1 `>`) reads", C.read_text_file(".consolidation/u16.targets")
          .splitlines()[1] == "ex.py\t2")

    # 11, 12: provider rows and printed paths
    check("v2.1-11: provider paths are normalized (backslashes, ./)",
          C._provider_rows(["./a.py", "b\\c.md\tnote\t.\\t.md", "# observed: x"]) == ["a.py", "b/c.md\tnote\tt.md"])
    check("v2.1-12: a path with a space is quoted in printed commands",
          C._q("a b.py") == '"a b.py"' and C._q("src/a.py") == "src/a.py")

    # 13, 16, 17: To be confirmed items
    check("v2.1-13: an item keeps a leading '-' or '*' of its own text",
          C.tbc_item_body("-1 is returned when the key is missing") == "-1 is returned when the key is missing"
          and C.tbc_item_body("**Owner** must confirm") == "**Owner** must confirm"
          and C.tbc_item_body("- Confirm X") == "Confirm X" and C.tbc_item_body("2. Confirm X") == "Confirm X")
    check("v2.1-16: a BOM before a line-1 section heading is found",
          C._tbc_heading_index(["﻿## To be confirmed", "", "- a"]) == 0)
    op = {"lines": "1-1", "span": "1:0-1:5", "disposition": C.NV, "tbc": "Confirm X", "file": "d.md"}
    check("v2.1-17: a numbered item is not duplicated",
          C.apply_file("Body.\n\n## To be confirmed\n\n1. Confirm X\n", C.plan_ops([op], "document"), "document")
          .count("Confirm X") == 1)

    # 14, 15, 5: document flows
    write("nn.md", "# T\n\nRetention follows the contract.")
    write("fe.md", "# T\n\nExternal rule.\n\n```text\nopen fence")
    commit("feat: docs", "nn.md", "fe.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "N1", "--scope", "nn.md",
        "--out", ".consolidation/n1.record")
    fill(".consolidation/n1.record", lambda u: (
        {"disposition": C.NV, "basis": "the contract is external", "tbc": "Confirm the retention period."}
        if "Retention" in u.get("preview", "") else {"disposition": C.STILL, "basis": "title"}))
    run("escalate", "--from-record", ".consolidation/n1.record")
    check("v2.1-5: the paragraph's entry carries its item key (tbc=)",
          f"tbc={C.tbc_key('Confirm the retention period.')}" in read("intake.md"))
    run("apply", "--record", ".consolidation/n1.record")
    sh("git", "add", "nn.md")
    sh("git", "commit", "-q", "-F", ".consolidation/n1.commit-msg")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("v2.1-14: an item appended to a file with no final newline passes gate --unit", code == C.OK)
    run("record-init", "--pass-kind", "document", "--unit-id", "N2", "--scope", "nn.md",
        "--unit-rule", "document-block", "--out", ".consolidation/n2.record")
    fill(".consolidation/n2.record", lambda u: {"disposition": C.NV, "basis": "external"} if u.get("in_tbc") == "yes"
         or "Retention" in u.get("preview", "") else {"disposition": C.STILL, "basis": "heading"})
    before = read("intake.md").count("\n")
    code, out = run("escalate", "--from-record", ".consolidation/n2.record")
    check("v2.1-5: the item is never escalated again (S66)",
          "S66" in out and read("intake.md").count("\n") == before)
    pfp = [u for u in C.parse_record(".consolidation/n1.record").units if "Retention" in u.get("preview", "")][0]["fingerprint"]
    run("escalate", "--rule", "--file", "nn.md", "--line", "3", "--fingerprint", pfp,
        "--ruling-text", "false: the contract no longer fixes retention; remove it")
    fill(".consolidation/n2.record", lambda u: (
        {"disposition": C.RULED, "basis": "owner ruling", "ruling": pfp}
        if u.get("in_tbc") == "yes" or "Retention" in u.get("preview", "")
        else {"disposition": C.STILL, "basis": "heading"}))
    code, out = run("record-check", "--record", ".consolidation/n2.record")
    check("v2.1-5: the paragraph's ruling removes its item too (S65)", code == C.OK)
    run("record-init", "--pass-kind", "document", "--unit-id", "F1", "--scope", "fe.md",
        "--out", ".consolidation/f1.record")
    fill(".consolidation/f1.record", lambda u: (
        {"disposition": C.NV, "basis": "external", "tbc": "Confirm the rule."}
        if "External" in u.get("preview", "") else {"disposition": C.STILL, "basis": "kept"}))
    code, out = run("record-check", "--record", ".consolidation/f1.record")
    check("v2.1-15: a section is never appended inside an unclosed fence", code == C.FAIL and "unclosed" in out)

    # review F: under the default document-paragraph rule each To be confirmed item is its own unit
    write("two.md", "# T\n\nRetention follows the contract.\n\nThe SLA is set by the vendor.\n")
    commit("feat: two", "two.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "T1", "--scope", "two.md",
        "--out", ".consolidation/t1.record")
    fill(".consolidation/t1.record", lambda u: (
        {"disposition": C.NV, "basis": "external", "tbc": "Confirm the retention period."}
        if "Retention" in u.get("preview", "") else
        {"disposition": C.NV, "basis": "external", "tbc": "Confirm the SLA."}
        if "SLA" in u.get("preview", "") else {"disposition": C.STILL, "basis": "title"}))
    run("escalate", "--from-record", ".consolidation/t1.record")
    run("apply", "--record", ".consolidation/t1.record")
    sh("git", "add", "two.md")
    sh("git", "commit", "-q", "-F", ".consolidation/t1.commit-msg")
    run("record-init", "--pass-kind", "document", "--unit-id", "T2", "--scope", "two.md",
        "--out", ".consolidation/t2.record")
    items = [u for u in C.parse_record(".consolidation/t2.record").units if u.get("in_tbc") == "yes"]
    check("review F: two To be confirmed items are two units under document-paragraph", len(items) == 2)
    fill(".consolidation/t2.record", lambda u: {"disposition": C.NV, "basis": "external"}
         if u.get("in_tbc") == "yes" or u["preview"][:1] in ("R", "T") and "#" not in u["preview"]
         else {"disposition": C.STILL, "basis": "heading"})
    before = read("intake.md").count("\n")
    code, out = run("escalate", "--from-record", ".consolidation/t2.record")
    check("review F: neither item is escalated again (S66)", read("intake.md").count("\n") == before)

    # 19: apply checks every file before writing any
    write("p1.js", "// restates a\na();\n")
    write("p2.js", "// restates b\nb();\n")
    commit("feat: p", "p1.js", "p2.js")
    run("record-init", "--pass-kind", "comment", "--unit-id", "P1", "--scope", "p1.js", "p2.js",
        "--out", ".consolidation/p1.record")
    fill(".consolidation/p1.record", lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    write("p2.js", "// restates b\nb();\nc();\n")
    check("v2.1-19: a refusal leaves no half-applied tree",
          run("apply", "--record", ".consolidation/p1.record")[0] == C.FAIL and read("p1.js").startswith("// restates a"))
    sh("git", "checkout", "--", "p2.js")

    # 21, 22, 23, 29: review pack and ADR check
    write("ad.py", "# we chose polling over webhooks: the vendor drops webhook retries\npoll()\n# restates poll\npoll()\n# a reason\nz = 1\n")
    commit("feat: ad", "ad.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "AD", "--scope", "ad.py",
        "--out", ".consolidation/ad.record")
    fill(".consolidation/ad.record", lambda u: (
        {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
         "adr": "docs/adr/0001-polling.md"} if u["lines"] == "1-1"
        else {"disposition": C.REGEN, "basis": "restates poll()"} if u["lines"] == "3-3"
        else {"disposition": C.STILL, "basis": "carries a reason"}))
    s = C.spot_sample(C.parse_record(".consolidation/ad.record"), 0.25)
    check("v2.1-21: the spot-check is drawn from the entries that change nothing", s == {"3"})
    check("v2.1-22: a pack fence outruns the backticks of its content", C._fenced("a ``` b")[0] == "````")
    run("apply", "--record", ".consolidation/ad.record")
    sh("git", "add", "ad.py")
    sh("git", "commit", "-q", "-F", ".consolidation/ad.commit-msg")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("v2.1-29: gate --unit fails when the named ADR was not added", code == C.FAIL and "ADR" in out)
    write("docs/adr/0001-polling.md", "# 0001 — Polling over webhooks\n\nStatus: accepted\n")
    sh("git", "add", "docs/adr/0001-polling.md")
    sh("git", "commit", "-q", "--amend", "--no-edit")
    check("v2.1-29: with the ADR added the unit passes",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    code, out = run("review-pack", "--record-from-commit", "HEAD", "--out", ".consolidation/ad.review.md")
    pack = read(".consolidation/ad.review.md")
    check("v2.1-23: the pack reports the gate verdict and lists the ADR file",
          "Gate: GATE PASSED" in pack and "docs/adr/0001-polling.md" in pack)

    # Phase 3: the batch flow (ADR 0013) — a master record classified once, cut bottom-up into
    # review units under the caps, each run end to end by batch-next
    dirs.append(new_repo("cons_selftest_batch_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 3}')
    write("big.py", "# restates a\na()\n# restates b\nb()\n# end of block\nc()\n# restates d\nd()\n"
                    "# restates e\ne()\ndef g():\n    # end of block\n    h()\n# restates i\ni()\n")
    write("small.js", "// restates go\ngo();\n// legacy auth path\nauth();\n")
    write("adr.py", "# we chose polling over webhooks: the vendor drops webhook retries\npoll()\n")
    write("nil.py", "# a reason the code cannot say\nx = 1\n")
    commit("base")
    code, out = run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1",
                    "--scope", "big.py", "small.js", "adr.py", "nil.py")
    mpath = next(Path(".consolidation").glob("B-1-*.batch"), None)
    check("batch: batch-init writes the master record <B>-<sha7>.batch",
          code == C.OK and mpath is not None and C.parse_record(str(mpath)).header.get("batch_master") == "yes")

    def judge(u):
        if "restates" in u["preview"]:
            return {"disposition": C.REGEN, "basis": "restates the call below"}
        if "end of block" in u["preview"]:
            return ({"disposition": C.STILL, "basis": "marks where the retry block ends"} if u["lines"] == "5-5"
                    else {"disposition": C.REGEN, "basis": "restates the dedent"})
        if "legacy" in u["preview"]:
            return {"disposition": C.DEFECT, "basis": "auth() is the only path; no legacy path exists"}
        if "polling" in u["preview"]:
            return {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
                    "adr": "docs/adr/0001-polling.md"}
        return {"disposition": C.STILL, "basis": "carries a reason"}
    fill(str(mpath), judge)
    code, out = run("escalate", "--from-record", "B-1")
    check("batch: escalate --from-record takes a batch id", code == C.OK and "`small.js:3`" in read("intake.md"))
    fp = [u for u in C.parse_record(str(mpath)).units if "legacy" in u["preview"]][0]["fingerprint"]
    run("escalate", "--rule", "--file", "small.js", "--line", "3", "--fingerprint", fp,
        "--ruling-text", "false: there is no legacy path; delete the comment")
    fill(str(mpath), lambda u: {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp}
         if u["fingerprint"] == fp else None)
    code, out = run("gate", "--pre", "--batch", "B-1")
    check("batch: gate --pre --batch passes a master over the judgement cap (no bound-check)",
          code == C.OK and "bound-check not run" in out)
    check("batch: a master record is never gated --unit", run("gate", "--unit", "--record", str(mpath))[0] == C.FAIL)
    check("batch: a master record is never applied", run("apply", "--record", str(mpath))[0] == C.FAIL)
    code, out = run("batch-plan", "--batch", "B-1")
    plan = read(re.sub(r"\.batch$", ".plan", str(mpath)))
    check("batch: batch-plan cuts a file over the cap bottom-up and packs whole files under the caps",
          code == C.OK and "part 1/4: B-1.1 | judgements 3 | lines 3 | scope: big.py:8-15" in plan
          and "part 2/4: B-1.2 | judgements 3 | lines 3 | scope: big.py:1-7" in plan
          and "part 3/4: B-1.3 | judgements 3 | lines 3 | scope: small.js, adr.py" in plan
          and "part 4/4: B-1.4 | nil | scope: nil.py" in plan)
    us = [{"lines": f"{n}-{n}", "span": f"{n}:0-{n}:5", "disposition": C.OBS} for n in (1, 3, 5, 7, 9)]
    check("batch: a range never starts below the `## To be confirmed` heading",
          C._cut_file("d.md", us, 1, 10, 2, 200)[0][0] == ("d.md", (6, 10))
          and C._cut_file("d.md", us, 1, 10, 2, 200, floor_line=4)[0][0] == ("d.md", (4, 10)))
    code, out = run("batch-next", "--batch", "B-1")
    check("batch: part 1 runs end to end and passes gate --unit", code == C.OK and "GATE PASSED" in out)
    check("ADR 0015: the master record is committed with the review unit",
          C.git_show("HEAD", C.repo_rel(str(mpath))) == read(str(mpath)))
    raw = mpath.read_bytes()
    mpath.write_bytes(raw.replace(b"restates the dedent", b"restates the dedent below"))
    code, out = run("batch-next", "--batch", "B-1")
    check("ADR 0015: a master correction on a unit a done review unit applied stops the batch",
          code == C.FAIL and "changed after a done review unit applied" in out)
    mpath.write_bytes(raw)
    Path(re.sub(r"\.batch$", ".plan", str(mpath))).write_text("# emptied by hand\n", encoding="utf-8")
    code, out = run("batch-next", "--batch", "B-1")
    check("batch: the twin above a deleted twin keeps its own judgement (exact carry)",
          code == C.OK and read("big.py") == "a()\nb()\n# end of block\nc()\nd()\ne()\ndef g():\n    h()\ni()\n")
    check("ADR 0015: an emptied .plan changes nothing — batch-next recomputes the plan", "part 2/4" in out)
    after2 = C.head_sha()
    code, out = run("batch-next", "--batch", "B-1")
    check("batch: a missing ADR stops the unit before apply",
          code == C.FAIL and "docs/adr/0001-polling.md" in out and C.head_sha() == after2)
    write("docs/adr/0001-polling.md", "# 0001 — Polling over webhooks\n\nStatus: accepted\n")
    rec3 = next(Path(".consolidation").glob(f"B-1.3-{after2[:7]}.record"))
    fill(str(rec3), lambda u: {"disposition": C.STILL, "basis": "forged in the part record"})
    code, out = run("batch-next", "--batch", "B-1")
    check("ADR 0015: an edit to a part record is never applied — the record is derived from the master",
          code == C.OK and "GATE PASSED" in out and f"applied={fp}:B-1.3@" in read("intake.md")
          and "state=applied" in read("intake.md") and Path("docs/adr/0001-polling.md").exists()
          and "legacy" not in read("small.js"))
    d3 = C.record_from_commit("HEAD")
    forged = C.Record(dict(d3.header), [dict(u) for u in d3.units])
    forged.units[0]["disposition"] = C.STILL
    check("ADR 0015: a part record whose judgement differs from the committed master fails batch-carry-check",
          any("differ from the master" in x for x in C.batch_carry_problems(forged, "HEAD"))
          and not C.batch_carry_problems(d3, "HEAD"))
    code, out = run("batch-next", "--batch", "B-1")
    check("batch: the nil unit commits only its record; the batch end replays every unit",
          code == C.OK and "record only" in out and "each replayed at its own commit" in out)
    code, out = run("batch-status", "--batch", "B-1")
    check("batch: batch-status reports every unit done, from git",
          code == C.OK and out.count("done ") == 4 and "every review unit is done" in out)
    check("batch: the batch's commits pass the history walk", run("preflight")[0] == C.OK)

    # ADR 0015: the batch's state is git — nothing else sits between its review units
    dirs.append(new_repo("cons_selftest_batchsec_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-2", "--scope", "a.py", "b.py")
    m2 = next(Path(".consolidation").glob("B-2-*.batch"))
    fill(str(m2), lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    run("batch-plan", "--batch", "B-2")
    code, out = run("batch-next", "--batch", "B-2")
    one = C.head_sha()
    write("backdoor.py", "import os\n")
    commit("mechanical: refresh last-verified-at", "backdoor.py")
    code, out = run("batch-next", "--batch", "B-2")
    check("ADR 0015: a mechanical commit inside a batch stops it (a batch range holds only runner commits)",
          code == C.FAIL and "is not review unit B-2.2" in out)
    sh("git", "reset", "-q", "--hard", one)
    write("a.py", "a()\nimport os\n")
    sh("git", "add", "a.py")
    sh("git", "commit", "-q", "--amend", "--no-edit")
    code, out = run("batch-next", "--batch", "B-2")
    check("ADR 0015: an amended review unit carrying code stops the next run (its replay fails)",
          code == C.FAIL and "does not pass its gate" in out and "undo:" in out)
    sh("git", "reset", "-q", "--hard", one)
    check("ADR 0015: after the undo the batch completes", run("batch-next", "--batch", "B-2")[0] == C.OK
          and "complete" in run("batch-next", "--batch", "B-2")[1])

    # ADR 0015: the history walk has no cap, and a mechanical commit is covered only inside a unit
    dirs.append(new_repo("cons_selftest_walk_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("w.py", "# restates w\nw()\n")
    write("d.md", "# Doc\n\nText.\n")
    commit("base")
    write("backdoor.py", "import os\n")
    commit("mechanical: refresh", "backdoor.py")
    tip = C.head_sha()
    tree = C.git("rev-parse", f"{tip}^{{tree}}").strip()
    for i in range(201):
        tip = C.git("commit-tree", tree, "-p", tip, "-m", f"mechanical: lva {i}").strip()
    sh("git", "reset", "-q", "--hard", tip)
    code, out = run("preflight")
    check("ADR 0015: 201 empty mechanical commits no longer hide one that adds code",
          code == C.FAIL and "exceeds the allowances" in out)
    sh("git", "reset", "-q", "--hard", "HEAD~202")
    write("w.py", "---\nlast-verified-at: x\n---\n# restates w\nw()\n")
    write("d.md", "---\nlast-verified-at: x\n---\n# Doc\n\nText.\n")
    commit("mechanical: refresh last-verified-at", "w.py", "d.md")
    cfg = C.load_config()
    check("review B: last-verified-at front matter is a mechanical change in a document only",
          C._mechanical_change_only(C.head_sha(), cfg) is False)
    sh("git", "reset", "-q", "--hard", "HEAD~1")
    write("backdoor.py", "import os\n")
    commit("mechanical: refresh", "backdoor.py")
    hist = C._history_record_problems
    C._history_record_problems = lambda cfg: []
    try:
        run("record-init", "--pass-kind", "comment", "--unit-id", "U1", "--scope", "w.py",
            "--out", ".consolidation/u1.record")
    finally:
        C._history_record_problems = hist
    fill(".consolidation/u1.record", lambda u: {"disposition": C.STILL, "basis": "kept"})
    sh("git", "add", "-f", ".consolidation/u1.record")
    commit("consolidation: a nil unit on top of the mechanical commit", ".consolidation/u1.record")
    code, out = run("preflight")
    check("ADR 0015: a unit's replay never covers a mechanical commit below its baseline",
          code == C.FAIL and "exceeds the allowances" in out)

    # B2 (ADR 0015): the runner writes last-verified-at, under the committed config's word (S99)
    dirs.append(new_repo("cons_selftest_lva_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "last_verified_at": true}')
    write("d.md", "# Doc\n\nSee TASK-1 for the history.\n\nText.\n")
    write("e.md", "---\ntitle: E\n---\n# E\n\nStill true.\n")
    commit("base")
    lbase = C.head_sha()
    run("batch-init", "--pass-kind", "document", "--batch-id", "B-3", "--scope", "d.md", "e.md")
    m3 = next(Path(".consolidation").glob("B-3-*.batch"))
    fill(str(m3), lambda u: {"disposition": C.STRIP, "basis": "a ticket id", "edit": "See the history."}
         if "TASK" in u["preview"] else {"disposition": C.STILL, "basis": "true"})
    run("batch-plan", "--batch", "B-3")
    code, out = run("batch-next", "--batch", "B-3")
    check("B2: a whole document's review unit writes last-verified-at = the batch baseline (S98)",
          code == C.OK and read("d.md").startswith(f"---\nlast-verified-at: {lbase}\n---\n# Doc"))
    code, out = run("batch-next", "--batch", "B-3")
    check("B2: an unchanged whole document is verified too, its front matter kept",
          code == C.OK and read("e.md") == f"---\ntitle: E\nlast-verified-at: {lbase}\n---\n# E\n\nStill true.\n"
          and "complete" in out)
    write("f.md", "# F\n\nText.\n")
    commit("feat: f", "f.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "L1", "--scope", "f.md",
        "--out", ".consolidation/l1.record")
    rec = C.parse_record(".consolidation/l1.record")
    check("B2: record-init writes last_verified_at for a whole document",
          rec.header.get("last_verified_at") == f"{C.head_sha()} f.md")
    rec.header["last_verified_at"] = f"{lbase} f.md"
    C.write_record(rec, ".consolidation/l1-forged.record")
    code, out = run("record-check", "--record", ".consolidation/l1-forged.record")
    check("B2: a last_verified_at that is not the record's baseline fails record-check",
          code == C.FAIL and "last_verified_at" in out)
    check("B2: set_lva and _strip_lva are inverse on CRLF and BOM",
          C._strip_lva(C.set_lva("\ufeff# T\r\n\r\nx\r\n", "abc")) == "\ufeff# T\r\n\r\nx\r\n"
          and C.set_lva("# T\r\n", "abc") == "---\r\nlast-verified-at: abc\r\n---\r\n# T\r\n")

    # Phase 4: facts — script-measured evidence on each stub, re-measured by record-check
    dirs.append(new_repo("cons_selftest_facts_"))
    write(".consolidation.json", '{"fragment_patterns": ["\\\\b[A-Z][A-Z0-9]+-\\\\d+\\\\b", "\\\\b\\\\d{4}-\\\\d{2}-\\\\d{2}\\\\b"]}')
    write("f.py", "def compute(a):\n    return a\n\n# TASK-123 (2026-10-01): see `legacyAuth` and compute_total\nx = 1\n"
                  "# y = compute(x)\nz = 2\n# --------\nw = 3\n")
    write("docs/n.md", "legacyAuth is described here.\n")
    write("other.js", "// legacyAuth is named in a comment only\nrun();\n")
    write("code.js", "compute_total();\n")
    commit("base")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "FA", "--scope", "f.py",
                    "--out", ".consolidation/fa.record")
    facts = {u["lines"]: u.get("facts", "") for u in C.parse_record(".consolidation/fa.record").units}
    check("facts: fragment_patterns is a known config key", code == C.OK and "unknown key" not in out)
    check("facts: fragments and a name no code names (comments and docs do not count)",
          facts.get("4-4") == "fragment=TASK-123,2026-10-01; absent=legacyAuth")
    check("facts: commented-out code is code-like, a rule line is a separator",
          facts.get("6-6") == "code-like" and facts.get("8-8") == "separator")
    fill(".consolidation/fa.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    check("facts: an honest record passes record-check", run("record-check", "--record", ".consolidation/fa.record")[0] == C.OK)
    rec = C.parse_record(".consolidation/fa.record")
    rec.units[0]["facts"] = "absent=compute_total"
    C.write_record(rec, ".consolidation/fa-forged.record")
    code, out = run("record-check", "--record", ".consolidation/fa-forged.record")
    check("facts: a forged facts line fails identity", code == C.FAIL and "facts" in out)
    fill(".consolidation/fa.record", lambda u: {"disposition": C.OBS,
                                                "basis": "identifier `compute_total` does not occur in the baseline tree"}
         if u["lines"] == "4-4" else None)
    code, out = run("record-check", "--record", ".consolidation/fa.record")
    check("facts: an absence claim that code contradicts fails record-check", code == C.FAIL and "compute_total" in out)
    fill(".consolidation/fa.record", lambda u: {"basis": "identifier `legacyAuth` does not occur in the baseline tree"}
         if u["lines"] == "4-4" else None)
    check("facts: a true absence claim passes", run("record-check", "--record", ".consolidation/fa.record")[0] == C.OK)

    # review fixes: a committed record is not code; grep.column cannot shift a hit into a comment
    sh("git", "add", "-f", ".consolidation/fa.record")
    commit("chore: keep a record under .consolidation/", ".consolidation/fa.record")
    sh("git", "config", "grep.column", "true")
    run("record-init", "--pass-kind", "comment", "--unit-id", "FB", "--scope", "f.py",
        "--out", ".consolidation/fb.record")
    facts = {u["lines"]: u.get("facts", "") for u in C.parse_record(".consolidation/fb.record").units}
    check("review H: a record committed under .consolidation/ never counts as code (absent= kept)",
          facts.get("4-4") == "fragment=TASK-123,2026-10-01; absent=legacyAuth")
    sh("git", "config", "--unset", "grep.column")
    check("review N1: a deeply nested expression is not code-like and does not crash",
          C.code_like("-" * 5000 + "1", "x.py") is False and C.code_like("not " * 5000 + "x", "x.py") is False)
    check("review G: a path on another drive is printed absolute, never a crash",
          os.name != "nt" or C.root_rel("Q:/nowhere/u.record", Path.cwd().resolve()) == "Q:/nowhere/u.record")

    # review D, E: each record version is judged by its own rules; only the current one is written
    dirs.append(new_repo("cons_selftest_versions_"))
    write("tw.py", "def f():\n    # end of block\n    x = 1\n# End of block\ny = 2\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "V2", "--scope", "tw.py",
        "--out", ".consolidation/v2.record")
    rec = fill(".consolidation/v2.record", lambda u: {"disposition": C.STILL, "basis": "marks where the block ends"})
    rec.header["record_version"] = "2"
    for u, s in zip(rec.units, C.stubs_for(C.head_sha(), rec.header, C.load_config())):
        u.pop("facts", None)
        u.update({k: s[k] for k in ("lines", "span", "fingerprint", "preview")})
    C.write_record(rec, ".consolidation/v2.record")
    check("review E: v2 counted twins on the raw body (both twins share one fingerprint)",
          len({u["fingerprint"] for u in rec.units}) == 1)
    sh("git", "add", "-f", ".consolidation/v2.record")
    commit("consolidation: a v2 unit committed before the upgrade", ".consolidation/v2.record")
    code, out = run("preflight")
    check("review E: a committed v2 record with case-only twins still passes the history walk", code == C.OK)
    code, out = run("record-check", "--record", ".consolidation/v2.record")
    check("review D: a v2 record in the working tree is refused (only the current version is gated)",
          code == C.FAIL and "must be version 3" in out)
    check("review D: a v2 record is never applied",
          run("apply", "--record", ".consolidation/v2.record")[0] == C.FAIL)

    # review (optional): a config saved with a BOM (Notepad, PowerShell 5.1) is read, never
    # replaced by the defaults
    dirs.append(new_repo("cons_selftest_bom_"))
    write(".gitignore", "in.md\n")
    Path(".consolidation.json").write_bytes(b"\xef\xbb\xbf" + b'{"intake_path": "in.md"}')
    commit("base")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        cfg, cfg_at = C.load_config(), C.load_config(C.head_sha())
    check("review (optional): a config with a BOM is parsed, in the worktree and at a commit",
          cfg.get("intake_path") == "in.md" and cfg["_tracked"] and cfg_at.get("intake_path") == "in.md"
          and "could not parse" not in buf.getvalue())

    # review N1 (optional): a forged facts: line on a stub with no facts fails identity, never a crash
    dirs.append(new_repo("cons_selftest_nofacts_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("k.py", "# a reason the code cannot say\nx = 1\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "NF", "--scope", "k.py",
        "--out", ".consolidation/nf.record")
    rec = fill(".consolidation/nf.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    check("review N1 premise: the stub has no facts", not rec.units[0].get("facts"))
    rec.units[0]["facts"] = "absent=x"
    C.write_record(rec, ".consolidation/nf.record")
    code, out = run("record-check", "--record", ".consolidation/nf.record")
    code2, out2 = run("apply", "--record", ".consolidation/nf.record")
    check("review N1: a forged facts line where the enumeration has none fails identity in record-check and apply",
          code == C.FAIL and "script-owned field 'facts'" in out
          and code2 == C.FAIL and "script-owned field 'facts'" in out2)

    # review O1 (optional): an open fence at the end refuses the item even when the section exists
    dirs.append(new_repo("cons_selftest_fence_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("fs.md", "# T\n\nExternal rule.\n\n## To be confirmed\n\n- old\n\n```text\nopen fence")
    commit("base")
    check("review O1 premise: the section exists and the document ends inside a fence",
          C._tbc_heading_index(read("fs.md").split("\n")) is not None and C.open_fence_at_end(read("fs.md")))
    run("record-init", "--pass-kind", "document", "--unit-id", "FS", "--scope", "fs.md",
        "--out", ".consolidation/fs.record")
    fill(".consolidation/fs.record", lambda u: (
        {"disposition": C.NV, "basis": "external", "tbc": "Confirm the rule."}
        if "External" in u.get("preview", "") else {"disposition": C.STILL, "basis": "kept"}))
    code, out = run("record-check", "--record", ".consolidation/fs.record")
    check("review O1: an item is never appended inside an open fence under an existing section",
          code == C.FAIL and "unclosed" in out)

    # review O2 (optional): S66 suppresses an item only in the file whose paragraph raised it
    dirs.append(new_repo("cons_selftest_s66_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("a.md", "# A\n\nRetention follows the contract.\n")
    write("b.md", "# B\n\nOther text.\n\n## To be confirmed\n\n- Confirm the retention period.\n")
    commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "SA", "--scope", "a.md",
        "--out", ".consolidation/sa.record")
    fill(".consolidation/sa.record", lambda u: (
        {"disposition": C.NV, "basis": "the contract is external", "tbc": "Confirm the retention period."}
        if "Retention" in u.get("preview", "") else {"disposition": C.STILL, "basis": "title"}))
    run("escalate", "--from-record", ".consolidation/sa.record")
    check("review O2 premise: a.md's entry carries the item key",
          f"tbc={C.tbc_key('Confirm the retention period.')}" in read("intake.md"))
    run("record-init", "--pass-kind", "document", "--unit-id", "SB", "--scope", "b.md",
        "--out", ".consolidation/sb.record")
    fill(".consolidation/sb.record", lambda u: {"disposition": C.NV, "basis": "external"}
         if u.get("in_tbc") == "yes" else {"disposition": C.STILL, "basis": "kept"})
    code, out = run("escalate", "--from-record", ".consolidation/sb.record")
    check("review O2: an identical item in another file is escalated, not suppressed by a.md's entry",
          code == C.OK and "S66" not in out and "`b.md:7`" in read("intake.md"))

    # mutation survivors (ADR 0015 guards no check noticed): one batch, one review unit done
    dirs.append(new_repo("cons_selftest_mutab_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n# restates b\nb()\n")
    write("c.py", "# restates c\nc()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-9", "--scope", "a.py", "c.py")
    m9 = next(Path(".consolidation").glob("B-9-*.batch"))
    fill(str(m9), lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    run("batch-plan", "--batch", "B-9")
    check("mutation A premise: review unit B-9.1 is done", run("batch-next", "--batch", "B-9")[0] == C.OK)
    raw9 = m9.read_bytes()
    rec = C.parse_record(str(m9))
    rec.header["floor_observed"] = C.head_sha()
    C.write_record(rec, str(m9))
    code, out = run("batch-next", "--batch", "B-9")
    check("mutation A3: a master header changed after a review unit ran stops the batch",
          code == C.FAIL and "header changed after a review unit ran" in out)
    m9.write_bytes(raw9)
    d1 = C.record_from_commit("HEAD")
    check("mutation A5: a part record that drops a master unit of its scope fails batch-carry-check",
          any("missing from this review unit" in x for x in C.batch_carry_problems(C.Record(dict(d1.header), []), "HEAD"))
          and not C.batch_carry_problems(d1, "HEAD"))
    run("batch-next", "--batch", "B-9")
    run("batch-next", "--batch", "B-9")
    olds = C.git("rev-list", "--reverse", f"{d1.header['baseline_sha']}..HEAD").split()
    sh("git", "reset", "-q", "--hard", olds[0])
    write("backdoor.py", "import os\n")
    sh("git", "add", "backdoor.py")
    sh("git", "commit", "-q", "--amend", "--no-edit")
    prev, new = olds[0], C.head_sha()
    for old in olds[1:]:
        sh("git", "cherry-pick", "-n", old)
        write(".consolidation/rw.msg", C.git("log", "-1", "--format=%B", old).replace(prev, new))
        sh("git", "commit", "-q", "-F", ".consolidation/rw.msg")
        prev, new = old, C.head_sha()
    code, out = run("batch-next", "--batch", "B-9")
    check("mutation A8: an earlier unit amended under a rebuilt chain fails the batch-end replay",
          len(olds) == 3 and code == C.FAIL and "review unit B-9.1" in out and "fails its gate at its own commit" in out)

    # review R1: a hand-made unit commit carrying a changed master copy never moves the reference
    dirs.append(new_repo("cons_selftest_r1_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n# restates b\nb()\n")
    write("c.py", "# restates c\nc()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-8", "--scope", "a.py", "c.py")
    m8 = next(Path(".consolidation").glob("B-8-*.batch"))
    fill(str(m8), lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    run("batch-plan", "--batch", "B-8")
    run("batch-next", "--batch", "B-8")
    check("review R1 premise: B-8.1 and B-8.2 are done",
          run("batch-next", "--batch", "B-8")[0] == C.OK and C.record_from_commit("HEAD").header["unit_id"] == "B-8.2")
    two = C.head_sha()
    rec = C.parse_record(str(m8))
    for u in rec.units:
        if u["lines"] == "3-3" and u["file"] == "a.py":
            u["basis"] = "restates b() below"
    C.write_record(rec, str(m8))
    sh("git", "add", "-f", str(m8))
    sh("git", "commit", "-q", "--amend", "--no-edit")
    code, out = run("batch-next", "--batch", "B-8")
    check("review R1: a judgement B-8.1 applied, changed in a later unit's master copy, stops the batch",
          code == C.FAIL and "changed after a done review unit applied" in out)
    sh("git", "reset", "-q", "--hard", two)
    rec = C.parse_record(str(m8))
    rec.header["floor_observed"] = two
    C.write_record(rec, str(m8))
    sh("git", "add", "-f", str(m8))
    sh("git", "commit", "-q", "--amend", "--no-edit")
    code, out = run("batch-next", "--batch", "B-8")
    check("review R1: a header changed in a later unit's master copy stops the batch",
          code == C.FAIL and "header changed after a review unit ran" in out)

    # fresh review O1: a resumed batch re-checks its last done unit with the full unit gate, not
    # only carry and replay — a unit whose applied ruling left the intake replays clean, but its
    # record-check fails
    dirs.append(new_repo("cons_selftest_o1_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("small.js", "// legacy auth path\nauth();\n")
    write("b.py", "# restates b\nb()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-7", "--scope", "small.js", "b.py")
    m7 = next(Path(".consolidation").glob("B-7-*.batch"))
    fill(str(m7), lambda u: {"disposition": C.DEFECT, "basis": "auth() is the only path; no legacy path exists"}
         if "legacy" in u["preview"] else {"disposition": C.REGEN, "basis": "restates the call below"})
    run("escalate", "--from-record", "B-7")
    fp7 = [u for u in C.parse_record(str(m7)).units if "legacy" in u["preview"]][0]["fingerprint"]
    run("escalate", "--rule", "--file", "small.js", "--line", "1", "--fingerprint", fp7,
        "--ruling-text", "false: there is no legacy path; delete the comment")
    fill(str(m7), lambda u: {"disposition": C.RULED, "basis": "owner ruling", "ruling": fp7}
         if u["fingerprint"] == fp7 else None)
    run("batch-plan", "--batch", "B-7")
    run("batch-next", "--batch", "B-7")
    check("fresh review O1 premise: B-7.1 applied the ruling and closed it",
          C.record_from_commit("HEAD").header["scope"] == "small.js" and "state=applied" in read("intake.md"))
    one = C.head_sha()
    write("intake.md", "")
    code, out = run("batch-next", "--batch", "B-7")
    check("fresh review O1: a done unit that fails its full gate stops the next run before any unit is stacked on it",
          code == C.FAIL and "review unit B-7.1" in out and "does not pass its gate" in out and C.head_sha() == one)

    # fresh review nit: a replay nested in an outer judged commit restores that commit, not HEAD
    with C._at_tip(one):
        C._replay_at(C.record_from_commit(one), C.load_config(), one + "^")
        inner = C.TIP
    check("fresh review nit: a nested replay restores the judged commit it found (TIP)",
          inner == one and C.TIP == "HEAD")

    # mutation A11: the history walk replays every record-carrying commit — a unit amended to
    # carry code keeps a record that passes record-check, so only the replay sees it
    dirs.append(new_repo("cons_selftest_walkreplay_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("h.py", "# restates a\na()\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "HW", "--scope", "h.py",
        "--out", ".consolidation/hw.record")
    fill(".consolidation/hw.record", lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    run("apply", "--record", ".consolidation/hw.record")
    sh("git", "add", "h.py")
    sh("git", "commit", "-q", "-F", ".consolidation/hw.commit-msg")
    check("mutation A11 premise: the unit passes the history walk", run("preflight")[0] == C.OK)
    write("h.py", "a()\nimport os\n")
    sh("git", "add", "h.py")
    sh("git", "commit", "-q", "--amend", "--no-edit")
    check("mutation A11: a unit amended to carry code fails the history walk (its replay)",
          run("preflight")[0] == C.FAIL)

    # mutations A12, A13, A15: one batch, review unit B-6.1 (a.py:2-4) done
    dirs.append(new_repo("cons_selftest_mutab2_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n# restates b\nb()\n")
    write("c.py", "# restates c\nc()\n")
    base6 = commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-6", "--scope", "a.py", "c.py")
    p6 = next(Path(".consolidation").glob("B-6-*.batch"))
    fill(str(p6), lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    run("batch-plan", "--batch", "B-6")
    run("batch-next", "--batch", "B-6")
    m6, mrel6 = C.parse_record(str(p6)), C._master_rel(p6)
    done6 = C.batch_chain(m6, mrel6)[0]
    check("mutation A premise: B-6.1 covers a.py:2-4 and passes the history walk",
          [d["record"].header["scope"] for d in done6] == ["a.py:2-4"] and run("preflight")[0] == C.OK)
    try:
        C.batch_remaining(m6, [{"record": C.Record({"scope": "a.py:1-1"}, [])}])
        top = False
    except C.Die as e:
        top = "not the bottom of its batch range" in str(e)
    check("mutation A13: done ranges that are not a bottom suffix of a cut file stop the batch", top)
    probs = C._master_problems(m6, mrel6, [dict(done6[0], commit=base6)], C.config_for_record(m6, C.load_config()))
    check("mutation A15: a done unit whose commit lacks the master record stops the batch",
          any("is not committed with review unit B-6.1" in p for p in probs))
    write(".consolidation/b6.msg", C.git("log", "-1", "--format=%B").replace("restates the call below",
                                                                              "restates a() and b() below"))
    sh("git", "commit", "-q", "--amend", "-F", ".consolidation/b6.msg")
    check("mutation A12: a part record whose judgement differs from its master fails the history walk (carry)",
          run("preflight")[0] == C.FAIL)

    # mutation B1: a last_verified_at header needs the committed config's word (S99)
    dirs.append(new_repo("cons_selftest_lvacfg_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("d.md", "# T\n\nSome text.\n")
    base_b1 = commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "LC", "--scope", "d.md",
        "--out", ".consolidation/lc.record")
    rec = fill(".consolidation/lc.record", lambda u: {"disposition": C.STILL, "basis": "kept"})
    check("mutation B1 premise: with the config's default, record-init writes no last_verified_at",
          not rec.header.get("last_verified_at") and run("record-check", "--record", ".consolidation/lc.record")[0] == C.OK)
    rec.header["last_verified_at"] = f"{base_b1} d.md"
    C.write_record(rec, ".consolidation/lc.record")
    code, out = run("record-check", "--record", ".consolidation/lc.record")
    check("mutation B1: a last_verified_at header without the committed config's `last_verified_at: true` fails",
          code == C.FAIL and "needs `last_verified_at: true`" in out)

    # mutation B4: in a batch, last_verified_at names the master record's baseline (S98)
    dirs.append(new_repo("cons_selftest_lvacarry_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write("old.txt", "x\n")
    first = commit("first")
    write(".consolidation.json", '{"intake_path": "intake.md", "last_verified_at": true}')
    write("d.md", "# T\n\nSome text.\n")
    commit("base")
    run("batch-init", "--pass-kind", "document", "--batch-id", "B-5", "--scope", "d.md")
    fill(str(next(Path(".consolidation").glob("B-5-*.batch"))), lambda u: {"disposition": C.STILL, "basis": "kept"})
    run("batch-plan", "--batch", "B-5")
    run("batch-next", "--batch", "B-5")
    d5 = C.record_from_commit("HEAD")
    check("mutation B4 premise: the review unit names the master's baseline and passes the carry check",
          C.lva_spec(d5)[1] == ["d.md"] and not C.batch_carry_problems(d5, "HEAD"))
    forged = C.Record(dict(d5.header, last_verified_at=f"{first} d.md"), d5.units)
    check("mutation B4: a part record whose last_verified_at names another ancestor fails batch-carry-check",
          any("must name the master record's baseline" in p for p in C.batch_carry_problems(forged, "HEAD")))

    # mutation B6: a v3 replay is exact — a marker the record does not name fails it
    check("mutation B6 premise: the unit passes its gate",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    base5 = C.lva_spec(d5)[0]
    write("d.md", read("d.md").replace(base5, first))
    sh("git", "add", "d.md")
    sh("git", "commit", "-q", "--amend", "--no-edit")
    code, out = run("gate", "--unit", "--record-from-commit", "HEAD")
    check("mutation B6: a committed marker naming a sha the record does not name fails the v3 replay",
          code == C.FAIL and re.search(r"FAIL\s+replay-check", out) is not None)

    # mutation B5: an uncommitted config never turns last_verified_at on (S99)
    write(".consolidation.json", '{"last_verified_at": true, "intake_path": "intake.md"}')
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        cfg5 = C.load_config()
    check("mutation B5: a locally modified config's last_verified_at: true falls back to false",
          cfg5["last_verified_at"] is False and "owner's word" in buf.getvalue())


def _v22_r1_tests(dirs):
    """v2.2 A3: the runner I/O layer. Creates its own repos with new_repo() and appends them to dirs."""
    # two repositories, the same path, one commit sha built identically in both, then diverging
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
    shas, heads = [], []
    for tag in ("one", "two"):
        dirs.append(new_repo(f"cons_v22r1_{tag}_"))
        write("f.txt", "same\n")
        sh("git", "add", "-A")
        subprocess.run(["git", "commit", "-qm", "base"], check=True, capture_output=True, env=env)
        shas.append(C.head_sha())
        write("f.txt", f"{tag}\n")
        write("only_" + tag + ".txt", "x\n")
        heads.append(commit(tag))
        check(f"A3: a full-sha read sees this repo's content ({tag})", C.git_show(heads[-1], "f.txt") == f"{tag}\n")
    check("A3: the two repos share a commit sha", shas[0] == shas[1])
    check("A3: a shared sha reads the same blob in each repo", C.git_show(shas[1], "f.txt") == "same\n")
    os.chdir(dirs[-2])
    check("A3: a memoized read is never served across repositories (content)",
          C.git_show(heads[0], "f.txt") == "one\n" and C.git_show(heads[1], "f.txt") is None)
    check("A3: a memoized read is never served across repositories (a path only the other repo has)",
          C.git_show(heads[0], "only_two.txt") is None and C.git_show(heads[0], "only_one.txt") == "x\n")
    os.chdir(dirs[-1])
    check("A3: ... and back in the other repository",
          C.git_show(heads[1], "only_two.txt") == "x\n" and C.git_show(heads[1], "only_one.txt") is None)
    # _memo shares its key shape with git_show: no answer crosses repositories either
    C.first_parent(heads[1])
    os.chdir(dirs[-2])
    check("A3: a memoized parent is never served across repositories",
          C.first_parent(heads[1]) is None)
    os.chdir(dirs[-1])
    # HEAD is never memoized: a commit mid-run is seen at once
    before = C.git_show("HEAD", "f.txt")
    write("f.txt", "three\n")
    third = commit("three")
    check("A3: after a new commit, HEAD reads see the new content",
          before == "two\n" and C.git_show("HEAD", "f.txt") == "three\n" and C.git_show(third, "f.txt") == "three\n")
    # a tree path and a non-ASCII path through the batch reader
    write("d/a.txt", "a\n")
    write("d/è.txt", "accent\n")
    t = commit("tree")
    listing = C._git_show_proc(t, "d")
    check("A3: a tree path falls back to git show (the same listing as before)",
          listing is not None and listing.startswith("tree ") and C.git_show(t, "d") == listing)
    check("A3: a non-ASCII path reads through the batch reader", C.git_show(t, "d/è.txt") == "accent\n")
    check("A3: an absent path is None", C.git_show(t, "nope.txt") is None and C.git_show(t, "d/nope") is None)
    r = subprocess.run(["git", "-c", "core.quotepath=off", "show", f"{t}:d/a.txt"], capture_output=True)
    check("A3: a blob through the batch reader equals git show byte for byte",
          C.encode(C.git_show(t, "d/a.txt")) == r.stdout)
    # CONSOLIDATION_PROFILE prints the profile line at exit
    p = subprocess.run([sys.executable, C.__file__, "batch-status", "--batch", "nope"], capture_output=True,
                       env=dict(os.environ, CONSOLIDATION_PROFILE="1"))
    check("A3: CONSOLIDATION_PROFILE=1 prints the profile line",
          re.search(r"^profile: batch-status [\d.]+s, \d+ git calls\r?$", C._decode_output(p.stderr), re.M) is not None)
    p = subprocess.run([sys.executable, C.__file__, "batch-status", "--batch", "nope"], capture_output=True,
                       env={k: v for k, v in os.environ.items() if k != "CONSOLIDATION_PROFILE"})
    check("A3: without CONSOLIDATION_PROFILE no profile line", b"profile:" not in p.stderr)
    # one `git log` listing equals the per-commit reads it replaces, a re-encoded message included
    Path(".consolidation").mkdir(exist_ok=True)
    Path(".consolidation/latin.msg").write_bytes("consolidation: caf\xe9\n\nbody\n\n--- x\n".encode("latin-1"))
    sh("git", "-c", "i18n.commitEncoding=ISO-8859-1", "commit", "-q", "--allow-empty", "-F", ".consolidation/latin.msg")
    shas = C.git("rev-list", "HEAD").split()
    direct = [(C.decode(C.git("log", "-1", "--format=%B", s, binary=True)), C.git("log", "-1", "--format=%s", s).strip(),
               C.git("rev-parse", s + "^").strip() if i < len(shas) - 1 else None) for i, s in enumerate(shas)]
    listed = C.commit_log("HEAD")
    check("A3: commit_log lists rev-list's commits in its order",  [x[0] for x in listed] == shas)
    check("A3: commit_log's subjects, messages and parents equal the per-commit reads",
          [(m, s.strip(), C.first_parent(h)) for h, s, m in listed] == direct and "café" in direct[0][0])
    check("A3: a memoized message equals the per-commit read", C.commit_message_of(shas[0]) == direct[0][0])
    # a remembered identifier answer equals a fresh grep, whatever set it was asked with
    write("code.py", "def used_name():\n    pass\n# gone_name only in a comment\n")
    c = commit("code")
    cfg = C.load_config()
    both = C.code_absent(c, ["used_name", "gone_name"], cfg)
    one = C.code_absent(c, ["gone_name", "never_name"], cfg)
    check("A3: code_absent answers per identifier, remembered or not",
          both == {"gone_name"} and one == {"gone_name", "never_name"}
          and C._code_absent(c, ["used_name", "gone_name", "never_name"], cfg) == {"gone_name", "never_name"})

# ----- end of v22 r1


def _v22_r2_tests(dirs):
    """v2.2 A1, A2: record-fill, ADR text in the record. Creates its own repos with new_repo() and appends them to dirs."""
    def jtext(blocks):
        """[(id, fingerprint, {field: value})] -> the text of a judgement file."""
        out = []
        for uid, fp, f in blocks:
            out.append(f"@@ {uid} {fp}")
            for k, v in f.items():
                if k in C.MULTILINE:
                    out += [f"{k}:"] + [("| " + l) if l else "|" for l in v.split("\n")]
                else:
                    out.append(f"{k}: {v}")
            out.append("")
        return "\n".join(out)

    def judge(u):
        if "restates" in u["preview"]:
            return {"disposition": C.REGEN, "basis": "restates the call below"}
        return {"disposition": C.STILL, "basis": "carries a reason the code cannot state"}

    def fill_j(j, units):
        heads = [l.split()[1:] for l in read(str(j)).splitlines() if l.startswith("@@")]
        write(str(j), jtext([(uid, fp, judge(units[uid])) for uid, fp in heads]))

    # A1: record-shard writes judgement files, record-fill writes them into the record
    dirs.append(new_repo("cons_v22_r2_fill_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("a.py", "# restates a\na()\n# a reason the code cannot say\nx = 1\n")
    write("b.js", "// restates go\ngo();\n// the vendor caps batches at 50\nsend();\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "F1", "--scope", "a.py", "b.js")
    rp = str(next(Path(".consolidation").glob("F1-*.record")))
    units = {u["id"]: u for u in C.parse_record(rp).units}
    code, out = run("record-shard", "--record", rp, "--shards", "2")
    js = sorted(Path(".consolidation").glob(Path(rp).name + ".shard-*.j"))
    briefs = [C.parse_record(str(j)[:-2]) for j in js]
    check("v2.2 A1: record-shard writes one judgement file per shard, `@@ <id> <fingerprint>` per unit and nothing else",
          code == C.OK and len(js) == 2 and all(
              read(str(j)) == "".join(f"@@ {u['id']} {u['fingerprint']}\n" for u in b.units) for j, b in zip(js, briefs)))
    for j in js:
        fill_j(j, units)
    before = read(rp)
    u1 = units["1"]
    bad = Path(".consolidation/bad.j")

    def refused(text, why, *extra):
        write(str(bad), text)
        code, out = run("record-fill", "--record", rp, "--from", str(bad), *extra)
        return code == C.FAIL and why in out and read(rp) == before

    check("v2.2 A1: record-fill refuses an unknown id and writes nothing",
          refused(jtext([("99", u1["fingerprint"], judge(u1))]), "not in the record"))
    check("v2.2 A1: record-fill refuses a fingerprint that differs from the stub's",
          refused(jtext([("1", "0badf00d", judge(u1))]), "fingerprint 0badf00d differs"))
    check("v2.2 A1: record-fill refuses a script-owned field in a judgement file",
          refused(f"@@ 1 {u1['fingerprint']}\nlines: 1-1\ndisposition: still true\nbasis: x\n", "script-owned"))
    check("v2.2 A1: record-fill refuses a unit given in two judgement files",
          refused(jtext([("1", u1["fingerprint"], judge(u1))]), "appears in", *map(str, js)))
    write("a.py", read("a.py") + "# written by a worker\n")
    code, out = run("record-fill", "--record", rp, "--from", *map(str, js))
    check("v2.2 A1: record-fill refuses a working-tree change outside .consolidation/",
          code == C.FAIL and "a.py" in out and read(rp) == before)
    sh("git", "checkout", "--", "a.py")
    code, out = run("record-fill", "--record", rp, "--from", str(js[0]))
    check("v2.2 A1: record-fill fills the units it is given and counts the empty ones",
          code == C.OK and f"filled {len(briefs[0].units)} unit(s)" in out
          and f"{len(briefs[1].units)} unit(s) still empty" in out)
    code, out = run("record-fill", "--record", rp, "--from", *map(str, js))
    check("v2.2 A1: shard -> fill from every judgement file -> gate --pre passes",
          code == C.OK and "0 unit(s) still empty" in out and run("gate", "--pre", "--record", rp)[0] == C.OK)
    old = C.parse_record(rp)
    x = next(u for u in old.units if "vendor" in u["preview"])
    write(str(bad), jtext([(x["id"], x["fingerprint"], {"disposition": C.NV, "basis": "the vendor's cap is external"})]))
    code, out = run("record-fill", "--record", rp, "--from", str(bad))
    new = C.parse_record(rp)
    nx = next(u for u in new.units if u["id"] == x["id"])
    check("v2.2 A1: a correction replaces one unit's judgement and leaves every other unit identical",
          code == C.OK and [u for u in new.units if u["id"] != x["id"]] == [u for u in old.units if u["id"] != x["id"]]
          and nx["disposition"] == C.NV and nx["basis"] == "the vendor's cap is external")
    y = next(u for u in new.units if "restates go" in u["preview"])
    write(str(bad), jtext([(y["id"], y["fingerprint"], {"disposition": C.NV, "basis": "the vendor's cap is external",
                                                        "escalate": "unverifiable-statement"})]))
    code, out = run("record-fill", "--record", rp, "--from", str(bad))
    mid = next(u for u in C.parse_record(rp).units if u["id"] == y["id"])
    write(str(bad), jtext([(y["id"], y["fingerprint"], {"disposition": C.STILL, "basis": "carries a reason"})]))
    code, out = run("record-fill", "--record", rp, "--from", str(bad))
    fin = next(u for u in C.parse_record(rp).units if u["id"] == y["id"])
    check("v2.2 A1: a correction drops the fields its judgement file does not carry",
          mid.get("escalate") == "unverifiable-statement" and code == C.OK
          and "escalate" not in fin and fin["disposition"] == C.STILL and fin["basis"] == "carries a reason")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "FB", "--scope", "a.py", "b.js")
    mp = next(Path(".consolidation").glob("FB-*.batch"))
    code, out = run("record-shard", "--record", "FB", "--shards", "1")
    j = Path(str(mp) + ".shard-1.j")
    check("v2.2 A1: record-shard takes a batch id", code == C.OK and j.is_file())
    fill_j(j, {u["id"]: u for u in C.parse_record(str(mp)).units})
    code, out = run("record-fill", "--record", "FB", "--from", str(j))
    check("v2.2 A1: record-fill takes a batch id; the filled master passes gate --pre --batch",
          code == C.OK and run("gate", "--pre", "--batch", "FB")[0] == C.OK)

    # A2: the ADR text in the record — the runner numbers, renders and writes the ADR
    dirs.append(new_repo("cons_v22_r2_adr_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("docs/adr/0003-x.md", "# 0003 — x\n\nStatus: accepted\n")
    write("docs/adr/README.md", "the index\n")
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n# restates poll\npoll()\n"
                  "# we cap retries at 5: the broker evicts after 6\nretry()\n")
    base = commit("base")
    body1 = "## Context\n\nThe vendor drops webhook retries.\n\n## Decision\n\nPoll.\n\n## Consequences\n\nOne poll a minute."
    body2 = "## Context\n\nThe broker evicts a consumer after 6 retries.\n\n## Decision\n\nCap at 5."

    def adr_judge(u):
        if "polling" in u["preview"]:
            return {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
                    "adr_title": "Polling over webhooks", "adr_text": body1}
        if "cap retries" in u["preview"]:
            return {"disposition": C.ADR, "basis": "retries capped at 5: the broker evicts after 6",
                    "adr_title": "Retries capped at 5 (broker evicts after 6)", "adr_text": body2}
        return {"disposition": C.REGEN, "basis": "restates poll()"}
    run("record-init", "--pass-kind", "comment", "--unit-id", "AT", "--scope", "p.py")
    rp = str(next(Path(".consolidation").glob("AT-*.record")))
    fill(rp, adr_judge)
    fill(rp, lambda u: {"adr": "docs/adr/0004-polling.md"} if "polling" in u["preview"] else None)
    code, out = run("record-check", "--record", rp)
    check("v2.2 A2: `adr:` together with `adr_text` is refused", code == C.FAIL and "exclude each other" in out)
    fill(rp, lambda u: {"adr": None, "adr_text": None} if "polling" in u["preview"] else None)
    code, out = run("record-check", "--record", rp)
    check("v2.2 A2: `adr_title` without `adr_text` is refused", code == C.FAIL and "requires `adr_text:`" in out)
    fill(rp, adr_judge)
    check("v2.2 A2: an adr_text record passes gate --pre", run("gate", "--pre", "--record", rp)[0] == C.OK)
    code, out = run("apply", "--record", rp)
    day = C._commit_date(base).isoformat()
    f4, f5 = "docs/adr/0004-polling-over-webhooks.md", "docs/adr/0005-retries-capped-at-5-broker-evicts-after-6.md"
    check("v2.2 A2: apply writes the ADRs numbered after the baseline's highest, in unit order, rendered exactly",
          code == C.OK and Path(f4).is_file() and Path(f5).is_file()
          and read(f4) == f"# 0004 — Polling over webhooks\n\nStatus: accepted\nDate: {day}\n\n{body1}\n"
          and read(f5) == f"# 0005 — Retries capped at 5 (broker evicts after 6)\n\nStatus: accepted\n"
                          f"Date: {day}\n\n{body2}\n" and f4 in out and "restore -- p.py\n" in out)
    sh("git", "add", "p.py", f4, f5)
    sh("git", "commit", "-q", "-F", re.sub(r"\.record$", ".commit-msg", rp))
    check("v2.2 A2: the unit with the rendered ADRs passes gate --unit",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    run("review-pack", "--record-from-commit", "HEAD", "--out", ".consolidation/at.review.md")
    check("v2.2 A2: the review pack lists the rendered ADR path", f4 in read(".consolidation/at.review.md")
          and f5 in read(".consolidation/at.review.md"))
    good = C.head_sha()
    write(f4, read(f4) + "an afterthought\n")
    sh("git", "commit", "-q", "-a", "--amend", "--no-edit")
    code, out = run("replay-check", "--record-from-commit", "HEAD")
    check("v2.2 A2: replay-check fails when the rendered ADR's content is altered",
          code == C.FAIL and "differs from the text the record renders" in out)
    sh("git", "reset", "-q", "--hard", good)
    sh("git", "rm", "-q", f5)
    sh("git", "commit", "-q", "--amend", "--no-edit")
    code, out = run("replay-check", "--record-from-commit", "HEAD")
    check("v2.2 A2: replay-check fails when the rendered ADR is missing", code == C.FAIL and f5 in out)
    sh("git", "reset", "-q", "--hard", good)

    # A2 in a batch: the master numbers the ADRs; batch-next never stops for an adr_text unit
    write("q.py", "# we chose LIFO eviction: the cache serves the newest keys\nevict()\n# restates go\ngo()\n")
    commit("feat: q")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "AB", "--scope", "q.py")
    mp = next(Path(".consolidation").glob("AB-*.batch"))
    fill(str(mp), lambda u: {"disposition": C.ADR, "basis": "LIFO eviction: the cache serves the newest keys",
                             "adr_title": "LIFO eviction", "adr_text": "## Decision\n\nEvict LIFO."}
         if "LIFO" in u["preview"] else {"disposition": C.REGEN, "basis": "restates go()"})
    code, out = run("batch-next", "--batch", "AB")
    f6 = "docs/adr/0006-lifo-eviction.md"
    check("v2.2 A2: batch-next runs an adr_text unit without stopping and commits the rendered ADR",
          code == C.OK and "GATE PASSED" in out and (C.git_show("HEAD", f6) or "").startswith("# 0006 — LIFO"))

    # an untracked config is the owner's input, bound by config_sha, as preflight treats it (D6's rule for record-fill)
    dirs.append(new_repo("cons_v22_r2_ucfg_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write("a.py", "# restates a\na()\n")
    commit("base")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    run("record-init", "--pass-kind", "comment", "--unit-id", "U1", "--scope", "a.py")
    rp = str(next(Path(".consolidation").glob("U1-*.record")))
    units = {u["id"]: u for u in C.parse_record(rp).units}
    run("record-shard", "--record", rp, "--shards", "1")
    j = next(Path(".consolidation").glob(Path(rp).name + ".shard-*.j"))
    fill_j(j, units)
    code, out = run("record-fill", "--record", rp, "--from", str(j))
    check("v2.2 A1: record-fill accepts an untracked .consolidation.json, as preflight does",
          code == C.OK and "filled 1 unit(s)" in out and "0 unit(s) still empty" in out)

    # the other half of the same guard: a tracked config with local changes is a real tree change
    dirs.append(new_repo("cons_v22_r2_tcfg_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("a.py", "# restates a\na()\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "T2", "--scope", "a.py")
    rp = str(next(Path(".consolidation").glob("T2-*.record")))
    run("record-shard", "--record", rp, "--shards", "1")
    j = next(Path(".consolidation").glob(Path(rp).name + ".shard-*.j"))
    fill_j(j, {u["id"]: u for u in C.parse_record(rp).units})
    before = read(rp)
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVED_LINE_CAP": 20}')
    code, out = run("record-fill", "--record", rp, "--from", str(j))
    check("v2.2 A1: record-fill refuses a tracked .consolidation.json modified in the tree",
          code == C.FAIL and ".consolidation.json" in out and "the working tree changed" in out
          and read(rp) == before)

    # a master correction that adds an adr_text unit before an applied one would renumber the
    # ADR a done review unit already wrote: the next batch-next stops (r2's _master_problems guard)
    dirs.append(new_repo("cons_v22_r2_renum_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("f.py", "# restates the call below\npoll()\n\n# we chose polling over webhooks: the vendor drops retries\npoll()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "RN", "--scope", "f.py")
    mp = str(next(Path(".consolidation").glob("RN-*.batch")))
    low = next(u for u in C.parse_record(mp).units if "restates" in u["preview"])
    fill(mp, lambda u: {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
                        "adr_title": "Polling over webhooks", "adr_text": "## Decision\n\nPoll."}
         if "polling over webhooks" in u["preview"] else judge(u))
    code, out = run("batch-next", "--batch", "RN")
    check("v2.2 A2: the adr_text unit on the higher lines runs first (cap 1, bottom-up) and writes 0001",
          code == C.OK and "GATE PASSED" in out
          and (C.git_show("HEAD", "docs/adr/0001-polling-over-webhooks.md") or "").startswith("# 0001 — "))
    head = C.head_sha()
    write(".consolidation/cor.j", jtext([(low["id"], low["fingerprint"],
                                          {"disposition": C.ADR, "basis": "a decision the record now owns",
                                           "adr_title": "Restated decision", "adr_text": "## Decision\n\nKeep."})]))
    code, out = run("record-fill", "--record", mp, "--from", ".consolidation/cor.j")
    check("v2.2 A2: record-fill applies a master correction on a unit no review unit applied",
          code == C.OK and "filled 1 unit(s)" in out)
    code, out = run("batch-next", "--batch", "RN")
    check("v2.2 A2: a correction that would renumber an applied ADR stops the batch",
          code == C.FAIL and "a correction renumbers" in out and "RN.1" in out and C.head_sha() == head)

# ----- end of v22 r2


def _v22_r3_tests(dirs):
    """v2.2 A4, A5, A6: batch-run, batch identity, carry-from, small defects. Creates its own repos with new_repo() and appends them to dirs."""
    def judge(u):
        if "restates" in u["preview"]:
            return {"disposition": C.REGEN, "basis": "restates the call below"}
        return {"disposition": C.STILL, "basis": "carries a reason"}

    # A4, A5: batch-run runs a batch to its end; the batch ends at its final unit, and the
    # owner's commits after it are reported, never judged or undone
    dirs.append(new_repo("cons_selftest_r3late_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    write("n.py", "# a reason the code cannot say\nx = 1\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "b.py", "n.py")
    fill(str(next(Path(".consolidation").glob("B-1-*.batch"))), judge)
    code, out = run("batch-run", "--batch", "B-1")
    check("A4: batch-run runs every review unit of a small batch to the batch end",
          code == C.OK and out.count("GATE PASSED") == 3 and "batch B-1 complete" in out
          and C.record_from_commit("HEAD").header["unit_id"] == "B-1.3")
    check("S2: a review unit batch-next gated is in the verified cache (ADR 0016)",
          C.head_sha() in C._verified_commits())
    end = C.head_sha()
    write("a.py", "# a note the owner added with the fix\na()\nfix = 1\n")
    commit("fix after a red suite")
    code, out = run("batch-status", "--batch", "B-1")
    check("A5: batch-status after a complete batch + 1 later commit reports it complete, exit 0",
          code == C.OK and f"batch B-1 complete; 1 later commit(s) after {end[:7]}" in out and "undo:" not in out)
    code, out = run("batch-next", "--batch", "B-1")
    check("A5: batch-next after a complete batch + 1 later commit reports it complete, never an undo",
          code == C.OK and f"batch B-1 complete; 1 later commit(s) after {end[:7]}" in out and "undo:" not in out)
    write("b.py", "b()\nfix = 2\n")
    commit("second fix")
    code, out = run("batch-next", "--batch", "B-1")
    code2, out2 = run("batch-status", "--batch", "B-1")
    check("A5: + 2 later commits: batch-next and batch-status report the batch complete, exit 0",
          code == C.OK and code2 == C.OK and "2 later commit(s)" in out and "2 later commit(s)" in out2
          and "undo:" not in out + out2)
    code, out = run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "b.py", "n.py")
    check("D4: batch-init refuses a batch id that already has a master record, and names the next free id",
          code == C.FAIL and "already has a master record" in out and "B-2" in out
          and len(list(Path(".consolidation").glob("B-1-*.batch"))) == 1)
    code, out = run("batch-init", "--pass-kind", "comment", "--batch-id", "B-2", "--scope", "a.py", "b.py", "n.py",
                    "--carry-from", "B-1")
    m2 = C.parse_record(str(next(Path(".consolidation").glob("B-2-*.batch"))))
    kept = [u for u in m2.units if u["file"] == "n.py"]
    new = [u for u in m2.units if u["file"] == "a.py"]
    check("D2: batch-init --carry-from B-1 carries the judgement of unchanged files and lists the rest",
          code == C.OK and "carried the judgement of 1 of 2 unit(s)" in out and f"uncarried (classify these): unit(s) {new[0]['id']}" in out
          and kept[0].get("basis") == "carries a reason" and not new[0].get("disposition"))

    # A4: batch-run stops after a unit that asks for the suite, and at a stop (exit 1)
    dirs.append(new_repo("cons_selftest_r3run_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1, "suite_cadence": "unit"}')
    write("a.py", "# restates a\na()\n")
    write("c.py", "# we chose polling over webhooks: the vendor drops webhook retries\npoll()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "c.py")
    fill(str(next(Path(".consolidation").glob("B-1-*.batch"))), lambda u: judge(u) if "restates" in u["preview"] else
         {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries", "adr": "docs/adr/0001-polling.md"})
    code, out = run("batch-run", "--batch", "B-1")
    check("A4: batch-run stops right after a unit whose SUITE line says to run the suite now",
          code == C.OK and out.count("GATE PASSED") == 1 and "SUITE: run the test suite now" in out
          and C.record_from_commit("HEAD").header["unit_id"] == "B-1.1")
    head = C.head_sha()
    code, out = run("batch-run", "--batch", "B-1")
    check("A4: batch-run stops at the first stop with exit 1",
          code == C.FAIL and "STOP: write the ADR" in out and C.head_sha() == head)
    write("docs/adr/0009-other.md", "# 0009\n")
    write("stray.py", "x = 1\n")
    sh("git", "add", "docs/adr/0009-other.md", "stray.py")
    undo = C._undo("git", head, [], "B-1", C.load_config())
    check("D7: the undo never lists an ADR file for deletion", "stray.py" in undo and "0009" not in undo)

    # D6: an untracked .consolidation.json does not stop batch-next, as it does not stop preflight
    dirs.append(new_repo("cons_selftest_r3cfg_"))
    write("a.py", "# restates a\na()\n")
    commit("base")
    write(".consolidation.json", '{"REMOVAL_JUDGEMENT_CAP": 10}')
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py")
    fill(str(next(Path(".consolidation").glob("B-1-*.batch"))), judge)
    code, out = run("batch-next", "--batch", "B-1")
    check("D6: an untracked .consolidation.json does not stop batch-next",
          code == C.OK and "GATE PASSED" in out and "the tree differs" not in out)

    # D8: a commit hook that rewrites a scope file stops the unit before its gate
    dirs.append(new_repo("cons_selftest_r3hook_"))
    write("a.py", "# restates a\na()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py")
    fill(str(next(Path(".consolidation").glob("B-1-*.batch"))), judge)
    write(".git/hooks/pre-commit", "#!/bin/sh\nprintf 'hooked = 1\\n' >> a.py\ngit add a.py\n")
    os.chmod(".git/hooks/pre-commit", 0o755)
    code, out = run("batch-next", "--batch", "B-1")
    check("D8: a commit hook that rewrote a scope file stops batch-next, naming the file",
          code == C.FAIL and "a.py" in out and "a commit hook rewrote them" in out and "undo:" in out)

    # the tree comparison keys are root-relative (apply wrote them), never rebased on where the
    # command was typed: a batch-next typed in a subdirectory raises no false hook alarm
    dirs.append(new_repo("cons_selftest_r3sub_"))
    write("a.py", "# restates a\na()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py")
    fill(str(next(Path(".consolidation").glob("B-1-*.batch"))), judge)
    Path("sub").mkdir()
    old = C.ORIG_CWD
    C.ORIG_CWD = str(Path.cwd() / "sub")
    try:
        code, out = run("batch-next", "--batch", "B-1")
    finally:
        C.ORIG_CWD = old
    check("D8: batch-next typed in a subdirectory raises no false hook alarm",
          code == C.OK and "GATE PASSED" in out and "a commit hook rewrote" not in out)

# ----- end of v22 r3


def _v22_b1_tests(dirs):
    """v2.2 B1 + B2 + B4: partial regenerable, pointer condense, the new facts and panels.
    Creates its own repos with new_repo() and appends them to dirs."""

    def tamper(record, fn):
        rec = C.parse_record(record)
        fn(rec)
        C.write_record(rec, record[:-7] + "-t.record")
        return run("record-check", "--record", record[:-7] + "-t.record")

    # B1: regenerable -> delete may carry an edit keeping a subset of the unit's whole lines
    dirs.append(new_repo("cons_v22b1_regen_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("r.py", "# banner line one\n# banner line two\n# banner line three\nx = 1\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "G1", "--scope", "r.py",
        "--out", ".consolidation/g1.record")
    fill(".consolidation/g1.record", lambda u: {"disposition": C.REGEN, "basis": "restates x = 1",
                                                "edit": "# banner line one\n# banner line three"})
    code, out = run("record-check", "--record", ".consolidation/g1.record")
    check("v2.2 B1: a partial regenerable edit keeping two of the three whole lines passes",
          code == C.OK)
    check("v2.2 B1: a reordered edit is not a subsequence of the unit's lines",
          tamper(".consolidation/g1.record", lambda r: r.units[0].update(
              edit="# banner line three\n# banner line one"))[0] == C.FAIL)
    check("v2.2 B1: an edit that changes a line is refused",
          tamper(".consolidation/g1.record", lambda r: r.units[0].update(
              edit="# banner line one\n# banner line two and more"))[0] == C.FAIL)
    check("v2.2 B1: an edit that drops no line is refused",
          tamper(".consolidation/g1.record", lambda r: r.units[0].update(
              edit="# banner line one\n# banner line two\n# banner line three"))[0] == C.FAIL)
    code, out = tamper(".consolidation/g1.record", lambda r: r.units[0].update(
        edit="# banner line one   \n\t# banner line three"))
    check("O5: a partial edit keeps the unit's whole lines modulo leading and trailing whitespace",
          code == C.OK)
    code, out = tamper(".consolidation/g1.record", lambda r: r.units[0].update(edit="   \n\t"))
    check("R3: a whitespace-only edit is an edit with no lines — the unit is removed whole or kept",
          code == C.FAIL and "without an edit the unit is removed whole" in out)
    code, out = tamper(".consolidation/g1.record", lambda r: r.units[0].update(edit=""))
    check("v2.2 B1: an edit with no lines is refused: without an edit the unit is removed whole",
          code == C.FAIL and "without an edit the unit is removed whole" in out)
    check("v2.2 B1: without an edit the disposition is unchanged (whole removal)",
          tamper(".consolidation/g1.record", lambda r: r.units[0].pop("edit", None))[0] == C.OK)
    code, out = tamper(".consolidation/g1.record", lambda r: r.units[0].update(
        edit="# banner line one\n//go:build ignore"))
    check("v2.2 B1: the comment-edit checks keep applying (no directive in the edit)",
          code == C.FAIL and "directive" in out)
    code, out = run("apply", "--record", ".consolidation/g1.record")
    check("v2.2 B1: apply replaces the unit with the kept lines (plan op replace, not remove)",
          code == C.OK and read("r.py") == "# banner line one\n# banner line three\nx = 1\n")

    # B2: a condense may condense to a pointer naming a spec, which must exist at the baseline
    dirs.append(new_repo("cons_v22b1_ptr_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("docs/spec.md", "# Spec\n\nThe driver buffers writes; flush before close.\n")
    write("c.py", "# flush before close because the driver buffers\n# writes and drops them; the\n"
                  "# rule we implement is stated in docs/spec.md, section three\ns = 1\n")
    commit("base")
    code, out = run("escalate", "--standing", "--ruling-text",
                    "condense three-line flush comments into one pointer line; keep the reason, cite the spec")
    sr = out.split("standing ruling recorded: ")[1].split()[0]

    def ptr_fill(u, edit="# flush first: see docs/spec.md §3",
                 claims="flush before close; the driver buffers; docs/spec.md §3"):
        return {"disposition": C.COND, "basis": "the rule restates the spec; the pointer keeps it",
                "claims": claims, "ruling": sr, "edit": edit}

    run("record-init", "--pass-kind", "comment", "--unit-id", "P1", "--scope", "c.py",
        "--out", ".consolidation/p1.record")
    fill(".consolidation/p1.record", ptr_fill)
    check("v2.2 B2: a condense whose pointer names a spec that exists at the baseline passes",
          run("record-check", "--record", ".consolidation/p1.record")[0] == C.OK)
    code, out = tamper(".consolidation/p1.record", lambda r: r.units[0].update(
        edit="# flush first: see docs/nope.md §3",
        claims="flush before close; the driver buffers; docs/nope.md"))
    check("v2.2 B2: a pointer to a path missing at the baseline fails record-check",
          code == C.FAIL and "'docs/nope.md', which is not a file at the baseline" in out)
    code, out = tamper(".consolidation/p1.record", lambda r: r.units[0].update(
        edit="# flush first: see docs §3", claims="flush before close; the driver buffers; docs"))
    check("O3: a pointer naming a directory fails record-check — a spec is a file",
          code == C.FAIL and "'docs', which is not a file at the baseline" in out)
    code, out = tamper(".consolidation/p1.record", lambda r: r.units[0].update(
        edit="# flush: see docs/spec.md §3, see docs/nope.md §1",
        claims="flush before close; the driver buffers; docs/spec.md §3; docs/nope.md §1"))
    check("O3: every pointer on a line is checked, not only the first",
          code == C.FAIL and "'docs/nope.md', which is not a file at the baseline" in out)
    code, out = tamper(".consolidation/p1.record", lambda r: r.units[0].update(
        claims="flush before close; the driver buffers"))
    check("v2.2 B2: a pointer whose path the claims ledger does not cite fails",
          code == C.FAIL and "claims ledger" in out)

    # B4a: the new facts, long=, narration, todo and dup-of=, re-measured by record-check
    dirs.append(new_repo("cons_v22b1_facts_"))
    write("f.py", "# call the api before the close\n"     # 1  narration
                  "x = 1\n"                                # 2
                  "# TODO revisit the retry cap\n"         # 3  todo
                  "y = 2\n"                                # 4
                  "# duplicated note\n"                    # 5  twin of 7
                  "z = 3\n"                                # 6
                  "# duplicated note\n"                    # 7  twin of 5
                  "w = 4\n"                                # 8
                  "# a long unit\n# with five lines\n# of comment text\n# so it is long\n# indeed\n"
                  "v = 5\n")                               # 9-13 long=5
    write("g.py", "# duplicated note\ng = 1\n")            # same body, another file: no dup-of
    write("d.md", "set the value from the config\none\ntwo\nthree\nfour\n\nTODO revisit the retry cap\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "FA", "--scope", "f.py", "g.py",
        "--out", ".consolidation/fa.record")
    run("record-init", "--pass-kind", "document", "--unit-id", "DA", "--scope", "d.md",
        "--out", ".consolidation/da.record")
    facts = {(u["file"], u["lines"]): u.get("facts", "") for p in (".consolidation/fa.record",
             ".consolidation/da.record") for u in C.parse_record(p).units}
    check("v2.2 B4a: narration — the first body line opens with a verb, case-insensitive",
          facts[("f.py", "1-1")] == "narration")
    check("v2.2 B4a: todo — TODO/FIXME/XXX/HACK, word-bounded", facts[("f.py", "3-3")] == "todo")
    check("v2.2 B4a: long=N from five lines up, comment and document passes",
          facts[("f.py", "9-13")] == "long=5" and facts[("d.md", "1-5")] == "long=5")
    check("O5: the todo mark is comment-pass only — a document unit carrying TODO gets no fact",
          facts[("d.md", "7-7")] == "")
    check("v2.2 B4a: dup-of names the other same-file twin(s), ascending",
          facts[("f.py", "5-5")] == "dup-of=4" and facts[("f.py", "7-7")] == "dup-of=3")
    check("v2.2 B4a: dup-of is same-file only, and narration is comment-only",
          not facts.get(("g.py", "1-1")))
    fill(".consolidation/fa.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    check("v2.2 B4a: an honest record carrying the new facts passes record-check",
          run("record-check", "--record", ".consolidation/fa.record")[0] == C.OK)
    code, out = tamper(".consolidation/fa.record", lambda r: r.units[0].update(
        facts="narration; dup-of=99"))
    check("v2.2 B4a: a forged new fact fails identity (record-check re-measures it)",
          code == C.FAIL and "facts" in out)

    # C3 + O5: the word boundary of narration, the near-misses, the 4-line edge, and dup-of's
    # normalized compare, ascending by number (ids 2, 9, 10 sort differently as strings)
    write("h.py", "# returns the value now\nr = 1\n"          # 1  no narration: `return` + \b
                  "# Return the value now\ns = 2\n"           # 3  narration, case-insensitive
                  "# a four line unit\n# two\n# three\n# four\nt = 3\n"   # 5-8 no long=
                  "# todomvc is the demo app\nu = 4\n")       # 10 no todo: word-bounded
    write("k.py", "".join(("# Same   Note\n" if i == 2 else "# same note\n" if i == 9 else
                           "# SAME note \n" if i == 10 else f"# unit {i} distinct\n") + f"v{i} = {i}\n"
                          for i in range(1, 11)))
    write("e.md", "Alpha rule holds.\n\nalpha  RULE holds.\n")
    commit("feat: facts edges", "h.py", "k.py", "e.md")
    run("record-init", "--pass-kind", "comment", "--unit-id", "FB", "--scope", "h.py",
        "--out", ".consolidation/fb.record")
    run("record-init", "--pass-kind", "comment", "--unit-id", "FC", "--scope", "k.py",
        "--out", ".consolidation/fc.record")
    run("record-init", "--pass-kind", "document", "--unit-id", "DB", "--scope", "e.md",
        "--out", ".consolidation/db.record")
    facts = {(u["file"], u["lines"]): u.get("facts", "") for p in (".consolidation/fb.record",
             ".consolidation/fc.record", ".consolidation/db.record") for u in C.parse_record(p).units}
    check("C3: narration is word-bounded — `returns` is no narration, `Return` is (case-insensitive)",
          facts[("h.py", "1-1")] == "" and facts[("h.py", "3-3")] == "narration")
    check("O5: a four-line unit carries no long=, and `todomvc` is no todo",
          facts[("h.py", "5-8")] == "" and facts[("h.py", "10-10")] == "")
    check("O5: dup-of compares the normalized text (case, inner and trailing space) and joins the "
          "twins ascending by number",
          facts[("k.py", "3-3")] == "dup-of=9,10" and facts[("k.py", "17-17")] == "dup-of=2,10"
          and facts[("k.py", "19-19")] == "dup-of=2,9")
    check("O5: dup-of reaches a document record too",
          facts[("e.md", "1-1")] == "dup-of=2" and facts[("e.md", "3-3")] == "dup-of=1")

    # B4b: the long-units panel question, stdout only
    dirs.append(new_repo("cons_v22b1_long_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("l.py", "# a long unit\n# with five lines\n# of comment text\n# so it is long\n# indeed\n"
                  "x = 1\n# must comply with the external policy rule\ny = 2\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "L1", "--scope", "l.py",
        "--out", ".consolidation/l1.record")
    fill(".consolidation/l1.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"}
         if u["lines"] == "1-5" else {"disposition": C.NV, "basis": "the policy rule is external"})
    code, out = run("escalate", "--from-record", ".consolidation/l1.record")
    check("v2.2 B4b: one question line names the long units that no standing ruling covered",
          'question: 1 long unit(s) (max 5 lines) that no standing ruling covered; to record one: '
          'escalate --standing --ruling-text "<the class and its keep-rules>"' in out)
    check("v2.2 B4b: the question is stdout only, never an intake entry",
          "question:" not in read("intake.md"))
    code, out = run("escalate", "--standing", "--ruling-text",
                    "condense five-line comment units to their reason; drop the narration")
    sr2 = out.split("standing ruling recorded: ")[1].split()[0]
    run("record-init", "--pass-kind", "comment", "--unit-id", "L2", "--scope", "l.py",
        "--out", ".consolidation/l2.record")
    fill(".consolidation/l2.record", lambda u: {"disposition": C.COND, "ruling": sr2,
                                                "basis": "the reason stays", "claims": "the reason stays",
                                                "edit": "# long unit: the reason stays"}
         if u["lines"] == "1-5" else {"disposition": C.STILL, "basis": "carries a reason"})
    code, out = run("escalate", "--from-record", ".consolidation/l2.record")
    check("v2.2 B4b: nothing when every long unit is condense", "question:" not in out)

    # O5: the question names the count of the long units and the longest of them
    dirs.append(new_repo("cons_v22b1_long2_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("m.py", "# a five line unit\n# of comment text\n# that no ruling\n# has ever\n# covered\n"
                  "x = 1\n"
                  "# a seven line unit\n# of comment text\n# that no ruling\n# has ever\n# covered\n"
                  "# not once\n# not twice\n"
                  "y = 2\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "M1", "--scope", "m.py",
        "--out", ".consolidation/m1.record")
    fill(".consolidation/m1.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    code, out = run("escalate", "--from-record", ".consolidation/m1.record")
    check("O5: two long units raise one question carrying their count and the longest",
          'question: 2 long unit(s) (max 7 lines) that no standing ruling covered; to record one: '
          'escalate --standing --ruling-text "<the class and its keep-rules>"' in out)

    # B4c: record-shard remembers each scoped file's unit rule from the nearest committed record
    dirs.append(new_repo("cons_v22b1_rule_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("d.md", "Tokens are signed with HMAC.\n")
    commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "R1", "--scope", "d.md",
        "--out", ".consolidation/r1.record")
    fill(".consolidation/r1.record", lambda u: {"disposition": C.NV, "basis": "the scheme is set by contract",
                                                "tbc": "Confirm the signing scheme."}
         if "HMAC" in u.get("preview", "") else {"disposition": C.STILL, "basis": "title"})
    run("apply", "--record", ".consolidation/r1.record")
    sh("git", "add", "d.md")
    sh("git", "commit", "-q", "-F", ".consolidation/r1.commit-msg")
    rec_commit = C.head_sha()
    write("noise.txt", "x\n")
    sh("git", "add", "noise.txt")
    sh("git", "commit", "-qm", "noise")
    run("record-init", "--pass-kind", "document", "--unit-id", "R2", "--scope", "d.md",
        "--out", ".consolidation/r2.record")
    code, out = run("record-shard", "--record", ".consolidation/r2.record", "--shards", "1")
    check("v2.2 B4c: record-shard remembers the unit rule from the nearest committed record below "
          "the baseline",
          f"d.md: unit rule document-paragraph from record R1 ({rec_commit[:7]})" in out)
    run("record-init", "--pass-kind", "document", "--unit-rule", "document-block", "--unit-id", "R3",
        "--scope", "d.md", "--out", ".consolidation/r3.record")
    code, out = run("record-shard", "--record", ".consolidation/r3.record", "--shards", "1")
    check("v2.2 B4c: a remembered rule that differs from the record's header carries warn:",
          f"warn: d.md: unit rule document-paragraph from record R1 ({rec_commit[:7]})" in out)
    cap = C.RULE_WALK_CAP
    try:
        C.RULE_WALK_CAP = 1   # the baseline (noise) only: R1's commit lies beyond the cap
        code, out = run("record-shard", "--record", ".consolidation/r3.record", "--shards", "1")
    finally:
        C.RULE_WALK_CAP = cap
    check("O2: a walk the cap stops with files left says so in one note line — a silent cap lies",
          "note: no document record found within 1 commits for 1 file(s)" in out and "unit rule" not in out)
    code, out = run("record-shard", "--record", ".consolidation/r3.record", "--shards", "1")
    check("O2: a walk that reaches its record within the cap prints no note", "note:" not in out)

    # C5: the remembered unit rule — the nearest committed document record wins, one line per
    # scoped file, and only a document record is remembered
    dirs.append(new_repo("cons_v22b1_near_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "document_exts": [".md", ".py"]}')
    write("d.md", "Tokens are signed with HMAC.\n")
    write("e.md", "The queue drains nightly.\n")
    write("p.py", "# a note\n\nx = 1\n")
    commit("base")

    def still_doc(uid, rule, *files):
        run("record-init", "--pass-kind", "document", "--unit-id", uid, *rule, "--scope", *files,
            "--out", f".consolidation/{uid.lower()}.record")
        fill(f".consolidation/{uid.lower()}.record", lambda u: {"disposition": C.STILL, "basis": "holds"})
        run("apply", "--record", f".consolidation/{uid.lower()}.record")
        sh("git", "commit", "-q", "--allow-empty", "-F", f".consolidation/{uid.lower()}.commit-msg")

    still_doc("R1", (), "d.md")
    still_doc("RM", (), "d.md", "e.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "RN", "--scope", "d.md", "e.md",
        "--out", ".consolidation/rn.record")
    code, out = run("record-shard", "--record", ".consolidation/rn.record", "--shards", "1")
    check("O5: one remembered-rule line per scoped file (a two-file record)",
          out.count("d.md: unit rule document-paragraph from record RM") == 1
          and out.count("e.md: unit rule document-paragraph from record RM") == 1
          and out.count("from record") == 2)
    still_doc("RD", (), "p.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "RC", "--scope", "p.py",
        "--out", ".consolidation/rc.record")
    fill(".consolidation/rc.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    run("apply", "--record", ".consolidation/rc.record")
    sh("git", "commit", "-q", "--allow-empty", "-F", ".consolidation/rc.commit-msg")
    run("record-init", "--pass-kind", "document", "--unit-id", "RQ", "--scope", "p.py",
        "--out", ".consolidation/rq.record")
    code, out = run("record-shard", "--record", ".consolidation/rq.record", "--shards", "1")
    check("C5: a comment-pass record covering the file yields no line — the walk continues below it",
          "p.py: unit rule document-paragraph from record RD" in out and "from record RC" not in out)
    still_doc("R2", ("--unit-rule", "document-block"), "d.md")
    run("record-init", "--pass-kind", "document", "--unit-rule", "document-block", "--unit-id", "R3",
        "--scope", "d.md", "--out", ".consolidation/r3.record")
    code, out = run("record-shard", "--record", ".consolidation/r3.record", "--shards", "1")
    check("C5: the nearest committed document record wins — an older one covering the file adds no line",
          "d.md: unit rule document-block from record R2" in out and "from record RM" not in out
          and "from record R1" not in out)


# ----- end of v22 b1


def _v22_b2_tests(dirs):
    """v2.2 wave 2, agent b2: B3 (duplicate -> delete with `of:`, `conflicts:` on a frozen unit)
    and B5 (batch-revert and the chain's revert-subject acceptance). Creates its own repos with
    new_repo() and appends them to dirs."""
    # --- B3: the document pass grows `duplicate -> delete` and the `of:` / `conflicts:` fields
    dirs.append(new_repo("cons_selftest_b3doc_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("auth.md", "# Auth\n"
                     "\n"
                     "Sessions expire after 30 minutes.\n"
                     "\n"
                     "Sessions expire after 24 hours.\n"
                     "\n"
                     "Retention follows GDPR Art. 5.\n"
                     "\n"
                     "Retention follows GDPR Art. 5.\n")
    commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "D1", "--scope", "auth.md",
        "--out", ".consolidation/d1.record")
    rec = C.parse_record(".consolidation/d1.record")
    check("B3: two identical paragraphs are two units with distinct fingerprints",
          len(rec.units) == 5 and len({u["fingerprint"] for u in rec.units}) == 5)
    dup = [u for u in rec.units if u["lines"] == "9-9"][0]
    kept = [u for u in rec.units if u["lines"] == "7-7"][0]["id"]
    part = [u for u in rec.units if u["lines"] == "3-3"][0]["id"]   # the unit the carrier conflicts with
    write(".consolidation/d1.j", f"@@ {dup['id']} {dup['fingerprint']}\ndisposition: {C.DUPL}\n"
                                 f"basis: duplicates the retention statement of unit {kept}\nof: {kept}\n")
    code, out = run("record-fill", "--record", ".consolidation/d1.record", "--from", ".consolidation/d1.j")
    r = C.parse_record(".consolidation/d1.record")
    check("B3: record-fill accepts `of:` and writes it with the disposition",
          code == C.OK and r.units[4].get("of") == kept and r.units[4].get("disposition") == C.DUPL)
    carrier = [u for u in rec.units if u["lines"] == "5-5"][0]["id"]   # the frozen unit that carries conflicts:

    def b3_judge(u):
        p = u.get("preview", "")
        if p.startswith("Sessions expire after 30"):
            return {"disposition": C.DEFECT, "basis": "sessions.py:2 sets EXPIRE_MINUTES = 30"}
        if p.startswith("Sessions expire after 24"):
            return {"disposition": C.DEFECT, "basis": "sessions.py:2 sets EXPIRE_MINUTES = 24",
                    "conflicts": part}
        if p.startswith("Retention follows"):
            if u["lines"] == "7-7":
                return {"disposition": C.NV, "basis": "GDPR is external", "tbc": "Confirm the retention period."}
            return {"disposition": C.DUPL, "basis": "duplicates the retention statement of the kept unit",
                    "of": kept}
        return {"disposition": C.STILL, "basis": "the section exists"}

    fill(".consolidation/d1.record", b3_judge)
    code, out = run("record-check", "--record", ".consolidation/d1.record")
    check("B3: a document record with duplicate -> delete (of:) and conflicts: passes record-check", code == C.OK)
    r = C.parse_record(".consolidation/d1.record")
    check("B3: of: and conflicts: survive the record round trip (parser and renderer)",
          r.units[4].get("of") == kept and r.units[2].get("conflicts") == part)

    def b3_bad(mutate, name, *needles):
        rr = C.parse_record(".consolidation/d1.record")
        mutate(rr)
        C.write_record(rr, ".consolidation/bad.record")
        code, out = run("record-check", "--record", ".consolidation/bad.record")
        check(name, code == C.FAIL and all(n in out for n in needles))

    b3_bad(lambda rr: rr.units[0].update({"of": kept}),
           "B3: `of:` is refused on a unit that is not duplicate -> delete", "`of:` belongs to")
    b3_bad(lambda rr: rr.units[4].pop("of"),
           "B3: duplicate -> delete without `of:` is refused", "requires `of:`")
    b3_bad(lambda rr: rr.units[4].update({"of": "99"}),
           "B3: `of:` naming no unit of the record's file is refused", "names no other unit")
    b3_bad(lambda rr: rr.units[4].update({"of": dup["id"]}),
           "B3: `of:` naming the unit itself is refused", "names no other unit")
    b3_bad(lambda rr: (rr.units[4].update({"of": "1"}),
                       rr.units[0].update({"disposition": C.ADR, "adr_title": "drop the auth heading",
                                           "adr_text": "## Context\n\nThe doc said why.\n\n## Decision\n\nDrop it.\n\n"
                                                       "## Consequences\n\nThe section stays."})),
           "B3: `of:` naming a unit whose disposition removes it (ADR) is refused",
           "whose disposition removes it")
    b3_bad(lambda rr: (rr.units[4].update({"of": part}), rr.units[1].pop("disposition"),
                       rr.units[1].update({"disposition": C.OBS, "basis": "gone"})),
           "B3: `of:` naming an obsolete unit without edit (removed) is refused",
           "whose disposition removes it")
    b3_bad(lambda rr: rr.units[0].update({"conflicts": part}),
           "B3: `conflicts:` on a unit that is not frozen is refused", "`conflicts:` belongs to a frozen unit")
    b3_bad(lambda rr: rr.units[1].update({"conflicts": carrier}),
           "B3: `conflicts:` on both units of a pair is refused", "one direction per pair")
    b3_bad(lambda rr: rr.units[2].update({"conflicts": "99"}),
           "B3: `conflicts:` naming no unit of the record's file is refused", "names no other unit")
    b3_bad(lambda rr: rr.units[4].update({"edit": "Retention follows GDPR Art. 5."}),
           "B3: duplicate -> delete takes no edit (the unit is removed whole)", "takes no edit")
    b3_bad(lambda rr: rr.units[0].update({"disposition": C.REGEN, "basis": "restates the title",
                                          "edit": "# Auth"}),
           "C2: regenerable -> delete (with an edit) stays out of a document pass — the partial-subset proof "
           "is comment-only", "is not a disposition of a document pass")

    code, out = run("apply", "--record", ".consolidation/d1.record")
    d = read("auth.md")
    check("B3: apply removes the duplicate whole and keeps the unit `of:` names",
          d.count("Retention follows GDPR Art. 5.") == 1 and d.count("Sessions expire after") == 2
          and "## To be confirmed" in d)
    sh("git", "add", "auth.md")
    sh("git", "commit", "-q", "-F", ".consolidation/d1.commit-msg")
    check("B3: the applied record with of: and conflicts: passes gate --unit",
          run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)

    write("c.py", "# Retention follows GDPR Art. 5.\nx = 1\n")
    commit("feat: c", "c.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "D2", "--scope", "c.py",
        "--out", ".consolidation/d2.record")
    fill(".consolidation/d2.record", lambda u: {"disposition": C.DUPL, "basis": "duplicates", "of": "1"})
    code, out = run("record-check", "--record", ".consolidation/d2.record")
    check("B3: duplicate -> delete is refused in a comment pass",
          code == C.FAIL and "is not a disposition of a comment pass" in out)
    fill(".consolidation/d2.record", lambda u: {"disposition": C.DEFECT, "basis": "c.py:2 is x = 1",
                                               "conflicts": "9"})
    code, out = run("record-check", "--record", ".consolidation/d2.record")
    check("K1: `conflicts:` on a comment-pass unit is refused — a field the pass does not admit "
          "is never acted on (the mutual-suppression case)",
          code == C.FAIL and "`conflicts:` belongs to a frozen unit" in out
          and "of a document pass only" in out)
    fill(".consolidation/d2.record", lambda u: {"disposition": C.STILL, "basis": "still true", "of": "1"})
    code, out = run("record-check", "--record", ".consolidation/d2.record")
    check("K1: `of:` on a comment-pass unit is refused the same way",
          code == C.FAIL and "`of:` belongs to" in out and "of a document pass only" in out)

    code, out = run("escalate", "--from-record", ".consolidation/d1.record")
    ents = [e for e in map(C.parse_intake_line, read("intake.md").split("\n")) if e]
    conf = [e for e in ents if f"conflicts with unit {part}" in e["body"]]
    fp5 = C.parse_record(".consolidation/d1.record").units[2]["fingerprint"]
    fp3 = C.parse_record(".consolidation/d1.record").units[1]["fingerprint"]
    check("B3: the conflict pair raises one entry whose text carries both texts",
          code == C.OK and len(conf) == 1 and "frozen unit, byte-for-byte" in conf[0]["body"]
          and "(auth.md:3-3): sessions.py:2 sets EXPIRE_MINUTES = 30" in conf[0]["body"]
          and conf[0]["fields"].get("fingerprint") == fp5)
    check("B3: the frozen partner's own entry is suppressed with one line",
          f"unit {part}: suppressed: the conflict partner of unit {carrier} carries the question" in out)
    check("B3: exactly the conflict entry and the tbc entry are raised",
          len(ents) == 2 and any(e["fields"].get("kind") == "unverifiable-statement" for e in ents))
    code, out = run("escalate", "--rule", "--file", "auth.md", "--line", "5", "--fingerprint", fp5,
                    "--ruling-text", "24 hours is right: fix the code", "--also-fingerprint", fp3)
    ruled = [l for l in read("intake.md").split("\n") if "RULED" in l and fp5 in l]
    check("B3: the ruling names both units (--also-fingerprint); units= is written by --rule only",
          code == C.OK and ruled and f"units={fp3}" in ruled[0] and "owner, units=" in ruled[0])

    # --- B5: batch-revert, and the chain's acceptance of the revert subject
    dirs.append(new_repo("cons_selftest_b5rev_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# legacy flush note\nx = 1\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "b.py")
    mpath = str(next(Path(".consolidation").glob("B-1-*.batch")))
    fpb = [u for u in C.parse_record(mpath).units if u["file"] == "b.py"][0]["fingerprint"]
    run("escalate", "--file", "b.py", "--line", "1", "--kind", "suspected-defect", "--divergence", "legacy flush")
    run("escalate", "--rule", "--file", "b.py", "--line", "1", "--fingerprint", fpb,
        "--ruling-text", "the note is false: delete it")
    fill(mpath, lambda u: ({"disposition": C.RULED, "basis": "owner ruling: the note is false", "ruling": fpb}
                           if u["file"] == "b.py" else {"disposition": C.REGEN, "basis": "restates a()"}))
    code, out = run("batch-run", "--batch", "B-1")
    check("B5 premise: the two-unit batch runs to the end and closes the applied ruling",
          code == C.OK and "batch B-1 complete" in out and "state=applied" in read("intake.md"))
    master = C.parse_record(mpath)
    done = C.batch_chain(master, C._master_rel(mpath))[0]
    u1, u2 = done[0]["commit"], done[1]["commit"]
    g = f"git -C {C._q(Path.cwd().resolve().as_posix())}"
    code, out = run("batch-revert", "--batch", "B-1", "--from", "2")
    check("B5: batch-revert prints exactly the git line for units 2..2 and re-opens the ruling",
          code == C.OK and f'{g} revert --no-commit {u2} && {g} commit -m '
                           f'"consolidation: revert batch B-1 units 2..2"' in out
          and "re-opened 1 ruling(s) on 1 entry/entries" in out and "warn:" not in out)
    ent = [e for e in map(C.parse_intake_line, read("intake.md").split("\n")) if e and e["fields"].get("fingerprint") == fpb]
    check("B5: the re-opened entry is ruled again and carries no applied triple",
          len(ent) == 1 and ent[0]["fields"].get("state") == "ruled"
          and fpb not in (ent[0]["fields"].get("applied") or ""))
    sh("git", "revert", "--no-commit", f"{u1}..{u2}")
    sh("git", "commit", "-qm", "consolidation: revert batch B-1 units 2..2")
    code, out = run("batch-status", "--batch", "B-1")
    check("B5: after the revert the batch is complete and the revert is a later commit",
          code == C.OK and f"batch B-1 complete; 1 later commit(s) after {u2[:7]}" in out)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "1")
    check("B5: --from 1 names every unit's own commit and reports no rulings",
          code == C.OK and f'{g} revert --no-commit {u1} {u2} && {g} commit -m '
                           f'"consolidation: revert batch B-1 units 1..2"' in out
          and "no applied rulings among units 1..2" in out)
    check("O1: a revert printed with HEAD above unit n warns that it lands above the later commits",
          f"warn: HEAD {C.head_sha()[:8]} is not unit 2's commit {u2[:8]}: the revert lands above "
          f"1 later commit(s)" in out)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "3")
    check("B5: --from above the done count is refused", code == C.FAIL and "out of 1..2" in out)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "0")
    check("B5: --from 0 is refused", code == C.FAIL and "out of 1..2" in out)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "x")
    check("B5: a non-integer --from is refused", code == C.FAIL and "an integer unit number" in out)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "01")
    check("B5: a zero-padded --from is refused", code == C.FAIL and "an integer unit number" in out)
    code, out = run("batch-revert", "--batch", "B-9", "--from", "1")
    check("B5: an unknown batch is refused", code == C.FAIL and "no master record" in out)

    # the chain accepts exactly the subject batch-revert prints, with 1 <= k <= n <= units done
    dirs.append(new_repo("cons_selftest_b5chain_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "b.py")
    mpath = str(next(Path(".consolidation").glob("B-1-*.batch")))
    fill(mpath, lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    code, out = run("batch-revert", "--batch", "B-1", "--from", "1")
    check("B5: a batch with no done unit is refused", code == C.FAIL and "no done review unit" in out)
    code, out = run("batch-next", "--batch", "B-1")
    check("B5 premise: unit 1 is done", code == C.OK and "GATE PASSED" in out)
    u1 = C.head_sha()
    sh("git", "commit", "-q", "--allow-empty", "-m", "consolidation: revert batch B-2 units 1..1")
    code, out = run("batch-status", "--batch", "B-1")
    check("B5: a revert subject naming another batch dies as today",
          code == C.FAIL and "record commit is missing" in out)
    sh("git", "reset", "-q", "--hard", "HEAD~1")
    sh("git", "commit", "-q", "--allow-empty", "-m", "consolidation: revert batch B-1 units 1..2")
    code, out = run("batch-status", "--batch", "B-1")
    check("B5: a revert whose range exceeds the units done before it dies as today",
          code == C.FAIL and "record commit is missing" in out)
    sh("git", "reset", "-q", "--hard", "HEAD~1")
    for subj in ("consolidation: revert batch B-1 units 0..1", "consolidation: revert batch B-1 units 2..1"):
        sh("git", "commit", "-q", "--allow-empty", "-m", subj)
        code, out = run("batch-status", "--batch", "B-1")
        check(f"R3: a revert subject out of bounds (units {subj.rsplit('units ', 1)[1]}) dies as a "
              f"foreign commit", code == C.FAIL and "record commit is missing" in out)
        sh("git", "reset", "-q", "--hard", "HEAD~1")
    rec_body = C.git("log", "--format=%B", "-n", "1", u1).split("\n", 1)[1]
    write("revmsg2.txt", "consolidation: revert batch B-1 units 1..1\n" + rec_body)
    sh("git", "commit", "-q", "--allow-empty", "-F", "revmsg2.txt")
    code, out = run("batch-status", "--batch", "B-1")
    check("R3: a record-carrying commit with a revert subject takes the unit path, never the skip",
          code == C.FAIL and "is not review unit B-1.2" in out)
    sh("git", "reset", "-q", "--hard", "HEAD~1")
    Path("revmsg2.txt").unlink()   # untracked dirt would fail the unit gate below
    sh("git", "revert", "--no-commit", u1)
    sh("git", "checkout", "HEAD", "--", ".consolidation")   # the revert keeps the record directory
    sh("git", "commit", "-qm", "consolidation: revert batch B-1 units 1..1")
    rv = C.head_sha()
    code, out = run("batch-next", "--batch", "B-1")
    check("B5: the chain accepts the printed revert subject: unit 2's baseline names it, the batch ends",
          code == C.OK and "batch B-1 complete" in out
          and C.record_from_commit("HEAD").header["baseline_sha"] == rv
          and read("a.py") == "# restates a\na()\n" and read("b.py") == "b()\n")

    # K3: the history walk never skips a record-carrying commit, whatever its subject — a revert
    # subject over a record is validated (here: unit 1's record replayed above unit 2's tree fails)
    done2 = C.batch_chain(C.parse_record(mpath), C._master_rel(mpath))[0]
    body = C.git("log", "--format=%B", "-n", "1", done2[0]["commit"]).split("\n", 1)[1]
    write("revmsg.txt", "consolidation: revert batch B-1 units 1..1\n" + body)
    sh("git", "commit", "-q", "--allow-empty", "-F", "revmsg.txt")
    rvsha = C.head_sha()
    probs = C._history_record_problems(C.load_config())
    check("K3: a record-carrying commit with a revert subject is judged by the walk, never skipped",
          any(rvsha[:8] in p for p in probs))
    sh("git", "reset", "-q", "--hard", "HEAD~1")

    # a revert never sits between a content commit and its record commit (the file channel)
    dirs.append(new_repo("cons_selftest_b5file_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1, "record_channel": "file"}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "b.py")
    mpath = str(next(Path(".consolidation").glob("B-1-*.batch")))
    fill(mpath, lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    code, out = run("batch-next", "--batch", "B-1")
    check("B5 premise: the file channel made unit 1's content commit and record commit",
          code == C.OK and "GATE PASSED" in out)
    write("a.py", "# restates a\na()\nhand = 1\n")
    sh("git", "add", "a.py")
    sh("git", "commit", "-qm", "hand content commit")
    code, out = run("batch-revert", "--batch", "B-1", "--from", "1")
    check("O1: batch-revert refuses while a content commit awaits its record commit — the chain would "
          "refuse the revert it prints",
          code == C.FAIL and "record commit is missing" in out and "git revert" not in out)
    sh("git", "commit", "-q", "--allow-empty", "-m", "consolidation: revert batch B-1 units 1..1")
    code, out = run("batch-status", "--batch", "B-1")
    check("B5: a revert never sits between a content commit and its record commit",
          code == C.FAIL and "is not review unit B-1.2" in out)

    # K2: a mid-batch revert committed without the `.consolidation` restore is refused — with
    # K >= 2 the master is rolled back, not deleted, and the chain is the only defense
    dirs.append(new_repo("cons_selftest_k2_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1, "record_channel": "file"}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    write("c.py", "# restates c\nc()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py", "b.py", "c.py")
    mpath = str(next(Path(".consolidation").glob("B-1-*.batch")))
    fill(mpath, lambda u: {"disposition": C.REGEN, "basis": "restates the call below"})
    run("batch-next", "--batch", "B-1")
    run("batch-next", "--batch", "B-1")
    master = C.parse_record(mpath)
    done = C.batch_chain(master, C._master_rel(mpath))[0]
    check("K2 premise: units 1 and 2 of 3 are done", len(done) == 2)
    a, z = done[0]["commit"], done[1]["commit"]
    sh("git", "revert", "--no-commit", f"{a}..{z}")
    sh("git", "commit", "-qm", "consolidation: revert batch B-1 units 2..2")   # restore forgotten
    code, out = run("batch-next", "--batch", "B-1")
    check("K2: a mid-batch revert that touches .consolidation/ is refused (the forgotten restore)",
          code == C.FAIL and "record commit is missing" in out)
    sh("git", "reset", "-q", "--hard", z)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "2")
    line = next((l for l in out.splitlines() if l.startswith("git -C ") and " revert --no-commit " in l), "")
    ran = subprocess.run(line, shell=True, capture_output=True).returncode if line else 1
    g = f"git -C {C._q(Path.cwd().resolve().as_posix())}"
    check("K2: batch-revert's line, run verbatim, restores .consolidation before its commit",
          code == C.OK and line == f'{g} revert --no-commit {done[1]["content"]} {z} && '
                                   f'{g} checkout HEAD -- .consolidation && '
                                   f'{g} commit -m "consolidation: revert batch B-1 units 2..2"' and ran == 0)
    code, out = run("batch-next", "--batch", "B-1")
    check("K2: the commit the printed line made is accepted (the file channel too)",
          code == C.OK and "batch B-1 complete" in out)

    # C4: batch-revert's re-open arithmetic — a ruling two review units applied keeps the
    # still-applied unit's triple, and the entry re-opens only when no covered unit still applies
    # it. The shared ruling: the paragraph and the tbc item it raised bind one entry (S65) — the
    # item by its text, the paragraph by its fingerprint, which follows the content wherever it
    # sits in the document.
    dirs.append(new_repo("cons_selftest_c4_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("r.md", "# Tape\n\nThe retention is 30 days.\n")
    commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "C0", "--scope", "r.md",
        "--out", ".consolidation/c0.record")
    fill(".consolidation/c0.record", lambda u: {"disposition": C.NV, "basis": "the period is external",
                                                "tbc": "Confirm the retention period."}
         if "retention" in u.get("preview", "").lower() else {"disposition": C.STILL, "basis": "the title"})
    run("escalate", "--from-record", ".consolidation/c0.record")
    fpP = next(u["fingerprint"] for u in C.parse_record(".consolidation/c0.record").units
               if "retention" in u.get("preview", "").lower())
    run("escalate", "--rule", "--file", "r.md", "--line", "3", "--fingerprint", fpP,
        "--ruling-text", "the claim is wrong: delete it")
    run("apply", "--record", ".consolidation/c0.record")
    sh("git", "add", "r.md")
    sh("git", "commit", "-q", "-F", ".consolidation/c0.commit-msg")
    # the owner moves the paragraph below its open item (a heading ends the section)
    write("r.md", "# Tape\n\n## To be confirmed\n\n- Confirm the retention period.\n\n"
                  "## Rules\n\nThe retention is 30 days.\n")
    commit("docs: the rule moves below its open item", "r.md")
    run("batch-init", "--pass-kind", "document", "--batch-id", "B-1", "--scope", "r.md")
    mpath = str(next(Path(".consolidation").glob("B-1-*.batch")))
    fill(mpath, lambda u: {"disposition": C.RULED, "basis": "owner ruling: the claim is wrong",
                           "ruling": fpP}
         if u.get("in_tbc") == "yes" or "retention" in u.get("preview", "").lower()
         else {"disposition": C.STILL, "basis": "the title"})
    code, out = run("batch-run", "--batch", "B-1")
    check("C4 premise: the batch runs to the end under the shared ruling",
          code == C.OK and "batch B-1 complete" in out)
    master = C.parse_record(mpath)
    done = C.batch_chain(master, C._master_rel(mpath))[0]
    b0 = done[0]["record"].header["baseline_sha"][:7]

    def c4_entry():
        return next(e for e in map(C.parse_intake_line, read("intake.md").split("\n"))
                    if e and e["fields"].get("fingerprint") == fpP)

    check("C4 premise: two review units applied the ruling and closed the entry",
          len(done) == 2 and c4_entry()["fields"].get("state") == "applied"
          and f"{fpP}:B-1.1@{b0}" in (c4_entry()["fields"].get("applied") or "")
          and ":B-1.2@" in (c4_entry()["fields"].get("applied") or ""))
    code, out = run("batch-revert", "--batch", "B-1", "--from", "2")
    check("C4: reverting unit 2 keeps unit 1's triple and the entry applied — a covered unit "
          "still applies the ruling",
          code == C.OK and "re-opened 1 ruling(s) on 1 entry/entries" in out and "warn:" not in out
          and c4_entry()["fields"].get("state") == "applied"
          and (c4_entry()["fields"].get("applied") or "") == f"{fpP}:B-1.1@{b0}")

    # Q2: the cut keeps a `duplicate -> delete` unit and the unit its `of:` names in one review
    # unit (the part record checks the pair), and the part record names the kept unit by its own
    # record-local id. Under the judgement cap 2 a cut by caps alone falls between lines 5 and 7.
    dirs.append(new_repo("cons_selftest_q2_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 2}')
    write("r.md", "# Retention\n\nThe queue is drained nightly.\n\nRetention follows GDPR Art. 5.\n\n"
                  "Retention follows GDPR Art. 5.\n\nThe archive is kept on tape.\n")
    commit("base")
    run("batch-init", "--pass-kind", "document", "--batch-id", "Q-1", "--scope", "r.md")
    mpath = str(next(Path(".consolidation").glob("Q-1-*.batch")))
    kept = [u for u in C.parse_record(mpath).units if u["lines"] == "5-5"][0]["id"]

    def q2_judge(u):
        if u["lines"] == "5-5":
            return {"disposition": C.OBS, "basis": "retention.py:3 cites Art. 6",
                    "edit": "Retention follows GDPR Art. 6."}
        if u["lines"] == "7-7":
            return {"disposition": C.DUPL, "basis": "duplicates the retention statement", "of": kept}
        if u["lines"] in ("3-3", "9-9"):
            return {"disposition": C.OBS, "basis": "no code drains a queue or writes a tape"}
        return {"disposition": C.STILL, "basis": "the title"}

    fill(mpath, q2_judge)
    code, out = run("batch-status", "--batch", "Q-1")
    check("Q2: the cut keeps the duplicate and its `of:` target in one review unit",
          code == C.OK and "Q-1.1  pending  — r.md:8-9" in out and "Q-1.2  pending  — r.md:4-7" in out
          and "Q-1.3  pending  — r.md:1-3" in out)
    code, out = run("batch-run", "--batch", "Q-1")
    d = read("r.md")
    check("Q2: the batch runs to the end: the review unit holding the pair passes its gates",
          code == C.OK and "batch Q-1 complete" in out and "Art. 6" in d and "Art. 5" not in d
          and "drained" not in d and "tape" not in d)
    done = C.batch_chain(C.parse_record(mpath), C._master_rel(mpath))[0]
    pr = done[1]["record"] if len(done) == 3 else C.Record({}, [])
    dup = [u for u in pr.units if C._norm(u.get("disposition")) == C._norm(C.DUPL)]
    tgt = [u for u in pr.units if u["lines"] == "5-5"]
    check("Q2: the part record's `of:` names the kept unit by the part record's own id",
          len(dup) == 1 and len(tgt) == 1 and dup[0].get("of") == tgt[0]["id"] != kept)
    cu = lambda i, ln, d, **kw: dict(id=i, lines=f"{ln}-{ln}", span=f"{ln}:1-{ln}:9", disposition=d, **kw)
    cut = C._cut_file("c.md", [cu("1", 3, C.OBS, edit="x"), cu("2", 5, C.DEFECT, conflicts="1"),
                               cu("3", 7, C.OBS)], 1, 8, 1, 200)
    check("Q2: the cut keeps a `conflicts:` pair in one range too (judgement cap 1)",
          [e for e, _, _ in cut] == [("c.md", (6, 8)), ("c.md", (1, 5))])

    # Q2b: --carry-from re-numbers: a carried `of:` names the same unit by the new record's id —
    # a verbatim id would name another unit, and the kept-unit check would guard the wrong one
    write("a.md", "# A\n\nAlpha holds.\n")
    write("b.md", "# B\n\nBeta is cached.\n\nBeta is cached.\n\nGamma holds.\n")
    commit("feat: a b", "a.md", "b.md")
    run("record-init", "--pass-kind", "document", "--unit-id", "W1", "--scope", "a.md", "b.md",
        "--out", ".consolidation/w1.record")
    w1 = C.parse_record(".consolidation/w1.record")
    wkept = [u for u in w1.units if u["file"] == "b.md" and u["lines"] == "3-3"][0]["id"]
    fill(".consolidation/w1.record", lambda u: {"disposition": C.DUPL, "basis": "duplicates the cache rule", "of": wkept}
         if u["file"] == "b.md" and u["lines"] == "5-5" else {"disposition": C.STILL, "basis": "holds"})
    check("Q2b premise: the wide record passes record-check",
          run("record-check", "--record", ".consolidation/w1.record")[0] == C.OK)
    code, out = run("record-init", "--pass-kind", "document", "--unit-id", "W2", "--scope", "b.md",
                    "--carry-from", ".consolidation/w1.record", "--out", ".consolidation/w2.record")
    w2 = C.parse_record(".consolidation/w2.record")
    wd = [u for u in w2.units if u["lines"] == "5-5"]
    wk = [u for u in w2.units if u["lines"] == "3-3"]
    check("Q2b: a carried `of:` names the kept unit by the new record's id",
          code == C.OK and wd and wk and wd[0].get("of") == wk[0]["id"] != wkept)
    code, out = run("record-init", "--pass-kind", "document", "--unit-id", "W3", "--scope", "b.md:4-7",
                    "--carry-from", ".consolidation/w1.record", "--out", ".consolidation/w3.record")
    w3 = C.parse_record(".consolidation/w3.record")
    wd = [u for u in w3.units if u["lines"] == "5-5"]
    check("Q2b: a unit whose `of:` target the new scope leaves out is left uncarried",
          code == C.OK and wd and not wd[0].get("disposition") and not wd[0].get("of"))

    # C1: `of:` and `conflicts:` name a unit of the same file — ids are record-wide, so a real id
    # of another file of the record must still be refused (a duplicate across documents is O5's)
    def c1_bad(mutate):
        rr = C.parse_record(".consolidation/w1.record")
        mutate(rr, {(u["file"], u["lines"]): u for u in rr.units})
        C.write_record(rr, ".consolidation/w1-c1.record")
        return run("record-check", "--record", ".consolidation/w1-c1.record")

    alpha = [u for u in w1.units if u["file"] == "a.md" and u["lines"] == "3-3"][0]["id"]
    code, out = c1_bad(lambda rr, at: at[("b.md", "5-5")].update({"of": alpha}))
    check("C1: `of:` naming a real unit of another file of the record is refused",
          code == C.FAIL and f"`of: {alpha}` names no other unit of b.md in this record" in out)
    code, out = c1_bad(lambda rr, at: at[("b.md", "7-7")].update(
        {"disposition": C.DEFECT, "basis": "gamma.py:1 says it does not hold", "conflicts": alpha}))
    check("C1: `conflicts:` naming a real unit of another file of the record is refused",
          code == C.FAIL and f"`conflicts: {alpha}` names no other unit of b.md in this record" in out)


# ----- end of v22 b2


def _v23_lexer_tests():
    """v23 S1 findings: every multi-line literal consumer that reaches the end of its input
    without the terminator ends certainty (B10 extended), and in the hash family a `<<` with
    a space is a left shift, not a heredoc."""
    U = LX.comment_units
    T = LX.code_tokens

    def unc(text, path):
        return LX.scan(text, path)[1].uncertain

    def spans(text, path):
        return [(u.sl, u.el) for u in U(text, path)]

    # --- v23-1: a literal that runs to the end of input hides the comment after it and is
    # never proved: code-invariance-check reports "cannot prove" and the suite decides
    check("v23-1: an unterminated JS template literal ends certainty",
          U("const s = `abc\n\ndrop();\n// after\n", "a.js") == []
          and unc("const s = `abc\n\ndrop();\n// after\n", "a.js") is True)
    check("v23-1: an unterminated C# verbatim string ends certainty",
          U('var s = @"abc\n\ndrop();\n// after\n', "A.cs") == []
          and unc('var s = @"abc\n\ndrop();\n// after\n', "A.cs") is True)
    check("v23-1: an unterminated C# triple-quoted string ends certainty",
          U('var s = """abc\n\ndrop();\n// after\n', "A.cs") == []
          and unc('var s = """abc\n\ndrop();\n// after\n', "A.cs") is True)
    check("v23-1: an unterminated Rust raw string ends certainty",
          U('const s = r#"abc\n\ndrop();\n// after\n', "a.rs") == []
          and unc('const s = r#"abc\n\ndrop();\n// after\n', "a.rs") is True)
    check("v23-1: an unterminated SQL dollar-quoted string ends certainty",
          U("SELECT $$abc\n\ndrop();\n-- after\n", "q.sql") == []
          and unc("SELECT $$abc\n\ndrop();\n-- after\n", "q.sql") is True)
    check("v23-1: an unterminated PHP heredoc ends certainty",
          U("<?php\n$s = <<<EOF\nabc\n\ndrop();\n// after\n", "a.php") == []
          and unc("<?php\n$s = <<<EOF\nabc\n\ndrop();\n// after\n", "a.php") is True)
    check("v23-1: an unterminated Go backtick string ends certainty",
          U("s := `abc\n\ndrop();\n// after\n", "a.go") == []
          and unc("s := `abc\n\ndrop();\n// after\n", "a.go") is True)
    check("v23-1: an unterminated PowerShell here-string ends certainty",
          U("$s = @'\nabc\n\ndrop\n# after\n", "a.ps1") == []
          and unc("$s = @'\nabc\n\ndrop\n# after\n", "a.ps1") is True)
    check("v23-1: the further literal consumers flag the same way",
          all(U(t, p) == [] and unc(t, p) is True for t, p in (
              ('var s = $"""abc\n\ndrop();\n// after\n', "A.cs"),        # raw interpolated
              ('var s = $@"abc\n\ndrop();\n// after\n', "A.cs"),         # verbatim interpolated
              ('val s = "${x}', "a.kt"),                                 # kotlin template hole
              ('let s = "a \\(b', "a.swift"),                            # swift interpolation
              ('String s = """abc\n\ndrop();\n// after\n', "A.java"),    # java triple quote
              ('const char* s = R"(abc\n\ndrop();\n// after\n', "a.c"),  # C raw string
              ("s = [==[abc\n\ndrop()\n-- after\n", "a.lua"),            # lua long bracket
              ("a { b: url(http://x\n\n/* after */\n", "a.scss"),        # unquoted url(
              ('<?php\n$s = "abc\n\ndrop();\n// after\n', "a.php"),      # php multi-line string
              ('(defparameter s "abc\n\ndrop\n; after\n', "a.lisp"),     # lisp multi-line string
              ("echo 'abc\n\necho def\n# after\n", "a.sh"),              # shell quote
              ("cat <<EOF\nabc\n# after\n", "a.sh"),                     # shell heredoc
              ("RUN <<EOF\n# in\nCOPY x y\n", "Dockerfile"),             # Dockerfile heredoc
              ("x = <<EOS\n# in\ny = 1\n", "a.rb"),                      # ruby heredoc
              ('key: "line one\n  # in\n', "a.yaml"),                    # yaml quoted scalar
              ("buildPhase = ''\n  # in\n", "a.nix"),                    # nix string
              ('<a><![CDATA[x\n\n<!-- after -->\n', "a.xml"))))          # CDATA section
    check("v23-1: an unterminated literal is never proved, the suite is asked",
          all(T(t, p)[1] is False for t, p in (
              ("const s = `abc\n\ndrop();\n// after\n", "a.js"),
              ('var s = @"abc\n\ndrop();\n// after\n', "A.cs"),
              ('String s = """abc\n\ndrop();\n// after\n', "A.java"),
              ("SELECT $$abc\n\ndrop();\n-- after\n", "q.sql"),
              ("<?php\n$s = <<<EOF\nabc\n\ndrop();\n// after\n", "a.php"))))
    check("v23-1: every terminated counterpart stays exactly as certain as before",
          all(unc(t, p) is False and len(U(t, p)) == 1 and LX.scan(t, p)[2] is c for t, p, c in (
              ("const s = `abc`;\n// real\n", "a.js", True),
              ('var s = @"abc";\n// real\nFoo();\n', "A.cs", True),
              ('var s = """abc""";\n// real\nFoo();\n', "A.cs", True),
              ('var s = $"""abc""";\n// real\nFoo();\n', "A.cs", True),
              ('var s = $@"abc";\n// real\nFoo();\n', "A.cs", True),
              ('val s = "${x}"\n// real\n', "a.kt", False),
              ('let s = "a \\(b) c"\n// real\n', "a.swift", False),
              ('const s: &str = r#"abc"#;\n// real\n', "a.rs", False),
              ("SELECT $$abc$$;\n-- real\n", "q.sql", True),
              ("<?php\n$s = <<<EOF\nabc\nEOF;\n// real\n", "a.php", True),
              ("s := `abc`\n// real\n", "a.go", False),
              ("$s = @'\nabc\n'@\n# real\n", "a.ps1", False),
              ('String s = """abc""";\n// real\n', "A.java", True),
              ('const char* s = R"(abc)";\n// real\n', "a.c", True),
              ("s = [==[abc]==]\n-- real\n", "a.lua", False),
              ("a { b: url(http://x) }\n/* real */\n", "a.scss", False),
              ('(defparameter s "abc")\n; real\n', "a.lisp", False),
              ("echo 'abc'\n# real\n", "a.sh", False),
              ("cat <<EOF\nabc\nEOF\n# real\n", "a.sh", False),
              ("RUN <<EOF\n# in\nEOF\n# real\n", "Dockerfile", False),
              ("x = <<EOS\n# in\nEOS\n# real\n", "a.rb", False),
              ('key: "line one\n  two"\n# real\n', "a.yaml", False),
              ("buildPhase = ''\n  # in\n'';\n# real\n", "a.nix", False))))

    # --- v23-2: in the hash family the delimiter must follow `<<` immediately, as Ruby and
    # Perl require, so a left shift with spaces opens no phantom heredoc
    check("v23-2: a ruby left shift with spaces opens no phantom heredoc, the comment after is a unit",
          spans("items << new_item\nx = 1\n\n# note\n", "a.rb") == [(4, 4)]
          and spans("a = b << c\n# note\n", "a.rb") == [(2, 2)])
    check("v23-2: a negative shifted value is not a heredoc either",
          spans("items << -1\n# note\n", "a.rb") == [(2, 2)])
    check("v23-2: an R superassignment with a space opens no phantom heredoc",
          spans("x <<- foo\n# note\n", "a.r") == [(2, 2)])
    check("v23-2: a ruby squiggly heredoc still hides its body",
          spans("s = <<~DOCS\n  # heading\nDOCS\n# real\n", "a.rb") == [(4, 4)])
    check("v23-2: a perl quoted heredoc still hides its body, with and without the `;` terminator",
          spans('print <<"EOF";\n# in\nEOF\n# real\n', "a.pl") == [(4, 4)]
          and spans('print <<"EOF";\n# in\nEOF;\n# real\n', "a.pl") == [(4, 4)])
    check("v23-2: a ruby dashed heredoc still hides its indented body and terminator",
          spans("s = <<-EOS\n  # in\n  EOS\n# real\n", "a.rb") == [(4, 4)])
    check("v23-2: a heredoc on a line that also holds a shift still opens",
          spans("q << s\nx = <<EOS\n# in\nEOS\n# real\n", "a.rb") == [(5, 5)])


def _v23_lexpin_tests():
    """Pins for lexer certainty guards no other check reaches: SQL `--` without a space, an
    interpolation hole that runs to the end after its string already ended at a newline
    (Kotlin ${, Swift \\(), and `/` after `)`."""
    U = LX.comment_units

    def unc(text, path):
        return LX.scan(text, path)[1].uncertain

    def cert(text, path):
        return LX.scan(text, path)[2]

    def spans(text, path, fine=False):
        return [(u.sl, u.el) for u in U(text, path, fine=fine)]

    # --- `--` with no space after it is arithmetic in the SQL dialect, never a comment, and
    # the file stops being certain; `-- ` with the space still opens one
    check("v23-40: SQL `5--1` is no comment and ends certainty, `-- real` after it is a unit",
          spans("SELECT 5--1;\n-- real comment\n", "q.sql", fine=True) == [(2, 2)]
          and unc("SELECT 5--1;\n-- real comment\n", "q.sql") is True
          and cert("SELECT 5--1;\n-- real comment\n", "q.sql") is False)
    check("v23-40: the spaced twin `5 - -1` stays certain with the same unit",
          spans("SELECT 5 - -1;\n-- real comment\n", "q.sql", fine=True) == [(2, 2)]
          and unc("SELECT 5 - -1;\n-- real comment\n", "q.sql") is False
          and cert("SELECT 5 - -1;\n-- real comment\n", "q.sql") is True)

    # --- the string ends at its newline, so only the hole scan reaches the end of input
    check("v23-41: a Kotlin ${ hole left open after a newline-ended string ends certainty",
          unc('val s = "${foo\n// after\nval x = 1\n', "a.kt") is True)
    check("v23-41: the closed Kotlin hole twin stays certain",
          unc('val s = "${foo}"\n// after\nval x = 1\n', "a.kt") is False)
    check("v23-42: a Swift \\( hole left open after a newline-ended string ends certainty",
          unc('let s = "\\(foo\n// after\nlet x = 1\n', "a.swift") is True)
    check("v23-42: the closed Swift hole twin stays certain",
          unc('let s = "\\(foo)"\n// after\nlet x = 1\n', "a.swift") is False)

    # --- after `)` a `/` may be division or a regex literal: undecidable here
    check("v23-43: `/` after `)` in JS ends certainty",
          unc("x = (a) / 2;\n// real\n", "a.js") is True
          and cert("x = (a) / 2;\n// real\n", "a.js") is False
          and spans("x = (a) / 2;\n// real\n", "a.js") == [(2, 2)])
    check("v23-43: `/` after an identifier stays certain",
          unc("x = a / 2;\n// real\n", "a.js") is False
          and cert("x = a / 2;\n// real\n", "a.js") is True
          and spans("x = a / 2;\n// real\n", "a.js") == [(2, 2)])

    # --- a comment or ANSI-C string with no closer hides the rest of the file: no unit, and
    # the file stops being certain; each terminated twin keeps its unit and stays certain
    check("v23-44: an unterminated shell $' string hides the comment after it and ends certainty",
          spans("echo $'abc\n\necho def\n# after\n", "a.sh") == []
          and unc("echo $'abc\n\necho def\n# after\n", "a.sh") is True)
    check("v23-44: the closed shell $' twin stays certain with its unit",
          spans("echo $'abc'\n# real\n", "a.sh") == [(2, 2)]
          and unc("echo $'abc'\n# real\n", "a.sh") is False)
    check("v23-45: an unterminated Razor @* comment is no unit and ends certainty",
          spans("@* note\n<p>y</p>\n", "a.cshtml") == []
          and unc("@* note\n<p>y</p>\n", "a.cshtml") is True)
    check("v23-45: the closed Razor @* *@ twin stays certain with its unit",
          spans("@* note *@\n<p>y</p>\n", "a.cshtml") == [(1, 1)]
          and unc("@* note *@\n<p>y</p>\n", "a.cshtml") is False)
    check("v23-46: an unterminated ASP.NET <%-- comment is no unit and ends certainty",
          spans("<p>x</p>\n<%-- note\n<p>y</p>\n", "a.aspx") == []
          and unc("<p>x</p>\n<%-- note\n<p>y</p>\n", "a.aspx") is True)
    check("v23-46: the closed ASP.NET <%-- --%> twin stays certain with its unit",
          spans("<p>x</p>\n<%-- note --%>\n<p>y</p>\n", "a.aspx") == [(2, 2)]
          and unc("<p>x</p>\n<%-- note --%>\n<p>y</p>\n", "a.aspx") is False)
    check("v23-47: an unterminated markup <!-- comment is no unit and ends certainty",
          spans("<p>x</p>\n<!-- note\n<p>y</p>\n", "a.html") == []
          and unc("<p>x</p>\n<!-- note\n<p>y</p>\n", "a.html") is True)
    check("v23-47: the closed markup <!-- --> twin stays certain with its unit",
          spans("<p>x</p>\n<!-- note -->\n<p>y</p>\n", "a.html") == [(2, 2)]
          and unc("<p>x</p>\n<!-- note -->\n<p>y</p>\n", "a.html") is False)


# ----- end of v23 lexer


def _v23_runner_tests(dirs):
    """v23 S2 findings: the runner's robustness fixes. Creates its own repos with new_repo()
    and appends them to dirs."""
    # --- v23-3: a NUL inside a commit body misaligns the -z field grid of `git log`; the parse
    # dies loud instead of silently skipping every record after the NUL
    def stream(*records):
        return "".join(f"{sha}\0{par}\0{subj}\0{body}\0" for sha, par, subj, body in records).encode()

    sha1_, sha2_, sha3_ = "a" * 40, "b" * 40, "c" * 40
    healthy = stream((sha1_, "", "first", "body one\n"), (sha2_, sha1_, "second", "body two\n"))
    nulled = stream((sha1_, "", "first", "body one\n"),
                    (sha2_, sha1_, "second", "body two carries a \0 NUL inside\n"),
                    (sha3_, sha2_, "third", "body three\n"))
    real_git, raised, parsed = C.git, None, None
    try:
        C.git = lambda *a, **k: nulled
        try:
            C.commit_log("HEAD")
        except C.Die as e:
            raised = e
        C.git = lambda *a, **k: healthy
        parsed = C.commit_log("HEAD")
    finally:
        C.git = real_git
    check("v23-3: a NUL inside a commit body dies loud, the commits after it are never dropped",
          isinstance(raised, C.Die) and "misaligned" in str(raised) and "NUL" in str(raised))
    check("v23-3: a well-formed stream with its empty trailing chunk parses in full",
          [x[0] for x in parsed] == [sha1_, sha2_] and [x[1] for x in parsed] == ["first", "second"])

    # --- v23-4: a rename in `git status` names two paths; status_entries keeps both sides of it,
    # and batch-next judges both, never the `a -> b` composite, which matches no file
    dirs.append(new_repo("cons_selftest_v23st_"))
    write("a.py", "a = 1\n")
    write("b.py", "b = 1\n")
    write("ol d.py", "old = 1\n")
    write("it's.py", "q = 1\n")
    commit("base")
    sh("git", "mv", "a.py", "c.py")
    sh("git", "mv", "ol d.py", "ne w.py")
    write("b.py", "b = 2\n")
    write("it's.py", "q = 2\n")
    write("café.py", "n = 1\n")
    # a user config that turns rename detection and the untracked listing off must not change it
    sh("git", "config", "status.renames", "false")
    sh("git", "config", "status.showUntrackedFiles", "no")
    check("v23-4: status_entries gives a rename as one entry with both sides, every name exactly as stored "
          "(a space, a quote, a non-ASCII letter), and the modified and untracked files beside it, "
          "whatever status.renames and status.showUntrackedFiles say",
          sorted(C.status_entries()) == sorted([("R ", "c.py", "a.py"), ("R ", "ne w.py", "ol d.py"),
                                                (" M", "b.py", None), (" M", "it's.py", None),
                                                ("??", "café.py", None)]))

    def judge(u):
        return {"disposition": C.REGEN, "basis": "restates the call below"}

    dirs.append(new_repo("cons_selftest_v23ren_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n.consolidation.json\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", "a.py")
    fill(str(next(Path(".consolidation").glob("B-1-*.batch"))), judge)
    sh("git", "mv", "a.py", "z.py")
    code, out = run("batch-next", "--batch", "B-1")
    check("v23-4: a renamed scope file stops the batch under both its names, never the composite",
          code == C.FAIL and "the tree differs" in out and "a.py" in out and "z.py" in out
          and "a.py -> z.py" not in out)

    # --- v23-5: the stale-lock unlink spares a fresh lock that another waiter just won
    lockfile = Path("intake.md.lock")
    lockfile.write_text("1")
    st = lockfile.stat()
    check("v23-5: an unchanged lock file is still the stale one, the unlink may proceed",
          C._lock_still_stale(lockfile, st))
    lockfile.write_text("12345")
    # the rewrite moves the mtime too: put it back so the size is the only thing that differs
    os.utime(lockfile, ns=(st.st_atime_ns, st.st_mtime_ns))
    check("v23-5: a lock whose size changed under the stat is spared",
          not C._lock_still_stale(lockfile, st))
    st2 = lockfile.stat()
    os.utime(lockfile, (time.time() - 5, time.time() - 5))
    check("v23-5: a lock whose mtime moved under the stat is spared",
          not C._lock_still_stale(lockfile, st2))
    lockfile.unlink()
    check("v23-5: a lock that vanished under the stat is spared",
          not C._lock_still_stale(lockfile, st2))
    t = time.time()
    lockfile.write_text("999")
    os.utime(lockfile, (t - 200, t - 200))
    acquired = False
    with C.intake_lock("intake.md"):
        acquired = lockfile.exists()
    check("v23-5: a stale lock is unlinked and the intake acquired",
          acquired and not lockfile.exists())
    lockfile.write_text("other")
    won = None
    try:
        with C.intake_lock("intake.md", timeout=0.5):
            pass
    except C.Die as e:
        won = e
    check("v23-5: a fresh lock held by another session is never unlinked, the acquire times out loud",
          isinstance(won, C.Die) and "intake is locked" in str(won) and lockfile.exists()
          and lockfile.read_text() == "other")
    lockfile.unlink()

    # --- v23-6: a BOM is an editor artifact: the same logical config with and without one
    # hashes alike, and a loosening still fails config-bound-check (R-gates 5)
    plain = '{"intake_path": "intake.md", "REMOVED_LINE_CAP": 150}'
    a = C._config_from_text(plain, "plain", tracked=True)
    b = C._config_from_text("﻿" + plain, "bom", tracked=True)
    check("v23-6: the same config with and without a BOM hashes to one config_sha",
          a["_config_sha"] == b["_config_sha"] != "" and a["REMOVED_LINE_CAP"] == 150)

    dirs.append(new_repo("cons_selftest_v23bom_"))
    write("a.py", "# note\nx = 1\n")
    write("intake.md", "")
    write(".gitignore", "intake.md\n.consolidation.json\n")
    write(".consolidation.json", plain)
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "B6", "--scope", "a.py",
        "--out", ".consolidation/b6.record")
    Path(".consolidation.json").write_bytes(b"\xef\xbb\xbf" + plain.encode("utf-8"))
    stamped = C.parse_record(".consolidation/b6.record").header["config_sha"]
    now = C.load_config()
    check("v23-6: a record built on the plain config binds its BOM'd twin",
          now["_config_sha"] == stamped
          and run("config-bound-check", "--record", ".consolidation/b6.record")[0] == C.OK)
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVED_LINE_CAP": 9999}')
    code, out = run("config-bound-check", "--record", ".consolidation/b6.record")
    check("v23-6: a loosening still fails config-bound-check, naming the value",
          code == C.FAIL and "REMOVED_LINE_CAP" in out)

    # --- v23-7: batch-init --out outside .consolidation/ refuses before anything is written
    code, out = run("batch-init", "--pass-kind", "comment", "--batch-id", "B-7", "--scope", "a.py",
                    "--out", "elsewhere/B-7.batch")
    check("v23-7: batch-init --out outside .consolidation/ refuses, saying where a master lives",
          code == C.FAIL and "a master record lives under .consolidation/" in out
          and not Path("elsewhere/B-7.batch").exists())
    check("v23-7: batch-init --out inside .consolidation/ still writes the master",
          run("batch-init", "--pass-kind", "comment", "--batch-id", "B-7", "--scope", "a.py",
              "--out", ".consolidation/B-7-here.batch")[0] == C.OK)
    check("v23-7: record-init still honors --out anywhere",
          run("record-init", "--pass-kind", "comment", "--unit-id", "R7", "--scope", "a.py",
              "--out", "notes/r7.record")[0] == C.OK)

    # --- v23-8: escalate --line on a file absent everywhere still appends, and warns loud
    code, out = run("escalate", "--file", "gone.py", "--line", "1", "--kind", "suspected-defect",
                    "--divergence", "the flush order", "--intake", "intake.md")
    entries = [l for l in read("intake.md").splitlines() if "`gone.py:1`" in l]
    warn = out.split("warn:")[-1] if "warn:" in out else ""
    check("v23-8: the entry is appended, binding by line only",
          code == C.OK and len(entries) == 1 and "fingerprint=" not in entries[0])
    check("v23-8: the total-absence warn names the file and the line-only binding",
          "gone.py" in warn and "binds by line" in warn)

    # --- v23-9: a record materialized under the v2 begin marker still parses (old commits)
    dirs.append(new_repo("cons_selftest_v23rec_"))
    write("a.py", "# note\nx = 1\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "OM", "--scope", "a.py",
        "--out", ".consolidation/om.record")
    rec = C.parse_record(".consolidation/om.record")
    write("old.msg", C.commit_message(rec).replace(C.RECORD_BEGIN, C.RECORD_BEGIN_V2))
    sh("git", "commit", "-q", "--allow-empty", "-F", "old.msg")
    old_sha = C.head_sha()
    old_rec = C.record_from_commit(old_sha)
    check("v23-9: a commit-message record with the v2 begin marker still materializes",
          old_rec.header["unit_id"] == "OM" and len(old_rec.units) == 1
          and old_rec.units[0]["file"] == "a.py" and not old_rec.problems
          and len(C._materialized_records_of(old_sha)) == 1)
    write("new.msg", C.commit_message(rec))
    sh("git", "commit", "-q", "--allow-empty", "-F", "new.msg")
    check("v23-9: the v3 marker the writer emits parses back, and the header reads record v3",
          C.record_from_commit(C.head_sha()).header["unit_id"] == "OM"
          and C.render_record(rec).splitlines()[0] == "# consolidation record v3")

    # --- v23-10: the dead code is gone (the eols no-op and the K2 comment pin no behavior)
    check("v23-10: enumerate_scope reads the baseline only — the never-passed worktree branch is gone",
          "worktree" not in C.enumerate_scope.__code__.co_varnames)

    # --- v23-11: unit-tree-check judges a rename by both its sides — a record-dir new side
    # must not hide the old side's deletion outside the record dir
    dirs.append(new_repo("cons_selftest_v23utc_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n.consolidation.json\n")
    write(".consolidation.json", '{"intake_path": "intake.md"}')
    write("a.py", "x = 1\n")
    write(".consolidation/keep", "")
    commit("base")
    sh("git", "mv", "a.py", ".consolidation/moved.record")
    check("v23-11 (premise): git status reports the move as one rename, not an add and a delete",
          [C.status_line(*e) for e in C.status_entries()] == ["R  a.py -> .consolidation/moved.record"])
    code, out = run("unit-tree-check")
    check("v23-11: a rename into the record dir fails the unit tree check on its old side",
          code == C.FAIL and "a.py" in out and ".consolidation/moved.record" in out)
    sh("git", "mv", ".consolidation/moved.record", "a.py")
    code, out = run("unit-tree-check")
    check("v23-11: a tree clean outside the record dir passes", code == C.OK and "working tree clean" in out)


def _v23_wave1_tests(dirs):
    """v23 S3: record-shard's shard count, script-owned unit ids, the review pack's ADR list, and pins
    of the ADR, judgement-file, later-commit and carry-from refusals. Creates its own repos with
    new_repo() and appends them to dirs."""
    def judge(u):
        if "restates" in u["preview"]:
            return {"disposition": C.REGEN, "basis": "restates the call below"}
        return {"disposition": C.STILL, "basis": "carries a reason the code cannot state"}

    def base_repo(prefix, cfg='{"intake_path": "intake.md"}'):
        dirs.append(new_repo(prefix))
        write("intake.md", "")
        write(".gitignore", "intake.md\n")
        write(".consolidation.json", cfg)

    # --- v23-12: record-shard refuses a shard count below 1 instead of coercing it to 1
    base_repo("cons_selftest_v23shd_")
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "SH", "--scope", "a.py", "b.py",
        "--out", ".consolidation/sh.record")
    shards = lambda: sorted(p.name for p in Path(".consolidation").glob("sh.record.shard-*"))
    code, out = run("record-shard", "--record", ".consolidation/no-such.record", "--shards", "0")
    check("v23-12: the --shards refusal comes before the record is read — a missing record still reports it",
          code == C.FAIL and "--shards 0: a shard count is 1 or more" in out)
    refusals = [run("record-shard", "--record", ".consolidation/sh.record", "--shards", n) for n in ("0", "-2")]
    check("v23-12: record-shard --shards 0 or below refuses, naming the flag, and writes no shard",
          all(code == C.FAIL and "--shards" in out and "1 or more" in out for code, out in refusals)
          and "--shards 0" in refusals[0][1] and "--shards -2" in refusals[1][1] and not shards())
    code, out = run("record-shard", "--record", ".consolidation/sh.record", "--shards", "1")
    check("v23-12: --shards 1 still writes one shard holding every file",
          code == C.OK and shards() == ["sh.record.shard-1", "sh.record.shard-1.j"] and "a.py, b.py" in out)
    for p in Path(".consolidation").glob("sh.record.shard-*"):
        p.unlink()
    code, out = run("record-shard", "--record", ".consolidation/sh.record", "--shards", "9")
    check("v23-12: --shards above the file count is clamped to it, and above 6 warns",
          code == C.OK and len([s for s in shards() if s.endswith(".j")]) == 2 and "beyond 6" in out)

    # --- v23-13: a unit id is the number record-init wrote; a hand-edited one is refused where
    # the ids are ordered, naming the unit and the record, never a ValueError
    check("v23-13: unit_number reads a record-init id and refuses any other",
          C.unit_number("12", "r") == 12
          and all(isinstance(_raises(C.unit_number, bad, "record R"), C.Die) for bad in ("x1", "", "1.0", "١"))
          and "'x1'" in str(_raises(C.unit_number, "x1", "record R"))
          and "record R" in str(_raises(C.unit_number, "x1", "record R")))
    base_repo("cons_selftest_v23uid_")
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n# restates poll\npoll()\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "UID", "--scope", "p.py",
        "--out", ".consolidation/uid.record")
    fill(".consolidation/uid.record", lambda u: {"disposition": C.ADR, "basis": "polling: the vendor drops retries",
                                                 "adr_title": "Polling", "adr_text": "## Decision\n\nPoll."}
         if "polling" in u["preview"] else judge(u))
    write(".consolidation/uidx.record", read(".consolidation/uid.record").replace("@@unit 1\n", "@@unit x1\n"))
    code, out = run("replay-check", "--record", ".consolidation/uidx.record")
    check("v23-13: replay-check on a hand-edited unit id refuses it by name and record, no ValueError",
          code == C.FAIL and "unit 'x1' of record UID" in out and "script-owned" in out and "ValueError" not in out)
    code, out = run("record-check", "--record", ".consolidation/uidx.record")
    check("v23-13: record-check still refuses the hand-edited id against the enumeration",
          code == C.FAIL and "unit x1: not a unit of the declared scope" in out)
    run("record-shard", "--record", ".consolidation/uid.record", "--shards", "1")
    write(".consolidation/uid.record", read(".consolidation/uid.record") + "@@unit zz\nfile: p.py\nlines: 3-3\n")
    code, out = run("record-merge", "--record", ".consolidation/uid.record")
    check("v23-13: record-merge with a hand-added unit id no shard covers refuses it by name, no ValueError",
          code == C.FAIL and "unit 'zz' of .consolidation/uid.record" in out and "ValueError" not in out)

    # --- v23-14: a hand-written `adr:` naming the path another unit renders is refused, naming
    # both units; the review pack, which renders a refused record too, lists the path once
    base_repo("cons_selftest_v23adr_")
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n"
                  "# this also polls: the vendor drops retries\npoll()\n")
    commit("base")
    f1 = "docs/adr/0001-polling-over-webhooks.md"

    def adr_pair(u):
        if "chose polling" in u["preview"]:
            return {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
                    "adr_title": "Polling over webhooks", "adr_text": "## Decision\n\nPoll."}
        return {"disposition": C.ADR, "basis": "the same polling decision", "adr": f1}
    run("record-init", "--pass-kind", "comment", "--unit-id", "AP", "--scope", "p.py", "--out", ".consolidation/ap.record")
    fill(".consolidation/ap.record", adr_pair)
    code, out = run("record-check", "--record", ".consolidation/ap.record")
    check("v23-14: a hand-written `adr:` naming the path another unit renders is refused, naming both units",
          code == C.FAIL and f"unit 2 (p.py:3-3): `adr: {f1}` names {f1}, the ADR unit 1 renders" in out)
    run("review-pack", "--record", ".consolidation/ap.record", "--no-gate", "--out", ".consolidation/ap.review.md")
    added = read(".consolidation/ap.review.md").split("## ADR files added", 1)[-1]
    check("v23-14: the review pack of the refused record lists the path both name once",
          added.count(f1) == 1)

    # --- v23-15 (pin): the hand-written file in the way of the rendered ADR is refused at apply
    run("record-init", "--pass-kind", "comment", "--unit-id", "AQ", "--scope", "p.py", "--out", ".consolidation/aq.record")
    fill(".consolidation/aq.record", lambda u: adr_pair(u) if "chose polling" in u["preview"] else judge(u))
    write(f1, "# a hand-written ADR\n")
    code, out = run("apply", "--record", ".consolidation/aq.record")
    check("v23-15: a hand-written ADR in the way of the path a unit renders refuses apply, nothing written",
          code == C.FAIL and "in the way of the ADR unit" in out and read(f1) == "# a hand-written ADR\n"
          and read("p.py").startswith("# we chose polling"))
    os.remove(f1)
    run("apply", "--record", ".consolidation/aq.record")
    sh("git", "add", "p.py", f1)
    sh("git", "commit", "-q", "-F", ".consolidation/aq.commit-msg")
    # a hand-written `adr:` naming an ADR the baseline already holds: the unit adds no ADR
    write("q.py", "# we chose LIFO eviction: the cache serves the newest keys\nevict()\n")
    commit("feat: q", "q.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "OLD", "--scope", "q.py", "--out", ".consolidation/old.record")
    fill(".consolidation/old.record", lambda u: {"disposition": C.ADR, "basis": "LIFO eviction: newest keys",
                                                 "adr": f1})
    run("apply", "--record", ".consolidation/old.record")
    sh("git", "add", "q.py")
    sh("git", "commit", "-q", "-F", ".consolidation/old.commit-msg")
    code, out = run("replay-check", "--record-from-commit", "HEAD")
    check("v23-15: a hand-written `adr:` naming an ADR that exists at the baseline fails replay-check",
          code == C.FAIL and f"the ADR {f1} is not added by this review unit" in out)
    # in a batch: one review unit's hand-written `adr:` naming the path another renders is refused
    # by the master record's gate, before any unit runs
    base_repo("cons_selftest_v23adrb_", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n\n"
                  "# this also polls: the vendor drops retries\npoll()\n")
    one = commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "AB", "--scope", "p.py")
    fill(str(next(Path(".consolidation").glob("AB-*.batch"))), adr_pair)
    code, out = run("batch-next", "--batch", "AB")
    check("v23-15: in a batch the master's gate refuses the hand `adr:` naming another unit's rendered path",
          code == C.FAIL and f"unit 2 (p.py:4-4): `adr: {f1}` names {f1}, the ADR unit 1 renders" in out
          and C.head_sha() == one and not Path(f1).exists())

    # --- v23-16 (pin): the ADR slug is capped at 60 characters, no trailing separator, and an
    # adr_dir with no numbered ADR numbers from 0001
    check("v23-16: adr_slug caps at 60 and drops a separator the cap leaves at the end",
          C.adr_slug("x" * 100) == "x" * 60 and C.adr_slug("y" * 59 + " tail") == "y" * 59
          and C.adr_slug("!!! ---") == "")
    base_repo("cons_selftest_v23slug_")
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n")
    commit("base")
    title = "Polling over webhooks because the vendor drops every retry after the third attempt"

    def long_adr(u):
        return {"disposition": C.ADR, "basis": "polling: the vendor drops retries",
                "adr_title": title, "adr_text": "## Decision\n\nPoll."}
    run("record-init", "--pass-kind", "comment", "--unit-id", "SL", "--scope", "p.py", "--out", ".consolidation/sl.record")
    fill(".consolidation/sl.record", long_adr)
    slug = "polling-over-webhooks-because-the-vendor-drops-every-retry-a"
    code, out = run("apply", "--record", ".consolidation/sl.record", "--dry-run")
    check("v23-16: no adr_dir at the baseline: the rendered ADR is 0001 with the 60-character slug",
          code == C.OK and f"docs/adr/0001-{slug}.md" in out and len(slug) == 60)
    write("docs/adr/README.md", "the index\n")
    commit("docs: adr index", "docs/adr/README.md")
    run("record-init", "--pass-kind", "comment", "--unit-id", "SL2", "--scope", "p.py", "--out", ".consolidation/sl2.record")
    fill(".consolidation/sl2.record", long_adr)
    code, out = run("apply", "--record", ".consolidation/sl2.record", "--dry-run")
    check("v23-16: an adr_dir holding no numbered ADR numbers from 0001 too",
          code == C.OK and f"docs/adr/0001-{slug}.md" in out)

    # --- v23-17 (pin): adr_title needs a body and adr_text a title; the adr fields belong to the ADR disposition only
    write("r.py", "# restates go\ngo()\n")
    commit("feat: r", "r.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "AC", "--scope", "p.py", "r.py",
        "--out", ".consolidation/ac.record")
    rp = ".consolidation/ac.record"

    def adr_check(decide):
        fill(rp, lambda u: {"disposition": None, "basis": None, "adr": None, "adr_title": None, "adr_text": None})
        fill(rp, decide)
        return run("record-check", "--record", rp)

    poll = lambda f: (lambda u: f if "polling" in u["preview"] else judge(u))
    code, out = adr_check(poll({"disposition": C.ADR, "basis": "polling", "adr_title": "Poll the queue"}))
    check("v23-17: adr_title without adr_text is refused",
          code == C.FAIL and "`adr_title` requires `adr_text:` — the ADR body "
          "(## Context, ## Decision, ## Consequences)" in out)
    code, out = adr_check(poll({"disposition": C.ADR, "basis": "polling",
                                "adr_text": "## Decision\n\nPoll."}))
    check("v23-17: adr_text without adr_title is refused",
          code == C.FAIL and "`adr_text` requires `adr_title:` with at least one letter or digit" in out)
    code, out = adr_check(poll({"disposition": C.ADR, "basis": "polling", "adr_title": "!!! ---",
                                "adr_text": "## Decision\n\nPoll."}))
    check("v23-17: an adr_title with no letter or digit is refused",
          code == C.FAIL and "`adr_text` requires `adr_title:` with at least one letter or digit" in out)
    code, out = adr_check(lambda u: {"disposition": C.REGEN, "basis": "restates go()", "adr": "docs/adr/0009-go.md"}
                          if "restates" in u["preview"] else judge(u))
    check("v23-17: `adr:` on a non-ADR disposition is refused",
          code == C.FAIL and "`adr:` belongs to" in out)
    code, out = adr_check(lambda u: {"disposition": C.STILL, "basis": "a reason", "adr_title": "Go",
                                     "adr_text": "## Decision\n\nGo."} if "polling" in u["preview"] else judge(u))
    check("v23-17: adr_title and adr_text on a non-ADR disposition are refused",
          code == C.FAIL and "`adr_title` and `adr_text` belong to" in out)
    code, out = adr_check(poll(long_adr(None)))
    check("v23-17: the same record with a titled adr_text passes", code == C.OK)

    # --- v23-18 (pin): a judgement file that is not `@@ <id> <fingerprint>` blocks of judgement
    # fields is refused whole, and record-fill writes nothing
    base_repo("cons_selftest_v23j_")
    write("a.py", "# restates a\na()\n# a reason the code cannot say\nx = 1\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "J", "--scope", "a.py", "--out", ".consolidation/j.record")
    u1 = C.parse_record(".consolidation/j.record").units[0]
    before = read(".consolidation/j.record")
    head = f"@@ 1 {u1['fingerprint']}"

    def refused(text, why):
        write(".consolidation/bad.j", text)
        code, out = run("record-fill", "--record", ".consolidation/j.record", "--from", ".consolidation/bad.j")
        return code == C.FAIL and why in out and "nothing written" in out and read(".consolidation/j.record") == before

    check("v23-18: a line before the first block is refused",
          refused(f"disposition: still true\n{head}\ndisposition: still true\nbasis: x\n", "a line before the first"))
    check("v23-18: a block header without its fingerprint is refused",
          refused("@@ 1\ndisposition: still true\nbasis: x\n", "is no block header"))
    check("v23-18: an `id:` field in a block is refused as script-owned",
          refused(f"{head}\nid: 2\ndisposition: still true\nbasis: x\n", "script-owned field(s) id"))
    check("v23-18: an unknown key in a block is refused",
          refused(f"{head}\ndisposition: still true\nbasis: x\nverdict: keep\n", "unknown key 'verdict'"))
    check("v23-18: a continuation line outside any block field is refused",
          refused(f"{head}\ndisposition: still true\n| stray\nbasis: x\n", "outside any block"))
    check("v23-18: a blank line inside a multi-line field is refused",
          refused(f"{head}\ndisposition: condense\nedit:\n| one\n\n| two\nbasis: x\n", "a blank line ends the edit: block"))

    # --- v23-19 (pin): a later commit that is itself a consolidation leaves the batch complete
    base_repo("cons_selftest_v23late_", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    write("c.py", "# restates c\nc()\n")
    commit("base")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "L-1", "--scope", "a.py", "b.py")
    fill(str(next(Path(".consolidation").glob("L-1-*.batch"))), judge)
    code, out = run("batch-run", "--batch", "L-1")
    end = C.head_sha()
    run("record-init", "--pass-kind", "comment", "--unit-id", "LC", "--scope", "c.py", "--out", ".consolidation/lc.record")
    fill(".consolidation/lc.record", judge)
    run("apply", "--record", ".consolidation/lc.record")
    sh("git", "add", "c.py")
    sh("git", "commit", "-q", "-F", ".consolidation/lc.commit-msg")
    later_ok = (code == C.OK and "batch L-1 complete" in out and C.record_from_commit("HEAD").header["unit_id"] == "LC"
                and run("gate", "--unit", "--record-from-commit", "HEAD")[0] == C.OK)
    code, out = run("batch-status", "--batch", "L-1")
    code2, out2 = run("batch-next", "--batch", "L-1")
    check("v23-19: a consolidation commit after a complete batch is a later commit: complete, exit 0",
          later_ok and code == C.OK and code2 == C.OK
          and f"batch L-1 complete; 1 later commit(s) after {end[:7]}" in out
          and f"batch L-1 complete; 1 later commit(s) after {end[:7]}" in out2 and "undo:" not in out + out2)

    # --- v23-20 (pin): --carry-from carries by fingerprint: a unit whose text changed is left to classify
    base_repo("cons_selftest_v23carry_")
    write("a.py", "# restates a\na()\n# a reason the code cannot say\nx = 1\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "C1", "--scope", "a.py", "--out", ".consolidation/c1.record")
    fill(".consolidation/c1.record", judge)
    write("a.py", "# restates a\na()\n# a reason the code cannot say, reworded\nx = 1\n")
    commit("feat: reword", "a.py")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "C2", "--scope", "a.py",
                    "--carry-from", ".consolidation/c1.record", "--out", ".consolidation/c2.record")
    old = {u["preview"]: u for u in C.parse_record(".consolidation/c1.record").units}
    new = {u["preview"]: u for u in C.parse_record(".consolidation/c2.record").units}
    moved = new["# a reason the code cannot say, reworded"]
    check("v23-20: a unit whose fingerprint changed is not carried, the unchanged one is",
          code == C.OK and "carried the judgement of 1 of 2 unit(s)" in out
          and f"uncarried (classify these): unit(s) {moved['id']}" in out
          and moved["fingerprint"] != old["# a reason the code cannot say"]["fingerprint"]
          and not moved.get("disposition") and not moved.get("basis")
          and new["# restates a"]["disposition"] == C.REGEN)


def _v23_cover_tests(dirs):
    """v23 S4: standalone coverage of coverage-check, standing-rulings, target-set's output, the
    escalate flags, batch-init --floor-observed/--force and --target-set through batch-next and
    batch-run. Creates its own repos with new_repo() and appends them to dirs."""
    def judge(u):
        return {"disposition": C.REGEN, "basis": "restates the call below"}

    dirs.append(new_repo("cons_selftest_v23cov_"))
    write("intake.md", "")
    write(".gitignore", "intake.md\n")
    write(".consolidation.json", '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1}')
    write("a.py", "# restates a\na()\n# restates b\nb()\n")
    write("b.js", "// restates go\ngo();\n")
    commit("base")

    # --- v23-21: coverage-check, standalone
    run("record-init", "--pass-kind", "comment", "--unit-id", "CV", "--scope", "a.py", "b.js",
        "--out", ".consolidation/cv.record")
    code, out = run("coverage-check", "--record", ".consolidation/cv.record")
    check("v23-21: coverage-check passes a record whose entries are the enumeration, one to one",
          code == C.OK and "ok: 3 entr(ies) == the 3 unit(s) enumerated at the baseline, one to one" in out)
    rec = C.parse_record(".consolidation/cv.record")
    gone = rec.units.pop()
    C.write_record(rec, ".consolidation/cv-short.record")
    code, out = run("coverage-check", "--record", ".consolidation/cv-short.record")
    check("v23-21: coverage-check fails a record missing a unit, naming it",
          code == C.FAIL and f"FAIL unit {gone['id']} ({gone['file']}:{gone['lines']}) is missing from the record" in out)

    # --- v23-22: target-set prints the floor, the pass, the rule, then a file and its unit count per line
    code, out = run("target-set", "--pass-kind", "comment", "--scope", "a.py", "b.js")
    check("v23-22: target-set's output is the three header lines, then file<TAB>units",
          code == C.OK and out == "# floor: self-report\n# pass_kind: comment\n# unit_rule: comment\na.py\t2\nb.js\t1\n")

    # --- v23-23: standing-rulings, empty and listed; escalate --standing takes --ruling and --context
    code, out = run("standing-rulings", "--intake", "intake.md")
    check("v23-23: standing-rulings on an intake without one says condense is unavailable, exit 0",
          code == C.OK and out == "no standing rulings: condense is unavailable until the owner rules one\n")
    text = "Condense a restating comment to the one line that keeps its reason"
    code, out = run("escalate", "--standing", "--ruling-text", text, "--ruling", "abc1234",
                    "--context", "panel-3", "--intake", "intake.md")
    ident = (re.search(r"standing ruling recorded: (SR-[0-9a-f]{8})", out) or [None, None])[1]
    e = C.parse_intake_line(read("intake.md").splitlines()[-1])
    check("v23-23: escalate --standing records the ruling with the given --ruling and --context",
          code == C.OK and ident is not None and e["ref"] == f"standing-ruling:{ident}" and e["body"] == text
          and e["fields"] == {"kind": "standing-ruling", "state": "ruled", "ruling": "abc1234", "id": ident,
                              "context": "panel-3"})
    run("escalate", "--file", "a.py", "--line", "1", "--kind", "suspected-defect", "--divergence", "an open entry",
        "--intake", "intake.md")
    code, out = run("standing-rulings", "--intake", "intake.md")
    check("v23-23: standing-rulings lists each ruled standing ruling, and no other entry",
          code == C.OK and out == f"{ident}: {text}\n")

    # --- v23-24: escalate --anchor/--observed/--context, then --rule with --ruling/--ruling-text
    code, out = run("escalate", "--file", "docs/x.md", "--anchor", "retention", "--kind", "unverifiable-statement",
                    "--divergence", "retention follows a rule outside the repo", "--observed", "def5678",
                    "--context", "panel-4", "--intake", "intake.md")
    e = C.parse_intake_line(read("intake.md").splitlines()[-1])
    check("v23-24: escalate --anchor keys the entry file#anchor, with --observed and --context as given",
          code == C.OK and "escalated docs/x.md#retention" in out and e["ref"] == "docs/x.md#retention"
          and e["fields"] == {"kind": "unverifiable-statement", "state": "open", "observed": "def5678",
                              "context": "panel-4"})
    n = len(read("intake.md").splitlines())
    flags = [run("escalate", "--file", "docs/x.md", "--anchor", "other", "--kind", "unverifiable-statement",
                 "--divergence", "d", flag, "two words", "--intake", "intake.md")
             for flag in ("--observed", "--context", "--ruling")]
    check("v23-24: --observed, --context and --ruling with whitespace are refused, nothing appended",
          all(c == C.FAIL and "must not contain whitespace" in o for c, o in flags)
          and len(read("intake.md").splitlines()) == n)
    code, out = run("escalate", "--file", "docs/x.md", "--anchor", "retention", "--rule", "--intake", "intake.md")
    check("v23-24: --rule without --ruling-text is refused",
          code == C.FAIL and "--rule needs --ruling-text" in out)
    code, out = run("escalate", "--file", "docs/x.md", "--anchor", "retention", "--rule", "--ruling", "fed4321",
                    "--ruling-text", "keep: the DPA states it", "--intake", "intake.md")
    e = C.parse_intake_line(read("intake.md").splitlines()[-1])
    check("v23-24: --rule rules the anchored entry at --ruling, appending the --ruling-text to its body",
          code == C.OK and "ruled: docs/x.md#retention" in out and e["fields"]["state"] == "ruled"
          and e["fields"]["ruling"] == "fed4321" and e["body"].endswith("(owner): keep: the DPA states it")
          and len(read("intake.md").splitlines()) == n)

    # --- v23-25: batch-init --floor-observed and --force
    code, out = run("batch-init", "--pass-kind", "comment", "--batch-id", "FO", "--scope", "a.py",
                    "--floor-observed", "2026-01-01")
    mp = next(Path(".consolidation").glob("FO-*.batch"))
    check("v23-25: batch-init --floor-observed writes it into the master header",
          code == C.OK and C.parse_record(str(mp)).header["floor_observed"] == "2026-01-01")
    code, out = run("batch-init", "--pass-kind", "comment", "--batch-id", "FO", "--scope", "a.py", "b.js",
                    "--floor-observed", "2026-02-02", "--force")
    m = C.parse_record(str(mp))
    check("v23-25: batch-init --force rewrites the batch id's master record in place",
          code == C.OK and list(Path(".consolidation").glob("FO-*.batch")) == [mp]
          and m.header["floor_observed"] == "2026-02-02" and m.header["scope"] == "a.py, b.js")

    # --- v23-26: --target-set reaches the gates of batch-next and batch-run
    write(".consolidation/good.targets", "# floor: self-report\n# pass_kind: comment\na.py\t2\nb.js\t1\n")
    write(".consolidation/bad.targets", "# floor: self-report\n# pass_kind: comment\nz.py\t1\n")
    run("batch-init", "--pass-kind", "comment", "--batch-id", "TS", "--scope", "a.py", "b.js")
    fill(str(next(Path(".consolidation").glob("TS-*.batch"))), judge)
    head = C.head_sha()
    code, out = run("batch-next", "--batch", "TS", "--target-set", ".consolidation/bad.targets")
    check("v23-26: batch-next --target-set cross-checks the review unit's scope at gate --pre",
          code == C.FAIL and "declared scope not in the target set" in out and "gate --pre failed" in out
          and C.head_sha() == head)
    code, out = run("batch-next", "--batch", "TS", "--target-set", ".consolidation/good.targets")
    one = C.head_sha()
    check("v23-26: batch-next --target-set with the scope's target set runs the unit",
          code == C.OK and "GATE PASSED" in out and one != head)
    code, out = run("batch-next", "--batch", "TS", "--target-set", ".consolidation/bad.targets")
    check("v23-26: batch-next --target-set re-gates the done unit at its commit with the target set too",
          code == C.FAIL and "does not pass its gate" in out and "declared scope not in the target set" in out
          and C.head_sha() == one)
    code, out = run("batch-run", "--batch", "TS", "--target-set", ".consolidation/bad.targets")
    check("v23-26: batch-run --target-set stops on the target set's failure",
          code == C.FAIL and "declared scope not in the target set" in out and "batch-run: stopped" in out
          and C.head_sha() == one)
    code, out = run("batch-run", "--batch", "TS", "--target-set", ".consolidation/good.targets")
    check("v23-26: batch-run --target-set with the scope's target set runs the batch to its end",
          code == C.OK and "batch TS complete" in out and C.head_sha() != one)


def _v23_review_tests(dirs):
    """v23 review round: config_sha compatibility, the Perl spaced heredoc, a partial regenerable's
    kept lines, batch-revert's range and line, the porcelain parser, the pointer gate, record-shard's
    rule walk, the ADR path one writer, review-pack's visible ADR failure, unit id form, and lexer
    pins. Creates its own repos with new_repo() and appends them to dirs."""
    def judge(u):
        return {"disposition": C.REGEN, "basis": "restates the call below"}

    def base_repo(prefix, cfg='{"intake_path": "intake.md"}'):
        dirs.append(new_repo(prefix))
        write("intake.md", "")
        write(".gitignore", "intake.md\n")
        write(".consolidation.json", cfg)

    # --- v23-27: a record built while the BOM was still hashed binds its config: the legacy
    # BOM-included sha is accepted wherever a record's config_sha is compared, never written
    plain = '{"intake_path": "intake.md"}'
    base_repo("cons_selftest_v23leg_", "﻿" + plain)
    write("a.py", "# restates a\na()\nb()\n")
    commit("base")
    rp = ".consolidation/leg.record"
    run("record-init", "--pass-kind", "comment", "--unit-id", "LEG", "--scope", "a.py", "--out", rp)
    new_sha = C.parse_record(rp).header["config_sha"]
    legacy = hashlib.sha1(("﻿" + plain).encode("utf-8")).hexdigest()
    rec = fill(rp, judge)
    rec.header["config_sha"] = legacy
    C.write_record(rec, rp)
    check("v23-27 premise: record-init writes the BOM-stripped sha, the legacy one differs",
          new_sha == hashlib.sha1(plain.encode("utf-8")).hexdigest() != legacy)
    code, out = run("record-check", "--record", rp)
    check("v23-27: a record carrying the legacy BOM-included config_sha passes record-check",
          code == C.OK and "config_sha" not in out)
    run("apply", "--record", rp)
    sh("git", "add", "a.py")
    sh("git", "commit", "-q", "-F", ".consolidation/leg.commit-msg")
    code, out = run("preflight")
    check("v23-27: the committed legacy-sha record passes preflight's history walk",
          code == C.OK and "carry no passing record" not in out)
    other = C.parse_record(rp)
    other.header["config_sha"] = hashlib.sha1(b'{"intake_path": "x.md"}').hexdigest()
    C.write_record(other, ".consolidation/leg-other.record")
    code, out = run("record-check", "--record", ".consolidation/leg-other.record")
    check("v23-27: a config_sha of a genuinely different config still fails",
          code == C.FAIL and "does not match the config in force" in out)

    def spans(text, path):
        return [(u.sl, u.el) for u in LX.comment_units(text, path)]

    def unc(text, path):
        return LX.scan(text, path)[1].uncertain

    # --- v23-28: Perl allows whitespace before a quoted heredoc delimiter; elsewhere in the hash
    # family the spaced quoted form is a shift of a string or a heredoc, undecidable
    perl = [('print << "EOF";\n# in\nEOF\n# real\n', "a.pl"), ("print << 'EOF';\n# in\nEOF\n# real\n", "a.pm")]
    check("v23-28: a perl heredoc with a space before its quoted delimiter hides its body, both quotes",
          all(spans(t, p) == [(4, 4)] and unc(t, p) is False for t, p in perl))
    check("v23-28: a ruby left shift with spaces still opens no heredoc, its comment certain",
          spans("items << x\n# note\n", "a.rb") == [(2, 2)] and unc("items << x\n# note\n", "a.rb") is False
          and spans("class << self\n# note\nend\n", "a.rb") == [(2, 2)])
    check("v23-28: the spaced quoted form outside Perl is uncertain, never a silent pass",
          spans('x << "str"\n# note\n', "a.rb") == [(2, 2)] and unc('x << "str"\n# note\n', "a.rb") is True
          and unc("x << 'str'\n# note\n", "a.rb") is True)

    # --- v23-29: a partial regenerable writes back the file's own kept lines, byte for byte:
    # an edit line copied whole, indentation included, never gets the indent twice
    base_repo("cons_selftest_v23keep_")
    body = ("def f():\n    # restates the loop\n    # keep: the vendor needs this order\n"
            "    # restates the return\n    return 1\n")
    write("i.py", body)
    write("n.py", body)
    write("w.py", body.replace("# restates the return", "# and keep this too"), crlf=True)
    write("s.py", body.replace("# keep: the vendor needs this order", "# keep: trailing   "))
    commit("base")
    rp = ".consolidation/keep.record"
    run("record-init", "--pass-kind", "comment", "--unit-id", "KEEP", "--scope", "i.py", "n.py", "w.py", "s.py",
        "--out", rp)
    edits = {"i.py": "    # keep: the vendor needs this order", "n.py": "# keep: the vendor needs this order",
             "w.py": "    # keep: the vendor needs this order\n    # and keep this too",
             "s.py": "# keep: trailing"}
    fill(rp, lambda u: dict(judge(u), edit=edits[u["file"]]))
    code, out = run("gate", "--pre", "--record", rp)
    run("apply", "--record", rp)
    kept = "def f():\n    # keep: the vendor needs this order\n    return 1\n"
    check("v23-29 premise: the partial regenerable edits pass gate --pre", code == C.OK)
    check("v23-29: an edit line carrying the indentation keeps it once",
          Path("i.py").read_bytes() == kept.encode())
    check("v23-29: an edit line without the indentation gets the file's own",
          Path("n.py").read_bytes() == kept.encode())
    check("v23-29: a CRLF file keeps its CRLF endings on the kept lines",
          Path("w.py").read_bytes() == ("def f():\r\n    # keep: the vendor needs this order\r\n"
                                        "    # and keep this too\r\n    return 1\r\n").encode())
    check("v23-29: the file's own trailing whitespace survives, never the edit's",
          Path("s.py").read_bytes() == b"def f():\n    # keep: trailing   \n    return 1\n")

    # --- v23-30: batch-revert names each unit's own commit, so a revert commit just before or
    # between units stays out of the line; the printed line runs verbatim (v23-31)
    def revert_line(frm, bid="B-1"):
        code, out = run("batch-revert", "--batch", bid, "--from", frm)
        line = next((l for l in out.splitlines() if l.startswith("git -C ") and " revert --no-commit " in l), "")
        ran = subprocess.run(line, shell=True, capture_output=True).returncode if line else None
        return code, line, ran

    def five(prefix, channel=""):
        base_repo(prefix, '{"intake_path": "intake.md", "REMOVAL_JUDGEMENT_CAP": 1%s}' % channel)
        for f in "abcde":
            write(f"{f}.py", f"# restates {f}\n{f}()\n")
        commit("base")
        run("batch-init", "--pass-kind", "comment", "--batch-id", "B-1", "--scope", *(f"{f}.py" for f in "abcde"))
        mp = str(next(Path(".consolidation").glob("B-1-*.batch")))
        fill(mp, judge)
        return mp

    mp = five("cons_selftest_v23rv_")
    g = f"git -C {C._q(Path.cwd().resolve().as_posix())}"
    for _ in range(3):
        run("batch-next", "--batch", "B-1")
    code, line, ran = revert_line("2")
    check("v23-31: mid-batch the printed line carries the restore, and runs verbatim",
          code == C.OK and f" && {g} checkout HEAD -- .consolidation && {g} commit -m " in line and ran == 0)
    rv = C.head_sha()
    code, out = run("batch-run", "--batch", "B-1")
    done = C.batch_chain(C.parse_record(mp), C._master_rel(mp))[0]
    check("v23-30 premise: units 4 and 5 run above the revert of units 2..3; the batch completes",
          code == C.OK and "batch B-1 complete" in out and len(done) == 5
          and done[3]["record"].header["baseline_sha"] == rv)
    code, line, ran = revert_line("4")
    check("v23-30: --from 4 names exactly the unit commits 4 and 5, never the revert between them",
          code == C.OK and line.startswith(f"{g} revert --no-commit {done[3]['commit']} {done[4]['commit']} ")
          and rv not in line and "git checkout" not in line and ran == 0)
    check("v23-30: the printed line leaves units 2..3 reverted and reverts 4..5, unit 1 applied",
          [read(f"{f}.py").startswith("# restates") for f in "abcde"] == [False, True, True, True, True])

    # --- v23-31: under the file channel the line restores .consolidation after a complete batch
    # too; a default-channel complete batch has no restore
    five("cons_selftest_v23rvf_", ', "record_channel": "file"')
    run("batch-run", "--batch", "B-1")
    g = f"git -C {C._q(Path.cwd().resolve().as_posix())}"
    code, line, ran = revert_line("2")
    check("v23-31: after a complete batch under the file channel the line carries the restore, runs verbatim",
          code == C.OK and f" && {g} checkout HEAD -- .consolidation && " in line and ran == 0
          and not any(f.startswith(".consolidation/") for f in C.changed_files("HEAD~1", "HEAD")))
    five("cons_selftest_v23rvp_", ', "record_channel": "file"')
    run("batch-run", "--batch", "B-1")
    sh("git", "rm", "-r", "-q", "--cached", ".consolidation")
    sh("git", "commit", "-qm", "chore: stop tracking the record directory")
    code, line, ran = revert_line("2")
    check("v23-31: when HEAD holds no .consolidation the line has no restore, never a dead pathspec",
          code == C.OK and line.startswith("git -C ") and "git checkout" not in line and ran == 0)

    # --- v23-48: a revert commit BETWEEN units k..n is never re-applied: the line names exactly
    # the unit commits, so units below K keep the revert the owner made
    five("cons_selftest_v23rv2_")
    g = f"git -C {C._q(Path.cwd().resolve().as_posix())}"
    for _ in range(3):
        run("batch-next", "--batch", "B-1")
    revert_line("2")
    rv2 = C.head_sha()
    run("batch-next", "--batch", "B-1")   # unit 4 runs above the revert of units 2..3
    mp2 = str(next(Path(".consolidation").glob("B-1-*.batch")))
    done = C.batch_chain(C.parse_record(mp2), C._master_rel(mp2))[0]
    code, line, ran = revert_line("3")
    check("v23-48: --from 3 names units 3 and 4 only, never the revert commit between them",
          code == C.OK and rv2 not in line
          and line.startswith(f"{g} revert --no-commit {done[2]['commit']} {done[3]['commit']} ") and ran == 0)
    check("v23-48: the revert of units 3..4 leaves unit 2's earlier revert standing",
          [read(f"{f}.py").startswith("# restates") for f in "abcde"] == [False, True, True, True, True])

    # --- v23-49: an uncommitted change under the record directory refuses before anything is
    # printed; the normal mid-batch state (untracked files only) never refuses
    five("cons_selftest_v23rv3_")
    for _ in range(2):
        run("batch-next", "--batch", "B-1")
    code, out = run("batch-revert", "--batch", "B-1", "--from", "2")
    check("v23-49 premise: untracked record files alone never refuse the revert",
          code == C.OK and "differs from HEAD" not in out)
    mp3 = str(next(Path(".consolidation").glob("B-1-*.batch")))
    rec3 = C.parse_record(mp3)
    rec3.units[3]["basis"] = "OWNER CORRECTION"
    C.write_record(rec3, mp3)
    code, out = run("batch-revert", "--batch", "B-1", "--from", "2")
    check("v23-49: an uncommitted master correction refuses, naming the file, before any line",
          code == C.FAIL and "differs from HEAD" in out and mp3.replace("\\", "/") in out
          and "git -C" not in out and "stash" in out)
    sh("git", "checkout", "--", mp3)
    code, line, ran = revert_line("2")
    check("v23-49: with the record directory back at HEAD the line prints and runs verbatim",
          code == C.OK and ran == 0)

    # --- v23-50: the line carries git -C <root>, so it runs from any directory
    five("cons_selftest_v23rv4_")
    for _ in range(2):
        run("batch-next", "--batch", "B-1")
    code, out = run("batch-revert", "--batch", "B-1", "--from", "2")
    line = next((l for l in out.splitlines() if l.startswith("git -C ") and " revert --no-commit " in l), "")
    check("v23-50 premise: the line names unit 2's commit behind a git -C",
          code == C.OK and line.startswith("git -C "))
    Path("sub").mkdir()
    r = None
    try:
        os.chdir("sub")
        r = subprocess.run(line, shell=True, capture_output=True)
    finally:
        os.chdir("..")
    subj = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True).stdout.strip()
    check("v23-50: run from a subdirectory the line still reverts and commits",
          r is not None and r.returncode == 0 and subj == "consolidation: revert batch B-1 units 2..2")

    # --- v23-51: a batch part record is exempt from the one-writer check: its paths rank in
    # its master, whose own gate runs it — the same collision outside a batch refuses (v23-34)
    base_repo("cons_selftest_v23adr3_")
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n"
                  "# this also polls: the vendor drops retries\npoll()\n")
    commit("base")
    run("record-init", "--pass-kind", "comment", "--unit-id", "AV", "--scope", "p.py", "--out",
        ".consolidation/av.record")

    def adr_twins(u):
        if "chose polling" in u["preview"]:
            return {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
                    "adr_title": "Polling over webhooks", "adr_text": "## Decision\n\nPoll."}
        return {"disposition": C.ADR, "basis": "the same polling decision",
                "adr": "docs/adr/0001-polling-over-webhooks.md"}
    fill(".consolidation/av.record", adr_twins)
    code, out = run("record-check", "--record", ".consolidation/av.record")
    rec = C.parse_record(".consolidation/av.record")
    rec.header["batch"] = ".consolidation/B-9.batch"
    C.write_record(rec, ".consolidation/av.record")
    code2, _ = run("record-check", "--record", ".consolidation/av.record")
    check("v23-51: the collision refuses a plain record and passes a batch part record",
          code == C.FAIL and "names docs/adr/0001-polling-over-webhooks.md" in out and code2 == C.OK)

    # --- v23-52: a rename whose new side is an output path still stops the batch, on its old
    # side — the old side is a real deletion the unit would run over
    five("cons_selftest_v23rn_")
    run("batch-next", "--batch", "B-1")
    sh("git", "mv", "b.py", ".consolidation/b.record")
    code, out = run("batch-next", "--batch", "B-1")
    check("v23-52: a scope file renamed into the record dir stops the batch under its old name",
          code == C.FAIL and "STOP" in out and "b.py" in out)

    # --- v23-33: one porcelain parser (-z): a rename by both sides whatever status.renames says,
    # names as stored, every untracked file whatever status.showUntrackedFiles says
    base_repo("cons_selftest_v23st_")
    write("a.py", "# restates a\na()\n")
    write("b.py", "# restates b\nb()\n")
    write(".consolidation/keep", "")
    commit("base")
    rp = ".consolidation/st.record"
    run("record-init", "--pass-kind", "comment", "--unit-id", "ST", "--scope", "b.py", "--out", rp)
    u = C.parse_record(rp).units[0]
    write(".consolidation/st.j", f"@@ {u['id']} {u['fingerprint']}\ndisposition: {C.REGEN}\nbasis: restates b()\n")
    sh("git", "config", "status.renames", "false")
    sh("git", "mv", "a.py", ".consolidation/a.record")
    check("v23-33: a rename is one entry with both sides, even under status.renames=false",
          [e for e in C.status_entries() if e[0] != "??"] == [("R ", ".consolidation/a.record", "a.py")])
    snap = C.tree_snapshot()
    check("v23-33: tree_snapshot sees a rename into the record dir by its old side, deleted",
          snap == {"a.py": "deleted"})
    code, out = run("record-fill", "--record", rp, "--from", ".consolidation/st.j")
    check("v23-33: record-fill refuses while a file was moved into the record dir, naming it",
          code == C.FAIL and "the working tree changed outside the record directory" in out and "a.py" in out)
    sh("git", "mv", ".consolidation/a.record", "a.py")
    check("v23-33 premise: with the rename undone record-fill writes",
          run("record-fill", "--record", rp, "--from", ".consolidation/st.j")[0] == C.OK)
    write("sp ace.py", "x\n")
    blob = C.git("hash-object", "-w", "sp ace.py").strip()
    # a quote is no NTFS file name: the entry lives in the index only (AD), as on any platform
    sh("git", "-c", "core.protectNTFS=false", "update-index", "--add", "--cacheinfo", f"100644,{blob},q\"x.py")
    ent = {(xy, p) for xy, p, _ in C.status_entries()}
    code, out = run("unit-tree-check")
    check("v23-33: a name with a space or a quote is read as stored, never C-quoted",
          ("??", "sp ace.py") in ent and ("AD", 'q"x.py') in ent
          and code == C.FAIL and "?? sp ace.py" in out and 'AD q"x.py' in out)
    sh("git", "-c", "core.protectNTFS=false", "rm", "-q", "--cached", 'q"x.py')
    os.remove("sp ace.py")
    sh("git", "config", "status.showUntrackedFiles", "no")
    write("new.py", "x\n")
    code, out = run("unit-tree-check")
    check("v23-33: unit-tree-check sees an untracked file under status.showUntrackedFiles=no",
          code == C.FAIL and "?? new.py" in out)
    os.remove("new.py")
    check("v23-33 premise: the tree is clean again", run("unit-tree-check")[0] == C.OK)

    # --- v23-34: one ADR file, one writer — a hand `adr:` spelling another unit's rendered path
    # differently is the same file, refused; apply_plan's baseline refusal stays as defense
    base_repo("cons_selftest_v23adr2_")
    write("p.py", "# we chose polling over webhooks: the vendor drops retries\npoll()\n"
                  "# this also polls: the vendor drops retries\npoll()\n")
    parent = commit("base")
    f1 = "docs/adr/0001-polling-over-webhooks.md"

    def adr_pair(u):
        if "chose polling" in u["preview"]:
            return {"disposition": C.ADR, "basis": "polling over webhooks: the vendor drops retries",
                    "adr_title": "Polling over webhooks", "adr_text": "## Decision\n\nPoll."}
        return {"disposition": C.ADR, "basis": "the same polling decision", "adr": "docs/adr/./0001-polling-over-webhooks.md"}
    run("record-init", "--pass-kind", "comment", "--unit-id", "AS", "--scope", "p.py", "--out", ".consolidation/as.record")
    fill(".consolidation/as.record", adr_pair)
    code, out = run("record-check", "--record", ".consolidation/as.record")
    check("v23-34: a hand `adr:` naming another unit's rendered path through `./` is refused, naming both units",
          code == C.FAIL and f"unit 2 (p.py:3-3): `adr: docs/adr/./0001-polling-over-webhooks.md` names {f1}, "
                             f"the ADR unit 1 renders" in out)
    write(f1, "# 0001 - Polling\n")
    commit("docs: the polling ADR", f1)
    run("record-init", "--pass-kind", "comment", "--unit-id", "AT", "--scope", "p.py", "--out", ".consolidation/at.record")
    rec = fill(".consolidation/at.record", lambda u: adr_pair(u) if "chose polling" in u["preview"] else
               {"disposition": C.STILL, "basis": "carries a reason the code cannot state"})
    C.write_record(C.Record(dict(rec.header, baseline_sha=parent, batch_master="yes"), rec.units), ".consolidation/at.batch")
    rec.header["batch"] = ".consolidation/at.batch"
    e = _raises(C.apply_plan, rec, C.load_config())
    check("v23-34: a rendered ADR path that exists at the unit's baseline is refused by apply_plan",
          isinstance(e, C.Die) and f"{f1}: the ADR unit 1 renders exists at the baseline" in str(e))

    # --- v23-35: the condensed pointer gate reads `See` and any whitespace before the path
    write("c.py", "# this flushes the buffer before close because the driver keeps a private buffer\nflush()\n\n"
                  "# this retries three times because the vendor drops the first two requests\nretry()\n")
    commit("feat: c", "c.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "PT", "--scope", "c.py", "--out", ".consolidation/pt.record")
    edits = {"flushes": "# See docs/nope.md §3", "retries": "# see  docs/none.md, §2"}
    fill(".consolidation/pt.record", lambda u: {"disposition": C.COND, "basis": "the spec holds the reason",
                                                 "claims": "the reason", "ruling": "SR-00000000",
                                                 "edit": next(v for k, v in edits.items() if k in u["preview"])})
    code, out = run("record-check", "--record", ".consolidation/pt.record", "--no-intake")
    check("v23-35: a capitalised `See` pointer and a double-spaced, comma-led one are both checked",
          code == C.FAIL and "the pointer names 'docs/nope.md', which is not a file" in out
          and "the pointer names 'docs/none.md', which is not a file" in out)

    # --- v23-37: review-pack whose rendered ADR paths cannot be computed fails loud, and the
    # pack says so, instead of silently listing none
    write(".consolidation/asx.record", read(".consolidation/as.record").replace("@@unit 1\n", "@@unit x1\n"))
    code, out = run("review-pack", "--record", ".consolidation/asx.record", "--no-gate",
                    "--out", ".consolidation/asx.review.md")
    check("v23-37: review-pack on a hand-edited unit id exits 1, naming the problem, and the pack carries it",
          code == C.FAIL and "FAIL the pack lists no rendered ADR file: unit 'x1'" in out
          and "- FAIL: the ADR files the runner renders cannot be listed: unit 'x1'"
          in read(".consolidation/asx.review.md"))

    # --- v23-38: record-shard's remembered unit rule belongs to a document pass, and its walk
    # reads the commits with one `git log`
    base_repo("cons_selftest_v23rule_")
    write("r.md", "# Tape\n\nSee docs/auth.md for the retention.\n")
    write("a.py", "# restates a\na()\n")
    commit("base")
    run("record-init", "--pass-kind", "document", "--unit-id", "D0", "--scope", "r.md", "--out", ".consolidation/d0.record")
    write("d0.msg", C.commit_message(C.parse_record(".consolidation/d0.record")))
    sh("git", "commit", "-q", "--allow-empty", "-F", "d0.msg")
    for i in range(20):
        sh("git", "commit", "-q", "--allow-empty", "-m", f"chore: {i}")
    run("record-init", "--pass-kind", "severance", "--unit-id", "SV", "--scope", "r.md", "--target", "docs/auth.md",
        "--out", ".consolidation/sv.record")
    code, out = run("record-shard", "--record", ".consolidation/sv.record", "--shards", "1")
    check("v23-38: a severance-pass record-shard prints no document record's rule against its own",
          code == C.OK and "unit rule" not in out)
    run("record-init", "--pass-kind", "document", "--unit-id", "D1", "--scope", "r.md", "--out", ".consolidation/d1.record")
    real_git, calls = C.git, []
    try:
        C.git = lambda *a, **k: (calls.append(a), real_git(*a, **k))[1]
        code, out = run("record-shard", "--record", ".consolidation/d1.record", "--shards", "1")
    finally:
        C.git = real_git
    check("v23-38: a document pass still reads the rule of the nearest document record",
          code == C.OK and "r.md: unit rule document-paragraph from record D0" in out and "warn:" not in out)
    check("v23-38: the walk over 21 commits spawns no message or parent lookup per commit",
          not [a for a in calls if a[:1] == ("rev-parse",) or a[:3] == ("log", "-1", "--format=%B")])
    # a comment pass past the walk cap: 500 commits in one fast-import
    branch, tip = C.git("symbolic-ref", "HEAD").strip(), C.head_sha()
    stream = "".join(f"commit {branch}\ncommitter t <t@t> 1700000000 +0000\ndata {len(m)}\n{m}"
                     + (f"from {tip}\n" if i == 0 else "") + "\n"
                     for i, m in enumerate(f"chore: bulk {i}\n" for i in range(C.RULE_WALK_CAP)))
    subprocess.run(["git", "fast-import", "--quiet"], input=stream.encode(), check=True, capture_output=True)
    sh("git", "reset", "-q", "--hard")
    run("record-init", "--pass-kind", "comment", "--unit-id", "CM", "--scope", "a.py", "--out", ".consolidation/cm.record")
    code, out = run("record-shard", "--record", ".consolidation/cm.record", "--shards", "1")
    check("v23-38: a comment-pass record-shard past the walk cap prints no walk note",
          code == C.OK and "a.py" in out and "note:" not in out and "unit rule" not in out)

    # --- v23-39: intake_lock unlinks an aged lock only when _lock_still_stale confirms it is the
    # one it stat'ed: a lock another waiter just replaced is never deleted
    lock = Path("intake.md.lock")
    lock.write_text("other")
    os.utime(lock, (time.time() - 200, time.time() - 200))
    real_stale, refused = C._lock_still_stale, None
    try:
        C._lock_still_stale = lambda *a: False
        with C.intake_lock("intake.md", timeout=0.3):
            pass
    except C.Die as e:
        refused = e
    finally:
        C._lock_still_stale = real_stale
    check("v23-39: an aged lock the re-stat no longer confirms is kept, and the acquire times out loud",
          isinstance(refused, C.Die) and "intake is locked" in str(refused)
          and lock.exists() and lock.read_text() == "other")
    lock.unlink(missing_ok=True)

    # --- v23-36: a unit id is the number record-init wrote: no zero, no leading zero
    check("v23-36: unit_number refuses 0 and a leading zero, takes 10",
          C.unit_number("10", "r") == 10
          and all(isinstance(_raises(C.unit_number, bad, "record R"), C.Die) for bad in ("0", "01", "007")))
    mp = five("cons_selftest_v23rvd_")
    run("batch-run", "--batch", "B-1")

    # --- v23-32: the batch id printed inside the line is the one batch-init writes
    write(".consolidation/hand.batch", read(mp).replace("unit_id: B-1\n", 'unit_id: B-1"; echo x; "\n'))
    code, out = run("batch-revert", "--batch", ".consolidation/hand.batch", "--from", "1")
    check("v23-32: a master record whose unit_id is not a batch id is refused, nothing printed",
          code == C.FAIL and "is not a batch id" in out and "git revert" not in out)
    os.remove(".consolidation/hand.batch")

    code, line, ran = revert_line("1")
    check("v23-31: after a complete batch in the default channel the line has no restore, runs verbatim",
          code == C.OK and "git checkout" not in line and ran == 0)


def _raises(fn, *a):
    try:
        fn(*a)
    except Exception as e:
        return e
    return None


def _misc_tests():
    write("w.js", "a();\r\n// note\r\nb();\r\n", crlf=False)
    write("x.unknownext", "data\n")
    write(".consolidation.json", '{"REMOVED_LINE_CAP": 5, "typo_key": 1}')
    commit("base")
    code, out = run("record-init", "--pass-kind", "comment", "--unit-id", "M1", "--scope", "x.unknownext",
                    "--out", ".consolidation/m.record")
    check("H4: record-init refuses an unsupported file instead of a silent zero", code == C.FAIL)
    run("record-init", "--pass-kind", "comment", "--unit-id", "M2", "--scope", "w.js", "--out", ".consolidation/w.record")
    fill(".consolidation/w.record", lambda u: {"disposition": C.REGEN, "basis": "restates nothing the code does not say"})
    run("apply", "--record", ".consolidation/w.record")
    check("CRLF line endings survive apply", read("w.js") == "a();\r\nb();\r\n")
    check("unknown config key does not become a default", C.load_config()["REMOVED_LINE_CAP"] == 5)
    Path("deep").mkdir()
    os.chdir("deep")
    check("config is found from a subdirectory", C.load_config()["REMOVED_LINE_CAP"] == 5)
    os.chdir("..")
    # a preview whose 70-char window ends in whitespace: the parse strips trailing whitespace
    # (D4), so the enumeration must never emit one (found by the GammaBot replay)
    write("pv.py", "# " + "a" * 67 + " tail of the comment\nx = 1\n")
    commit("feat: pv", "pv.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "PV", "--scope", "pv.py",
        "--out", ".consolidation/pv.record")
    fill(".consolidation/pv.record", lambda u: {"disposition": C.STILL, "basis": "carries a reason"})
    check("preview: a 70-char window ending in whitespace never fails identity",
          run("record-check", "--record", ".consolidation/pv.record")[0] == C.OK)

    # every disposition of the Requires column demands its basis (review round 2, R-docs 1)
    run("record-init", "--pass-kind", "comment", "--unit-id", "PV2", "--scope", "pv.py",
        "--out", ".consolidation/pv2.record")
    fill(".consolidation/pv2.record", lambda u: {"disposition": C.NV})
    check("not verifiable requires a basis", run("record-check", "--record", ".consolidation/pv2.record")[0] == C.FAIL)
    fill(".consolidation/pv2.record", lambda u: {"disposition": C.ADR, "basis": None})
    check("historical decision → ADR requires a basis",
          run("record-check", "--record", ".consolidation/pv2.record")[0] == C.FAIL)
    fill(".consolidation/pv2.record", lambda u: {"disposition": C.ADR, "basis": "chose X over Y for reason Z"})
    check("v2.1-29: historical decision → ADR without `adr:` fails (v3 record)",
          run("record-check", "--record", ".consolidation/pv2.record")[0] == C.FAIL)
    fill(".consolidation/pv2.record", lambda u: {"adr": "src/x.md"})
    check("v2.1-29: an `adr:` outside adr_dir fails",
          run("record-check", "--record", ".consolidation/pv2.record")[0] == C.FAIL)
    fill(".consolidation/pv2.record", lambda u: {"adr": "docs/adr/0001-x-over-y.md"})
    check("historical decision → ADR with a one-line basis passes",
          run("record-check", "--record", ".consolidation/pv2.record")[0] == C.OK)
    # R-gates 4: a BOM'd Python file consolidates; apply keeps the BOM
    Path("bom.py").write_bytes(b"\xef\xbb\xbf# restates x\nx = 1\n")
    commit("feat: bom.py", "bom.py")
    run("record-init", "--pass-kind", "comment", "--unit-id", "BOM", "--scope", "bom.py",
        "--out", ".consolidation/bom.record")
    fill(".consolidation/bom.record", lambda u: {"disposition": C.REGEN, "basis": "restates x = 1"})
    check("a BOM'd Python file passes record-check (the compile proof ignores the BOM)",
          run("record-check", "--record", ".consolidation/bom.record")[0] == C.OK)
    run("apply", "--record", ".consolidation/bom.record")
    check("apply on a BOM'd Python file keeps the BOM and leaves no BOM-only line",
          Path("bom.py").read_bytes() == b"\xef\xbb\xbfx = 1\n")
    sh("git", "checkout", "--", "bom.py")
    bu = LX.comment_units("﻿# old\nx = 1\n", "a.py")[0]
    op = {"lines": "1-1", "span": bu.span(), "disposition": C.OBS, "edit": "# one\n# two"}
    check("code tokens ignore a leading BOM (removing a BOM'd line-1 comment keeps the tokens)",
          LX.code_tokens("﻿// c\nx = 1;\n", "a.js")[0] == LX.code_tokens("﻿x = 1;\n", "a.js")[0])
    check("a multi-line replace of a BOM'd line-1 comment keeps every line and one BOM",
          C.apply_file("﻿# old\nx = 1\n", C.plan_ops([op], "comment"), "comment")
          == "﻿# one\n# two\nx = 1\n")

    write("w.js", "dirty();\n")
    check("preflight fails on a dirty tree", run("preflight")[0] == C.FAIL)

    # --- E4: the lva stripper and a marker-only front-matter block
    check("E4: a front-matter block holding only the marker is dropped whole",
          C._strip_lva("---\nlast-verified-at: abc123\n---\n# T\n") == "# T\n")
    check("E4: a marker inside a populated block drops the marker line alone",
          C._strip_lva("---\ntitle: x\nlast-verified-at: abc\n---\n# T\n") == "---\ntitle: x\n---\n# T\n")
    check("E4: text with no marker block is untouched",
          C._strip_lva("# T\n") == "# T\n" and C._strip_lva("---\ntitle: x\n---\n") == "---\ntitle: x\n---\n")
    check("R4a: a BOM'd marker-only block is dropped and the BOM kept",
          C._strip_lva("﻿---\nlast-verified-at: abc\n---\n# T\n") == "﻿# T\n")
    check("R4a: a BOM'd populated block drops the marker line alone",
          C._strip_lva("﻿---\ntitle: x\nlast-verified-at: a\n---\n# T\n") == "﻿---\ntitle: x\n---\n# T\n")

    # R-runner 3: a malformed script-owned field fails cleanly, never a traceback
    rec = C.parse_record(".consolidation/pv.record")
    rec.units[0].update({"disposition": C.NV, "basis": "external rule"})
    rec.units[0]["lines"] = "oops"
    C.write_record(rec, ".consolidation/t.record")
    code, out = run("escalate", "--from-record", ".consolidation/t.record", "--intake", "intake.md")
    check("malformed lines fail cleanly (escalate --from-record), never a traceback",
          code == C.FAIL and "ValueError" in out)


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):   # run directly on a cp1252 console, the arrows must print
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
