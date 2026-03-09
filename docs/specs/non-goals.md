# Non-goals

This system intentionally does *not* attempt to be a full documentation framework or a full-featured knowledge base.

## Explicit non-goals

- **Not a general documentation site builder**: No MkDocs/Sphinx integration is required for core note creation.
- **Not a task manager**: Checklists may exist inside notes, but there is no “tasks database” or workflow engine.
- **Not a YAML processor**: Frontmatter handling is intentionally minimal and string-based (only used for TOC labels/grouping).
- **Not a synchronization/publishing tool**: No git/datalad push/deploy commands are part of `makenotes`.
- **Not a permissions or secrets system**: No encryption, secret management, or access control.
- **Not a multi-user concurrency solution**: It does not prevent timestamp collisions across machines/users beyond “likely unique”.
- **Not a template language**: Template substitution is limited to environment variable replacement (`envsubst`).
- **Not a global installer**: The system lives inside a repo folder; it does not require a system-wide package install.

## Out of scope (for now)

- Automatic linking/backlink graph generation.
- Full-text search/indexing.
- Rich metadata validation (e.g., enforcing schema for issue notes).
- Interactive prompts (e.g., ask for title/participants) without additional tooling.

