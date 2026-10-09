# Chrome MCP extraction — JavaScript-rendered sites

Read this when Step 2 detects a JavaScript-rendered site, or when a pipeline run ends
with `SPARSE CONTENT WARNING`.

Many documentation portals (SAP Help, Microsoft Learn) render their content entirely via
JavaScript. Static fetching returns an empty shell for them, so drive a real browser instead
and feed the rendered HTML into the same pipeline.

## Chrome MCP Extraction Workflow

**Claude Code only — pick the work directory** `<workdir>`, which holds the pages file
(the bookkeeping the pipeline consumes) and the saved HTML. Choose a path in the system
temp area: `/tmp/w2d_<domain>` on POSIX, `%TEMP%\w2d_<domain>` on Windows. The first save
creates the directory and the file, so there is nothing to set up first.

Write `<workdir>` out as that literal path in every command below, and use the same one
throughout the run. Do not rely on a shell variable: state does not survive between
commands.
On claude.ai there is no pages file — keep the structured content of each page in the 
conversation and assemble the document directly at the end.

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
  --url "<current_page_url>" \
  --title "<page_title>" \
  --html-file "<workdir>/page_<N>.html" \
  --depth <depth_level> \
  --pages-file "<workdir>/pages.json"
```

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
  --url "<start_url>" \
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
