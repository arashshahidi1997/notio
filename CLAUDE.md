# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**notio** is a lightweight CLI for creating templated Markdown notes and maintaining browsable log indexes. Notes are plain Markdown with YAML frontmatter, configured entirely via TOML. No database or external runtime dependencies — only Python 3.11+ stdlib (MCP server requires `fastmcp` as optional dependency).

## Common Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run locally without installing
PYTHONPATH=src python -m notio --root . <command>

# CLI commands
notio init [--force] [--write-config]   # Scaffold workspace
notio note <type> [--owner] [--title]   # Create a note
notio toc [<type>|--all]                # Regenerate indexes
notio diataxis init [--mkdocs]         # Scaffold Diataxis docs structure
notio diataxis add <section> <slug>    # Add a page to a section
notio diataxis toc [<section>|--all]   # Rebuild section indexes
notio mcp                              # Start FastMCP server (stdio)

# Testing and building
make test                               # Run pytest
make build                              # Build wheel and sdist
make check                              # twine check
make clean                              # Remove build artifacts
make publish                            # Upload to PyPI
make publish-test                       # Upload to TestPyPI

# Documentation
pip install ".[docs]"
mkdocs serve

# Make shortcuts (defined in workflow/*.mk)
make toc-all
```

## Architecture

Source modules in `src/notio/`:

- **cli.py** — argparse command router, entry point (`notio.cli:main`)
- **config.py** — TOML config loading into dataclasses. Config precedence: `notio.toml` > `[tool.notio]` in `pyproject.toml` > hardcoded defaults
- **core.py** — Note business logic: template rendering (`string.Template` with `${variable}` syntax), frontmatter parsing (regex + YAML), note file creation, and index generation
- **diataxis.py** — Diataxis documentation scaffolding: section templates, page creation, and section index generation. Reuses `core.parse_frontmatter`
- **query.py** — Read-only note query functions (`list_notes`, `latest_note`, `read_note`). Exported from `notio.__init__` for library use by projio
- **mcp/** — FastMCP server package (optional, requires `fastmcp`). Exposes all notio operations as MCP tools. Uses `NOTIO_ROOT` env var for project root resolution

Default note types are four core types: **idea**, **issue**, **task**, **meeting** (all event mode). Projects can add custom types (including period-mode types like `daily`, `weekly`) via `notio.toml`.

All templates include `series` (string) and `refs` (list of cross-references) frontmatter fields. Series groups related notes; refs provide structured cross-references to other notes, plan sections, or pipeline mods.

Default templates are embedded in `core.py`. User-customizable templates go in `.projio/notio/templates/`. Generated notes and indexes live under `docs/log/`.

## Configuration

All behavior is declarative via `notio.toml`. Each note type defines: `mode`, `template`, `filename` pattern (with `{owner}`, `{date}`, `{timestamp}` placeholders), `toc_keys`, and optional `toc_groupby`.

The optional `[diataxis]` section configures docs scaffolding with `docs_root` (default `"docs"`) and `sections` (default: tutorials, how-to, explanation, reference). Section names accept aliases (e.g. `tutorial`, `ref`, `howto`).
