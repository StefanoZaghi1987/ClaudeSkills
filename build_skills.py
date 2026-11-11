#!/usr/bin/env python3
"""Zip each skills/<name>/ into dist/<name>.skill and dist/<name>.zip (top-level folder = skill name)."""
import json, re, shutil, subprocess, sys, zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # the frontmatter reader; a fresh interpreter does not ship it
    sys.exit("error: pyyaml is missing: the build reads each SKILL.md's frontmatter with it "
             "(pip install pyyaml)")

ROOT = Path(__file__).resolve().parent
SKIP = {"__pycache__", ".DS_Store", "Thumbs.db", ".git"}   # and macOS ._* AppleDouble files

def _index_modes():
    """{absolute path: 0o755 or 0o644} as git's index records them. A checkout git cannot read
    stops the build, since every archive would silently lose its executable bits; outside a
    checkout every file is 0o644, with a warning."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s", "-z", "skills"],
                             capture_output=True, check=True).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError) as e:
        if (ROOT / ".git").exists():
            sys.exit(f"error: git cannot list the index, so the archives would lose their file modes: "
                     f"{getattr(e, 'stderr', b'') and e.stderr.decode(errors='replace').strip() or e}")
        print("warning: not a git checkout: every archived file gets mode 0644", file=sys.stderr)
        return {}
    modes = {}
    for entry in filter(None, out.split("\0")):
        meta, path = entry.split("\t", 1)
        modes[(ROOT / path).resolve()] = 0o755 if meta.startswith("100755") else 0o644
    return modes

INDEX_MODES = _index_modes()

def index_mode(p):
    return INDEX_MODES.get(p.resolve(), 0o644)

def _index_paths():
    """{absolute path} of every tracked file under skills/. The archives are built from the
    index, not from the disk: rglob picked up untracked files (an editor backup, Desktop.ini),
    so a developer machine and a clean CI checkout zipped different trees from the same commit."""
    return {p for p in INDEX_MODES}


def _archive_files(src, name):
    """(archive name, path) of every file of `name`'s skill folder, sorted by archive name.

    Tracked files always ship. Untracked ones ship only when git cannot be asked (outside a
    checkout), so a stale disk file never enters a release unnoticed; a tracked file missing
    from the disk is an error, because the archive would silently lose it."""
    tracked = {p for p in _index_paths() if src in p.parents}
    if tracked:
        missing = sorted(str(p.relative_to(src)) for p in tracked if not p.is_file())
        if missing:
            sys.exit(f"error: skills/{name}: tracked file(s) missing from the disk: {', '.join(missing)}")
        untracked = sorted(
            str(p.relative_to(src)) for p in src.rglob("*") if p.is_file() and p not in tracked
            and not SKIP.intersection(p.parts) and not any(part.startswith("._") for part in p.parts))
        if untracked:
            sys.exit(f"error: skills/{name}: file(s) not in the git index (git add them, or delete them): "
                     f"{', '.join(untracked)}")
        chosen = tracked
    elif INDEX_MODES:
        # a checkout, and a skill folder the index knows nothing about: that is a skill
        # not yet added, exactly the moment stray files sit beside it
        sys.exit(f"error: skills/{name}: no file of this skill is in the git index (git add it first)")
    else:
        chosen = set(src.rglob("*"))
    files = []
    for p in chosen:
        if not p.is_file() or SKIP.intersection(p.parts) or any(part.startswith("._") for part in p.parts):
            continue
        files.append((p.relative_to(src).as_posix(), p))
    return sorted(files)

NAME_OK = re.compile(r"[a-z0-9-]{1,64}")  # official skill-name charset
# Claude Code only: these take the spec's 1024-char description limit, not claude.ai's 200
CODE_ONLY = {"consolidate-comments", "consolidate-specs"}


def _check_evals(name, src, data):
    """The build is the one gate that reads evals.json, so it carries the eval loop's
    contract: every case runnable (an id, a prompt, assertions) and every sample file
    it lists shipped (paths are relative to the skill folder)."""
    where = f"skills/{name}: evals/evals.json"
    cases = data.get("evals") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        sys.exit(f"error: {where} has no non-empty 'evals' list")
    if data.get("skill_name") != name:
        sys.exit(f"error: {where}: skill_name is {data.get('skill_name')!r}, expected {name!r}")
    seen = set()
    for case in cases:
        cid = case.get("id") if isinstance(case, dict) else None
        case_where = f"{where} case {cid!r}"
        if not isinstance(cid, str) or not cid:
            sys.exit(f"error: {case_where} needs a non-empty 'id'")
        if cid in seen:
            sys.exit(f"error: {case_where} repeats an id this file already used")
        seen.add(cid)
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            sys.exit(f"error: {case_where} needs a non-empty 'prompt'")
        assertions = case.get("assertions")
        if not isinstance(assertions, list) or not assertions or not all(
                isinstance(a, str) and a.strip() for a in assertions):
            sys.exit(f"error: {case_where} needs an 'assertions' list of non-empty strings")
        files = case.get("files", [])
        if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
            sys.exit(f"error: {case_where}: 'files' must be a list of paths relative "
                     f"to the skill folder")
        for listed in files:
            listed_path = (src / listed).resolve()
            if not listed_path.is_relative_to(src.resolve()):
                sys.exit(f"error: {case_where} lists '{listed}', which is outside the skill folder")
            if not listed_path.is_file():
                sys.exit(f"error: {case_where} lists '{listed}', which the skill does not ship "
                         f"(paths are relative to the skill folder)")

def build(name):
    src, out = ROOT / "skills" / name, ROOT / "dist" / f"{name}.skill"
    if not (src / "SKILL.md").is_file():
        sys.exit(f"error: skills/{name} has no SKILL.md")
    all_lines = (src / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if all_lines[0].startswith("﻿"):
        sys.exit(f"error: skills/{name}: SKILL.md starts with a BOM")
    if all_lines[0].strip() != "---":
        sys.exit(f"error: skills/{name}: SKILL.md must open with a '---' frontmatter line")
    if "---" not in all_lines[1:]:
        sys.exit(f"error: skills/{name}: frontmatter is not closed by '---'")
    try:
        fm = yaml.safe_load("\n".join(all_lines[1:all_lines.index("---", 1)]))
    except yaml.YAMLError as e:
        sys.exit(f"error: skills/{name}: SKILL.md frontmatter is not valid YAML: {e}")
    if not isinstance(fm, dict):
        sys.exit(f"error: skills/{name}: SKILL.md frontmatter is not a YAML mapping")
    fm_name = fm.get("name", "")
    if fm_name != name:
        sys.exit(f"error: skills/{name}: frontmatter name is {fm_name!r}, expected {name!r}")
    if not NAME_OK.fullmatch(name):
        sys.exit(f"error: skills/{name}: name must be lowercase letters, digits and hyphens, <= 64 chars")
    if "claude" in name or "anthropic" in name:
        sys.exit(f"error: skills/{name}: name must not contain the reserved words 'claude' or 'anthropic'")
    desc = fm.get("description", "")
    if not isinstance(desc, str) or not desc:
        sys.exit(f"error: skills/{name}: frontmatter has no description")
    limit = 1024 if name in CODE_ONLY else 200  # claude.ai caps uploads at 200 chars
    if len(desc) > limit:
        sys.exit(f"error: skills/{name}: description is {len(desc)} chars, max {limit}")
    # claude.ai file delivery must be described at capability level, never with
    # sandbox paths or guessed tool names; write_pdf (weasyprint API) is fine
    for p in sorted(set(src.rglob("*.md")) | set(src.rglob("*.json")) | set(src.rglob("*.py"))):
        if any(re.search(r"/mnt/|computer://|present_files|create_file", l) for l in p.read_text(encoding="utf-8").splitlines()):
            sys.exit(f"error: skills/{name}: {p.name} hard-codes sandbox paths or guessed tool names")
        if p.suffix == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except ValueError as e:
                sys.exit(f"error: skills/{name}: {p.name} is not valid JSON: {e}")
            if p == src / "evals" / "evals.json":
                _check_evals(name, src, data)
    out.parent.mkdir(exist_ok=True)
    # the same tree gives the same bytes from the same zlib build: entries sorted by archive name,
    # a fixed timestamp, Unix modes taken from the index rather than the build machine's disk
    files = _archive_files(src, name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, p in files:
            info = zipfile.ZipInfo(f"{name}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100000 | index_mode(p)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes(), compresslevel=9)
    shutil.copyfile(out, out.with_suffix(".zip"))
    print(f"built dist/{name}.skill dist/{name}.zip")

for n in sys.argv[1:] or sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir()):
    build(n)
