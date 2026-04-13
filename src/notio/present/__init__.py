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
    load_sections,
    write_assembled,
)
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
    "write_assembled",
    "scaffold_deck",
]
