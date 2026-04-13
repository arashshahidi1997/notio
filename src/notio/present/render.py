"""Renderer dispatcher for presentio decks.

Reads ``spec.format`` and delegates to the right backend module. Backend
modules are imported lazily so a Marp-only install doesn't require
pandoc, and a reveal.js-only setup doesn't require marp-cli.
"""

from __future__ import annotations

from pathlib import Path

from notio.present.schema import DeckSpec


def render(
    spec: DeckSpec,
    base_dir: Path,
    *,
    formats: list[str] | None = None,
) -> list[Path]:
    """Dispatch to the renderer matching ``spec.format``.

    - ``marp`` → :func:`notio.present.render_marp.render_marp`
    - ``revealjs`` → :func:`notio.present.render_revealjs.render_revealjs`

    Raises :class:`ValueError` if the format is unknown.
    """
    if spec.format == "marp":
        from notio.present.render_marp import render_marp

        return render_marp(spec, base_dir, formats=formats)
    elif spec.format == "revealjs":
        from notio.present.render_revealjs import render_revealjs

        return render_revealjs(spec, base_dir, formats=formats)
    else:
        raise ValueError(f"Unknown deck format: {spec.format!r}")
