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

