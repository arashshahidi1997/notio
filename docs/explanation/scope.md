# Scope And Goals

`notio` is a lightweight CLI for one narrow problem: structured note creation and index generation inside ordinary repositories.

Its goals are:

- make note creation fast
- keep notes as plain Markdown files
- support per-project configuration without code edits
- keep navigation pages deterministic and easy to regenerate
- stay small enough to embed into other repositories

Its non-goals are:

- a database-backed note system
- a full documentation framework
- a task engine or workflow tracker
- a synchronization or publishing backend

## Subpackages

- `notio.manuscript`: manuscript assembly and pandoc rendering. It is retired once the first project that
  uses it (pixecog) builds its manuscript with Quarto alone.
- `notio.present`: **deprecated** (2026-11-24). Importing it raises a `DeprecationWarning`, and it is removed
  after the next notio release. Write decks as Quarto reveal.js (`format: revealjs`); in projio the
  `quarto-talks` skill does this, and projio's `present_*` MCP tools are opt-in until the removal.
