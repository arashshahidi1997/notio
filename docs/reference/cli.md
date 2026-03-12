# CLI

## `notio init`

```bash
notio init [--force] [--write-config]
```

Creates the workspace directories, default templates, and index files.

Options:

- `--force`: overwrite default templates
- `--write-config`: write a default `notio.toml` when it does not exist

## `notio note`

```bash
notio note TYPE [--owner NAME] [--title TEXT] [--date YYYY-MM-DD] [--timestamp VALUE] [--force]
```

Creates or updates a note and refreshes indexes.

Examples:

```bash
notio note daily
notio note weekly --date 2026-03-09
notio note meeting --title "Design review"
```

## `notio toc`

```bash
notio toc [TYPE] [--all]
```

Regenerates index files without creating notes.

## `notio diataxis init`

```bash
notio diataxis init [--mkdocs]
```

Scaffolds a Diataxis documentation structure under the configured `docs_root` (default `docs/`).

Creates four section directories with index files:

- `tutorials/index.md`
- `how-to/index.md`
- `explanation/index.md`
- `reference/index.md`

Also creates a root `docs/index.md` linking to all sections.

Options:

- `--mkdocs`: print a suggested `mkdocs.yml` nav snippet to stdout

Idempotent — existing files are not overwritten.

## `notio diataxis add`

```bash
notio diataxis add SECTION SLUG [--title TEXT]
```

Creates a new page in a Diataxis section using a section-appropriate template.

Each section type has its own template structure:

- **tutorials**: What you will learn, Prerequisites, Steps, Next steps
- **how-to**: Problem, Prerequisites, Solution steps, See also
- **explanation**: Overview, Discussion, Further reading
- **reference**: Synopsis, Details, See also

The section index is automatically updated after adding a page.

Section names accept aliases: `tutorial`, `howto`, `how_to`, `ref`, `explain`.

Examples:

```bash
notio diataxis add tutorial quickstart --title "Getting Started"
notio diataxis add how-to custom-templates
notio diataxis add ref cli-reference --title "CLI Reference"
```

## `notio diataxis toc`

```bash
notio diataxis toc [SECTION] [--all]
```

Regenerates Diataxis section index files. Without arguments or with `--all`, rebuilds all section indexes and the root docs index.

## `notio mcp`

```bash
notio mcp
```

Starts the FastMCP server over stdio. Requires `pip install notio[mcp]`.

Exposes all notio operations as MCP tools for agent consumption:

- `note_list` — list recent notes, optionally filtered by type
- `note_latest` — content of the most recent note
- `note_read` — read a specific note by path
- `note_create` — create a new note
- `note_types` — list configured note types
- `toc_rebuild` — regenerate note indexes
- `diataxis_init` — scaffold Diataxis docs
- `diataxis_add` — add a page to a section
- `diataxis_toc` — rebuild section indexes
- `config_show` — show current configuration

The server resolves the project root from the `--root` flag or the `NOTIO_ROOT` environment variable.

## Library API

The following functions are exported from `notio` for programmatic use:

```python
from notio import list_notes, latest_note, read_note
```

### `list_notes(root, *, note_type=None, limit=20)`

Returns a list of dicts with note metadata (path, type, frontmatter fields). Sorted by modification time, newest first.

### `latest_note(root, *, note_type=None)`

Returns the most recent note as a dict including full content, or `None`.

### `read_note(root, path)`

Reads a specific note by its relative path. Returns a dict with content and frontmatter, or `None`.

