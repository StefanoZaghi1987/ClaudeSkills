#!/usr/bin/env python3
"""Zip each skills/<name>/ into dist/<name>.skill and dist/<name>.zip (top-level folder = skill name)."""
import json, re, shutil, sys, zipfile
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP = {"__pycache__", ".DS_Store", "Thumbs.db"}
NAME_OK = re.compile(r"[a-z0-9-]{1,64}")  # official skill-name charset
# Claude Code only: these take the spec's 1024-char description limit, not claude.ai's 200
CODE_ONLY = {"consolidate-comments", "consolidate-specs"}

def build(name):
    src, out = ROOT / "skills" / name, ROOT / "dist" / f"{name}.skill"
    if not (src / "SKILL.md").is_file():
        sys.exit(f"error: skills/{name} has no SKILL.md")
    all_lines = (src / "SKILL.md").read_text(encoding="utf-8").splitlines()
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
                json.loads(p.read_text(encoding="utf-8"))
            except ValueError as e:
                sys.exit(f"error: skills/{name}: {p.name} is not valid JSON: {e}")
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            if p.is_file() and not SKIP.intersection(p.parts):
                z.write(p, f"{name}/{p.relative_to(src).as_posix()}")
    shutil.copyfile(out, out.with_suffix(".zip"))
    print(f"built dist/{name}.skill dist/{name}.zip")

for n in sys.argv[1:] or sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir()):
    build(n)
