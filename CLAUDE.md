# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**notio** is a lightweight CLI for creating templated Markdown notes and maintaining browsable log indexes. Notes are plain Markdown with YAML frontmatter, configured entirely via TOML. No database or external runtime dependencies — only Python 3.11+ stdlib.

## Common Commands

```bash
# Install for development
pip install .

# Run locally without installing
PYTHONPATH=src python -m notio --root . <command>

# CLI commands
notio init [--force] [--write-config]   # Scaffold workspace
notio note <type> [--owner] [--title]   # Create a note
notio toc [<type>|--all]                # Regenerate indexes
notio diataxis init [--mkdocs]         # Scaffold Diataxis docs structure
notio diataxis add <section> <slug>    # Add a page to a section
notio diataxis toc [<section>|--all]   # Rebuild section indexes

# Documentation
pip install ".[docs]"
mkdocs serve

# Make shortcuts (defined in workflow/*.mk)
make note-daily
make note-weekly
make toc-all
```

There is no formal test suite. CI runs a smoke test: init, create a note, verify index generation.

## Architecture

Four source modules in `src/notio/`:

- **cli.py** — argparse command router, entry point (`notio.cli:main`)
- **config.py** — TOML config loading into dataclasses. Config precedence: `notio.toml` > `[tool.notio]` in `pyproject.toml` > hardcoded defaults
- **core.py** — Note business logic: template rendering (`string.Template` with `${variable}` syntax), frontmatter parsing (regex + YAML), note file creation, and index generation
- **diataxis.py** — Diataxis documentation scaffolding: section templates, page creation, and section index generation. Reuses `core.parse_frontmatter`

Note types have two modes:
- **period** (e.g. `daily`, `weekly`) — reusable files keyed by date/week
- **event** (e.g. `commit`, `idea`, `meeting`) — unique timestamped files

Default templates are embedded in `core.py`. User-customizable templates go in `.notio/templates/`. Generated notes and indexes live under `docs/log/`.

## Configuration

All behavior is declarative via `notio.toml`. Each note type defines: `mode`, `template`, `filename` pattern (with `{owner}`, `{date}`, `{timestamp}` placeholders), `toc_keys`, and optional `toc_groupby`.

The optional `[diataxis]` section configures docs scaffolding with `docs_root` (default `"docs"`) and `sections` (default: tutorials, how-to, explanation, reference). Section names accept aliases (e.g. `tutorial`, `ref`, `howto`).
