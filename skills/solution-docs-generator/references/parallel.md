# Parallel work

Read when the rule below says to use workers. Everything in this skill works sequentially; workers
only make the independent parts faster. They never change what is produced: the same files, the
same checks, the same checkpoint.

## The rule

Use workers when **both** are true:

1. the environment has a subagent tool (Claude Code, and Cowork when it offers one; claude.ai
   does not), and
2. the step has **two or more independent units** (table below).

Otherwise work sequentially, in the same order, with the same files. When the user asks for
"sequential" (or "no subagents"), work sequentially even when the rule says otherwise. Say in one
line which steps ran in parallel and with how many workers; nothing else about it reaches the
user.

| Step | Unit | Worker writes | You (the lead) then |
|---|---|---|---|
| Phase 4 — code analysis | one component or repository (from the component table) | `work/analysis/<unit>.md` | merge into `work/analysis.md`; resolve conflicts between units |
| Phase 6 — writing | one document of the set, except the solution sheet | `<doc>.md` (the master) | write the solution sheet yourself (it lists the others); run `check_doc.py --set` on every master; fix cross-references |
| Phase 6 — languages | one extra language of a master | `<doc>.<lang>.md` | run `check_doc.py --parity` against the first-language master |
| Phase 7 — verification | one document | `work/verify-<doc>.md` | apply the corrections you accept; re-run the gate |

Not parallel, ever: the intake, the transcript cleaning (one glossary), the checkpoint, the
rendering of the delivered files, the delivery message. Never one worker per chapter: the voice
and the cross-references break.

Above six workers, each worker's fixed cost (reading the references, the analysis, the glossary)
outweighs its share: group units so that there are at most six.

## Handoff: files, not messages

A worker sees none of your session. Everything it needs is a file in the work folder, named in
its prompt; everything it produces is a file. Before dispatching, write:

- `work/analysis.md` — claims register, conflicts register, coverage map, decisions taken at the
  checkpoint (phases 6–7);
- `work/glossary.md` — the transcription glossary and the canonical spellings;
- `work/distribution.md` — the distribution matrix (topic → document) and the ID prefix of each
  document (phase 6 of a set);
- the corpus index `corpus/INDEX.md` and the source inventory `sources.md`.

Workers are read-only on everything except the one file their prompt names. They never edit the
sources, the corpus, another worker's file, or `analysis.md`.

## Dispatch

Dispatch all workers of a step **in one message**, one subagent call each, with the prompt
below. Workers do judgement work: where the environment offers worker tiers, do not put this
work on a lookup tier.

```
You are a worker of the solution-docs-generator skill (skill folder: <SKILL_DIR>).
Task: <ONE OF: "analyse the code of <unit>" | "write the <type> of <subject> in <lang>" |
       "translate <master> into <lang>" | "verify <master> against its sources">
Read first: <SKILL_DIR>/SKILL.md (only the phase named below), then <REFERENCES FOR THE TASK>.
Phase: <4 | 6 | 7>
Work folder: <WORK_DIR>   Inputs (read-only): <LIST OF FILES>
Language pack: <SKILL_DIR>/assets/i18n/<lang>.json (or <PACK_PATH>)
Profile: <PROFILE_PATH or "none">
Decisions from the checkpoint: <ONE LINE EACH, or "none">
Your ID prefix (writers): <PREFIX>; other documents of the set and their prefixes: <LIST>
Style example: <SKILL_DIR>/evals/samples/golden/ShipLabelApp - troubleshooting - manuale operativo.md

Write only <OUTPUT_FILE>. Never write a credential; cite source IDs (SRC-nn) for every
non-obvious statement in your notes; mark what the sources do not settle with the open-item
marker of the language pack. Do not ask the user anything: list your questions at the end of
your output file under "Open questions".
Return: the output path, counts (sections, IDs, open items), and the open questions.
```

### Task specifics

- **Code analysis** — follow `references/code-analysis.md` for the unit only; output the
  component row, the checklist findings with file references, known-behaviour candidates,
  potential problems, security findings (without values).
- **Writing** — follow the type file in `references/types/`, `references/authoring-format.md`
  and `references/writing-standards.md`; take content only from `work/analysis.md` and the corpus;
  cross-reference the other documents of the set by name and section instead of repeating them.
- **Translation** — translate the prose; keep IDs, heading numbers, identifiers, UI labels of
  non-localized products, quoted messages, code and tables' structure; chapter names from the
  target pack.
- **Verification** — a fresh reader: for each non-obvious statement of the master, find its
  support in the corpus or the claims register; list unsupported statements, statements that
  contradict a source, missing coverage-map topics, credentials. Output a table: line ·
  statement · finding · suggested fix. Do not edit the master.

## After the workers

1. Read every output. A worker's "Open questions" go to the checkpoint (phase 4) or become open
   items (phases 6–7) — never silently dropped.
2. Merge (analysis) or check (`check_doc.py --set` / `--parity`) as the table says.
3. Continue the phase as in sequential mode. If a worker failed or its output is unusable, do
   that unit yourself, sequentially.
