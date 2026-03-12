# Set Up Diataxis Documentation

## Scaffold the structure

Run `notio diataxis init` to create the four standard Diataxis sections:

```bash
notio diataxis init
```

This creates `docs/tutorials/`, `docs/how-to/`, `docs/explanation/`, and `docs/reference/`, each with an `index.md`.

To get a suggested `mkdocs.yml` nav block, add `--mkdocs`:

```bash
notio diataxis init --mkdocs
```

## Add a page

Use `notio diataxis add` with a section name and a filename slug:

```bash
notio diataxis add tutorial quickstart --title "Getting Started"
notio diataxis add how-to deploy --title "Deploy to Production"
notio diataxis add explanation architecture
notio diataxis add ref api --title "API Reference"
```

Each section uses a template suited to its purpose. The section index is updated automatically.

Section aliases are supported: `tutorial`, `howto`, `ref`, `explain`.

## Rebuild indexes

To regenerate all section indexes:

```bash
notio diataxis toc --all
```

Or rebuild a single section:

```bash
notio diataxis toc tutorials
```

## Customize the docs root

By default, diataxis pages live under `docs/`. To change this, add a `[diataxis]` section to `notio.toml`:

```toml
[diataxis]
docs_root = "documentation"
```

## Use a subset of sections

To manage only some Diataxis sections:

```toml
[diataxis]
sections = ["tutorials", "reference"]
```
