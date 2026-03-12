# Existing Repo Walkthrough

This walkthrough shows how to add `notio` to a repository that already has docs and project-specific conventions.

## Add the package

Install `notio` in the project environment:

```bash
pip install notio
```

Or vendor it locally and run:

```bash
PYTHONPATH=src python -m notio --root . init --write-config
```

## Review the generated config

Open `notio.toml` and set:

- `notes_root`
- `template_root`
- note types and filename patterns
- TOC grouping and metadata keys

## Adjust templates

Edit files under `.notio/templates/` to match the project’s note style.

## Optional Make wrappers

If the project wants short commands, add a thin wrapper:

```make
PYTHON ?= python3
NOTIO := PYTHONPATH=src $(PYTHON) -m notio --root .

note-daily:
	@$(NOTIO) note daily
```

The wrapper should stay thin. The policy belongs in `notio.toml`, not in the Makefile.

