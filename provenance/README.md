# Provenance

Every skill in this repository was generated from written prompts and project specifications. This folder keeps that material, skill by skill, so anyone can audit how a skill was built.

## Layout

Each generator skill has a folder with its name, for example `technical-translation/`:

| Path | What it holds |
| --- | --- |
| `docs/` | The generated documents: project context, project instructions, and the domain-knowledge document |
| `project/1_config/prompts/` | The prompt that generated the project configuration |
| `project/2_knowledge/prompts/` | The prompt that generated the domain-knowledge document |

Two folders differ from this layout:

- `web-site-to-document/` keeps only the original Italian specification, under `prompts/`.
- `documentation-lifecycle/` holds the material for the whole toolkit, not for a single skill.

## How to audit a skill

1. Pick a skill folder, for example `provenance/technical-translation/`.
2. Read the prompts in order: `project/1_config/prompts/` first, then `project/2_knowledge/prompts/`.
3. Compare their outputs with the documents in `docs/`.
4. Compare those documents with the shipped skill in `skills/<name>/SKILL.md`.

The prompts record the intent at generation time. The shipped skill is the evolved result of that intent. Comparing the two shows how far the skill has come.
