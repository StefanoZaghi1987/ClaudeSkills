#!/usr/bin/env python3
"""
robots.py — robots.txt rules as RFC 9309 defines them.

urllib.robotparser applies the first rule that matches, in file order, and has
no wildcards. So "Allow: /" above "Disallow: /private" let /private/a through,
and "Disallow: /*?sort=" blocked nothing. Here the longest matching rule wins,
an Allow wins a tie, and `*` and `$` work.

Same interface as RobotFileParser for what the crawl calls — parse(),
can_fetch(), crawl_delay(), request_rate() — so it is a drop-in replacement.
"""

import re
import urllib.parse
from typing import List, NamedTuple, Optional


class RequestRate(NamedTuple):
    requests: int
    seconds: int


class _Group:
    def __init__(self):
        self.agents: List[str] = []
        self.rules = []          # (allow, octet length, compiled pattern)
        self.delay: Optional[float] = None
        self.rate: Optional[RequestRate] = None


# Every printable ASCII character but the space stays as written, so an existing
# %xx escape is kept; a raw non-ASCII path in the file is encoded the way the URL
# already is. Hex digits are upper-cased after, so %c3 and %C3 compare equal.
_SAFE = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"


def _norm(path: str) -> str:
    quoted = urllib.parse.quote(path, safe=_SAFE)
    return re.sub(r"%[0-9a-fA-F]{2}", lambda m: m.group(0).upper(), quoted)


def _compile(pattern: str):
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile(regex + (r"\Z" if anchored else ""))


def _product_token(value: str) -> str:
    # "Googlebot/2.1 (+http://…)" names the product token "googlebot"
    return value.split("/")[0].split()[0].lower() if value.strip() else ""


class RobotsRules:
    def __init__(self):
        self._groups: List[_Group] = []

    def parse(self, lines) -> None:
        group, in_rules = None, False
        for line in lines:
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (s.strip() for s in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                # Consecutive user-agent lines share one group; one after a rule
                # opens the next group
                if group is None or in_rules:
                    group, in_rules = _Group(), False
                    self._groups.append(group)
                group.agents.append(_product_token(value))
            elif group is None:
                continue                       # a rule before any user-agent
            elif key in ("allow", "disallow"):
                in_rules = True
                if not value:
                    continue                   # "Disallow:" with no path allows all
                if not value.startswith(("/", "*")):
                    value = "/" + value
                value = _norm(value)
                group.rules.append((key == "allow", len(value), _compile(value)))
            elif key == "crawl-delay":
                in_rules = True
                try:
                    group.delay = float(value)
                except ValueError:
                    pass
            elif key == "request-rate":
                in_rules = True
                try:
                    n, s = value.split("/")
                    group.rate = RequestRate(int(n), int(s))
                except ValueError:
                    pass

    def _groups_for(self, agent: str) -> List[_Group]:
        """The groups naming this agent, combined; else the `*` groups, combined."""
        token = _product_token(agent)
        named = [g for g in self._groups if token in g.agents]
        return named or [g for g in self._groups if "*" in g.agents]

    def can_fetch(self, agent: str, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        if parsed.path == "/robots.txt":
            return True
        target = _norm((parsed.path or "/") + ("?" + parsed.query if parsed.query else ""))
        best = None                            # (length, allow) of the longest match
        for group in self._groups_for(agent):
            for allow, length, rx in group.rules:
                if rx.match(target) and (best is None or (length, allow) > best):
                    best = (length, allow)
        return True if best is None else best[1]

    def crawl_delay(self, agent: str) -> Optional[float]:
        return next((g.delay for g in self._groups_for(agent) if g.delay is not None), None)

    def request_rate(self, agent: str) -> Optional[RequestRate]:
        return next((g.rate for g in self._groups_for(agent) if g.rate is not None), None)
