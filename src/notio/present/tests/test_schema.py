"""Round-trip and scaffold tests for DeckSpec."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from notio.present.schema import (
    VALID_FORMATS,
    DeckFigure,
    DeckSection,
    DeckSectionImport,
    DeckSpec,
    resolve_deck_render,
    scaffold_deck,
)


def _sample_dict() -> dict:
    return {
        "name": "smoketest",
        "title": "Smoketest Deck",
        "subtitle": "A smoke test",
        "author": [{"name": "Alice", "affiliation": "Lab"}],
        "date": "2026-04-24",
        "venue": "lab-meeting",
        "format": "marp",
        "sections": [
            {"key": "intro", "path": "sections/intro.md", "order": 10},
            {
                "key": "imported",
                "path": "sections/imported.md",
                "order": 20,
                "import": {
                    "from_project": "pixecog",
                    "deck": "thesis",
                    "section": "methods",
                    "mode": "reference",
                },
            },
        ],
        "figures": [
            {"id": "fig-arch", "source": "figio", "figure": "architecture"},
        ],
        "bibliography": {"bib_file": "", "csl": ""},
        "render": {
            "output_dir": "build/",
            "theme": "gaia",
            "ratio": "16:9",
            "paginate": True,
            "marp_args": ["--html"],
        },
        "outputs": [{"format": "html", "path": "build/deck.html"}],
    }


def test_deckspec_from_dict():
    data = _sample_dict()
    spec = DeckSpec.from_dict(data)
    assert spec.name == "smoketest"
    assert spec.title == "Smoketest Deck"
    assert spec.format == "marp"
    assert spec.render.theme == "gaia"
    assert len(spec.sections) == 2
    assert spec.sections[0].key == "intro"
    assert spec.sections[1].import_ is not None
    assert spec.sections[1].import_.from_project == "pixecog"
    assert spec.figures[0].id == "fig-arch"
    assert spec.author[0].name == "Alice"


def test_deckspec_roundtrip(tmp_path: Path):
    data = _sample_dict()
    spec = DeckSpec.from_dict(data)
    path = tmp_path / "deck.yml"
    path.write_text(yaml.dump(spec.to_dict(), sort_keys=False), encoding="utf-8")
    reloaded = DeckSpec.from_yaml(path)
    assert reloaded.name == spec.name
    assert reloaded.title == spec.title
    assert reloaded.format == spec.format
    assert len(reloaded.sections) == len(spec.sections)
    assert reloaded.sections[1].import_ is not None
    assert reloaded.sections[1].import_.deck == "thesis"
    assert reloaded.render.marp_args == ["--html"]


def test_deckspec_invalid_format():
    data = _sample_dict()
    data["format"] = "powerpoint"
    with pytest.raises(ValueError, match="Unknown deck format"):
        DeckSpec.from_dict(data)


def test_valid_formats_constant():
    assert "marp" in VALID_FORMATS
    assert "revealjs" in VALID_FORMATS


def test_scaffold_deck_lab_meeting(tmp_path: Path):
    base = tmp_path / "lab-meeting-deck"
    base.mkdir()
    spec = scaffold_deck("lab-meeting-deck", base, template="lab-meeting")

    assert spec.name == "lab-meeting-deck"
    assert spec.format == "marp"
    assert (base / "deck.yml").is_file()
    section_keys = [s.key for s in spec.sections]
    assert "title" in section_keys
    assert "results" in section_keys

    # Section files scaffolded with frontmatter
    first_section = base / spec.sections[0].path
    assert first_section.is_file()
    body = first_section.read_text(encoding="utf-8")
    assert body.startswith("---")
    assert "deck: lab-meeting-deck" in body


def test_scaffold_deck_journal_club(tmp_path: Path):
    base = tmp_path / "jc"
    base.mkdir()
    spec = scaffold_deck("jc", base, template="journal-club")
    keys = [s.key for s in spec.sections]
    assert "motivation" in keys
    assert "takeaways" in keys


def test_scaffold_deck_invalid_template(tmp_path: Path):
    base = tmp_path / "x"
    base.mkdir()
    with pytest.raises(ValueError, match="Unknown template"):
        scaffold_deck("x", base, template="nonexistent")


def test_scaffold_deck_invalid_format(tmp_path: Path):
    base = tmp_path / "x"
    base.mkdir()
    with pytest.raises(ValueError, match="Unknown deck format"):
        scaffold_deck("x", base, format="powerpoint")


def test_resolve_deck_render_no_project(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = DeckSpec.from_dict(_sample_dict())
    resolved = resolve_deck_render(spec, base)
    # No .projio/render.yml means no inherited bib
    assert resolved["bib_file"] == ""
    assert resolved["theme"] == "gaia"
    assert resolved["ratio"] == "16:9"
