# Changelog

## Unreleased

### Deprecated
- `notio.present` (slide decks): importing it raises a `DeprecationWarning`, and it is removed after the next notio release. Write decks as Quarto reveal.js (`format: revealjs`); in projio the `quarto-talks` skill does this. projio's `present_*` MCP tools are opt-in until the removal.

## 0.2.0 (2026-11-19)

### Added
- `notio.present`: research presentation decks, the counterpart of `notio.manuscript`. `DeckSpec` with four templates (lab-meeting, journal-club, conference-talk, progress-report), section assembly, figure insertion, citation pre-resolution with pandoc, validation, and two renderers: Marp and reveal.js (`pandoc -t revealjs`). Sections import across projects (`DeckSectionImport`).
- `commit` note type: structured change records with `subsystem`, `commit_hash` and file lists.

### Changed
- Manuscript render config: `ResolvedRender.conda_env` is now `render_env` (the pixi env that has pandoc). The legacy `conda_env` key in `render.yml` is still read as a fallback.
- The version has one source, `notio.__version__` (it said 0.1.0 while the package was 0.1.1).
- The `mcp` extra pins `fastmcp>=2,<4`.

### Fixed
- MCP `note_create` / `note_update` accept the fields as a mapping, a JSON object or YAML (the on-disk form failed and wrote nothing); `note_create` returns the note id.
- The log root index links only note types that have an index (an empty configured type broke `mkdocs --strict`).
- `find_pandoc()` falls back to `~/.pixi/bin/pandoc` and `~/.local/bin/pandoc` when pandoc is not on PATH.

## 0.1.1

Earlier releases (0.1.0, 0.1.1); see the git history.
