"""Assembly tests: section loading, Marp frontmatter, intra-file --- preservation."""
from __future__ import annotations

from pathlib import Path

import pytest

from notio.present.assembly import (
    assemble_marp,
    load_sections,
    local_resolver,
    strip_frontmatter,
    write_assembled,
)
from notio.present.schema import DeckSpec, scaffold_deck


def _write_section(base: Path, rel: str, title: str, body: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: \"{title}\"\norder: 10\n---\n\n{body}\n",
        encoding="utf-8",
    )


def _sample_deck(base: Path) -> DeckSpec:
    spec = scaffold_deck("assembly-smoke", base, template="lab-meeting")
    # Overwrite section bodies so we know exactly what we're asserting on.
    for section in spec.sections:
        (base / section.path).write_text(
            f"---\ntitle: {section.key}\norder: {section.order}\n---\n\n"
            f"# {section.key.title()}\n\nContent for {section.key}.\n",
            encoding="utf-8",
        )
    return spec


def test_load_sections_orders_correctly(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = _sample_deck(base)

    sections = load_sections(spec, base)
    assert [s.entry.key for s in sections] == sorted(
        (s.key for s in spec.sections),
        key=lambda k: next(e.order for e in spec.sections if e.key == k),
    )
    # First section's content has frontmatter stripped
    assert sections[0].content.startswith("# ")
    assert "---" not in sections[0].content.split("\n\n")[0]


def test_load_sections_missing_file(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = _sample_deck(base)
    # Delete one section file
    (base / spec.sections[0].path).unlink()
    with pytest.raises(FileNotFoundError):
        load_sections(spec, base)


def test_load_sections_custom_resolver(tmp_path: Path):
    """The resolver callable lets phase 4 cross-project imports plug in."""
    base = tmp_path / "deck"
    base.mkdir()
    spec = _sample_deck(base)

    called = []

    def tracking_resolver(entry, base_dir):
        called.append(entry.key)
        return local_resolver(entry, base_dir)

    sections = load_sections(spec, base, resolver=tracking_resolver)
    assert len(sections) == len(spec.sections)
    assert sorted(called) == sorted(s.key for s in spec.sections)


def test_assemble_marp_prepends_frontmatter(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = _sample_deck(base)
    text = assemble_marp(spec, base)

    assert text.startswith("---\n")
    assert "marp: true" in text
    assert "theme: default" in text
    # Frontmatter terminator appears before the first section
    head, _, body = text.partition("\n---\n")
    assert "# " in body or "Title" in body


def test_assemble_marp_preserves_intra_file_separators(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = scaffold_deck("intra-separator", base, template="lab-meeting")
    # Replace first section with one containing an intra-file slide break
    first = base / spec.sections[0].path
    first.write_text(
        "---\ntitle: intro\norder: 10\n---\n\n"
        "# Slide A\n\nBody A\n\n---\n\n# Slide B\n\nBody B\n",
        encoding="utf-8",
    )
    # Trim to just the first section
    spec.sections = [spec.sections[0]]
    text = assemble_marp(spec, base)

    # The intra-file --- survives into the assembled output
    body_after_front = text.split("\n---\n", 1)[1]
    assert body_after_front.count("---") >= 1
    assert "Slide A" in text
    assert "Slide B" in text


def test_assemble_marp_between_sections(tmp_path: Path):
    """Two sections get a slide separator between them."""
    base = tmp_path / "deck"
    base.mkdir()
    spec = _sample_deck(base)
    # Keep only first two for clarity
    spec.sections = spec.sections[:2]
    text = assemble_marp(spec, base)
    # Slide break between the two section bodies
    post_frontmatter = text.split("\n---\n", 1)[1]
    # At least one --- appears between the section bodies
    assert "\n---\n" in post_frontmatter


def test_write_assembled_creates_output(tmp_path: Path):
    base = tmp_path / "deck"
    base.mkdir()
    spec = _sample_deck(base)
    path = write_assembled(spec, base)
    assert path.is_file()
    assert path.name == "assembled.md"
    assert "marp: true" in path.read_text(encoding="utf-8")


def test_strip_frontmatter_imported_from_manuscript():
    """Sanity check the re-export — manuscript change would surface here."""
    text = "---\nfoo: 1\n---\n\nbody\n"
    assert strip_frontmatter(text) == "body\n"
