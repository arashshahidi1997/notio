"""Master document support — dual-marker docs that use Lua transclusion filter.

Master documents (e.g. docs/plan/master.md) use:
    [[plan/overview]]
    {% include-markdown "plan/overview.md" %}

The Lua filter handles Pandoc rendering; include-markdown + ezlinks handle MkDocs.
This module provides scanning, building, and scaffolding for master documents.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


MASTER_FILENAME = "master.md"
INCLUDE_RE = re.compile(
    r'\{%\s*include-markdown\s+"([^"]+)"\s*%\}'
)


def _parse_master_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from a master document."""
    fm_match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not fm_match:
        return {}
    try:
        import yaml
        return yaml.safe_load(fm_match.group(1)) or {}
    except Exception:
        return {}


def find_master_files(root: Path, *, require_frontmatter: bool = False) -> list[dict[str, Any]]:
    """Scan for ``docs/**/master.md`` files recursively.

    Only includes files whose frontmatter contains ``type: master``.
    Legacy master.md files without frontmatter are included when
    *require_frontmatter* is False (default) for backwards compatibility.

    Returns a list of dicts with keys: name, path, section_root,
    section_count, nav_include, and any other frontmatter fields.
    """
    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        return []
    masters = []
    for master_path in sorted(docs_dir.rglob(MASTER_FILENAME)):
        if not master_path.is_file():
            continue
        # Determine section root: first dir component under docs/
        rel = master_path.relative_to(docs_dir)
        section_root = rel.parts[0] if len(rel.parts) > 1 else rel.stem
        # Skip hidden/internal directories
        if any(p.startswith(".") or p.startswith("_") for p in rel.parts[:-1]):
            continue

        text = master_path.read_text(encoding="utf-8")
        fm = _parse_master_frontmatter(text)

        # Filter: require type: master in frontmatter
        if fm.get("type") != "master":
            if require_frontmatter:
                continue
            # Legacy compat: accept files without frontmatter only at depth 1
            if len(rel.parts) != 2:
                continue

        sections = INCLUDE_RE.findall(text)
        entry: dict[str, Any] = {
            "name": section_root,
            "path": str(master_path.relative_to(root)),
            "section_root": section_root,
            "section_count": len(sections),
            "nav_include": fm.get("nav_include", True),
        }
        entry.update(fm)
        masters.append(entry)
    return masters


def _load_render_defaults(root: Path) -> dict[str, Any]:
    """Load .projio/render.yml if present, else return empty dict."""
    import yaml

    render_yml = root / ".projio" / "render.yml"
    if not render_yml.is_file():
        return {}
    return yaml.safe_load(render_yml.read_text(encoding="utf-8")) or {}


def build_master(
    root: Path,
    name: str,
    format: str = "pdf",
    render_config: dict[str, Any] | None = None,
) -> Path:
    """Build a master document via pandoc with Lua filter + citeproc.

    Args:
        root: Project root directory.
        name: Master document name (subdirectory under docs/).
        format: Output format (pdf, latex, md, docx, html).
        render_config: Optional override for render settings.
            Falls back to .projio/render.yml.

    Returns:
        Path to the output file.
    """
    master_path = root / "docs" / name / MASTER_FILENAME
    if not master_path.is_file():
        raise FileNotFoundError(f"Master document not found: {master_path}")

    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError("pandoc not found — install pandoc to build master documents")

    config = render_config or _load_render_defaults(root)

    output_dir = root / "_build" / "pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}-master.{format}"

    cmd = [pandoc, str(master_path), "-o", str(output_path)]

    # Lua filter
    lua_filter = config.get("lua_filter", ".projio/filters/include.lua")
    if lua_filter:
        filter_path = root / lua_filter
        if filter_path.is_file():
            cmd.extend([f"--lua-filter={filter_path}"])

    # Bibliography + citeproc
    bib = config.get("bibliography", "")
    if bib:
        bib_path = root / bib
        if bib_path.is_file():
            cmd.extend(["--citeproc", f"--bibliography={bib_path}"])

    csl = config.get("csl", "")
    if csl:
        csl_path = root / csl
        if csl_path.is_file():
            cmd.extend([f"--csl={csl_path}"])

    # PDF engine
    pdf_engine = config.get("pdf_engine", "lualatex")
    if pdf_engine and format == "pdf":
        cmd.extend([f"--pdf-engine={pdf_engine}"])

    # Resource path
    resource_path = config.get("resource_path", [])
    if resource_path:
        cmd.extend([f"--resource-path={':'.join(resource_path)}"])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))
    if result.returncode != 0:
        raise RuntimeError(
            f"pandoc failed (exit {result.returncode}):\n{result.stderr}"
        )
    return output_path


def generate_master_md(sections: list[dict[str, str]], name: str) -> str:
    """Generate a dual-marker master.md from a section list.

    Each section dict should have keys: path (relative .md path), title (optional).
    The generated file uses both wikilink and include-markdown markers.

    Args:
        sections: List of dicts with 'path' and optional 'title' keys.
        name: Document name (used in the YAML frontmatter title).

    Returns:
        Generated markdown string.
    """
    lines = [
        "---",
        f'title: "{name}"',
        "---",
        "",
    ]
    for section in sections:
        path = section["path"]
        # Derive wikilink target: strip .md extension and docs/ prefix
        wiki_target = path
        if wiki_target.endswith(".md"):
            wiki_target = wiki_target[:-3]
        if wiki_target.startswith("docs/"):
            wiki_target = wiki_target[5:]

        lines.append(f"[[{wiki_target}]]")
        lines.append('{{% include-markdown "{path}" %}}'.format(path=path))
        lines.append("")

    return "\n".join(lines)
