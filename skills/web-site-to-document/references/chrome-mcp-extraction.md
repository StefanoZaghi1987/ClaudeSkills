# Chrome MCP extraction — JavaScript-rendered sites

Read this when Step 2 detects a JavaScript-rendered site, or when a pipeline run ends
with `SPARSE CONTENT WARNING`.

Many documentation portals (SAP Help, Microsoft Learn) render their content entirely via
JavaScript. Static fetching returns an empty shell for them, so drive a real browser instead
and feed the rendered HTML into the same pipeline.

## Chrome MCP Extraction Workflow

**Claude Code only — pick the work directory** `<workdir>`, which holds the pages file
(the bookkeeping the pipeline consumes) and the saved HTML. Ask Python for the system temp
area — `python -c "import tempfile; print(tempfile.gettempdir())"` — and use
`<that path>/w2d_<domain>_<YYYYMMDD-HHMMSS>`, with every character of the host other than
letters, digits, `.`, `_` and `-` written as `_` (a port's `:` included), and the time the run
starts: a directory left by an earlier run would hand its pages back as "already saved". Do not
write `/tmp` or `%TEMP%`
yourself: no shell expands `%TEMP%` for Python, and on Windows `/tmp` does not name the same
directory for the file tools and for Python. The first save creates the directory and the
file, so there is nothing to set up first.

Write `<workdir>` out as that literal path in every command below, and use the same one
throughout the run. Do not rely on a shell variable: state does not survive between
commands.
On claude.ai there is no pages file — keep the structured content of each page in the 
conversation and assemble the document directly at the end.

**robots.txt first**, as on the claude.ai branch: before opening the first page of a host,
read `<scheme>://<host>/robots.txt` and follow the rules it gives `*`, as the "robots.txt"
rule under "Important behaviors" in SKILL.md reads them.
Never open a page it disallows; keep its URL aside. On Claude Code, before Step E, write those
URLs to `<workdir>/pages.coverage.json` as `{"blocked_domains": [], "robots_excluded": [...]}`
with the Write tool: the build lists them in the document's References section.

For each page to extract (start with the root URL, then follow navigation links):

**Step A — Navigate to the page:**
Use the connector's tool that opens a URL (the name varies by connector — use the 
navigation tool this connector actually exposes) and wait for the content to render 
(`networkidle` or a brief pause).

**Step B — Read the rendered HTML:**
Use the connector's tool that returns the fully-rendered page (DOM/HTML).
On Claude Code, also save it to `<workdir>/page_<N>.html`

**Step C — Extract and save structured content:**
Structure the page content from the rendered HTML now in context: title, heading 
hierarchy, paragraphs, tables, code blocks, lists, images.
On Claude Code, append it to the pages file:

```bash
python "<SKILL_DIR>/scripts/chrome_extract.py" \
  --url '<current_page_url>' \
  --html-file "<workdir>/page_<N>.html" \
  --depth <depth_level> \
  --pages-file "<workdir>/pages.json"
```

The URL goes in single quotes and the title stays off the command line: both come from the
site, and inside double quotes Bash runs a `$(…)` or a backtick they carry. Write a `'` in the
URL as `%27`. The script takes the title from the saved HTML. Run one call at a time, never
in parallel: each call rewrites the pages file.

Images in the rendered page are still fetched from the site, so they are paced too: 
`--rate-limit` defaults to 1 second between image downloads. Lower it only for a site 
you know tolerates it, and pass `--no-images` when the user wants speed over pictures — 
a page with 40 pictures otherwise adds about 40 seconds.

**Step D — Discover next links:**
Read the navigation links out of the rendered HTML Step B already put in context — 
the sidebar and TOC anchors are in it, and this works on every connector.
When the connector also exposes a JavaScript tool (the name varies), that tool gives 
the same list directly:
`[...document.querySelectorAll('nav a[href]')].map(a => ({href: a.href, text: a.textContent}))`
(the spread is needed: a NodeList has `forEach`, but no `map`).
Resolve relative hrefs against the page's `<base href>` when it declares one, and 
filter to links within the same domain scope.
Repeat Steps A–C for each linked page, respecting the user's depth limit.

**Step E — Build the document from collected pages:**
Run the Step 3.5 checks first. Nothing on this path enforces them — a `--pages-file`
build checks only the filename counter — so they are yours to apply on both branches.
Then build with the branch for this environment (see "Execution branches"):
- **claude.ai:** build with the environment's document skills (`.docx` and `.pdf` via
  their documented tooling, `.md` written directly) and let the platform deliver the file.
- **Claude Code:** run the pipeline on the collected pages:

```bash
python "<SKILL_DIR>/scripts/main.py" \
  --url '<start_url>' \
  --format <docx|pdf|md> \
  --output "<output_dir>/<filename>" \
  --pages-file "<workdir>/pages.json"
```

## Tips for Chrome MCP extraction

- **Navigation links**: On doc sites, links are usually in a left sidebar (`nav`, `.sidebar`, 
  `[class*="nav"]`) — extract them with the querySelectorAll snippet from Step D
- **Content load**: After navigating, if content appears empty, check with 
  `document.querySelector('main')?.innerHTML` before moving on.
- **Accordion/tabs**: Run `document.querySelectorAll('[data-toggle], [aria-expanded]')` 
  and click them before reading the page to expand all panels.
- **Page limit**: Respect the user's max pages limit.
- **Errors**: If a page fails to load, skip it and continue with the next one.
- **Large sites**: For sites with hundreds of pages, inform the user and confirm before proceeding.
