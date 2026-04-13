"""Deck validation tests."""
from __future__ import annotations

from pathlib import Path

from notio.present.schema import DeckSpec, scaffold_deck
from notio.present.validate import validate_deck


def test_validate_scaffolded_deck_is_structurally_valid(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    scaffold_deck("v", base, template="lab-meeting")
    spec = DeckSpec.from_yaml(base / "deck.yml")

    result = validate_deck(spec, base)
    assert result.valid
    assert not result.errors


def test_validate_detects_missing_section_file(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    scaffold_deck("v", base, template="lab-meeting")
    spec = DeckSpec.from_yaml(base / "deck.yml")

    # Delete one section
    (base / spec.sections[0].path).unlink()
    result = validate_deck(spec, base)
    assert not result.valid
    assert any("missing" in e.lower() for e in result.errors)


def test_validate_detects_duplicate_order(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    scaffold_deck("v", base, template="lab-meeting")
    spec = DeckSpec.from_yaml(base / "deck.yml")
    spec.sections[1].order = spec.sections[0].order
    result = validate_deck(spec, base)
    assert not result.valid
    assert any("Duplicate" in e for e in result.errors)
