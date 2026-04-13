"""Tests for the DeckSection import metadata round-trip.

The actual `present_section_import` MCP tool lives in the projio repo
(src/projio/mcp/presentio.py) and is exercised by an end-to-end smoke
test there. These tests cover only the notio-side contract: the
DeckSectionImport dataclass serializes cleanly through deck.yml so
imports survive round-tripping.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from notio.present.schema import (
    DeckSection,
    DeckSectionImport,
    DeckSpec,
    scaffold_deck,
)


def test_deck_section_import_roundtrip(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = scaffold_deck("d", base, template="lab-meeting")

    # Add an imported section
    spec.sections.append(
        DeckSection(
            key="remote-intro",
            path="imports/projio-ecosystem-overview.md",
            order=60,
            import_=DeckSectionImport(
                from_project="projio",
                deck="ecosystem-intro",
                section="overview",
                mode="reference",
            ),
        )
    )

    # Write out and reload
    deck_yml = base / "deck.yml"
    deck_yml.write_text(
        yaml.dump(spec.to_dict(), default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    reloaded = DeckSpec.from_yaml(deck_yml)

    remote = next((s for s in reloaded.sections if s.key == "remote-intro"), None)
    assert remote is not None
    assert remote.import_ is not None
    assert remote.import_.from_project == "projio"
    assert remote.import_.deck == "ecosystem-intro"
    assert remote.import_.section == "overview"
    assert remote.import_.mode == "reference"
    assert remote.path == "imports/projio-ecosystem-overview.md"


def test_freeze_mode_roundtrip(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = scaffold_deck("d", base, template="lab-meeting")
    spec.sections.append(
        DeckSection(
            key="r",
            path="imports/x.md",
            order=99,
            import_=DeckSectionImport(
                from_project="p",
                deck="d",
                section="s",
                mode="freeze",
            ),
        )
    )
    path = base / "deck.yml"
    path.write_text(yaml.dump(spec.to_dict(), sort_keys=False), encoding="utf-8")
    reloaded = DeckSpec.from_yaml(path)
    assert reloaded.sections[-1].import_.mode == "freeze"  # type: ignore[union-attr]


def test_non_imported_sections_have_none_import(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = scaffold_deck("d", base, template="lab-meeting")
    for s in spec.sections:
        assert s.import_ is None
