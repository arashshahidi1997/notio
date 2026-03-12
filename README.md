# notio

`notio` is a lightweight, project-agnostic CLI for creating templated Markdown notes and maintaining browsable log indexes.

It is meant for repositories that want plain Markdown notes with predictable structure, local templates, and repo-owned index pages, without introducing a database or a large documentation framework.

## Install

```bash
pip install notio
```

## Package surface

- `notio init`
- `notio note <type>`
- `notio toc [<type>|--all]`
- `notio diataxis init`
- `notio diataxis add <section> <slug>`
- `notio diataxis toc [<section>|--all]`

The source of truth is the Python CLI plus `notio.toml`. Make wrappers are optional convenience only.

## Quickstart

Initialize a workspace:

```bash
notio init --write-config
```

Create a note:

```bash
notio note meeting --title "Sprint sync"
```

Rebuild all indexes:

```bash
notio toc --all
```

Scaffold Diataxis documentation:

```bash
notio diataxis init --mkdocs
notio diataxis add tutorial quickstart --title "Getting Started"
```

## Local development

Install with development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
make test
```

Run directly from the repository without installation:

```bash
PYTHONPATH=src python -m notio --root . init
PYTHONPATH=src python -m notio --root . note meeting --title "Sprint sync"
PYTHONPATH=src python -m notio --root . toc --all
```

## Documentation

The repository includes an MkDocs site with a Diataxis-style structure:

- Tutorials
- How-to guides
- Explanation
- Reference

Build docs locally with:

```bash
pip install ".[docs]"
mkdocs serve
```

## Configuration

`notio` reads configuration from:

- `notio.toml`
- `[tool.notio]` in `pyproject.toml`

## Make wrappers

- `make init`
- `make note-daily`
- `make note-weekly`
- `make note-issue TITLE="Fix plotting bug"`
- `make toc-all`

## Release

See [RELEASE.md](RELEASE.md) for build and publish instructions.
