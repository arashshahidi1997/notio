# Manuscript Tutorial

This tutorial walks through creating a manuscript, adding sections, wiring figures and citations, and rendering to PDF.

## Prerequisites

- `notio` installed with manuscript support
- `pandoc` available in PATH (for rendering)
- A `.bib` file managed by biblio (optional, for citations)
- figio figure specs (optional, for figures)

## 1. Scaffold a manuscript

```bash
notio manuscript init my-paper
```

This creates:

```
docs/manuscript/my-paper/
├── manuscript.yml          # manifest
└── sections/
    ├── abstract.md
    ├── introduction.md
    ├── methods.md
    ├── results.md
    └── discussion.md
```

Each section file has frontmatter:

```yaml
---
title: "Introduction"
order: 2
manuscript: my-paper
status: draft
tags: [manuscript, section]
---

# Introduction

```

## 2. Edit the manifest

Open `docs/manuscript/my-paper/manuscript.yml` and configure:

```yaml
name: my-paper
title: "My Paper Title"
authors:
  - name: "Alice Smith"
    affiliation: "University X"
    email: alice@example.com

sections:
  - key: abstract
    path: sections/abstract.md
    order: 1
  - key: introduction
    path: sections/introduction.md
    order: 2
  - key: methods
    path: sections/methods.md
    order: 3
  - key: results
    path: sections/results.md
    order: 4
  - key: discussion
    path: sections/discussion.md
    order: 5

bibliography:
  bib_file: ../../../bib/project.bib    # relative to manuscript.yml
  csl: ../../../bib/csl/nature.csl

figures:
  dir: figures/
  mappings:
    - id: fig-overview
      spec: figures/overview.figurespec.yaml
      caption: "System overview showing the processing pipeline."

render:
  output_dir: _build/
  formats: [pdf]
  pandoc_args: ["--pdf-engine=xelatex"]
```

## 3. Write section content

Edit the section files under `sections/`. Use standard Markdown with:

- **Citations**: `[@citekey]` syntax (resolved by pandoc citeproc)
- **Figure references**: `![caption](fig:<figure-id>)` syntax (resolved during assembly)

Example in `sections/methods.md`:

```markdown
---
title: "Methods"
order: 3
manuscript: my-paper
status: draft
tags: [manuscript, section]
---

# Methods

We used the preprocessing pipeline described in [@smith2024].
The analysis followed the approach of [@jones2023; @lee2025].

![System overview](fig:fig-overview)

## Participants

Thirty participants were recruited...
```

## 4. Add a section

To add a new section (e.g., acknowledgements):

1. Create the file:

```bash
cat > docs/manuscript/my-paper/sections/acknowledgements.md << 'EOF'
---
title: "Acknowledgements"
order: 6
manuscript: my-paper
status: draft
tags: [manuscript, section]
---

# Acknowledgements

This work was supported by...
EOF
```

2. Add it to `manuscript.yml`:

```yaml
sections:
  # ... existing sections ...
  - key: acknowledgements
    path: sections/acknowledgements.md
    order: 6
```

## 5. Wire figio figures

If you have figio figure specs, add them to the manifest's `figures.mappings`:

```yaml
figures:
  dir: figures/
  mappings:
    - id: fig-overview
      spec: figures/overview.figurespec.yaml
      caption: "System overview"
    - id: fig-results
      spec: figures/results.figurespec.yaml
      caption: "Main experimental results"
```

Build figures first with figio, then reference them in sections:

```markdown
![System overview](fig:fig-overview)
```

During assembly, `fig:fig-overview` resolves to the actual built file path (PDF preferred, then SVG, then PNG).

## 6. Validate

Check that everything is wired correctly:

```bash
notio manuscript validate my-paper
```

This checks:
- All section files exist
- Section order has no gaps or duplicates
- All `[@citekey]` references exist in the bibliography
- All figure mappings have built outputs
- Pandoc is available

## 7. Preview the assembly

Generate the assembled markdown without rendering:

```bash
notio manuscript assemble my-paper
```

This writes `_build/assembled.md` — a single concatenated document with frontmatter stripped and figures resolved. Useful for reviewing what pandoc will see.

## 8. Build the manuscript

Render to PDF:

```bash
notio manuscript build my-paper --format pdf
```

Or multiple formats:

```bash
notio manuscript build my-paper --format pdf --format latex
```

Output goes to `docs/manuscript/my-paper/_build/my-paper.pdf`.

## 9. Check status

```bash
notio manuscript status my-paper
```

Shows section count, word counts, draft status, and figure availability.

## Using MCP tools

All manuscript operations are available as MCP tools (via projio):

```
manuscript_init("my-paper")              # scaffold
manuscript_list()                         # list manuscripts
manuscript_status("my-paper")            # sections + figures status
manuscript_validate("my-paper")          # run all checks
manuscript_assemble("my-paper")          # generate assembled markdown
manuscript_build("my-paper", "pdf")      # render to PDF
manuscript_figure_insert("my-paper",     # wire a figure into a section
    "methods", "fig-overview")
```

## Full paper pipeline

The complete workflow combining projio subsystems:

1. **biblio**: `biblio_merge()` → up-to-date `.bib` file
2. **figio**: `figio_build(figure_id)` → built figure SVGs/PDFs
3. **notio/manuscript**: `manuscript_build("my-paper", "pdf")` → assembled + rendered paper

```
biblio (bib-merge)  ──► bib/project.bib
                              │
figio (build all)   ──► figures/*.pdf
                              │
section atoms       ──► assembled.md ◄──┘
  (sections/*.md)         │
                          ├──► pandoc + citeproc ──► paper.pdf
                          └──► pandoc ──► paper.tex
```
