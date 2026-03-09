# Redesign suggestions (keeping specs)

This proposes a more elegant layout and configuration story while preserving the current specs:
template-based note creation, predictable log structure, and TOC generation.

## 1) Introduce a single configuration file

Add a `makenotes.yml` (or `pyproject.toml` section) that defines:

- Note types (`daily`, `weekly`, `issue`, `commit`, `meeting`, `idea`, `personal`)
- Template file per type
- Destination directory per type
- Filename pattern per type (period vs event)
- TOC behavior (which metadata keys to show, optional grouping)

Example shape:

```yaml
notes:
  root: docs/log
  types:
    daily:   {template: note-daily.template.md,  mode: period,  pattern: "daily-{owner}-{date}.md"}
    weekly:  {template: note-weekly.template.md, mode: period,  pattern: "weekly-{owner}-{year}-W{week}.md"}
    issue:   {template: note-issue.template.md,  mode: event,   pattern: "issue-{owner}-{timestamp}.md", toc: {keys: [status], groupby: status}}
    meeting: {template: note-meeting.template.md,mode: event,   pattern: "meeting-{owner}-{timestamp}.md", toc: {keys: [participants]}}
```

This keeps Make targets stable while allowing per-project customization.

## 2) Move policy into a small Python CLI (Sphinx-inspired)

Inspired by Sphinx’s `conf.py` + `sphinx-quickstart`, create:

- `python -m makenotes init` (or `makenotes-init`) to scaffold:
  - `makenotes.yml`
  - `.foam/templates/` default templates
  - `docs/log/` tree
  - Optional minimal `Makefile` wrapper (`make note-daily` delegates to CLI)
- `python -m makenotes note <type> [--date ...] [--title ...] [--owner ...]`
- `python -m makenotes toc [<type>|--all]`

Make then becomes a thin convenience layer rather than the “source of truth”.

## 3) Improve template engine (still simple)

Replace `envsubst` with a minimal templater that supports:

- Defaults (`{{ title | default("issue") }}`)
- Basic conditionals (`{% if participants %}...{% endif %}`)
- Safe escaping rules

Jinja2 is the obvious choice, but even a tiny built-in formatter can cover 90% of needs.

## 4) Strengthen metadata handling

- Parse frontmatter with a real YAML parser (PyYAML or `ruamel.yaml`) to support lists and nested values.
- Validate metadata schemas per note type (optional, warnings-only by default).

## 5) Make destinations relocatable

Allow choosing destinations per type:

- Logs could go to `notes/log/` instead of `docs/log/`.
- Templates could be `templates/notes/` instead of `.foam/templates/`.

The config file becomes the single authority; nothing is hard-coded in Make rules.

## 6) Compatibility layer

Keep the existing UX stable:

- `make note-daily` still works.
- Existing environment overrides remain supported (`DATE`, `OWNER`, `TITLE`).
- Existing folder conventions remain the default when no config is present.

