"""Regression: note_create/note_update fields accept a dict, JSON or YAML.

A bare json.loads made YAML frontmatter fail with "Expecting value: line 1
column 1 (char 0)" and no note was written.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastmcp")

from notio.config import load_config
from notio.core import init_workspace
from notio.mcp.common import parse_fields
from notio.mcp.server import note_create_tool, note_update_tool

EXPECTED = {"series": "spindle", "refs": ["a", "b"]}


@pytest.mark.parametrize("value", [
    '{"series": "spindle", "refs": ["a", "b"]}',
    "series: spindle\nrefs: [a, b]",
    {"series": "spindle", "refs": ["a", "b"]},
])
def test_parse_fields_forms(value) -> None:
    assert parse_fields(value, "frontmatter") == EXPECTED


def test_parse_fields_empty_and_dates() -> None:
    assert parse_fields("", "frontmatter") is None
    assert parse_fields("updated: 2026-11-06", "fields") == {"updated": "2026-11-06"}


@pytest.mark.parametrize("value", ["just a sentence", "[a, b]", "key: [unclosed"])
def test_parse_fields_clear_error(value) -> None:
    with pytest.raises(ValueError, match="frontmatter"):
        parse_fields(value, "frontmatter")


def _fn(tool):
    return getattr(tool, "fn", tool)


def test_note_create_and_update_with_yaml(tmp_path, monkeypatch) -> None:
    init_workspace(load_config(tmp_path))
    monkeypatch.setenv("NOTIO_ROOT", str(tmp_path))
    result = _fn(note_create_tool)(note_type="idea", title="yaml fm", frontmatter="series: spindle\ntags: [idea]")
    assert "error" not in result, result
    assert result["id"] in result["path"]
    assert "series: spindle" in (tmp_path / result["path"]).read_text()

    updated = _fn(note_update_tool)(path=result["path"], fields="status: done\nupdated: 2026-11-06")
    assert "error" not in updated, updated
    assert "status: done" in (tmp_path / result["path"]).read_text()

    bad = _fn(note_create_tool)(note_type="idea", title="x", frontmatter="just words")
    assert "frontmatter must be a mapping" in bad["error"]
