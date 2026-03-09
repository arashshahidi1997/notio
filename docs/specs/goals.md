# Goals

The `makenotes` system is a tiny, portable, Makefile-driven way to create and organize project notes in a consistent, automatable structure.

## Primary goals

- **Fast note creation from templates**: Create new notes with a single `make` target, using `.foam/templates/*.template.md` and variable substitution.
- **Predictable locations**: Write notes under `docs/log/<type>/...` using a stable naming scheme.
- **Two classes of notes**:
  - **Period notes**: “daily” and “weekly” are *idempotent* (same target rewrites the same file for that period).
  - **Event notes**: “issue/commit/meeting/idea/personal” are *append-only* (timestamped, unlimited).
- **Low dependency surface**: Depend on common tools (`make`, `envsubst`, `python3` for date helpers + TOC generation).
- **Human-readable storage**: Notes are Markdown files that can be edited with any editor and versioned in git.
- **Index generation**: Provide `toc-*` targets that regenerate `docs/log/<type>/index.md` so the log folders remain browsable.
- **Project-agnostic**: No assumptions about the surrounding repository beyond “you have a folder to place logs and templates”.

## UX goals

- **Simple CLI surface**: A small set of targets (`note-*`, `toc-*`) with obvious overrides (`DATE`, `OWNER`, `TITLE`).
- **Works offline**: No network access required.
- **Fails loudly when missing tools**: Clear error if `envsubst` is missing.

