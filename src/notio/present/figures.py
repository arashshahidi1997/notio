"""Figure reference resolution for deck sections.

Format-aware extension selection:
- Marp → PNG preferred (most reliable for html/pdf/pptx export)
- Reveal.js → SVG preferred, fall back to PNG (phase 3)
- PPTX → PNG preferred (phase 5)

Phase 1 only supports ``source: figio`` figures (local project). Phase 4
adds ``source: worklog`` for cross-project figure resolution via
``mcp__worklog__worklog_read_file``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from notio.present.schema import DeckFigure, DeckSpec

FormatHint = Literal["marp", "revealjs", "pptx"]

FIGURE_REF_RE = re.compile(r"!\[([^\]]*)\]\(fig:([a-zA-Z0-9_\-]+)\)")

_EXT_PREFERENCE: dict[FormatHint, tuple[str, ...]] = {
    "marp": ("png", "svg", "pdf"),
    "revealjs": ("svg", "png", "pdf"),
    "pptx": ("png", "svg", "pdf"),
}


def _figio_build_dir(figure: DeckFigure, base_dir: Path) -> Path:
    """Resolve the figio ``_build`` directory for a figure.

    Phase 1 assumes figures live under the project's ``figures/`` directory
    as scanned by figio. The search starts at ``base_dir`` (the deck dir)
    and walks up to the project root looking for a ``figures/_build`` tree.
    This mirrors how figio itself discovers figures via
    ``figio.mcp.mcp_figure_list``.
    """
    from notio.repo import repo_root

    root = repo_root(base_dir) or base_dir
    # Primary: project-wide figures/_build
    candidates = [
        root / "figures" / "_build",
        root / "docs" / "figures" / "_build",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    # Fallback: deck-local figures/_build
    return base_dir / "figures" / "_build"


def resolve_figure_paths(
    spec: DeckSpec,
    base_dir: Path,
    format: FormatHint = "marp",
) -> dict[str, Path]:
    """Map deck figure ids to their built output paths.

    Returns ``{figure_id: absolute_path}`` for every figure that resolves.
    Unresolved figures are omitted — the caller decides whether that's an
    error (render) or a warning (validate).
    """
    resolved: dict[str, Path] = {}
    preference = _EXT_PREFERENCE.get(format, ("png", "svg", "pdf"))

    for figure in spec.figures:
        if figure.source != "figio":
            # Phase 4 will implement worklog source.
            continue
        fig_id = figure.figure or figure.id
        build_dir = _figio_build_dir(figure, base_dir)

        for ext in preference:
            candidate = build_dir / f"{fig_id}.{ext}"
            if candidate.is_file():
                resolved[figure.id] = candidate
                break
        else:
            bare = fig_id.removeprefix("fig-")
            for ext in preference:
                candidate = build_dir / f"{bare}.{ext}"
                if candidate.is_file():
                    resolved[figure.id] = candidate
                    break

    return resolved


def insert_figure_references(
    text: str,
    figures: dict[str, Path],
    base_dir: Path,
) -> str:
    """Replace ``![caption](fig:<id>)`` placeholders with real paths.

    Unresolved figure ids are left untouched so validation can flag them.
    """

    def _replace(m: re.Match) -> str:
        caption = m.group(1)
        fig_id = m.group(2)
        if fig_id not in figures:
            return m.group(0)
        fig_path = figures[fig_id]
        try:
            rel = fig_path.relative_to(base_dir)
        except ValueError:
            rel = fig_path
        return f"![{caption}]({rel})"

    return FIGURE_REF_RE.sub(_replace, text)


def validate_figures(
    spec: DeckSpec,
    base_dir: Path,
    format: FormatHint = "marp",
) -> list[str]:
    """Return a list of figure ids that have no built output."""
    resolved = resolve_figure_paths(spec, base_dir, format=format)
    return [f.id for f in spec.figures if f.id not in resolved]
