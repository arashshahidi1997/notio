"""Figure reference resolution and figio integration."""

from __future__ import annotations

import re
from pathlib import Path

from notio.manuscript.schema import ManuscriptSpec

# Matches ![caption](fig:<figure-id>) or ![](fig:<figure-id>)
FIGURE_REF_RE = re.compile(r"!\[([^\]]*)\]\(fig:([a-zA-Z0-9_-]+)\)")


def resolve_figure_paths(
    spec: ManuscriptSpec, base_dir: Path
) -> dict[str, Path]:
    """Map figure IDs to their built output paths.

    Checks figio ``_build/`` directories for rendered outputs (PDF preferred,
    then SVG, then PNG). Returns a dict of ``{figure_id: output_path}``.
    """
    resolved: dict[str, Path] = {}
    for mapping in spec.figures.mappings:
        if mapping.spec:
            spec_path = base_dir / mapping.spec
            build_dir = spec_path.parent / "_build"
        else:
            build_dir = base_dir / spec.figures.dir / "_build"

        # Try common output formats in preference order
        fig_id = mapping.id
        for ext in ("pdf", "svg", "png"):
            candidate = build_dir / f"{fig_id}.{ext}"
            if candidate.is_file():
                resolved[fig_id] = candidate
                break
        else:
            # Also try without the fig- prefix
            bare_id = fig_id.removeprefix("fig-")
            for ext in ("pdf", "svg", "png"):
                candidate = build_dir / f"{bare_id}.{ext}"
                if candidate.is_file():
                    resolved[fig_id] = candidate
                    break

    return resolved


def insert_figure_references(
    text: str,
    figures: dict[str, Path],
    base_dir: Path,
) -> str:
    """Replace figure placeholders with resolved paths.

    Placeholders use the syntax ``![caption](fig:<figure-id>)``. If a figure
    ID is not in *figures*, the placeholder is left unchanged.
    """

    def _replace(m: re.Match) -> str:
        caption = m.group(1)
        fig_id = m.group(2)
        if fig_id not in figures:
            return m.group(0)  # leave unresolved
        fig_path = figures[fig_id]
        try:
            rel = fig_path.relative_to(base_dir)
        except ValueError:
            rel = fig_path
        return f"![{caption}]({rel})"

    return FIGURE_REF_RE.sub(_replace, text)


def validate_figures(
    spec: ManuscriptSpec, base_dir: Path
) -> list[str]:
    """Check that all referenced figures have been built.

    Returns a list of missing figure IDs (empty if all present).
    """
    resolved = resolve_figure_paths(spec, base_dir)
    missing: list[str] = []
    for mapping in spec.figures.mappings:
        if mapping.id not in resolved:
            missing.append(mapping.id)
    return missing
