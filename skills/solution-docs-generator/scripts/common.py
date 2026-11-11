#!/usr/bin/env python3
"""
common.py - helpers shared by more than one script of solution-docs-generator.

Standard library only. Python 3.10 or newer.

- Secret detection and redaction (used by extract_sources.py and check_doc.py).
- The small front-matter / key-value reader used by render.py and check_doc.py.
- UTF-8 file helpers that behave the same on Windows and Linux.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("solution-docs-generator scripts need Python 3.10 or newer "
             f"(this is {sys.version_info[0]}.{sys.version_info[1]})")

REDACTED = "«REDACTED»"

# --------------------------------------------------------------------------------------
# Secret detection
# --------------------------------------------------------------------------------------
# Names that mark a value as a secret. "key" alone is too broad (dictionary keys,
# primary keys), so it only counts with a qualifier.
_SECRET_NAME = (
    r"(?:password|passwd|pwd|passphrase|secret|client[_\-. ]?secret|app[_\-. ]?secret|"
    r"api[_\-. ]?key|apikey|access[_\-. ]?key|secret[_\-. ]?key|private[_\-. ]?key|"
    r"account[_\-. ]?key|shared[_\-. ]?access[_\-. ]?key|auth[_\-. ]?token|access[_\-. ]?token|"
    r"refresh[_\-. ]?token|bearer[_\-. ]?token|token[_\-. ]?secret|signing[_\-. ]?key|"
    r"encryption[_\-. ]?key|credentials?)"
)

# Each detector: (kind, compiled regex, group holding the secret value)
_DETECTORS: list[tuple[str, re.Pattern, int]] = [
    # PEM private keys (multi-line): the whole block is the secret
    ("private-key-block",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), 0),
    # <add key="ClientSecret" value="..."/>  (.NET config files)
    ("config-key-value",
     re.compile(r"""key\s*=\s*["'][^"']*""" + _SECRET_NAME + r"""[^"']*["']\s+value\s*=\s*["']([^"']+)["']""",
                re.I), 1),
    # JSON / YAML / INI / env / XML attribute:  "Password": "x" | password: x | PASSWORD=x | password="x"
    ("named-value",
     re.compile(r"""(?<![A-Za-z0-9])["']?[A-Za-z0-9_.\-]*""" + _SECRET_NAME + r"""[A-Za-z0-9_.\-]*["']?"""
                r"""\s*(?::=|=>|[:=])\s*(?:"([^"\r\n]{1,512})"|'([^'\r\n]{1,512})'|([^\s;,"'<>{}\]\)]{1,512}))""",
                re.I), -1),
    # connection strings: ...;Password=x;  Pwd=x  (also inside larger strings)
    ("connection-string",
     re.compile(r"(?i)(?:^|[;\s\"'])(?:password|pwd)\s*=\s*([^;\"'\r\n]+)"), 1),
    # URL with user:password@
    ("url-credentials",
     re.compile(r"(?i)\b[a-z][a-z0-9+.\-]*://[^\s/:@\"']+:([^\s/@\"']+)@"), 1),
    # Authorization: Bearer xxx / Basic xxx
    ("authorization-header",
     re.compile(r"(?i)\b(?:bearer|basic)\s+([A-Za-z0-9\-._~+/]{16,}=*)"), 1),
    # JSON Web Token
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), 0),
    # Microsoft Entra ID client secret format (xxx8Q~...)
    ("entra-client-secret", re.compile(r"\b[A-Za-z0-9_\-.]{3}\dQ~[A-Za-z0-9_\-.~]{31,40}\b"), 0),
    # Azure storage / service bus account keys and SAS signatures
    ("azure-key", re.compile(r"(?i)\b(?:AccountKey|SharedAccessKey)\s*=\s*([A-Za-z0-9+/=]{20,})"), 1),
    ("sas-signature", re.compile(r"(?i)[?&]sig=([A-Za-z0-9%+/=]{20,})"), 1),
    # Cloud / SaaS tokens with recognisable prefixes
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), 0),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"), 0),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b"), 0),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), 0),
    ("generic-sk-key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}\b"), 0),
    # Database command lines: hdbsql -p x, mysql -px, sqlcmd -P x, psql password via PGPASSWORD=x
    ("cli-password",
     re.compile(r"(?i)\b(?:hdbsql|mysql|mysqldump|sqlcmd|bcp|isql|sqlplus|mongosh?|redis-cli)\b[^\r\n]*?\s-[pP]\s*([^\s\"'-][^\s\"']*)"), 1),
    ("env-password", re.compile(r"(?i)\b(?:PGPASSWORD|MYSQL_PWD|SA_PASSWORD)\s*=\s*([^\s;\"']+)"), 1),
]

# Values that are placeholders, not secrets: never redact (and never report) them.
_PLACEHOLDER = re.compile(
    r"""^(?:\*+|x+|\.{3}|…|<[^>]*>|&lt;.*&gt;|\{[^}]*\}|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_]+%|"""
    r"""null|none|nil|true|false|yes|no|empty|changeme|change_me|your[_\-]?\w*|example\w*|"""
    r"""redacted|«redacted»|\[redacted\]|password|secret|string|todo|tbd|""|'')$""",
    re.I)


def _looks_like_literal_secret(value: str) -> bool:
    """An unquoted value counts only when it looks like a literal secret.

    Prose ("Password: archiviata in ...") and code ("pwd = ComputeHash(x)",
    "password = config.Password") are words or expressions: no digit or symbol, or a call.
    """
    if "(" in value or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", value):
        return False
    return bool(re.search(r"[0-9!@#$%^&*+=?~|]", value))


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip("\"'")
    return not v or len(v) < 3 or bool(_PLACEHOLDER.match(v)) or REDACTED in v


def find_secrets(text: str, extra: list[re.Pattern] | None = None) -> list[dict]:
    """Every secret-looking span in text: [{kind, start, end, line}], value never returned.

    Overlapping hits are merged so a value matched by two detectors is reported once.
    """
    hits: list[tuple[int, int, str]] = []
    detectors = list(_DETECTORS) + [("custom", p, 0) for p in (extra or [])]
    for kind, rx, group in detectors:
        for m in rx.finditer(text):
            if group == -1:  # named-value: the first non-empty alternative group
                gi = next((i for i in (1, 2, 3) if m.group(i) is not None), None)
                if gi is None:
                    continue
                start, end, value = m.start(gi), m.end(gi), m.group(gi)
                if gi == 3 and not _looks_like_literal_secret(value):
                    continue  # an unquoted word or a code expression, not a literal
            elif kind == "connection-string" and not _looks_like_literal_secret(value.strip()):
                continue
            else:
                start, end, value = m.start(group), m.end(group), m.group(group)
            if _is_placeholder(value):
                continue
            hits.append((start, end, kind))
    hits.sort()
    merged: list[tuple[int, int, str]] = []
    for s, e, k in hits:
        if merged and s < merged[-1][1]:
            ps, pe, pk = merged[-1]
            merged[-1] = (ps, max(pe, e), pk)
        else:
            merged.append((s, e, k))
    return [{"kind": k, "start": s, "end": e, "line": text.count("\n", 0, s) + 1}
            for s, e, k in merged]


def redact(text: str, extra: list[re.Pattern] | None = None) -> tuple[str, list[dict]]:
    """Text with every detected secret value replaced by «REDACTED», and the hit list."""
    hits = find_secrets(text, extra)
    out, pos = [], 0
    for h in hits:
        out.append(text[pos:h["start"]])
        out.append(REDACTED)
        pos = h["end"]
    out.append(text[pos:])
    return "".join(out), hits


def compile_extra_patterns(patterns: list[str]) -> list[re.Pattern]:
    """Organisation-specific secret patterns (from the documentation profile)."""
    out = []
    for p in patterns:
        try:
            out.append(re.compile(p))
        except re.error as e:
            print(f"warning: ignoring invalid secret pattern {p!r}: {e}", file=sys.stderr)
    return out


# --------------------------------------------------------------------------------------
# Front matter and key-value blocks
# --------------------------------------------------------------------------------------
def split_front_matter(text: str) -> tuple[dict, str]:
    """(metadata, body) for a Markdown file that may open with a '---' block.

    The block is read by parse_simple_yaml (the documented subset, never PyYAML).
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            raw = "".join(lines[1:i])
            body = "".join(lines[i + 1:])
            return parse_simple_yaml(raw), body
    return {}, text


def parse_simple_yaml(raw: str) -> dict:
    """The YAML subset the skill documents, read the same way on every machine.

    The skill's own reader is always used (never PyYAML), so a front matter, a profile or a type
    file gives the same values everywhere, and text stays text: 'version: 1.10' is '1.10',
    'color: 000000' is '000000'. Supported:

        key: value          text; true/false/yes/no; whole numbers without a leading zero
        key: "value"        quotes removed; '# comment' after a value is dropped
        key: [a, b]         a list
        key:                followed by '- item' or '- Label: value' lines: a list,
                            or by indented 'sub: value' lines: one nested map
    Anything else (multi-line blocks, deeper nesting) is skipped with a warning.
    """
    data: dict = {}
    current: str | None = None
    skipped: list[str] = []
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # an empty 'key:' is "" until a list item or a nested line says what it holds
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and current is not None and (data.get(current) == "" or isinstance(data.get(current), list)):
            val = _strip_comment(item.group(1))
            # '- Label: value' is a cover field; a label never holds '|', so a table row
            # ('1.1 | date | author | Nota: x') stays text
            kv = re.match(r"^([^:\"'|]+?):\s+(.*)$", val)
            if not isinstance(data.get(current), list):
                data[current] = []
            data[current].append({kv.group(1).strip(): _scalar(kv.group(2))} if kv else _scalar(val))
            continue
        nested = re.match(r"^(\s+)([A-Za-z0-9_\-.]+):\s*(.*)$", line)
        if nested and current is not None and (data.get(current) == "" or isinstance(data.get(current), dict)):
            if not isinstance(data[current], dict):
                data[current] = {}
            val = _strip_comment(nested.group(3))
            if not val.strip() or val.strip()[:1] in "|>":
                skipped.append(line.strip())  # a third level or a block scalar
                continue
            data[current][nested.group(2)] = _scalar(val)
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), _strip_comment(m.group(2))
            current = key
            if val.strip()[:1] in ("|", ">"):
                skipped.append(line.strip())
                data[key] = ""
                continue
            data[key] = _scalar(val) if val.strip() else ""
            continue
        skipped.append(line.strip())
    if skipped:
        print(f"warning: {len(skipped)} front-matter line(s) outside the supported subset were skipped: "
              f"{'; '.join(s[:40] for s in skipped[:3])}", file=sys.stderr)
    return data


def _strip_comment(v: str) -> str:
    """'value   # comment' -> 'value'; '"quoted # text"  # comment' -> '"quoted # text"';
    a value that is only a comment -> ''. A '#' with no space before it is part of the value."""
    s = v.strip()
    if s[:1] in ("'", '"'):
        end = s.find(s[0], 1)
        if end > 0 and re.fullmatch(r"\s*(?:#.*)?", s[end + 1:]):
            return s[:end + 1]
        return s
    if s.startswith("#"):
        return ""
    return re.sub(r"\s+#(?:\s.*)?$", "", s)


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if len(v) >= 2 and v[0] == "[" and v[-1] == "]":
        return [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?(?:0|[1-9]\d*)", v):
        return int(v)
    return v


# --------------------------------------------------------------------------------------
# Language packs (assets/i18n/<lang>.json)
# --------------------------------------------------------------------------------------
I18N_DIR = Path(__file__).resolve().parent.parent / "assets" / "i18n"


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _flat_keys(d: dict, prefix: str = "") -> set[str]:
    keys = set()
    for k, v in d.items():
        keys |= _flat_keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {prefix + k}
    return keys


def lang_code(lang) -> str:
    """'it', 'IT', 'it-IT', 'pt_BR' -> 'it', 'it', 'it', 'pt'."""
    return re.split(r"[-_]", str(lang or "en").strip().lower())[0] or "en"


def available_langs() -> list[str]:
    return sorted(p.stem for p in I18N_DIR.glob("*.json"))


def _read_pack(path: Path) -> dict:
    import json
    try:
        data = json.loads(read_text(path))
    except (OSError, ValueError) as e:
        sys.exit(f"error: language pack {path} cannot be read: {e}")
    if not isinstance(data, dict):
        sys.exit(f"error: language pack {path} is not a JSON object")
    return data


def load_lang(lang="en", pack_path: Path | None = None, overrides: dict | None = None,
              quiet: bool = False) -> dict:
    """The language pack for lang, completed with English for every missing key.

    pack_path: a pack outside the skill (a language the skill does not ship, written in the
    work folder). overrides: single labels from the profile ('labels:' in render-style).
    """
    base = _read_pack(I18N_DIR / "en.json")
    code = lang_code(lang)
    if pack_path:
        pack = _read_pack(Path(pack_path))
    elif (I18N_DIR / f"{code}.json").is_file():
        pack = _read_pack(I18N_DIR / f"{code}.json")
    else:
        pack = {}
        if not quiet and code != "en":
            print(f"warning: no language pack for '{code}': English labels are used. Write one from "
                  f"{I18N_DIR / 'en.json'} and pass it with --lang-pack", file=sys.stderr)
    if pack and not quiet:
        missing = sorted(_flat_keys(base) - _flat_keys(pack) - {"lang", "name"})
        if missing:
            print(f"warning: language pack '{pack.get('lang', code)}' lacks {len(missing)} key(s), "
                  f"English used: {', '.join(missing[:8])}{' …' if len(missing) > 8 else ''}", file=sys.stderr)
    merged = _deep_merge(base, pack)
    if overrides:
        merged["labels"] = _deep_merge(merged["labels"], {k: v for k, v in overrides.items() if v})
    merged["lang"] = pack.get("lang", code) if pack else code
    return merged


def all_packs(extra: Path | None = None) -> list[dict]:
    """Every shipped pack, plus an extra one: the vocabulary check_doc.py accepts in any document."""
    packs = [_read_pack(p) for p in sorted(I18N_DIR.glob("*.json"))]
    if extra:
        packs.append(_read_pack(Path(extra)))
    return packs


def format_date(d, pack: dict) -> str:
    """A date in the pack's format ('dd/mm/yyyy', 'yyyy-mm-dd', 'dd.mm.yyyy')."""
    fmt = str(pack.get("date_format", "yyyy-mm-dd"))
    return fmt.replace("yyyy", f"{d.year:04d}").replace("mm", f"{d.month:02d}").replace("dd", f"{d.day:02d}")


def read_text(path: Path) -> str:
    """Read a text file as UTF-8 (BOM tolerated) or UTF-16 (BOM or NUL pattern, as some Windows
    exports write it), falling back to cp1252 for legacy files."""
    data = Path(path).read_bytes()
    if data[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"):
        return data.decode("utf-32", errors="replace")
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    sample = data[:2000]
    even = data[: len(data) // 2 * 2]  # a truncated last byte must not hide the encoding
    if len(sample) >= 4 and sample[1::2].count(0) > 0.4 * len(sample) / 2:
        try:
            return even.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    if len(sample) >= 4 and sample[0::2].count(0) > 0.4 * len(sample) / 2:
        try:
            return even.decode("utf-16-be")
        except UnicodeDecodeError:
            pass
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def configure_stdout() -> None:
    """Print UTF-8 on every console (Windows defaults to cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
