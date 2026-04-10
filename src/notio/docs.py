"""MkDocs monorepo nav generation for notio-managed directories.

Follows the pipeio ``docs_nav()`` pattern: scan a ``docs/`` subdirectory,
build a hierarchical nav, and write a standalone ``mkdocs.yml`` consumed by
the ``mkdocs-monorepo-plugin`` via ``!include`` in the root ``mkdocs.yml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from notio.config import load_config

# Directories under docs/ that are handled by their own nav generators
# and should be skipped by master_nav().
_MANAGED_SECTIONS = {"log", "pipelines", "manuscript", "plan", "infra"}


# ---------------------------------------------------------------------------
# Log nav
# ---------------------------------------------------------------------------


def log_nav(root: Path, *, write: bool = True) -> str:
    """Generate nav for ``docs/log/`` and optionally write the monorepo sub-mkdocs.yml.

    Produces a slim nav with one entry per note type pointing at its
    ``index.md`` (the auto-generated TOC).  Individual notes are NOT
    listed — the index pages already provide that listing.

    When *write* is True (default), writes ``docs/log/mkdocs.yml`` — a
    standalone MkDocs config consumed by the monorepo plugin via
    ``!include ./docs/log/mkdocs.yml`` in the root ``mkdocs.yml``.

    Returns the generated YAML string.
    """
    config = load_config(root)
    docs_base = config.notes_root  # typically root / "docs" / "log"
    if not docs_base.exists():
        return "# No docs/log/ directory found.\n"

    type_navs: list[dict[str, str]] = []

    # Root index first
    root_idx = docs_base / "index.md"
    if root_idx.exists():
        type_navs.append({"Overview": "index.md"})

    for type_dir in sorted(d for d in docs_base.iterdir() if d.is_dir()):
        if type_dir.name.startswith("."):
            continue

        idx = type_dir / "index.md"
        if not idx.exists():
            # Skip type dirs without an index — nothing useful to link to
            continue

        label = type_dir.name.replace("-", " ").replace("_", " ").title()
        type_navs.append({label: str(idx.relative_to(docs_base))})

    if not type_navs:
        return "# docs/log/ exists but contains no type indexes.\n"

    sub_config = {
        "site_name": "log",
        "docs_dir": ".",
        "nav": type_navs,
    }
    sub_yaml = yaml.dump(sub_config, sort_keys=False, default_flow_style=False)

    if write:
        sub_mkdocs = docs_base / "mkdocs.yml"
        sub_mkdocs.write_text(sub_yaml, encoding="utf-8")

    return sub_yaml


# ---------------------------------------------------------------------------
# Manuscript nav
# ---------------------------------------------------------------------------


def manuscript_nav(root: Path, *, write: bool = True) -> str:
    """Generate nav for ``docs/manuscript/`` and optionally write the monorepo sub-mkdocs.yml.

    Scans ``docs/manuscript/`` for manuscript subdirectories (each containing
    a ``manuscript.yml``).  Sections within each manuscript are listed by
    order, and a master.md link is included when present.

    When *write* is True (default), writes ``docs/manuscript/mkdocs.yml``.

    Returns the generated YAML string.
    """
    docs_base = root / "docs" / "manuscript"
    if not docs_base.exists():
        return "# No docs/manuscript/ directory found.\n"

    manuscript_navs: list[dict[str, Any]] = []

    for ms_dir in sorted(d for d in docs_base.iterdir() if d.is_dir()):
        if ms_dir.name.startswith("."):
            continue

        entries: list[dict[str, Any]] = []
        spec_path = ms_dir / "manuscript.yml"

        if spec_path.is_file():
            # Use manuscript spec for ordered sections
            try:
                from notio.manuscript.schema import ManuscriptSpec

                spec = ManuscriptSpec.from_yaml(spec_path)
                for section in sorted(spec.sections, key=lambda s: s.order):
                    section_path = ms_dir / section.path
                    if section_path.is_file():
                        title = section.key.replace("-", " ").replace("_", " ").title()
                        entries.append(
                            {title: str(section_path.relative_to(docs_base))}
                        )
            except Exception:
                # Fall back to scanning .md files
                pass

        if not entries:
            # Fallback: scan for .md files
            idx = ms_dir / "index.md"
            if idx.exists():
                entries.append({"Overview": str(idx.relative_to(docs_base))})
            for md in sorted(ms_dir.glob("*.md")):
                if md.name in ("index.md", "manuscript.yml"):
                    continue
                title = md.stem.replace("-", " ").replace("_", " ").title()
                entries.append({title: str(md.relative_to(docs_base))})

        # master.md
        master = ms_dir / "master.md"
        if master.is_file():
            entries.append({"Master": str(master.relative_to(docs_base))})

        if entries:
            manuscript_navs.append({ms_dir.name: entries})

    if not manuscript_navs:
        return "# docs/manuscript/ exists but contains no docs.\n"

    sub_config = {
        "site_name": "manuscript",
        "docs_dir": ".",
        "nav": manuscript_navs,
    }
    sub_yaml = yaml.dump(sub_config, sort_keys=False, default_flow_style=False)

    if write:
        sub_mkdocs = docs_base / "mkdocs.yml"
        sub_mkdocs.write_text(sub_yaml, encoding="utf-8")

    return sub_yaml


# ---------------------------------------------------------------------------
# Master doc nav
# ---------------------------------------------------------------------------


def master_nav(root: Path, *, write: bool = True) -> dict[str, str]:
    """Generate sub-mkdocs.yml for each ``docs/*/`` directory containing a master.md.

    Skips directories already managed by dedicated nav generators
    (pipelines, manuscript, log, infra).

    For each qualifying section directory (e.g. ``docs/plan/``), writes a
    standalone ``mkdocs.yml`` listing all ``.md`` files — analogous to
    how ``manuscript_nav()`` works for ``docs/manuscript/``.

    Returns a dict mapping section names to generated YAML strings.
    """
    from notio.manuscript.master import find_master_files

    masters = find_master_files(root)
    if not masters:
        return {}

    seen_sections: set[str] = set()
    results: dict[str, str] = {}

    for entry in masters:
        section = entry["section_root"]
        if section in seen_sections or section in _MANAGED_SECTIONS:
            continue
        # Respect nav_include frontmatter flag
        if not entry.get("nav_include", True):
            continue
        seen_sections.add(section)

        section_dir = root / "docs" / section
        if not section_dir.is_dir():
            continue

        nav_entries: list[dict[str, Any]] = []

        # index.md first
        idx = section_dir / "index.md"
        if idx.exists():
            nav_entries.append({"Overview": "index.md"})

        # All .md files (sorted), excluding index and mkdocs.yml
        skip = {"index.md", "mkdocs.yml"}
        for md in sorted(section_dir.glob("*.md")):
            if md.name in skip:
                continue
            title = md.stem.replace("-", " ").replace("_", " ").title()
            if md.name == "master.md":
                title = "Master Document"
            nav_entries.append({title: md.name})

        # Subdirectories with .md files (one level)
        for sub in sorted(d for d in section_dir.iterdir() if d.is_dir()):
            if sub.name.startswith(".") or sub.name.startswith("_"):
                continue
            sub_entries: list[dict[str, str]] = []
            for md in sorted(sub.glob("*.md")):
                title = md.stem.replace("-", " ").replace("_", " ").title()
                sub_entries.append(
                    {title: str(md.relative_to(section_dir))}
                )
            if sub_entries:
                label = sub.name.replace("-", " ").replace("_", " ").title()
                nav_entries.append({label: sub_entries})

        if not nav_entries:
            continue

        sub_config = {
            "site_name": section,
            "docs_dir": ".",
            "nav": nav_entries,
        }
        sub_yaml = yaml.dump(sub_config, sort_keys=False, default_flow_style=False)

        if write:
            sub_mkdocs = section_dir / "mkdocs.yml"
            sub_mkdocs.write_text(sub_yaml, encoding="utf-8")

        results[section] = sub_yaml

    return results
