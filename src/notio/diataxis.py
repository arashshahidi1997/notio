from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from string import Template

from notio.config import Config
from notio.core import parse_frontmatter


@dataclass(frozen=True)
class SectionInfo:
    title: str
    description: str
    page_template: str


SECTION_META: dict[str, SectionInfo] = {
    "tutorials": SectionInfo(
        title="Tutorials",
        description="Learning-oriented walkthroughs that take you through a series of steps.",
        page_template="""\
---
title: "$title"
date: $date
tags: [tutorial]
---

# $title

## What you will learn

-

## Prerequisites

-

## Steps

### 1.

### 2.

### 3.

## Next steps

-
""",
    ),
    "how-to": SectionInfo(
        title="How-To Guides",
        description="Task-oriented guides that help you solve a specific problem.",
        page_template="""\
---
title: "$title"
date: $date
tags: [how-to]
---

# $title

## Problem

## Prerequisites

-

## Solution

### Step 1

### Step 2

## See also

-
""",
    ),
    "explanation": SectionInfo(
        title="Explanation",
        description="Understanding-oriented discussion that clarifies concepts.",
        page_template="""\
---
title: "$title"
date: $date
tags: [explanation]
---

# $title

## Overview

## Discussion

## Further reading

-
""",
    ),
    "reference": SectionInfo(
        title="Reference",
        description="Information-oriented technical descriptions.",
        page_template="""\
---
title: "$title"
date: $date
tags: [reference]
---

# $title

## Synopsis

## Details

## See also

-
""",
    ),
}

_SECTION_ALIASES: dict[str, str] = {
    "tutorial": "tutorials",
    "howto": "how-to",
    "how_to": "how-to",
    "explain": "explanation",
    "ref": "reference",
}


def _normalize_section(raw: str, valid: tuple[str, ...]) -> str:
    if raw in valid:
        return raw
    alias = _SECTION_ALIASES.get(raw)
    if alias is not None and alias in valid:
        return alias
    raise ValueError(
        f"Unknown section: {raw!r}. "
        f"Valid sections: {', '.join(valid)}"
    )


def _section_dir(config: Config, section: str) -> Path:
    return config.root / config.diataxis.docs_root / section


def _build_section_index(config: Config, section: str) -> Path:
    info = SECTION_META.get(section)
    title = info.title if info else section.capitalize()
    description = info.description if info else ""

    folder = _section_dir(config, section)
    folder.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix == ".md" and path.name != "index.md"
    )

    lines = [f"# {title}", ""]
    if description:
        lines.append(description)
        lines.append("")
    if files:
        for path in files:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            label = meta.get("title", path.stem)
            lines.append(f"- [{label}]({path.name})")
        lines.append("")

    index_path = folder / "index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def _build_root_docs_index(config: Config) -> Path:
    docs_root = config.root / config.diataxis.docs_root
    docs_root.mkdir(parents=True, exist_ok=True)

    lines = ["# Documentation", "", "## Sections", ""]
    for section in config.diataxis.sections:
        info = SECTION_META.get(section)
        title = info.title if info else section.capitalize()
        lines.append(f"- [{title}]({section}/index.md)")
    lines.append("")

    index_path = docs_root / "index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def _mkdocs_nav_snippet(config: Config) -> str:
    lines = ["# Suggested mkdocs.yml nav entries:"]
    for section in config.diataxis.sections:
        info = SECTION_META.get(section)
        title = info.title if info else section.capitalize()
        lines.append(f"  - {title}:")
        lines.append(f"      - {section}/index.md")
    return "\n".join(lines)


def diataxis_init(config: Config, *, mkdocs: bool = False) -> tuple[list[Path], str | None]:
    created: list[Path] = []
    for section in config.diataxis.sections:
        folder = _section_dir(config, section)
        folder.mkdir(parents=True, exist_ok=True)
        created.append(folder)
        index_path = folder / "index.md"
        if not index_path.exists():
            created.append(_build_section_index(config, section))

    root_index = config.root / config.diataxis.docs_root / "index.md"
    if not root_index.exists():
        created.append(_build_root_docs_index(config))

    snippet = _mkdocs_nav_snippet(config) if mkdocs else None
    return created, snippet


def diataxis_add(
    config: Config,
    section: str,
    slug: str,
    *,
    title: str | None = None,
) -> Path:
    section = _normalize_section(section, config.diataxis.sections)
    resolved_title = title or slug.replace("-", " ").replace("_", " ").title()
    values = {"title": resolved_title, "date": date.today().isoformat()}

    info = SECTION_META.get(section)
    if info is None:
        raise ValueError(f"No template defined for section: {section!r}")
    rendered = Template(info.page_template).safe_substitute(values)

    folder = _section_dir(config, section)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug}.md"
    if path.exists():
        raise FileExistsError(f"Page already exists: {path}")
    path.write_text(rendered, encoding="utf-8")

    _build_section_index(config, section)
    return path


def diataxis_toc(config: Config, section: str | None = None) -> list[Path]:
    written: list[Path] = []
    if section is None:
        for sec in config.diataxis.sections:
            if _section_dir(config, sec).is_dir():
                written.append(_build_section_index(config, sec))
        written.append(_build_root_docs_index(config))
    else:
        sec = _normalize_section(section, config.diataxis.sections)
        written.append(_build_section_index(config, sec))
    return written
