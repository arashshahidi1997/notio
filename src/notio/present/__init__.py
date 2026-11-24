"""notio.present — research presentation deck subpackage.

Deck artifacts parallel to notio.manuscript: YAML spec + ordered section
tree + Marp renderer (phase 1). Reveal.js and cross-project imports land
in later phases.

See docs/specs/presentio/presentio.md for the full design.

Deprecated (2026-11-24): notio.present is removed after the next notio release.
Write new decks as Quarto reveal.js (``format: revealjs``); in projio the
``quarto-talks`` skill does this.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "notio.present is deprecated and will be removed after the next notio release; "
    "write decks as Quarto reveal.js (format: revealjs, the quarto-talks skill in projio).",
    DeprecationWarning,
    stacklevel=2,
)

from notio.present.assembly import (
    Section,
    assemble_marp,
    assemble_pandoc,
    load_sections,
    write_assembled,
)
from notio.present.render import render
from notio.present.schema import (
    DeckFigure,
    DeckOutput,
    DeckSection,
    DeckSpec,
    scaffold_deck,
)

__all__ = [
    "DeckSpec",
    "DeckSection",
    "DeckFigure",
    "DeckOutput",
    "Section",
    "load_sections",
    "assemble_marp",
    "assemble_pandoc",
    "write_assembled",
    "render",
    "scaffold_deck",
]
