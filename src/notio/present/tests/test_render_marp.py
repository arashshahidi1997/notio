"""render_marp tests — marp-cli is mocked; pandoc preresolve is skipped
when no bib is configured.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from notio.present.render_marp import (
    build_marp_command,
    prepare_deck_markdown,
    render_marp,
)
from notio.present.schema import DeckSpec, scaffold_deck


def _sample_spec(tmp_path: Path) -> tuple[DeckSpec, Path]:
    base = tmp_path / "smoketest"
    base.mkdir()
    spec = scaffold_deck("smoketest", base, template="lab-meeting")
    # Ensure section files have visible bodies so assembly output is checkable.
    for section in spec.sections:
        (base / section.path).write_text(
            f"---\ntitle: {section.key}\norder: {section.order}\n---\n\n"
            f"# {section.key.title()}\n\nText in {section.key}.\n",
            encoding="utf-8",
        )
    return spec, base


def test_build_marp_command_includes_theme(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)
    spec.render.theme = "gaia"
    spec.render.marp_args = ["--html"]

    marp = Path("/fake/marp")
    cmd = build_marp_command(marp, base / "assembled.md", base / "out.html", spec)
    assert cmd[0] == "/fake/marp"
    assert "--theme" in cmd
    assert "gaia" in cmd
    assert "--allow-local-files" in cmd
    assert "--html" in cmd


def test_prepare_deck_markdown_writes_assembled_and_processed(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)
    text, processed_path = prepare_deck_markdown(spec, base)

    assembled_path = base / spec.render.output_dir / "assembled.md"
    assert assembled_path.is_file()
    assert processed_path.is_file()
    assert processed_path.name == "deck.processed.md"
    assert "marp: true" in text
    # No bibliography configured → processed == assembled
    assert processed_path.read_text(encoding="utf-8") == text


def test_render_marp_shells_out_and_returns_output(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)

    fake_marp = Path("/fake/marp")
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )

    with patch(
        "notio.present.render_marp.find_marp", return_value=fake_marp
    ), patch(
        "notio.present.render_marp.subprocess.run", return_value=completed
    ) as mock_run:
        outputs = render_marp(spec, base, formats=["html"])

    assert len(outputs) == 1
    assert outputs[0].name == "smoketest.html"
    # marp-cli got called with processed.md as input
    call_args = mock_run.call_args.args[0]
    assert call_args[0] == "/fake/marp"
    assert call_args[1].endswith("deck.processed.md")


def test_render_marp_unknown_format(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)
    with patch(
        "notio.present.render_marp.find_marp", return_value=Path("/fake/marp")
    ), patch(
        "notio.present.render_marp.subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    ):
        with pytest.raises(RuntimeError, match="Unsupported Marp output format"):
            render_marp(spec, base, formats=["gif"])


def test_render_marp_missing_binary(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)
    with patch("notio.present.render_marp.find_marp", return_value=None):
        with pytest.raises(RuntimeError, match="marp-cli not found"):
            render_marp(spec, base, formats=["html"])


def test_render_marp_wrong_format(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)
    spec.format = "revealjs"
    with pytest.raises(RuntimeError, match="render_marp called on deck with format"):
        render_marp(spec, base, formats=["html"])


def test_render_marp_failure_raises(tmp_path: Path):
    spec, base = _sample_spec(tmp_path)
    failed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="boom"
    )
    with patch(
        "notio.present.render_marp.find_marp", return_value=Path("/fake/marp")
    ), patch(
        "notio.present.render_marp.subprocess.run", return_value=failed
    ):
        with pytest.raises(RuntimeError, match="marp-cli failed"):
            render_marp(spec, base, formats=["html"])
