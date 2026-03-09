# Critique

This is a pragmatic system, but it has rough edges that are worth calling out.

## What works well

- **Very low friction**: `make note-daily` is fast and easy to remember.
- **Plain files**: Markdown-in-folders is robust, debuggable, and plays well with git.
- **Separation of concerns**: Templates in `.foam/templates/`, rendered notes in `docs/log/`.
- **Automatable**: `make toc-all` gives deterministic navigation files.

## Limitations / pain points

- **`envsubst` is blunt**: No conditionals, loops, defaults, or escaping rules beyond environment substitution.
- **Date parsing + portability**: GNU `date` portability issues are avoided here via Python, but the system now implicitly requires `python3`.
- **Frontmatter parsing is not YAML**: The TOC script only supports simple `key: value` lines and ignores nested structures/lists; quoted values and edge cases can break silently.
- **Hard-coded layout**: Note destinations and types are compiled into the Makefiles; adding a new note type requires editing Make rules and templates.
- **Mixed responsibilities**: Makefiles handle orchestration *and* policy (naming schemes, directory layout) rather than delegating policy to a configuration layer.
- **Index generation is per-folder**: The system does not create higher-level summaries (e.g., “issues by week”, “commits since last release”) without custom scripts.
- **Timestamp uniqueness is best-effort**: Two notes created in the same second by the same user can collide.

## Operational concerns

- **OS differences**: Make + shell commands behave differently across environments (BSD vs GNU tools).
- **Editor workflow**: Without editor integration (Foam/Obsidian), templates and links are less discoverable.
- **Scaffolding**: Copying `makenotes/` into a new project is straightforward, but there’s no “one command init” yet.

