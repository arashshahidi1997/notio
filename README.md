# notio

`notio` is a lightweight project-agnostic CLI for creating templated Markdown notes and maintaining browsable log indexes.

## Package surface

- `notio init`: scaffold `notio.toml`, `.notio/templates/`, and `docs/log/`
- `notio note <type>`: create or update a configured note
- `notio toc [<type>|--all]`: rebuild one or all indexes

The repo includes thin `make` wrappers, but the source of truth is now the Python CLI and `notio.toml`.

## Local runtime

This repo uses `/storage/share/python/environments/Anaconda3/envs/labpy/bin/python`.

Run directly from the repository without installing:

```bash
PYTHONPATH=src /storage/share/python/environments/Anaconda3/envs/labpy/bin/python -m notio --root . init
PYTHONPATH=src /storage/share/python/environments/Anaconda3/envs/labpy/bin/python -m notio --root . note meeting --title "Sprint sync"
PYTHONPATH=src /storage/share/python/environments/Anaconda3/envs/labpy/bin/python -m notio --root . toc --all
```

Install as a package in another project:

```bash
pip install .
notio init --root /path/to/project --write-config
```

## Configuration

`notio` reads configuration from `notio.toml`, or falls back to `[tool.notio]` in `pyproject.toml`.

This repository ships a default config in [notio.toml](/storage2/arash/projects/makenotes/notio.toml).

## Make wrappers

- `make init`
- `make note-daily`
- `make note-weekly`
- `make note-issue TITLE="Fix plotting bug"`
- `make toc-all`
