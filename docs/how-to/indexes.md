# Maintain Indexes

## Rebuild all indexes

```bash
notio toc --all
```

## Rebuild one note-type index

```bash
notio toc meeting
```

## How indexes work

`notio` scans files under each configured note folder, reads simple frontmatter fields, and writes `index.md` files for:

- the note type, such as `docs/log/meeting/index.md`
- the root notes directory, such as `docs/log/index.md`

Indexes are refreshed automatically when you create notes through `notio note`.

## Card feed styling

Type indexes render each note as a **card** in a vertically-stacked feed
(inspired by Reddit/Stack Exchange thread layouts). Each card contains:

- A **title link** to the note file (styled via `.note-card-title`)
- A **metadata chips row** showing frontmatter fields such as date, status,
  series, confidence, and tags
- A **horizontal rule** separating cards

The card layout is styled by `stylesheets/cards.css` (referenced in
`mkdocs.yml` under `extra_css`). It uses mkdocs-material CSS variables and
degrades gracefully on plain mkdocs.

## Group ordering and collapsible sections

When a note type defines `toc_groupby` (e.g. tasks grouped by `status`),
the index orders groups to surface active work first:

1. **Active groups** appear at the top in a fixed order:
   `open` → `pending` → `in_progress` → `scheduled` → `partial`
2. **Other groups** follow alphabetically
3. **Closed groups** (`done`, `cancelled`, `resolved`) are rendered as
   **collapsed `<details>` blocks** — hidden by default, click to expand

Each group heading includes a count, e.g. `## open (3)` or
`??? note "done (81)"`.

This requires the `pymdownx.details` mkdocs extension (add it to
`markdown_extensions` in `mkdocs.yml`).

## Customizing card metadata

The metadata chips shown on each card are controlled by `_note_card()` in
`core.py`. By default it displays: `date`, `created`, `status`, `series`,
`confidence`, and `tags`. The `toc_keys` field in `notio.toml` controls
which keys appear in the non-card (legacy) entry format.

