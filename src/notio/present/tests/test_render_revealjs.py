"""Tests for the reveal.js backend (pandoc -t revealjs).

Pandoc is mocked via subprocess.run patching so tests run without a
pandoc install. A separate integration test would exercise real
pandoc, but is gated behind pandoc availability like the citeproc test.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from notio.present.assembly import assemble_pandoc, write_assembled_pandoc
from notio.present.render import render
from notio.present.render_revealjs import (
    build_pandoc_revealjs_command,
    prepare_deck_markdown,
    render_revealjs,
)
from notio.present.schema import DeckSpec, scaffold_deck


def _sample_revealjs_spec(tmp_path: Path) -> tuple[DeckSpec, Path]:
    base = tmp_path / "reveal-deck"
    base.mkdir()
    spec = scaffold_deck("reveal-deck", base, template="lab-meeting")
    spec.format = "revealjs"
    spec.title = "Reveal Smoke"
    spec.render.theme = "black"
    spec.render.ratio = "16:9"
    for section in spec.sections:
        (base / section.path).write_text(
            f"---\ntitle: {section.key}\norder: {section.order}\n---\n\n"
            f"# {section.key.title()}\n\nBody of {section.key}.\n",
            encoding="utf-8",
        )
    return spec, base


def test_assemble_pandoc_emits_pandoc_frontmatter(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    text = assemble_pandoc(spec, base)
    assert text.startswith("---\n")
    assert 'title: "Reveal Smoke"' in text
    # Must NOT contain Marp-specific keys
    assert "marp: true" not in text
    assert "paginate: true" not in text
    # Theme passes through as a variable
    assert "theme: black" in text
    # Section slide separators present
    post_front = text.split("\n---\n", 1)[1]
    assert "\n---\n" in post_front
    # Sections present
    assert "# Title" in text
    assert "# Context" in text


def test_assemble_pandoc_preserves_intra_file_separators(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    first = base / spec.sections[0].path
    first.write_text(
        "---\ntitle: intro\norder: 10\n---\n\n"
        "# Slide A\n\nBody A\n\n---\n\n# Slide B\n\nBody B\n",
        encoding="utf-8",
    )
    spec.sections = [spec.sections[0]]
    text = assemble_pandoc(spec, base)
    assert "Slide A" in text
    assert "Slide B" in text
    # Intra-file --- survives in the section body
    body = text.split("\n---\n", 1)[1]
    assert "---" in body


def test_write_assembled_dispatches_by_format(tmp_path: Path):
    """write_assembled picks pandoc vs marp by spec.format."""
    from notio.present.assembly import write_assembled

    spec, base = _sample_revealjs_spec(tmp_path)
    path = write_assembled(spec, base)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert 'title: "Reveal Smoke"' in text
    assert "marp: true" not in text


def test_build_pandoc_revealjs_command_contains_key_flags(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    pandoc = Path("/fake/pandoc")
    cmd = build_pandoc_revealjs_command(
        pandoc, base / "in.md", base / "out.html", spec, base
    )
    assert cmd[0] == "/fake/pandoc"
    assert "-t" in cmd and "revealjs" in cmd
    assert "--standalone" in cmd
    assert "--slide-level=0" in cmd
    # Theme as variable
    assert "theme=black" in cmd
    # 16:9 ratio → width/height vars
    assert "width=1280" in cmd and "height=720" in cmd
    # Paginate → slideNumber
    assert "slideNumber=true" in cmd


def test_prepare_deck_markdown_writes_assembled_and_processed(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    text, processed = prepare_deck_markdown(spec, base)
    assembled = base / spec.render.output_dir / "assembled.md"
    assert assembled.is_file()
    assert processed.is_file()
    assert processed.name == "deck.processed.md"
    # No citation preresolve for pandoc backend — assembled and processed
    # should match when no figure refs need replacing.
    assert text == processed.read_text(encoding="utf-8")


def test_render_revealjs_shells_out(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    fake = Path("/fake/pandoc")
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    with patch(
        "notio.present.render_revealjs.find_pandoc", return_value=fake
    ), patch(
        "notio.present.render_revealjs.subprocess.run", return_value=completed
    ) as mock_run:
        outputs = render_revealjs(spec, base, formats=["html"])

    assert len(outputs) == 1
    assert outputs[0].name == "reveal-deck.html"
    call_args = mock_run.call_args.args[0]
    assert call_args[0] == "/fake/pandoc"
    assert "revealjs" in call_args


def test_render_revealjs_rejects_wrong_format(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    spec.format = "marp"
    with pytest.raises(RuntimeError, match="render_revealjs called on deck"):
        render_revealjs(spec, base, formats=["html"])


def test_render_revealjs_missing_pandoc(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    with patch("notio.present.render_revealjs.find_pandoc", return_value=None):
        with pytest.raises(RuntimeError, match="pandoc not found"):
            render_revealjs(spec, base, formats=["html"])


def test_render_revealjs_unsupported_format(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    with patch(
        "notio.present.render_revealjs.find_pandoc",
        return_value=Path("/fake/pandoc"),
    ), patch(
        "notio.present.render_revealjs.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
    ):
        with pytest.raises(RuntimeError, match="Unsupported reveal.js output format"):
            render_revealjs(spec, base, formats=["pdf"])


def test_render_revealjs_pandoc_failure(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    failed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="pandoc kaboom"
    )
    with patch(
        "notio.present.render_revealjs.find_pandoc",
        return_value=Path("/fake/pandoc"),
    ), patch(
        "notio.present.render_revealjs.subprocess.run", return_value=failed
    ):
        with pytest.raises(RuntimeError, match="pandoc revealjs failed"):
            render_revealjs(spec, base, formats=["html"])


def test_dispatcher_picks_marp(tmp_path: Path):
    base = tmp_path / "marp-deck"
    base.mkdir()
    spec = scaffold_deck("marp-deck", base, template="lab-meeting")
    # format defaults to marp
    fake_marp = Path("/fake/marp")
    with patch(
        "notio.present.render_marp.find_marp", return_value=fake_marp
    ), patch(
        "notio.present.render_marp.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
    ):
        outputs = render(spec, base, formats=["html"])
    assert outputs and outputs[0].name == "marp-deck.html"


def test_dispatcher_picks_revealjs(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    fake_pandoc = Path("/fake/pandoc")
    with patch(
        "notio.present.render_revealjs.find_pandoc", return_value=fake_pandoc
    ), patch(
        "notio.present.render_revealjs.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
    ):
        outputs = render(spec, base, formats=["html"])
    assert outputs and outputs[0].name == "reveal-deck.html"


def test_dispatcher_unknown_format(tmp_path: Path):
    spec, base = _sample_revealjs_spec(tmp_path)
    spec.format = "bogus"
    with pytest.raises(ValueError, match="Unknown deck format"):
        render(spec, base, formats=["html"])
