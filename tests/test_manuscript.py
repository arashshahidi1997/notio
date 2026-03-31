"""Tests for notio.manuscript subpackage."""

from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from notio.manuscript.schema import (
    Author,
    BibConfig,
    FigureMapping,
    FiguresConfig,
    ManuscriptSpec,
    RenderConfig,
    SectionEntry,
    scaffold_spec,
)
from notio.manuscript.assembly import (
    adjust_headings,
    assemble,
    load_sections,
    strip_frontmatter,
    write_assembled,
)
from notio.manuscript.figures import (
    insert_figure_references,
    resolve_figure_paths,
    validate_figures,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestManuscriptSpec:
    def test_from_dict_minimal(self):
        spec = ManuscriptSpec.from_dict({"name": "test"})
        assert spec.name == "test"
        assert spec.title == ""
        assert spec.sections == []
        assert spec.authors == []

    def test_from_dict_full(self):
        data = {
            "name": "my-paper",
            "title": "My Paper",
            "authors": [
                {"name": "Alice", "affiliation": "Uni X"},
                {"name": "Bob"},
            ],
            "sections": [
                {"key": "intro", "path": "sections/intro.md", "order": 1},
                {"key": "methods", "path": "sections/methods.md", "order": 2, "heading_level": 2},
            ],
            "bibliography": {"bib_file": "refs.bib", "csl": "nature.csl"},
            "figures": {
                "dir": "figs/",
                "mappings": [
                    {"id": "fig-1", "label": "Figure 1", "caption": "Overview"},
                ],
            },
            "render": {
                "output_dir": "out/",
                "formats": ["pdf", "docx"],
                "pandoc_args": ["--toc"],
                "variables": {"fontsize": "12pt"},
            },
        }
        spec = ManuscriptSpec.from_dict(data)
        assert spec.name == "my-paper"
        assert len(spec.authors) == 2
        assert spec.authors[0].affiliation == "Uni X"
        assert len(spec.sections) == 2
        assert spec.sections[1].heading_level == 2
        assert spec.bibliography.csl == "nature.csl"
        assert len(spec.figures.mappings) == 1
        assert spec.render.formats == ["pdf", "docx"]
        assert spec.render.variables["fontsize"] == "12pt"

    def test_to_dict_roundtrip(self):
        spec = ManuscriptSpec(
            name="rt",
            title="Roundtrip",
            authors=[Author(name="Test")],
            sections=[SectionEntry(key="a", path="a.md", order=1)],
        )
        d = spec.to_dict()
        spec2 = ManuscriptSpec.from_dict(d)
        assert spec2.name == spec.name
        assert spec2.sections[0].key == "a"

    def test_from_yaml(self, tmp_path):
        yaml_text = textwrap.dedent("""\
            name: yaml-test
            title: YAML Test Paper
            sections:
              - key: intro
                path: sections/intro.md
                order: 1
            bibliography:
              bib_file: refs.bib
        """)
        spec_path = tmp_path / "manuscript.yml"
        spec_path.write_text(yaml_text, encoding="utf-8")
        spec = ManuscriptSpec.from_yaml(spec_path)
        assert spec.name == "yaml-test"
        assert spec.title == "YAML Test Paper"
        assert len(spec.sections) == 1
        assert spec.bibliography.bib_file == "refs.bib"


class TestScaffold:
    def test_scaffold_creates_files(self, tmp_path):
        spec = scaffold_spec("my-paper", tmp_path)
        assert spec.name == "my-paper"
        assert (tmp_path / "manuscript.yml").is_file()
        assert (tmp_path / "sections" / "abstract.md").is_file()
        assert (tmp_path / "sections" / "introduction.md").is_file()
        assert (tmp_path / "sections" / "methods.md").is_file()
        assert (tmp_path / "sections" / "results.md").is_file()
        assert (tmp_path / "sections" / "discussion.md").is_file()
        assert len(spec.sections) == 5

    def test_scaffold_idempotent(self, tmp_path):
        scaffold_spec("my-paper", tmp_path)
        # Modify a section
        intro = tmp_path / "sections" / "introduction.md"
        intro.write_text("custom content", encoding="utf-8")
        # Scaffold again — should not overwrite
        scaffold_spec("my-paper", tmp_path)
        assert intro.read_text(encoding="utf-8") == "custom content"


# ---------------------------------------------------------------------------
# Assembly tests
# ---------------------------------------------------------------------------


class TestStripFrontmatter:
    def test_with_frontmatter(self):
        text = "---\ntitle: Test\norder: 1\n---\n\n# Heading\n\nBody text.\n"
        result = strip_frontmatter(text)
        assert result == "# Heading\n\nBody text.\n"

    def test_without_frontmatter(self):
        text = "# Just a heading\n\nBody.\n"
        assert strip_frontmatter(text) == text

    def test_empty(self):
        assert strip_frontmatter("") == ""


class TestAdjustHeadings:
    def test_no_offset(self):
        text = "# H1\n## H2\n"
        assert adjust_headings(text, 0) == text

    def test_positive_offset(self):
        text = "# H1\n## H2\n"
        result = adjust_headings(text, 1)
        assert "## H1" in result
        assert "### H2" in result

    def test_negative_offset(self):
        text = "## H2\n### H3\n"
        result = adjust_headings(text, -1)
        assert "# H2" in result
        assert "## H3" in result

    def test_clamp_min(self):
        text = "# H1\n"
        result = adjust_headings(text, -2)
        assert result.startswith("# ")  # clamped to 1

    def test_clamp_max(self):
        text = "###### H6\n"
        result = adjust_headings(text, 2)
        assert result.startswith("###### ")  # clamped to 6


class TestLoadSections:
    def test_loads_and_orders(self, tmp_path):
        (tmp_path / "b.md").write_text("---\ntitle: B\n---\n\n# B\n", encoding="utf-8")
        (tmp_path / "a.md").write_text("---\ntitle: A\n---\n\n# A\n", encoding="utf-8")
        spec = ManuscriptSpec(
            name="test",
            sections=[
                SectionEntry(key="b", path="b.md", order=2),
                SectionEntry(key="a", path="a.md", order=1),
            ],
        )
        sections = load_sections(spec, tmp_path)
        assert len(sections) == 2
        assert sections[0].entry.key == "a"
        assert sections[1].entry.key == "b"

    def test_missing_section_raises(self, tmp_path):
        spec = ManuscriptSpec(
            name="test",
            sections=[SectionEntry(key="missing", path="nope.md", order=1)],
        )
        with pytest.raises(FileNotFoundError, match="missing"):
            load_sections(spec, tmp_path)

    def test_heading_adjustment(self, tmp_path):
        (tmp_path / "s.md").write_text("# Title\n\nBody.\n", encoding="utf-8")
        spec = ManuscriptSpec(
            name="test",
            sections=[SectionEntry(key="s", path="s.md", order=1, heading_level=2)],
        )
        sections = load_sections(spec, tmp_path)
        assert "## Title" in sections[0].content


class TestAssemble:
    def _make_sections(self, tmp_path):
        (tmp_path / "a.md").write_text(
            "---\ntitle: A\norder: 1\n---\n\n# Section A\n\nContent A.\n",
            encoding="utf-8",
        )
        (tmp_path / "b.md").write_text(
            "---\ntitle: B\norder: 2\n---\n\n# Section B\n\nContent B.\n",
            encoding="utf-8",
        )
        return ManuscriptSpec(
            name="test",
            title="Test Paper",
            authors=[Author(name="Alice", affiliation="Uni")],
            sections=[
                SectionEntry(key="a", path="a.md", order=1),
                SectionEntry(key="b", path="b.md", order=2),
            ],
        )

    def test_assemble_concatenates(self, tmp_path):
        spec = self._make_sections(tmp_path)
        result = assemble(spec, tmp_path)
        assert "# Section A" in result
        assert "# Section B" in result
        assert result.index("Section A") < result.index("Section B")

    def test_assemble_includes_metadata(self, tmp_path):
        spec = self._make_sections(tmp_path)
        result = assemble(spec, tmp_path)
        assert 'title: "Test Paper"' in result
        assert "Alice" in result

    def test_assemble_strips_frontmatter(self, tmp_path):
        spec = self._make_sections(tmp_path)
        result = assemble(spec, tmp_path)
        # Section frontmatter should not appear (except the pandoc metadata block)
        assert "order: 1" not in result
        assert "order: 2" not in result

    def test_write_assembled(self, tmp_path):
        spec = self._make_sections(tmp_path)
        path = write_assembled(spec, tmp_path)
        assert path.is_file()
        assert path.name == "assembled.md"
        assert "Section A" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Figure tests
# ---------------------------------------------------------------------------


class TestFigures:
    def test_resolve_finds_pdf(self, tmp_path):
        build_dir = tmp_path / "figures" / "_build"
        build_dir.mkdir(parents=True)
        (build_dir / "fig-1.pdf").write_text("fake pdf", encoding="utf-8")
        spec = ManuscriptSpec(
            name="test",
            figures=FiguresConfig(
                dir="figures/",
                mappings=[FigureMapping(id="fig-1")],
            ),
        )
        resolved = resolve_figure_paths(spec, tmp_path)
        assert "fig-1" in resolved
        assert resolved["fig-1"].suffix == ".pdf"

    def test_resolve_prefers_pdf_over_svg(self, tmp_path):
        build_dir = tmp_path / "figures" / "_build"
        build_dir.mkdir(parents=True)
        (build_dir / "fig-1.pdf").write_text("pdf", encoding="utf-8")
        (build_dir / "fig-1.svg").write_text("svg", encoding="utf-8")
        spec = ManuscriptSpec(
            name="test",
            figures=FiguresConfig(
                dir="figures/",
                mappings=[FigureMapping(id="fig-1")],
            ),
        )
        resolved = resolve_figure_paths(spec, tmp_path)
        assert resolved["fig-1"].suffix == ".pdf"

    def test_resolve_via_spec_path(self, tmp_path):
        spec_dir = tmp_path / "figs" / "overview"
        build_dir = spec_dir / "_build"
        build_dir.mkdir(parents=True)
        (build_dir / "fig-overview.svg").write_text("svg", encoding="utf-8")
        spec = ManuscriptSpec(
            name="test",
            figures=FiguresConfig(
                mappings=[
                    FigureMapping(id="fig-overview", spec="figs/overview/overview.figurespec.yaml"),
                ],
            ),
        )
        resolved = resolve_figure_paths(spec, tmp_path)
        assert "fig-overview" in resolved

    def test_validate_missing(self, tmp_path):
        spec = ManuscriptSpec(
            name="test",
            figures=FiguresConfig(
                mappings=[FigureMapping(id="fig-missing")],
            ),
        )
        missing = validate_figures(spec, tmp_path)
        assert missing == ["fig-missing"]

    def test_validate_all_present(self, tmp_path):
        build_dir = tmp_path / "figures" / "_build"
        build_dir.mkdir(parents=True)
        (build_dir / "fig-1.png").write_text("png", encoding="utf-8")
        spec = ManuscriptSpec(
            name="test",
            figures=FiguresConfig(
                dir="figures/",
                mappings=[FigureMapping(id="fig-1")],
            ),
        )
        assert validate_figures(spec, tmp_path) == []


class TestInsertFigureReferences:
    def test_replaces_known_figures(self, tmp_path):
        text = "Some text.\n\n![Overview](fig:fig-1)\n\nMore text.\n"
        figures = {"fig-1": tmp_path / "figures" / "_build" / "fig-1.pdf"}
        result = insert_figure_references(text, figures, tmp_path)
        assert "fig:" not in result
        assert "fig-1.pdf" in result

    def test_leaves_unknown_figures(self):
        text = "![](fig:unknown)\n"
        result = insert_figure_references(text, {}, Path("/tmp"))
        assert result == text

    def test_preserves_caption(self, tmp_path):
        text = "![My caption](fig:fig-x)\n"
        figures = {"fig-x": tmp_path / "out" / "fig-x.svg"}
        result = insert_figure_references(text, figures, tmp_path)
        assert "![My caption]" in result
