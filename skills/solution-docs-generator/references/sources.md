# Sources: kinds, access, inventory

The skill works with any number of sources of any mix. What follows tells how to reach each
kind in each environment, and how to record them so every statement can cite its origin.

## Kinds of source

| Kind | Typical form | What it gives the document |
|---|---|---|
| Session transcript | Any meeting platform or speech-to-text engine: `.vtt`, `.srt`, engine `.json`, `.tsv`, `.txt`, `.docx`, `.pdf` | The knowledge only people hold: purpose, practice, history, tricks, priorities |
| Session chat | Messages pasted by the user | The correct spelling of names, codes, paths, commands |
| Screenshots | Images pasted in the chat or saved in a folder | Figures; UI labels spelled as the user sees them |
| Existing documentation | Word, PDF, Markdown, text, Excel, slides | Earlier manuals, technical sheets, configuration notes, test reports |
| Mails and tickets | `.msg`, `.eml`, PDF prints, pasted text | Historical incidents, decisions, workarounds, contacts |
| Source code | Repository on any host, or a local/network folder | Architecture, real behaviour, configuration keys, messages, known behaviours |
| Database objects and scripts | `.sql` views and procedures, shell/cron/PowerShell | Data flows, schedules, diagnostic queries |
| Vendor documentation | Help portals, PDF guides | Concepts and procedures of the platforms the solution relies on |
| The user's answers | The checkpoint and any clarification | Decisions, current practice, business rules |

## Reaching the sources

Work **read-only** everywhere. Never commit, push, edit or delete in a source location; copy
what you need into a working folder (for example `docs-work/<subject>/` in the folder the user
chooses, or in the session's own workspace).

### Files and folders

- **Local paths** and **mapped drives** (`D:\Projects\App`, `J:\Docs`) are read directly where the
  shell runs on that machine.
- **Network shares**: a UNC path (`\\server\share\folder`) is read directly by Python on Windows;
  on Linux or WSL it must be mounted first (ask the user for the mount point). When the
  environment reaches the user's computer through a bridge that only grants specific folders,
  the user has to connect the folder (or copy the files into a connected one): say exactly which
  folder is needed.
- **Uploads**: files attached to the conversation are read from where the platform stores them.
  A large folder is best uploaded as a single zip, which you extract into the working folder.

### Screenshots

A screenshot the user pastes into the conversation becomes a figure only as a file. On Claude
Code, copy the pasted image from where the platform stores it into `images/`, or ask for a
folder of screenshots. On claude.ai and Cowork, where the platform's document skill can embed
conversation images, use that route when the local renderer cannot run, and say so. A
screenshot that stays only in the conversation and never reaches the document is an open item,
never an invented screen.

### Source code

Find out where each component lives before reading it: a project sheet, a README, the profile's
"Locations" section, or the user. Then, in order of preference:

1. **A local checkout** the user names: read it in place.
2. **A remote repository** (GitHub, Azure DevOps, GitLab, Bitbucket, a self-hosted server): clone it
   read-only into the working folder — `git clone --filter=blob:none <url>` keeps history
   (useful for dates of changes and incidents) without downloading every old file. Use the hosting
   platform's CLI or connector when authentication requires it (`gh repo clone`, `az repos`). Never
   store a token in a file or a command line the user will see.
3. **A code backup** (dated zip in a project folder): extract it into the working folder and note
   its date — it may be older than production.

When the code sits on the user's computer and the analysis runs elsewhere (a cloud workspace
reaching the computer through a bridge), do the reading where the code is when a shell is
available there (`grep`, `find`, `git log`). If the analysis needs the files on the other side,
bundle once: one zip of the relevant folders without build output, dependencies and binaries
(`bin`, `obj`, `node_modules`, `packages`, `.git`), then extract it there. One transfer of a
bundle beats hundreds of single-file transfers.

Large repositories: start from the entry points `extract_sources.py` lists in `INDEX.md`
(solution and project files, `Program.cs`/`Startup.cs`, `web.config`/`appsettings*.json`,
`package.json`, crontab, Dockerfile), then follow the call graph from the features the transcript
discusses. Do not read everything; read what the document needs, and record which parts were read.

### Mails

`.msg` needs the `extract-msg` package; `.eml` is read with the standard library; both keep their
attachments, which `extract_sources.py` extracts one level deep. Pasted mail text is fine too.
Mail signatures, disclaimers and logos are noise: ignore them.

### Web portals and online guides

- Use the environment's web tools to read the pages the user names; follow links only as far as
  the document needs (a concept, a procedure, a parameter).
- A portal behind a login: use a browser tool already signed in, when the environment has one and
  the user agrees; otherwise ask the user to export the pages (PDF or saved HTML).
- Save what you used (URL, title, date read) in the inventory: the references appendix cites it.
- Never copy long passages of vendor documentation: explain in your own words and cite the page.

### Recordings without a transcript

Ask for the transcript or the captions file first: every meeting platform and every
speech-to-text engine exports one, and `transcript.py` reads all the common formats
(`references/transcript.md`). Otherwise, on a machine where a local engine is installed (for
example `faster-whisper` or `whisper`), offer to transcribe, writing JSON or VTT so times and
speakers survive; ask before installing anything, since models are large and a GPU helps. A cloud
transcription service is the user's choice, never the skill's: it sends the recording outside.
Never guess the content of a recording.

## Running the extraction

```bash
<python> scripts/extract_sources.py --out docs-work/<subject>/corpus \
    --profile <profile.md> \
    --label "Repository ShipLabelApp=<path-to-checkout>" \
    --transcript <session.json> \
    <path-to-checkout> <project-folder> <mails-folder> <old-manual.docx>
```

- Each argument becomes one source (`SRC-01`, `SRC-02`, …); a folder keeps its tree.
- `--transcript` marks a session transcript in any format (or a folder of them): it is normalized
  like `transcript.py normalize` does. Files named `*transcri*`/`*trascri*`, `.vtt`, `.srt` and
  `.sbv` are recognized without it.
- Secrets are replaced with `«REDACTED»`; the count per file is in `INDEX.md`. Work from the
  corpus, not from the originals, whenever you copy text into notes or the document.
- Images (screenshots, pictures inside Word files) are copied as files, ready to be reused as
  figures.
- Legacy Office formats need LibreOffice; a scanned PDF is reported as having no text layer.

## The source inventory

Show it to the user at the end of Phase 2, and keep it in `docs-work/<subject>/sources.md`:

```markdown
| ID | Source | Kind | Access route | Status |
|---|---|---|---|---|
| SRC-01 | Session of 04/11 – transcript | transcript | upload | ok, 1 h 12 min |
| SRC-02 | Session chat | chat | pasted | ok |
| SRC-03 | Repository ShipLabelApp | code | clone of https://… (main, 2026-10-30) | ok, 214 files |
| SRC-04 | Project folder PRJ\1234\Output | documents | network share | 2 PDF ok, 1 scanned (no text) |
| SRC-05 | Mails 2024–2026 on print errors | mail | .msg files | ok, 6 mails |
| SRC-06 | Vendor help – Service Layer | web | https://… | ok, 3 pages |
```

The document's header ("Fonti" / "Sources") and its references appendix are written from this
inventory; the claims register in `analysis.md` cites these IDs.
