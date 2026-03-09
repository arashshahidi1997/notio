# Snippet style (short demo)

This repo uses short Markdown notes as teaching examples (see `makefile-usage.md` and `makefile-codex.md`). Keep them easy to scan so students can learn the concept quickly.

## What good demo notes look like

- **Short intro**: 2–4 sentences explaining what the thing is and when you’d use it.
- **Clear sections**: 2–4 `##` headings with action-oriented names.
- **Bullets over paragraphs**: lists for key points and steps; one idea per bullet.
- **Small example**: one short code/command block that demonstrates the payoff.
- **Exact names**: wrap files, folders, commands, and target names in backticks (e.g. `make help`, `docs/log/`).

## Common section patterns (pick what fits)

- `## What <thing> helps with (any project)` — quick bullet benefits.
- `## In this <repo>/ demo` — a short list of the concrete commands/targets available.
- `## Simple example (memory vs Makefile)` — contrast “manual steps” vs “one command”.
- `## Tiny workflow example` — a 2–3 line end-to-end flow.

## Suggested template

````md
# <Title> (short demo)

2–4 sentences: what this is, why it exists, and when to use it.

## What it helps with (any project)
- **Benefit**: one sentence.
- **Benefit**: one sentence.

## In this <repo>/ demo
- `<command>` — what it does.
- `<command>` — what it does.

## Example

```bash
<command>
```
````
