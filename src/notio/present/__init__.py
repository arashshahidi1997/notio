"""notio.present — research presentation deck subpackage.

Deck artifacts parallel to notio.manuscript: YAML spec + ordered section
tree + Marp renderer (phase 1). Reveal.js and cross-project imports land
in later phases.

See docs/specs/presentio/presentio.md for the full design.
"""
from __future__ import annotations

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
