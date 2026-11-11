#!/usr/bin/env python3
"""
crawl.py — site analysis and BFS traversal for web-site-to-document skill.
SiteAnalyzer probes a site once (reachability, JS rendering, robots, sitemap);
WebScraper then walks it, handing each page to the extractor.
"""

import codecs
import email.utils
import gzip
import io
import ipaddress
import os
import posixpath   # URL paths: os.path is ntpath on Windows and splits on "\\" too
import tempfile
import time
import urllib.parse
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup

from common import (BINARY_EXTENSIONS, USER_AGENT, _parse_link, get_hop_by_hop,
                    host_is_internal, read_capped, sparse)
from extract import ImageHandler, PageExtractor
from robots import RobotsRules

# Sentinel returned by _fetch_page for a reachable but non-HTML response:
# skip it without counting toward the consecutive-error stop
SKIP = object()

REQUEST_TIMEOUT = 20
# One pause-and-retry on HTTP 429. Without it ten throttled pages in a row spend
# the whole consecutive-error budget in ten seconds and end the crawl.
RETRY_AFTER_MAX = 60
RETRY_AFTER_MIN = 1
RETRY_AFTER_DEFAULT = 5
# What one page may read. A page is untrusted input like the images and the
# compressed sitemaps already bounded here: without a cap, an endless or huge
# response decides how much memory the run uses. No real page comes near this.
MAX_PAGE_BYTES = 20 * 1024 * 1024
# What the existence probe reads. Enough for the opening tag of any sitemap; the
# parse below re-fetches the file properly. read_capped is the wrong tool here —
# it answers None past its cap, so a small cap would make a large sitemap look
# absent whenever the server does not label it as XML.
SITEMAP_PROBE_BYTES = 64 * 1024
# Cap across every sitemap a site declares, not per sitemap
SITEMAP_MAX_URLS = 5000
# How many sitemaps one analysis may consider. Not the same bound as
# SITEMAP_MAX_URLS, which counts URLs collected: a child sitemap that returns
# none never advances that count, so an index listing 50000 empty children was
# fetched 50001 times — unpaced, because --rate-limit and Crawl-delay reach
# WebScraper and never the analyzer. Point those entries at one third-party
# address and the skill is a request cannon. Spent on every sitemap considered,
# refusals included, so a hostile index cannot flood the console either. 200 is
# past what a real split sitemap needs: a monthly index over ten years is ~120.
SITEMAP_MAX_FETCHES = 200
# robots.txt is an untrusted body like a page or an image. A real one is a few KB.
ROBOTS_MAX_BYTES = 1024 * 1024
# What a robots.txt that answered 5xx or 429 is read as
ROBOTS_DISALLOW_ALL = "User-agent: *\nDisallow: /\n"
# Hops a page fetch follows; each one is checked before it is requested
MAX_PAGE_REDIRECTS = 10
# What a compressed sitemap may expand to. The sitemap standard's own ceiling is
# 50 MB uncompressed, so a real one is never cut short by this; a hostile one is.
SITEMAP_MAX_BYTES = 50 * 1024 * 1024
# What a sitemap may be on the wire. A separate limit from the one above, which
# bounds what a compressed sitemap expands to: gzip amplifies (199 KB measured at
# 438 MB), so one guards memory after a transform and the other guards bytes off
# the network. They meet at 50 MB only because the standard sets both.
SITEMAP_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
# Product token only, for both robots.txt questions: the full User-Agent would
# match lines meant for browsers ("Mozilla")
ROBOTS_AGENT = "WebSiteToDocument"
# A Crawl-delay multiplies by every page, so its cap is tighter than the one-off
# RETRY_AFTER_MAX: 30s over 100 pages is already a 50-minute crawl. Above the cap
# the site is really saying "do not crawl me", and the console says so, so the
# agent can put that to the user instead of quietly pacing at the maximum.
CRAWL_DELAY_MAX = 30
# Connection failures in a row, with no answer from the host between them, that
# write a host off for the rest of the run
CONNECTION_FAILURES_TO_BLOCK = 3
# ponytail: hand-listed common two-level public suffixes, not the full Public
# Suffix List — extend the set if a user hits an unmapped country ending
SECOND_LEVEL_SUFFIXES = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "org.au",
    "co.jp", "or.jp", "ne.jp", "com.br", "com.mx", "co.nz", "co.in",
    "co.kr", "com.tr", "com.ar", "com.cn", "com.sg", "co.za",
}
# Hosting platforms that give every customer a subdomain: two subdomains of
# readthedocs.io are two unrelated projects, so for --scope subdomains the
# platform's domain is a public suffix like co.uk, never the site's own root
SHARED_HOST_SUFFIXES = {
    "github.io", "gitlab.io", "readthedocs.io", "netlify.app", "vercel.app",
    "pages.dev", "web.app", "firebaseapp.com", "appspot.com", "herokuapp.com",
    "azurewebsites.net", "azurestaticapps.net", "cloudfront.net", "blogspot.com",
    "gitbook.io", "onrender.com", "fly.dev", "surge.sh", "bitbucket.io",
}

# If visible text / total HTML length < this ratio → likely JS-rendered.
# 0.02, not lower: real SPA shells measure < 0.01, while text-rich static pages
# (measured counterexample: books.toscrape.com at 0.034) must not be flagged.
JS_RATIO_THRESHOLD = 0.02

# Minimum visible text chars below which we always flag as JS-rendered
# (catches tiny SPA shells that have < 8000 bytes of HTML)
JS_MIN_VISIBLE_CHARS = 200

# Sparse-content stop: no document gets built from a page set common.sparse
# calls empty, so there is nothing to gain from crawling the rest of the site at
# one request per second to fill it. The probe needs a second opinion before it
# may end a crawl — a navigation-only landing page also extracts to nothing, and
# correctly so, since nav is noise. Phase 1's JS verdict is that second opinion;
# both must agree.
SPARSE_PROBE_PAGES = 10
# Directory index documents fold to the directory URL: sites self-link with
# both /a/ and /a/index.html spellings of the same page
INDEX_DOCUMENTS = {
    "index.html", "index.htm", "index.php", "index.aspx", "index.jsp",
    "index.shtml", "default.html", "default.htm", "default.aspx", "default.php",
}


def _retry_after(value: Optional[str]) -> int:
    """Seconds to wait from a Retry-After header, bounded at both ends.

    The header has two legal forms — a number of seconds, or an HTTP-date that
    email.utils reads. Anything unreadable falls back to RETRY_AFTER_DEFAULT.

    The floor matters as much as the cap: a 0, a negative value or an HTTP-date
    already in the past (routine, with any clock skew) would otherwise re-ask a
    host that just said "slow down", with nothing at all in between.
    """
    try:
        secs = int(value)
    except (TypeError, ValueError):
        try:
            when = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return RETRY_AFTER_DEFAULT
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        secs = (when - datetime.now(timezone.utc)).total_seconds()
    return int(max(RETRY_AFTER_MIN, min(secs, RETRY_AFTER_MAX)))


def _asked_delay(rp) -> float:
    """Seconds between requests this robots.txt asks for, 0 when it asks for none.

    Crawl-delay and Request-rate are both floors on the gap between requests, so
    the slower of the two governs. Neither is in the original robots.txt standard,
    and both are widely honoured.
    """
    if rp is None:
        return 0.0
    try:
        delay = rp.crawl_delay(ROBOTS_AGENT) or 0
        rate = rp.request_rate(ROBOTS_AGENT)
    except Exception:
        return 0.0
    if rate and rate.requests > 0:
        delay = max(delay, rate.seconds / rate.requests)
    return float(delay)


def effective_delay(rp, rate_limit: float) -> float:
    """The gap this crawl leaves between requests, given one host's robots.txt.

    The caller's own --rate-limit is a floor, never a ceiling: someone asking to
    be slower than the site does stays slower. CRAWL_DELAY_MAX caps what the site
    asks for, not that floor — capping the floor too meant a --rate-limit of 60
    was quietly cut to 30 by a robots.txt asking for an hour.

    main.py reports the pace in Phase 1 and WebScraper enforces it, so the rule
    lives here rather than in each of them.
    """
    return max(rate_limit, min(_asked_delay(rp), CRAWL_DELAY_MAX))


def _path_prefixes(values: Optional[List[str]]) -> List[str]:
    """The user's URL path prefixes, normalized. Blank entries are dropped.

    A blank is dropped rather than kept as "/": SKILL.md hands the agent a command
    template to fill in, so an unset substitution arrives as an empty string, and
    "/" as an exclude prefix would match every page on the site — a one-page
    archive with nothing in the output saying why.

    The leading slash is optional. Git Bash on Windows rewrites any argument that
    looks like an absolute POSIX path into a Windows one, turning
    --include-path /docs/ into C:/Program Files/docs/ before Python ever sees it,
    so the slash-less spelling is the one that survives every shell.
    """
    out = []
    for v in values or []:
        v = v.strip()
        if v:
            out.append(v if v.startswith("/") else "/" + v)
    return out


def _probe_get(session, url, allow_internal: bool, **kwargs):
    """GET for the probes (homepage, robots.txt, sitemaps), redirects walked hop by
    hop: a site-controlled 302 must not send an unchecked request anywhere. Scope does
    not apply here — these probes are how the analyzer learns where the site lives (an
    apex redirecting to its new domain is the documented case) — but the trust zone
    does: an address on this machine's own network is refused, the first one included,
    unless the site the user named is on it (`allow_internal`). Judged on the user's
    start host, never on the URL itself: a robots.txt or sitemap URL is the site's
    choice, and a www. host it points at 127.0.0.1 must not pass as "asked for"."""

    def refused(hop):
        if allow_internal or not host_is_internal(urllib.parse.urlparse(hop).hostname or ""):
            return False
        what = "Internal address" if hop == url else "Redirects to an internal address"
        print(f"  ⏭️  {what}, skipped: {url}", flush=True)
        return True

    return get_hop_by_hop(session, url, refused, MAX_PAGE_REDIRECTS, **kwargs)


def _looks_like_html(body: bytes) -> bool:
    """Whether a body sent with no Content-Type is a web page."""
    head = body[:1024].lstrip(codecs.BOM_UTF8 + b" \t\r\n").lower()
    return head.startswith((b"<!doctype html", b"<html")) or b"<html" in head


def _strip_www(host: str) -> str:
    """www.example.com → example.com (one leading label only)."""
    return host[4:] if host.startswith("www.") else host


def _robots_text(session, origin: str, allow_internal: bool = False) -> Optional[str]:
    """robots.txt for one scheme://host, or None when it has none.

    One reader for both callers: SiteAnalyzer wants the text for its Sitemap:
    lines, WebScraper only the rules. Fetched through the session with a
    timeout, so a dead robots.txt cannot hang the whole crawl.

    Bounded, because robots.txt is an untrusted body like a page or an image and
    both of those are capped already. Past the cap the first ROBOTS_MAX_BYTES are
    parsed, up to their last full line: RFC 9309 asks for a parsing limit of at
    least 500 KiB, not for the file to be dropped.

    A server or network failure is a host that could not say what it allows, and
    RFC 9309 reads that as a complete disallow: a 5xx or 429 answer, or a fetch
    that still fails to connect or times out on its one retry. A 4xx answer means
    the site has no robots.txt.
    """
    url = f"{origin}/robots.txt"
    for attempt in (1, 2):
        try:
            resp = _probe_get(session, url, allow_internal, timeout=5, stream=True)
            if resp is None:
                return None                    # an internal address: refused, and said so
            if resp.status_code >= 500 or resp.status_code == 429:
                resp.close()
                print(f"  🤖 robots.txt answered HTTP {resp.status_code} — the whole host is "
                      f"treated as disallowed (RFC 9309): {origin}", flush=True)
                return ROBOTS_DISALLOW_ALL
            if resp.status_code != 200:
                resp.close()
                return None
            raw = read_capped(resp, ROBOTS_MAX_BYTES + 1, truncate=True)
            if len(raw) > ROBOTS_MAX_BYTES:
                cut = raw.rfind(b"\n", 0, ROBOTS_MAX_BYTES)
                raw = raw[:cut + 1] if cut >= 0 else raw[:ROBOTS_MAX_BYTES]
                print(f"  ⏭️  robots.txt over {ROBOTS_MAX_BYTES // 1024}KB, the rest "
                      f"ignored: {url}", flush=True)
            # utf-8-sig: a BOM left in front of the first "User-agent" hid the
            # whole first group, its rules and its Crawl-delay
            return raw.decode("utf-8-sig", errors="replace")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError, TimeoutError) as e:
            if attempt == 2:
                print(f"  🤖 robots.txt unreachable ({type(e).__name__}) — the whole host "
                      f"is treated as disallowed (RFC 9309): {origin}", flush=True)
                return ROBOTS_DISALLOW_ALL
        except Exception:
            return None


def _sitemap_lines(robots_text: str) -> List[str]:
    """Every sitemap robots.txt declares. Sites routinely split them by section
    (sitemap-posts.xml, sitemap-pages.xml); keeping only the last loses the rest."""
    declared = (ln.split(":", 1)[1].strip() for ln in robots_text.splitlines()
                if ln.lower().startswith("sitemap:"))
    return [url for url in declared if url]


# ─── Site Analyzer ─────────────────────────────────────────────────────────────

class SiteAnalyzer:
    """Quick site analysis: reachability, JS detection, robots, sitemap."""

    # __init__ always sets these; they only serve an analyzer the checks build
    # through __new__, which should not have to know about a budget or a pace.
    # The host anchor gets no such default on purpose: an unset budget is still
    # a bound, while an unset host would be a guard that passes everything.
    _sitemap_fetches = SITEMAP_MAX_FETCHES
    rate_limit = 0.0
    _sitemap_paced = False
    allow_internal = False

    def __init__(self, url: str, rate_limit: float = 0.0):
        self.url = url
        # The host a sitemap has to belong to. analyze() refreshes it from the
        # address the site answers on, before any sitemap is read.
        self.host = _strip_www(urllib.parse.urlparse(url).netloc.lower())
        self._sitemap_fetches = SITEMAP_MAX_FETCHES
        self.rate_limit = rate_limit
        # The trust zone, drawn as WebScraper draws it: from the site the user named
        self.allow_internal = host_is_internal(urllib.parse.urlparse(url).hostname or "")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def _pace_sitemap(self) -> None:
        """Wait between sitemap fetches, at the pace the rest of the run keeps.

        The analyzer's other requests are four, whatever the site: a burst that
        needs no pacing. Sitemaps are the one place it can issue many — up to
        SITEMAP_MAX_FETCHES, every one of them to the site's own host now — so
        this is where --rate-limit and Crawl-delay have to reach. WebScraper and
        ImageHandler both paced already; this was the traffic that did not.

        Never before the first, so a site with one sitemap waits for nothing.
        """
        if self._sitemap_paced and self.rate_limit > 0:
            time.sleep(self.rate_limit)
        self._sitemap_paced = True

    def analyze(self, read_sitemap: bool = True) -> Dict[str, Any]:
        """Probe the site. `read_sitemap` False stops before the sitemap parse.

        Reachability, the JavaScript verdict and robots.txt always run — they
        are four requests and every caller needs them. The sitemap parse is the
        one part that can run to hundreds of paced fetches, and scrape() seeds
        from a sitemap only on an unlimited-depth run, so a depth-limited build
        used to spend that hour on a result nothing could read. One rule, stated
        here rather than twice.
        """
        result = {
            "reachable": False, "js_rendered": False,
            "has_robots": False,
            "has_sitemap": False, "sitemap_url": None,
            "sitemap_page_count": 0, "sitemap_urls": [],
            "homepage_links": 0,
            # The status the homepage answered with, when it answered at all. A
            # host that refuses is not a host that is down, and SKILL.md keys
            # different guidance on each.
            "status": None,
            "error": None, "final_url": self.url,
        }

        # Reachability + JS detection
        try:
            resp = _probe_get(self.session, self.url, self.allow_internal,
                              timeout=REQUEST_TIMEOUT, stream=True)
            if resp is None:
                result["error"] = "redirects to an address on this machine's own network"
                return result
            if resp.status_code == 429:
                # Throttling an unknown crawler on its first request is normal;
                # without this the whole run ends here, reporting a live site as
                # unreachable, and WebScraper's own retry is never reached
                wait = _retry_after(resp.headers.get("Retry-After"))
                resp.close()
                print(f"  ⏳ HTTP 429 on the first request, waiting {wait}s and asking once more", flush=True)
                time.sleep(wait)
                resp = _probe_get(self.session, self.url, self.allow_internal,
                                  timeout=REQUEST_TIMEOUT, stream=True)
                if resp is None:
                    result["error"] = "redirects to an address on this machine's own network"
                    return result
            result["status"] = resp.status_code
            resp.raise_for_status()
            result["reachable"] = True
            result["final_url"] = resp.url
            # The homepage is an untrusted body, and the crawl already refuses a
            # page past this cap. stream=True is what makes the cap real: without
            # it requests buffers the whole body before read_capped is reached.
            # Reachable even so, because the host answered — calling it
            # unreachable would send the agent down SKILL.md's stop-here branch
            # instead of naming what happened.
            body = read_capped(resp, MAX_PAGE_BYTES)
            if body is None:
                result["error"] = (f"homepage over {MAX_PAGE_BYTES // 1024 // 1024}MB "
                                   "— not analysed")
                return result
            soup = BeautifulSoup(body, "lxml")
            visible_text = soup.get_text(strip=True)
            # JS detection: either very few visible chars overall, or low text/html ratio
            few_chars = len(visible_text) < JS_MIN_VISIBLE_CHARS
            # byte length ≈ latin-1 text length; only the ratio matters
            low_ratio = len(body) > 2000 and len(visible_text) < len(body) * JS_RATIO_THRESHOLD
            if few_chars or low_ratio:
                result["js_rendered"] = True
            result["homepage_links"] = self._count_links(soup, resp.url)
        except Exception as e:
            result["error"] = str(e)
            return result

        parsed = urllib.parse.urlparse(result["final_url"])
        base = f"{parsed.scheme}://{parsed.netloc}"
        # Anchor the sitemap host on the address the site answers on, not the one
        # the user typed. An apex that redirects (angular.io → angular.dev) serves
        # its robots.txt from the new host and names its sitemaps there, so an
        # un-refreshed anchor would refuse every one of them.
        self.host = _strip_www(parsed.netloc.lower())

        # Robots.txt
        declared_sitemaps: List[str] = []
        robots_text = _robots_text(self.session, base, self.allow_internal)
        if robots_text is not None:
            result["has_robots"] = True
            rp = RobotsRules()
            rp.parse(robots_text.splitlines())
            result["_rp"] = rp  # consumed by WebScraper; "_" keeps it out of the JSON summary
            # The pace this host asks for governs the sitemap fetches below too:
            # they are requests to it like any other, and they are the only ones
            # here that can run into the hundreds. Read before they are spent,
            # which is the whole reason robots.txt is fetched first.
            self.rate_limit = effective_delay(rp, self.rate_limit)
            declared_sitemaps = _sitemap_lines(robots_text)
            if declared_sitemaps:
                result["has_sitemap"] = True
                result["sitemap_url"] = declared_sitemaps[0]

        # Everything below this line is sitemap work, so one gate covers the
        # probe and the parse alike
        if not read_sitemap:
            return result

        # Sitemap fallback
        if not result["has_sitemap"]:
            for sm_path in ["/sitemap.xml", "/sitemap_index.xml"]:
                try:
                    sm = _probe_get(self.session, f"{base}{sm_path}", self.allow_internal,
                                    timeout=5, stream=True)
                    if sm is None:
                        continue
                    # One chunk: this only has to see the opening tag. Reading
                    # the whole body downloaded up to 50 MB, threw it away, and
                    # left _parse_sitemap to fetch the same file again.
                    head = next(sm.iter_content(SITEMAP_PROBE_BYTES), b"")
                    sm.close()
                    if sm.status_code == 200 and ("xml" in sm.headers.get("content-type", "") or b"<urlset" in head or b"<sitemapindex" in head):
                        result["has_sitemap"] = True
                        result["sitemap_url"] = f"{base}{sm_path}"
                        break
                except Exception:
                    pass

        # Parse every declared sitemap, under one shared cap
        targets = declared_sitemaps or ([result["sitemap_url"]] if result["sitemap_url"] else [])
        urls: List[str] = []
        for target in targets:
            if len(urls) >= SITEMAP_MAX_URLS:
                break
            urls.extend(self._parse_sitemap(target, max_urls=SITEMAP_MAX_URLS - len(urls)))
        result["sitemap_urls"] = list(dict.fromkeys(urls))
        result["sitemap_page_count"] = len(result["sitemap_urls"])

        return result

    @staticmethod
    def _count_links(soup: BeautifulSoup, base_url: str) -> int:
        """Distinct same-domain pages the homepage links to.

        A floor for the page estimate, and the only one available on a site with
        no sitemap. Counts the default scope only — a subdomain or custom scope
        reaches more, never fewer — and folds www, fragments and binaries the way
        the crawl does, so the figure means what the crawl will act on.
        """
        host = _strip_www(urllib.parse.urlparse(base_url).netloc.lower())
        found = set()
        for a in soup.find_all("a", href=True):
            p = _parse_link(base_url, a["href"])
            if p is None:
                continue
            if p.scheme not in ("http", "https") or _strip_www(p.netloc.lower()) != host:
                continue
            if posixpath.splitext(p.path.lower())[1] in BINARY_EXTENSIONS:
                continue
            found.add(p._replace(fragment="").geturl())
        return len(found)

    def _sitemap_host_ok(self, url: str) -> bool:
        """True when a sitemap is the analysed site's own to declare.

        The sitemap protocol scopes a sitemap to its own location, and a
        cross-host one counts only after out-of-band verification — so refusing
        an off-host sitemap is the protocol, not a heuristic. Without this the
        archived site chose what this machine fetched: 127.0.0.1:8080 and
        169.254.169.254 both reached, measured, from --analyze-only alone.

        One leading www. folds, because example.com/robots.txt naming
        www.example.com/sitemap.xml is routine.

        ponytail: the start host only. SiteAnalyzer is built from a URL and knows
        no --scope, so a subdomain-scoped run loses a sitemap on a sibling host
        and reaches those pages by following links instead. Pass the scope in if
        a real site turns up that needs it.
        """
        p = _parse_link(url, "")
        return p is not None and _strip_www(p.netloc.lower()) == self.host

    def _parse_sitemap(self, sitemap_url: str, depth: int = 0,
                       max_urls: int = SITEMAP_MAX_URLS) -> List[str]:
        # Both bounds sit here, the one point every caller routes through: the
        # robots.txt Sitemap: lines above, and the <sitemap> recursion below.
        if depth > 3 or self._sitemap_fetches <= 0:
            return []
        self._sitemap_fetches -= 1
        if self._sitemap_fetches == 0:
            print(f"  ⏭️  Sitemap budget ({SITEMAP_MAX_FETCHES}) spent — ignoring "
                  "the rest", flush=True)
        if not self._sitemap_host_ok(sitemap_url):
            print(f"  ⏭️  Sitemap on another host, skipped: {sitemap_url}", flush=True)
            return []
        urls = []
        try:
            self._pace_sitemap()
            # One line per sitemap, like the crawl's one line per page. A paced
            # fan-out is otherwise a silent wait: 200 sitemaps on a host asking
            # for 30s is an hour of Phase 1 with nothing on screen.
            print(f"  📋 Reading sitemap: {sitemap_url}", flush=True)
            resp = _probe_get(self.session, sitemap_url, self.allow_internal,
                              timeout=10, stream=True)
            # A .xml.gz sitemap is a gzip file, not a gzip Content-Encoding, so
            # requests hands the body over still compressed and the XML parser
            # finds nothing in it. www.gnu.org publishes a sitemap index pointing
            # only at sitemap0.xml.gz, so its whole sitemap read as zero pages.
            # A corrupt archive raises here and the except below answers it the
            # way an unreadable sitemap has always been answered: no URLs.
            #
            # Round 13 bounded the expansion, having recognised a sitemap as
            # untrusted input, but left the download unbounded — so a plain 2 GB
            # sitemap still decided how much memory the run used. Its own limit,
            # not the expansion's: see SITEMAP_MAX_DOWNLOAD_BYTES.
            body = read_capped(resp, SITEMAP_MAX_DOWNLOAD_BYTES)
            if body is None:
                print(f"  ⏭️  Sitemap over {SITEMAP_MAX_DOWNLOAD_BYTES // 1024 // 1024}MB, "
                      f"skipped: {sitemap_url}", flush=True)
                return []
            if body[:2] == b"\x1f\x8b":
                # Bounded on purpose. A sitemap is untrusted input, and an
                # unbounded gzip.decompress lets the site decide how much
                # memory this run uses — 199 KB of gzipped zeros measured at
                # 438 MB peak, the same hazard ImageHandler streams to avoid.
                # read() stops at the cap instead, and bs4's XML parser
                # recovers, so a truncated file still yields what parsed.
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(
                    SITEMAP_MAX_BYTES)
            soup = BeautifulSoup(body, "lxml-xml")
            # Sitemap index
            for sm in soup.find_all("sitemap"):
                loc = sm.find("loc")
                if loc and len(urls) < max_urls:
                    urls.extend(self._parse_sitemap(loc.text.strip(), depth + 1, max_urls - len(urls)))
            # URL set
            for url_tag in soup.find_all("url"):
                loc = url_tag.find("loc")
                if loc:
                    urls.append(loc.text.strip())
                if len(urls) >= max_urls:
                    break
        except Exception:
            pass
        return urls


# ─── Web Scraper ───────────────────────────────────────────────────────────────

class WebScraper:
    """BFS scraper: traverses site tree and returns list of page dicts."""

    # Empty tuples, not lists: __init__ replaces them and nothing ever mutates
    # them, so there is no shared-default hazard. Class-level so an unconfigured
    # filter is simply empty — the checks build a scraper through __new__ to skip
    # the robots.txt fetch, and a filter is not something they should have to know
    # about to stay green.
    include_paths = ()
    exclude_paths = ()
    # Same reason: __init__ always sets both, so these only serve a scraper the
    # checks build through __new__, which should not have to know about pacing
    rate_limit = 0.0
    image_handler = None
    allow_internal = False
    _start_norm = None
    _conn_failures = None

    def __init__(
        self,
        base_url: str,
        scope: str = "same",
        allowed_domains: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
        max_pages: Optional[int] = None,
        rate_limit: float = 1.0,
        embed_images: bool = True,
        work_dir: Optional[str] = None,
        robots: Optional[RobotsRules] = None,
        js_rendered: bool = False,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        self.base_url = base_url
        self.base_domain = urllib.parse.urlparse(base_url).netloc.lower()
        self.scope = scope
        self.allowed_domains = [d.lower() for d in (allowed_domains or [])]
        # URL path prefixes, for archiving one section of a large site. Applied
        # in _in_scope, the one gate every candidate URL passes through, so they
        # narrow the sitemap seeding as well as the link following.
        self.include_paths = _path_prefixes(include_paths)
        self.exclude_paths = _path_prefixes(exclude_paths)
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.rate_limit = rate_limit
        # Phase 1's verdict, and the only thing that lets the sparse probe below
        # end a crawl early
        self.js_rendered = js_rendered
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="w2d_")

        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

        # robots.txt is a per-host file, and a subdomain or custom scope crawls
        # more than one host: one parser per host, fetched on first visit.
        # A host maps to None when it has no robots.txt or the fetch failed.
        self._robots_by_host: Dict[str, Optional[RobotsRules]] = {}
        if robots:
            # Reuse the analyzer's parse for the start host: one fetch per run
            self._robots_by_host[self.base_domain] = robots

        images_dir = os.path.join(self.work_dir, "images")
        # A picture may come from this machine's own network only when the site
        # being archived is already on it — a docs server on localhost keeps its
        # own pictures, while a public page cannot aim the download inward.
        allow_internal = host_is_internal(
            urllib.parse.urlparse(base_url).hostname or "")
        # The same zone bounds where a page's redirect may lead
        self.allow_internal = allow_internal
        # Held, not just handed on: _raise_delay lifts its pace with the crawl's
        img_handler = (ImageHandler(self.session, images_dir, rate_limit,
                                    allow_internal=allow_internal)
                       if embed_images else None)
        self.image_handler = img_handler
        self.extractor = PageExtractor(img_handler)

        self.visited: Set[str] = set()
        self.blocked_domains: Set[str] = set()
        self._conn_failures: Dict[str, int] = {}
        # Recorded in the document: a reader months later cannot otherwise tell
        # a page the site withheld from a page that never existed
        self.robots_excluded: List[str] = []
        self.consecutive_errors = 0
        self.total_errors = 0

        # The analyzer already fetched the start host's robots.txt, so
        # _allowed_by_robots never fetches for that host — its pace has to be
        # taken here as well, or the commonest case of all is missed
        if robots:
            self._raise_delay(robots, self.base_domain)

    def _raise_delay(self, rp, host: str) -> None:
        """Adopt a host's Crawl-delay for the rest of the run, when it is slower.

        robots.txt is a per-host file; the crawl paces itself globally — one float,
        shared with the image downloader. Raising it to the slowest host seen is
        slower than each quiet host requires and never faster than any host asked,
        which is the side to err on. Only ever raised, so the pace cannot fall back
        halfway through a run.
        """
        pace = effective_delay(rp, self.rate_limit)
        if pace <= self.rate_limit:
            return
        self.rate_limit = pace
        if self.image_handler:
            self.image_handler.rate_limit = pace
        asked = _asked_delay(rp)
        capped = " — the maximum this crawl waits" if asked > CRAWL_DELAY_MAX else ""
        print(f"  🐢 {host} asks for {asked:g}s between requests — pacing at "
              f"{pace:g}s{capped}", flush=True)

    def _fetch_robots(self, origin: str):
        """The robots.txt rules for one scheme://host, or None when it has none."""
        text = _robots_text(self.session, origin, self.allow_internal)
        if text is None:
            return None
        rp = RobotsRules()
        rp.parse(text.splitlines())
        return rp

    def _allowed_by_robots(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()
        # "not in", not .get(): None is a cached answer ("this host has none"),
        # not a missing entry, and re-fetching it every page would be one extra
        # request per URL on a site without robots.txt
        if host not in self._robots_by_host:
            rp = self._fetch_robots(f"{parsed.scheme}://{parsed.netloc}")
            self._robots_by_host[host] = rp
            self._raise_delay(rp, host)
        rp = self._robots_by_host[host]
        if not rp:
            return True
        try:
            return rp.can_fetch(ROBOTS_AGENT, url)
        except Exception:
            return True

    def _in_scope(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if not domain or parsed.scheme not in ("http", "https"):
            return False
        if not self._domain_ok(domain):
            return False
        # The path a prefix is judged against is the normalized one, the same
        # spelling the visited set uses. A site links its section index as
        # /docs as often as /docs/, and the raw path made those two different
        # pages: --include-path docs/ dropped the index, and --exclude-path
        # docs/legacy/ archived the branch's index it was meant to withhold.
        # The domain is judged on the raw netloc above, because _normalize
        # folds www. and --allowed-domains www.foo.com then matches nothing.
        return self._path_ok(urllib.parse.urlparse(self._normalize(url)).path)

    def _domain_ok(self, domain: str) -> bool:
        if self.scope == "same":
            # Fold one leading "www.": sites mix example.com and www.example.com
            # in their internal links, and both forms are the same site
            return _strip_www(domain) == _strip_www(self.base_domain)
        if self.scope == "subdomains":
            root = self._registrable_root()
            return domain in (self.base_domain, root) or domain.endswith("." + root)
        if self.scope == "custom" and self.allowed_domains:
            return any(domain == d or domain.endswith("." + d) for d in self.allowed_domains)
        # custom scope with no --allowed-domains falls back to the "same" rule, www
        # folding included — a stricter rule of its own would archive one page of a
        # site that mixes example.com and www.example.com in its own links
        return _strip_www(domain) == _strip_www(self.base_domain)

    def _path_ok(self, path: str) -> bool:
        """Prefix match against the user's path filters.

        Exclude wins over include, so "/docs/ but not /docs/legacy/" is one pair
        of arguments rather than a list of every branch to keep. An empty include
        list means any path. Case-sensitive, like _normalize, which keeps path
        case because many servers serve distinct pages at /Docs and /docs.
        """
        if any(path.startswith(p) for p in self.exclude_paths):
            return False
        return not self.include_paths or any(path.startswith(p) for p in self.include_paths)

    def _registrable_root(self) -> str:
        """help.example.co.uk → example.co.uk (three labels: the last two are a
        two-level public suffix), help.example.com → example.com, and
        proj.readthedocs.io → proj.readthedocs.io (a shared host's customer). An
        address is its own root: 192.168.1.10 has no parent the crawl may widen to."""
        host = urllib.parse.urlsplit("//" + self.base_domain).hostname or self.base_domain
        try:
            ipaddress.ip_address(host)
            return self.base_domain
        except ValueError:
            pass
        names, labels = host.split("."), self.base_domain.split(".")
        tail = ".".join(names[-2:])
        n = 3 if len(names) > 2 and tail in SECOND_LEVEL_SUFFIXES | SHARED_HOST_SUFFIXES else 2
        return ".".join(labels[-n:])

    def _normalize(self, url: str) -> str:
        p = urllib.parse.urlparse(url)
        # Fold one leading "www." too: the apex and its www form are the same
        # page in practice, so both variants share one visited-set key
        netloc = _strip_www(p.netloc.lower())
        p = p._replace(fragment="", scheme=p.scheme.lower(), netloc=netloc)
        # Remove common session/tracking params
        if p.query:
            # keep_blank_values: "?x=&y=1" and "?y=1" are different pages
            params = urllib.parse.parse_qs(p.query, keep_blank_values=True)
            for k in list(params.keys()):
                # lang/locale stay: distinct localized pages (?lang=it vs ?lang=en) must not merge
                if k.lower() in ("sid", "session", "utm_source", "utm_medium",
                                  "utm_campaign", "ref", "source"):
                    del params[k]
            p = p._replace(query=urllib.parse.urlencode(params, doseq=True))
        # Normalize trailing slash for directories. An empty path (the bare
        # domain) must share the "/" key too, or the homepage is scraped twice
        path = p.path
        if not path or (not posixpath.splitext(path)[1] and not path.endswith("/")):
            path += "/"
            p = p._replace(path=path)
        # Directory index documents fold to the directory URL: sites self-link
        # with both /a/ and /a/index.html spellings of the same page
        head, _, last = path.rpartition("/")
        if last.lower() in INDEX_DOCUMENTS:
            p = p._replace(path=head + "/")
        # Keep path/query case: many servers serve distinct pages at /Docs and /docs
        return urllib.parse.urlunparse(p)

    def scrape(self, sitemap_urls: Optional[List[str]] = None) -> List[Dict]:
        """Main entry: BFS traversal. Returns list of page dicts."""
        pages: List[Dict] = []
        queue: deque = deque()

        start_norm = self._normalize(self.base_url)
        self._start_norm = start_norm
        self.visited.add(start_norm)
        queue.append((self.base_url, 0))

        # Seed from sitemap only on unlimited-depth runs: a depth limit means
        # "N hops of links", and sitemap URLs would all enter the queue at
        # depth 0, ignoring that limit
        if sitemap_urls and self.max_depth is None:
            print(f"  📋 Seeding from sitemap: {len(sitemap_urls)} URLs", flush=True)
            for u in sitemap_urls:
                # A <loc> value is untrusted input: an unparseable one is skipped,
                # never allowed to end the run with a traceback
                try:
                    n, in_scope = self._normalize(u), self._in_scope(u)
                except ValueError:
                    continue
                if n not in self.visited and in_scope:
                    self.visited.add(n)
                    queue.append((u, 0))
        elif sitemap_urls:
            print("  ℹ️  Sitemap available but not seeded: depth-limited run follows links only.", flush=True)

        page_count = 0

        while queue:
            url, depth = queue.popleft()

            # Limits
            if self.max_pages is not None and page_count >= self.max_pages:
                print(f"  ℹ️  Max pages limit ({self.max_pages}) reached.", flush=True)
                break
            if self.max_depth is not None and depth > self.max_depth:
                continue

            # Skip binaries
            ext = posixpath.splitext(urllib.parse.urlparse(url).path.lower())[1]
            if ext in BINARY_EXTENSIONS:
                continue

            # A domain written off after repeated connection failures is out for the rest of the
            # run: no repeat requests, no repeat noise, and — per the error contract —
            # no consecutive-error budget spent on a host that is simply down. Lower-cased on
            # both sides: a site self-linking with an upper-case host is one host here, while
            # the failure records the prepared URL's spelling (lower-case)
            if urllib.parse.urlparse(url).netloc.lower() in self.blocked_domains:
                continue

            if self._page_internal_refused(url):
                continue

            # Robots.txt check
            if not self._allowed_by_robots(url):
                print(f"  🤖 robots.txt disallows: {url}", flush=True)
                self.robots_excluded.append(url)
                continue

            page_count += 1
            print(f"  [{page_count}] depth={depth} → {url}", flush=True)

            page = self._fetch_page(url, depth)

            # One sleep for every request attempt, error paths included: a site
            # answering 403 or 429 must not be hit at full speed
            if self.rate_limit > 0:
                time.sleep(self.rate_limit)

            if page is SKIP:
                # Reachable but no page to archive: not HTML, or past the size
                # cap. Not an error — release the slot the progress line took.
                # _fetch_page names the reason, where the reason is known.
                page_count -= 1
                continue

            if page is None:
                if urllib.parse.urlparse(url).netloc.lower() in self.blocked_domains:
                    page_count -= 1  # blocked domain: excluded, not an error
                    continue
                self.consecutive_errors += 1
                self.total_errors += 1
                print(f"  ⚠️  Error (consecutive: {self.consecutive_errors}, total: {self.total_errors})", flush=True)
                if self.consecutive_errors >= 10:
                    print("  ❌ 10 consecutive errors — stopping scrape.", flush=True)
                    break
                continue

            # The response may come from a different URL than the one requested:
            # register the final spelling too, or a direct link to it is archived
            # a second time. Belt-and-braces: with the hop walk above, scope and
            # robots were already checked on every hop, so these two re-checks are
            # unreachable on the real fetch path — they stand guard over _fetch_page
            # itself, the seam a stubbed or future fetch path can bypass.
            # ponytail: the <link rel=canonical> hint stays out of this — sites
            # get it wrong often enough that trusting it would drop real pages
            final_url = page.get("url") or url
            final_key = self._normalize(final_url)
            if final_key != self._normalize(url):
                # A redirect means the address that answered is not the address
                # that was asked for, so both gates that ran before the fetch
                # have to run again on the one that answered. Skips, not errors:
                # a site that redirects many of its links must not spend the
                # consecutive-error budget on them.
                #
                # Scope exempts the start URL, which is archived wherever it
                # lands — it is what the crawl follows links from, and
                # --include-path deliberately does not gate it. robots.txt
                # exempts nothing: it is the site's rule, not the user's
                # preference, and the pre-fetch check already covers every page.
                if self._normalize(url) != start_norm and not self._in_scope(final_url):
                    # Without this an outbound-link redirector (/out?url=…) puts
                    # arbitrary third-party pages into a same-domain archive.
                    print(f"  ↪️  Redirects outside the scope, skipped: {url}", flush=True)
                    page_count -= 1
                    continue
                if not self._allowed_by_robots(final_url):
                    print(f"  🤖 robots.txt disallows the redirect target: {final_url}", flush=True)
                    self.robots_excluded.append(final_url)
                    page_count -= 1
                    continue
                if final_key in self.visited:
                    print(f"  ⏭️  Redirects to a page already archived, skipped: {url}", flush=True)
                    page_count -= 1
                    continue
                self.visited.add(final_key)

            self.consecutive_errors = 0
            pages.append(page)

            if (self.js_rendered and len(pages) == SPARSE_PROBE_PAGES
                    and sparse(pages)):
                print(f"  ⏹️  First {SPARSE_PROBE_PAGES} pages of this "
                      "JavaScript-rendered site are near-empty — stopping the "
                      "crawl here.", flush=True)
                break

            # Enqueue child links
            next_depth = depth + 1
            if self.max_depth is None or next_depth <= self.max_depth:
                for link in page.get("links", []):
                    n = self._normalize(link)
                    if n not in self.visited and self._in_scope(link):
                        self.visited.add(n)
                        queue.append((link, next_depth))

        return pages

    def _page_internal_refused(self, url: str) -> bool:
        """True when a directly-requested page sits on this machine's own network while
        the archived site does not. The redirect hops get the same question inside
        _hop_refused; without this, a custom scope naming an internal host fetched its
        pages directly while pictures from the same address were refused."""
        if self.allow_internal:
            return False
        if not host_is_internal(urllib.parse.urlparse(url).hostname or ""):
            return False
        print(f"  ⏭️  Page on an internal address, skipped: {url}", flush=True)
        return True

    def _hop_refused(self, hop: str, requested: str, exempt_scope: bool) -> bool:
        """True when a redirect may not be followed to `hop`; says why.

        The address the crawl asked for passed these gates before the fetch;
        every later hop passes them before it is requested. The start URL is
        archived wherever it lands, so it skips the scope gate only.
        """
        if hop == requested:
            return False
        if not exempt_scope and not self._in_scope(hop):
            print(f"  ↪️  Redirects outside the scope, skipped: {requested}", flush=True)
            return True
        # Before robots: fetching a hop's robots.txt is already a request to it
        if not self.allow_internal and host_is_internal(urllib.parse.urlparse(hop).hostname or ""):
            print(f"  ⏭️  Redirects to an internal address, skipped: {requested}", flush=True)
            return True
        if not self._allowed_by_robots(hop):
            print(f"  🤖 robots.txt disallows the redirect target: {hop}", flush=True)
            self.robots_excluded.append(hop)
            return True
        return False

    def _fetch_page(self, url: str, depth: int, retry: bool = True) -> Optional[Dict]:
        try:
            # stream=True, so the headers decide whether the body is worth
            # reading at all. Without it requests read every body in full first,
            # and a thumbnail linking to its own full-size JPEG had that JPEG
            # downloaded and thrown away — once per picture, at the crawl's pace,
            # with the site paying the bandwidth. close() on every path that
            # does not read the body, as ImageHandler does.
            exempt = self._normalize(url) == self._start_norm
            resp = get_hop_by_hop(self.session, url,
                                  lambda hop: self._hop_refused(hop, url, exempt),
                                  MAX_PAGE_REDIRECTS, timeout=REQUEST_TIMEOUT, stream=True)
            if resp is None:
                return SKIP                    # _hop_refused said why
            if self._conn_failures:
                self._conn_failures.pop(
                    urllib.parse.urlparse(getattr(resp, "url", None) or url).netloc.lower(), None)
            if retry and (resp.status_code == 429 or (
                    resp.status_code == 503 and resp.headers.get("Retry-After"))):
                # 429 is the site asking for a slower pace, not a broken page,
                # and a 503 that names a Retry-After is a server saying when to
                # come back: wait the interval it names and give the page one
                # more chance
                wait = _retry_after(resp.headers.get("Retry-After"))
                resp.close()
                print(f"  ⏳ HTTP {resp.status_code}, waiting {wait}s before one retry: {url}",
                      flush=True)
                time.sleep(wait)
                return self._fetch_page(url, depth, retry=False)
            if resp.status_code != 200:
                # Name the status: 403 and 429 mean bot-protection or throttling,
                # which call for a different strategy than a plain 404
                resp.close()
                print(f"  ⚠️  HTTP {resp.status_code}: {url}", flush=True)
                return None
            ct = resp.headers.get("content-type", "")
            # No Content-Type at all is a server that did not say, not one that
            # said "not HTML": the body decides, below
            if ct and "html" not in ct:
                resp.close()
                print(f"  ⏭️  Not HTML, skipped: {url}", flush=True)
                return SKIP
            body = read_capped(resp, MAX_PAGE_BYTES)
            if body is None:
                print(f"  ⏭️  Page over {MAX_PAGE_BYTES // 1024 // 1024}MB, "
                      f"skipped: {url}", flush=True)
                return SKIP
            if not ct and not _looks_like_html(body):
                print(f"  ⏭️  Not HTML, skipped: {url}", flush=True)
                return SKIP
            # A header charset is authoritative (pages may declare an encoding
            # only there); with none, decoding would fall back to latin-1, so
            # hand bs4 the bytes and let the <meta charset> decide
            html = body
            if "charset" in ct.lower():
                try:
                    html = body.decode(resp.encoding or "utf-8", errors="replace")
                except LookupError:
                    pass   # the header named a codec Python has not got: use bytes
            page = self.extractor.extract(html, resp.url)
            page["depth"] = depth
            return page
        except requests.exceptions.ConnectionError as e:
            # ConnectTimeout subclasses ConnectionError: one slow connect is a
            # per-request failure, never grounds for writing off a whole domain
            if isinstance(e, requests.exceptions.Timeout):
                print(f"  ⚠️  Connect timeout: {url}", flush=True)
                return None
            # The host that failed is the hop's, which a redirect makes another
            # than the page's. One reset or TLS error is a failed page; only
            # CONNECTION_FAILURES_TO_BLOCK in a row with no answer between them
            # write the host off — before, a single one ended the crawl of the
            # site being archived and the document came out silently short.
            failed = getattr(e.request, "url", None) or url
            domain = urllib.parse.urlparse(failed).netloc.lower()
            if self._conn_failures is None:
                self._conn_failures = {}
            self._conn_failures[domain] = self._conn_failures.get(domain, 0) + 1
            if self._conn_failures[domain] < CONNECTION_FAILURES_TO_BLOCK:
                print(f"  ⚠️  Connection failed ({type(e).__name__}): {url}", flush=True)
            elif domain not in self.blocked_domains:
                self.blocked_domains.add(domain)
                print(f"  ⛔ Network blocked or unreachable: {domain}", flush=True)
            return None
        except Exception as e:
            print(f"  ⚠️  {type(e).__name__}: {url}", flush=True)
            return None
