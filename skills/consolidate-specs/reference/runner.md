# The runner

`scripts/consolidate.py` (with `lexer.py`, `selftest.py`), stdlib-only Python 3, byte-identical in both consolidation skills. Invoke as `python "<skill dir>/scripts/consolidate.py" <command>` (`python3` where `python` is absent). It moves to the repository root itself; paths you type are resolved from your directory. Run `self-test` to verify an install. With `CONSOLIDATION_PROFILE=1` in the environment, every command prints at exit, to stderr, `profile: <command> <seconds>s, <n> git calls`.

## Commands

| Manual step | Command | Exit |
|---|---|---|
| M1 | `preflight` — clean tree, upstream, foreign commits, baseline candidate | 0 / 1 |
| M2 | `target-set --pass-kind K --scope FILES… [--unit-rule R]` — files and unit counts; an unsupported file type fails. Its output goes to `.consolidation/`, which `record-init` creates; run `mkdir -p .consolidation` first | 0 / 1 / 2 |
| M3 | `record-init --pass-kind K --unit-id U --scope FILES… [--unit-rule R] [--narrowing-reason TEXT] [--target T…] [--floor graph] [--carry-from OLD]` — `U` takes letters, digits, `.`, `_` and `-` only, because it names the record file. `--carry-from` copies judgement onto units identical in file and fingerprint, so a bound-driven split is not classified twice. A unit whose identical twins in its file changed in number is left empty, and the command lists it as uncarried: classify it. A carried `of:` or `conflicts:` names the same unit by the new record's id; a unit whose named unit the new scope leaves out is left uncarried too | 0 / 1 |
| M4 | `record-shard --record R --shards N` — `R` is a record path or a batch id, `N` ≥ 1. It splits by file and writes, for each shard, the read-only brief `R.shard-k` (the stubs) and the judgement file `R.shard-k.j` (one `@@ <id> <fingerprint>` line per unit, no other field). For a `document` record it also prints, after the shard lines, one line per scoped file whose unit rule the nearest committed `document` record on the first-parent walk from the record's baseline gives it: `<file>: unit rule <rule> from record <unit_id> (<sha7>)`, `warn: ` prefixed when that rule differs from the record header's `unit_rule`. The walk reads at most 500 commits; when it stops there with files left it prints `note: no document record found within 500 commits for <k> file(s)` | 0 / 1 |
| M4 | `record-fill --record R --from J…` — `R` is a record path or a batch id. It writes the judgement fields of each `J` block into that unit of `R`, replacing the unit's earlier judgement fields, and leaves every other unit untouched. It refuses (nothing written) an unknown id, a fingerprint that differs from the stub's, a script-owned field, a unit given twice across the `J` files, and any working-tree change outside `.consolidation/` (an untracked `.consolidation.json` is the owner's input, not a change — ADR 0022). It prints how many units it filled and how many units of `R` are still empty. It serves the first classification (every shard's `J`) and every later correction (a `J` with only the corrected units). `record-merge --record R` is the legacy command for hand-filled shard files | 0 / 1 |
| M5 | `gate --pre --record R [--target-set T]` | 0 / 1 |
| M6 | `escalate --from-record R`, `escalate --rule …` (`escalation.md`) | 0 / 1 |
| M7 | `apply --record R [--dry-run]` — checks every file before it writes any, then writes the files (the ADR file of each `adr_text` unit included, "ADR text" below), `R`'s `.commit-msg` (and `.content-msg` under `record_channel: file`), and prints the `next:` commit line — which adds the ADR files the record names — and the `undo:` line. Both lines use `git -C <root>` and root-relative paths, so they run from any directory | 0 / 1 |
| M8 | `gate --unit --record-from-commit C [--target-set T]` — `C` is the unit's record-carrying commit | 0 / 1 |
| M8 | `escalate --close-applied --record-from-commit C` — after the unit gate passed: marks the rulings the unit applied (`escalation.md`) | 0 / 1 |
| M9 | `review-pack --record-from-commit C --out FILE [--target-set T] [--no-gate]` — runs `gate --unit` itself and opens with its verdict line; `--no-gate` skips the run, and the pack says so. When the ADR files the record renders cannot be listed, the pack is still written, with a `FAIL:` line in its ADR section, and the command fails | 0 / 1 |
| — | Other options: `record-init --out PATH` (another record path), `--force` (overwrite an existing record), `--floor-observed X` (the header's informational floor state); `record-check --no-intake` (skip ruling lookups); `bound-check --judgement`, `--project-lines`, `--measured` (one half only); `code-invariance-check --worktree` (against the working tree, not HEAD); `baseline-ancestry-check --baseline SHA [--unit-gate]`; `escalate --baseline SHA` (fingerprint the unit at that sha), `--anchor A` (a reference without a line), `--observed`, `--context`, `--ruling` (override the observation sha, the context and the ruling sha; no whitespace), `--intake PATH` (another intake file) | |

`gate --pre` runs `config-bound-check`, `record-check` (identity, admissibility, evidence, edit proofs), `scope-cross-check` (only for a `graph` or `exclusion-inventory` floor, or with `--target-set`), `floor-staleness-check`, `baseline-ancestry-check` and `bound-check --judgement --project-lines`. `gate --unit` runs `config-bound-check`, `record-check` (the intake included: a `ruling:` that cannot be verified fails), `record-provenance-check` (the record is one this review unit materialized — a commit's message or a committed record file, never one handed in from the side), `unit-tree-check` (the tree is clean outside `.consolidation/`), `replay-check` (on a v3 record also: the unit adds every ADR file an `adr:` field names, and for each `adr_text` unit exactly the file the runner derives, with exactly the rendered content), `removal-authorization-check`, `code-invariance-check` (comment passes), `baseline-ancestry-check --unit-gate`, `scope-cross-check` (under the same condition), `floor-staleness-check` and `bound-check`. Each is also a command of its own. For a `graph` or `exclusion-inventory` floor, `scope-cross-check` re-runs the provider and ignores `--target-set`, and `floor-staleness-check` measures the provider's own `# observed:` line (ADR 0011); a self-report floor is cross-checked only against a `--target-set` file. A gate exits 1 on any FAIL; an ADVISORY (self-report floor, a provider floor from an uncommitted config or with no observation state, projected line cap, unprovable invariance) never blocks, and is printed. Gates judge with the config of the baseline: a tracked `.consolidation.json` is read from the baseline blob, an untracked one is bound by the record header's `config_sha` and may only tighten the gates (`config-bound-check`, ADR 0012).

Every unit's last commit carries the record in its message (`-F <R>.commit-msg`): the content commit in the default channel, the record commit under `record_channel: file` (whose content commit uses `<R>.content-msg`), the record commit of a nil pass. So `--record-from-commit HEAD` names it right after the unit's commits. On a gate failure run the `undo:` line `apply` printed (`git reset --mixed HEAD~N && git restore -- <scope files>`) — the mixed reset keeps the record and any ADR file on disk. A record whose header names `last_verified_at` gets that front matter from `apply` itself, so no `mechanical:` commit writes the marker (ADR 0015).

When the record holds at least one unit with the `long=` fact whose disposition is not `condense`, `escalate --from-record` prints, after the units, exactly one line: `question: <N> long unit(s) (max <M> lines) that no standing ruling covered; to record one: escalate --standing --ruling-text "<the class and its keep-rules>"` — `N` such units, `M` the largest `long=` among them. It is stdout only, enters nothing in the intake, and does not print when every long unit is `condense`.

The `SUITE:` line of `gate --unit` on a comment pass (printed just above the verdict) says when to run the suite: now (invariance unprovable for some file, or `suite_cadence: unit`) or at the batch end.

### ADR text

A `historical decision → ADR` unit with `adr_title` and `adr_text` (`classify.md`) carries no `adr:`. The runner derives the file and `apply` writes it:

- **Path:** `<adr_dir>/<NNNN>-<slug>.md`. The slug is the title lower-cased, every run of characters outside `a-z` and `0-9` (accented letters included) turned into one `-`, trimmed, at most 60 characters. The first `adr_text` unit of the master record (outside a batch: of the record), in unit-id order, takes 1 + the highest four-digit number among the files in `adr_dir` at the batch baseline (outside a batch: the record's baseline); each later one takes the next number.
- **Content:** `# NNNN — <title>`, a blank line, `Status: accepted`, `Date: <the baseline commit's date, YYYY-MM-DD>`, a blank line, the `adr_text` lines, and a final newline.

`replay-check` fails unless the unit adds exactly that file with exactly that content, and `batch-next` never stops for such a unit. A unit with `adr:` and no `adr_text` keeps the legacy flow: you write the file at that path, and `batch-next` stops until it exists.

## Batch commands (ADR 0013, ADR 0015, ADR 0019)

A batch runs the steps above over many review units. It classifies once, holds one panel, and runs one command per review unit. Git is its only state: the master record is committed with every review unit, and `batch-next` reads the done units from the commits.

| Step | Command | Exit |
|---|---|---|
| B1 | `batch-init --pass-kind K --batch-id B --scope FILES… [--unit-rule R] [--narrowing-reason TEXT] [--target T…] [--floor graph] [--carry-from OLD] [--force]` — the master record `.consolidation/<B>-<sha7>.batch` (header `batch_master: yes`) over the whole batch scope, at HEAD. `record-shard` and `record-fill` take its batch id. `--carry-from OLD` (a record path or a batch id) re-baselines a classified master: it copies judgement onto units equal in file and fingerprint (the `record-init` carry rule) and lists the uncarried units to classify. It serves a bound-driven narrowing, a second batch on the same feature, and a stale master. `batch-init` refuses a batch id that already has a master record, and prints the next free id; `--force` reuses the id | 0 / 1 |
| B2 | `gate --pre --batch B` — the `gate --pre` checks without `bound-check`: a master record is not a review unit. `escalate --from-record B` takes the batch id. `apply` and `gate --unit` refuse a master record | 0 / 1 |
| B3 | `batch-plan --batch B` — after the gate and the panel: prints the review units in run order, the done ones read from git, and writes `<B>-<sha7>.plan` as a display copy that `batch-next` never reads. Whole files are packed under `REMOVAL_JUDGEMENT_CAP` and the projected `REMOVED_LINE_CAP`. A file over a cap is cut into `path:A-B` ranges, run bottom-up, never inside a unit, never inside the line span of a unit and the unit its `of:` or `conflicts:` names, and never below a `## To be confirmed` heading a pass adds items under; a review unit's record names the pair by its own ids. Unchanged files form one final nil unit. A review unit's id is `B.k`. A cut that cannot fit the caps fails and names the range | 0 / 1 |
| B4 | `batch-next --batch B [--target-set T]` — the next review unit, end to end. It reads the done units from git: every commit since the batch baseline must be one `batch-next` made or a mid-batch revert commit (`batch-revert`, below; ADR 0015, ADR 0021), and the last one is replayed. It checks the master record (its gate, and that no correction touched an applied unit or would renumber an ADR a review unit wrote) and cuts the plan from what remains. Then it derives the unit's record — the master's judgement on units equal in file, lines, span and fingerprint, after checking that the unit's lines equal the batch baseline — and runs `gate --pre`, `apply`, `git add` + `git commit -F` with the master record (hooks run), `gate --unit`, `escalate --close-applied` and `review-pack`. `T` goes to both gates. On success it prints the verdict, the pack, the `SUITE:` line and `next:`. It stops (exit 1) on a failing `gate --pre` (correct the master record with `record-fill`, `gate --pre --batch B`, run again), on a legacy `adr:` file not written yet (write it, run again), and on a failing commit or `gate --unit`, with an `undo:` line. After the final unit it replays every unit at its own commit, then prints `batch B complete` | 0 / 1 |
| B4 | `batch-run --batch B [--target-set T]` — runs `batch-next` in a loop and prints every unit's output. It stops at the first `STOP` (exit 1), right after a unit whose `SUITE:` line says to run the suite now for a reason other than the batch end, and when the batch is complete. Each unit is still gated, committed and packed on its own | 0 / 1 |
| B5 | `batch-status --batch B` — the done review units (from git) and the pending ones, each pack, and the next command; this is how a session resumes a batch | 0 / 1 |
| — | `batch-revert --batch B --from K` — prints the one line that reverts the done units K..n; the owner runs it verbatim, from any directory, and the runner never runs it: `git -C <root> revert --no-commit <c_K> <c_K+1> … <c_n> && git -C <root> checkout HEAD -- .consolidation && git -C <root> commit -m "consolidation: revert batch <B> units <K>..<n>"`, where n is the number of done units at invocation and `<c_K> … <c_n>` those units' own commits — under `record_channel: file` a unit's content commit and its record commit — named one by one and never a range: a range would also revert a revert commit the chain holds between two units, re-applying units outside K..n. The `git checkout HEAD -- .consolidation` step is in the line mid-batch and under `record_channel: file`, whenever HEAD holds `.consolidation` (mid-batch it always does): the revert stages the deletion of the `.consolidation/` files the units added — every unit commit carries the master record — and the step restores them; the chain refuses a mid-batch revert that changes a file under `.consolidation/`. After a completed batch in the default channel the line has no such step, and a revert from unit 1 removes the master record file from the worktree (`git checkout <the last done unit's commit> -- .consolidation` brings it back). It refuses (exit 1) an unknown batch, a `K` that is not an integer in 1..n, a batch with no done units, a batch whose last content commit still awaits its record commit (`batch-next` prints that undo), and a record directory that differs from HEAD — the revert and its restore step would discard an uncommitted record change; the next unit's commit carries one, a stash keeps one; when HEAD is not the last done unit's commit it prints `warn: HEAD <sha> is not unit <n>'s commit <sha>: the revert lands above <m> later commit(s)` first. For each unit of K..n whose disposition is `ruled → apply` with a `ruling:`, it removes the unit's `(fingerprint, unit_id, baseline)` triple from the entry's `applied=` — the mirror of `escalate --close-applied`; an `applied` entry returns to `ruled` when a content key it closed on (`units=` or its own fingerprint) is left without a still-applied unit, and an entry `escalate --close-applied` closed at once, with no content key, stays `applied` — and writes the intake once, printing `re-opened <x> ruling(s) on <y> entry/entries`, or `no applied rulings among units <K>..<n>`. The chain accepts the commit it produces: a recordless commit whose subject is exactly `consolidation: revert batch <bid> units <k>..<n>`, with integers 1 ≤ k ≤ n ≤ the units done before it, that changes no file under `.consolidation/`, is not a unit and not `pending`, and the next unit's baseline names it; a revert never sits between a content commit and its record commit (ADR 0021). The history walk holds no batch context: it skips a recordless commit with that subject without checking the batch id, the bounds, or whether the commit changes a file under `.consolidation/`, and it judges every record-carrying commit, whatever its subject. To `batch-next` and `batch-status` a revert after completion is a later commit, and mid-batch the accepted subject. The reverted units stay done in the chain: the batch never plans them again, and only their rulings re-open | 0 / 1 |

A batch ends at its final review unit. From the batch baseline to that unit, every commit on the first-parent line is one `batch-next` made or a mid-batch revert commit (`batch-revert`, above; ADR 0015, ADR 0021). Commits after it are reported, never judged: `batch-next` and `batch-status` print `batch B complete; N later commit(s) after <sha7>` and exit 0, with no `undo:` line (ADR 0019).

A red suite at the batch end is reverted, not patched forward. `git bisect run <suite>` over the unit commits finds the culprit unit — each unit's own commit locates one (`S182`) — and `batch-revert --batch B --from <k>` for that unit `k` prints the line that reverts units k..n and re-opens the rulings they applied.

`B` is the batch id or the master record's path; the master record lives in `.consolidation/`. A part record is derived: a judgement is corrected in the master record, through `record-fill`, never in a part record, and `gate --unit` fails a part record that differs from the master record committed with it (`batch-carry-check`). Outside a batch, `record-init --carry-from` (step M3) remains the manual split.

### The manual flow

`batch-next` runs steps M3, M5 and M7–M9 of the first table for one unit. Run them by hand only when it says the plan no longer holds, or for work outside a batch:

1. `record-init` for the unit, with `--carry-from <the master record>` to copy its judgement; classify every stub it lists as uncarried in a `.j` file and `record-fill` it.
2. `escalate --from-record`, and hold the owner panel for the frozen units ([`escalation.md`](escalation.md)): record each answer with `escalate --rule --fingerprint <FP>`, and write the units the answers correct in a correction file and `record-fill` it.
3. `gate --pre`, then `apply` and its `next:` line.
4. `gate --unit --record-from-commit C`, then `escalate --close-applied --record-from-commit C` once it passes.
5. `review-pack --record-from-commit C`.

The batch rules hold unchanged by hand: `escalate --rule` always takes `--fingerprint`; a document keeps one unit rule in every unit; a severance `--scope` is the surviving documents, and `--target-set` is omitted when `--target` named the targets; the exclusion inventory update is a plain-subject commit after the last unit.

## Record format (v3)

```
record_version: 3
unit_id: U-C1
baseline_sha: <full sha>
pass_kind: comment                 # comment | document | severance
unit_rule: comment                 # comment, comment-fine | document-paragraph, document-block | reference-occurrence
scope: src/a.py, docs/x.md:10-80   # a range declares a subset of one file (S26)
narrowing_reason: bound-driven split: …   # required when the scope is narrower than the target set
floor: self-report                 # self-report | graph | exclusion-inventory (observed by the gate)
floor_observed: <sha or ISO date>  # informational: a provider floor's state is its `# observed:` line
config_sha: <sha1 of .consolidation.json, empty when the repo has none>
last_verified_at: <sha> docs/x.md   # document pass, `last_verified_at: true`: the whole documents apply marks verified
@@unit 1
file: src/a.py
lines: 4-4
span: 4:0-4:27
fingerprint: 3b1f09aa             # path + occurrence index + text; identical units never share one
preview: # returns the sum of a and b
facts: absent=legacyAuth; code-like   # evidence only (classify.md, "Facts")
disposition: regenerable → delete
basis: restates def add(a, b): return a + b
```

Everything above `disposition` is script-owned; `record-check` re-enumerates the scope at the baseline and fails on any difference. `facts` (v3; comment and document passes) is re-measured too: `fragment=` matches of `fragment_patterns`, `absent=` code-shaped names no code at the baseline names (one `git grep -w`; hits in comments and documentation files do not count), `separator`, `long=` (a unit of 5 lines or more), `dup-of=` (the other units of the file with an equal normalized text) and, in a comment pass, `code-like`, `narration` and `todo`. A basis of the form "identifier `X` does not occur in the baseline tree" is checked the same way. Judgement fields: `disposition`, `basis`, `edit:` and `claims:` (lines prefixed `| `), `ruling`, `tbc` (document passes), `escalate`, `of:`/`conflicts:` (document passes — the cross-unit references a duplicate or contradiction names), and for a `historical decision → ADR` unit either `adr_title` + `adr_text:` (the runner writes the file, "ADR text" above) or the legacy `adr` (a Markdown path under `adr_dir`, written by hand). A v2 record — one carried by an earlier unit's commit — is still judged by v2 rules, which do not require `adr`.

The agent never edits a record. It writes judgement in a `.j` file — blocks of a header line `@@ <id> <fingerprint>` followed only by judgement fields, in the syntax above — and `record-fill` writes them into the record.

The record lives at `.consolidation/<unit_id>-<sha7>.record` under the repository root, wherever the command runs. It is materialized in the consolidation commit's message (default `record_channel: commit-message`, outside retrieval by construction). With `record_channel: file`, commit it with `git add -f` after the content commit. Where nothing changed, commit the record itself (`S169`).

## `.consolidation.json`

Found by walking up from the working directory to the repository root. Unknown keys are reported, never absorbed.

| Key | Default | Read by |
|---|---|---|
| `REMOVED_LINE_CAP` | 200 | `bound-check` (measured and projected) |
| `REMOVAL_JUDGEMENT_CAP` | 30 | `bound-check` |
| `SPOT_CHECK_RATE` | 0.25 | `bound-check`, `review-pack` |
| `FLOOR_STALENESS_THRESHOLD_DAYS` | 7 | `floor-staleness-check` (`FLOOR_STALENESS_THRESHOLD` is an accepted alias) |
| `FUNCTIONAL_DIFF_THRESHOLD`, `ADDED_LINE_CEILING` | 400, 200 | no gate: bounds the human applies |
| `suite_cadence` | `batch` | `gate --unit` |
| `last_verified_at` | `false` | `record-init`, `batch-next`: on `true` a document pass writes `last-verified-at: <baseline>` into each whole document it verifies — the owner's word that the merge strategy keeps that sha resolvable (`S99`); only the committed config can set it |
| `fragment_patterns` | ticket ids, `#123`, ISO and Italian dates | regular expressions for the `fragment=` fact |
| `directive_patterns` | `[]` | extra regular expressions for comments a tool reads (`S176`) |
| `adr_dir` | `docs/adr` | `replay-check`: added ADR files and ADR status lines are declared outputs; never a scope |
| `document_exts` | `.md .rst .txt .adoc` | `document`/`severance` scopes accept documentation files only |
| `record_channel` | `commit-message` | `apply`: `file` writes the content commit from `<R>.content-msg` and the record commit from `<R>.commit-msg`; both channels put the record in the unit's last commit message |
| `knowledge_graph` | — | a shell command; its stdout lines are the scope files — `target-set` without `--scope`, and the gate's re-run for a `graph` floor (`record-init --floor graph`). A `# observed: <ISO date or sha>` line in its output is the graph's build state (ADR 0011) |
| `exclusion_inventory` | — | a shell command; its stdout lines are the inventory, each `surviving-doc<TAB>…<TAB>target` (the runner reads the last tab-separated field as the target), plus an optional `# observed:` line — severance `target-set` (without it the command exits 2, `severance DISABLED`), `record-init`, and the gate's re-run for an `exclusion-inventory` floor; `--target` at `record-init` overrides it and makes the floor self-report. The inventory file itself is the provider's: update it outside the review unit |
| `intake_path` | `~/.claude/escalations.md` | `escalate`, `record-check` (rulings) |

The caps are uncalibrated defaults (`O8`). Calibrating them is the owner's decision; a pass never raises a cap to get through a gate (`S81`). A config that is not the committed one — untracked, or modified in the worktree — may only tighten: a cap above its default, a `SPOT_CHECK_RATE` below it or a `document_exts` entry outside the default list falls back to the default and fails `config-bound-check`; its provider commands floor nothing (ADR 0012).

## Languages

Comment units are enumerated by a string-aware lexer: Python (stdlib `tokenize`); JS/TS, C/C++, Java/Kotlin/Scala/Swift/Dart/Groovy, C#, Go, Rust, PHP, SQL, CSS/SCSS/LESS, HTML/Vue/Svelte with inline script and style, XML, Razor (`@* *@`), ASP.NET (`<%-- --%>`), shell, PowerShell, batch, VB, Fortran, Lua, Haskell, Lisp, YAML/TOML/Ruby/R/Perl/Make/CMake/Terraform, INI, Dockerfile and ignore files. An unknown file type in scope fails `target-set` and `record-init` rather than yielding a silent zero. The invariance proof is *certain* only for the languages whose fixes are tested here — Python, JS, C/C++, Java, C#, CSS, SQL, PHP (`.jsx`/`.tsx` use their own JSX scanner and report cannot-prove); every other language reports "cannot prove" and the unit runs the test suite.
