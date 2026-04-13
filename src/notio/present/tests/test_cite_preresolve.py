"""Citation preresolve tests.

Only runs the pandoc path if pandoc is available on PATH; otherwise
exercises the no-bib fast path and the missing-pandoc error branch.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from notio.present.cite_preresolve import find_pandoc, preresolve_citations


def test_preresolve_no_bib_returns_unchanged():
    text = "Body with @smith2024 in it."
    result = preresolve_citations(text, bib_file=None)
    assert result == text


@pytest.mark.skipif(find_pandoc() is None, reason="pandoc not installed")
def test_preresolve_resolves_citation(tmp_path: Path):
    bib = tmp_path / "refs.bib"
    bib.write_text(
        "@article{smith2024, author = {Smith, Alice}, title = {A Paper}, "
        "year = {2024}, journal = {Nature}}\n",
        encoding="utf-8",
    )
    text = "Body with @smith2024 in it.\n"
    result = preresolve_citations(text, bib_file=bib, work_dir=tmp_path)
    # Pandoc renders the inline citation — the raw @key should be gone,
    # and the formatted name should appear.
    assert "@smith2024" not in result
    assert "Smith" in result


def test_preresolve_raises_when_pandoc_missing(monkeypatch, tmp_path: Path):
    """Force the missing-pandoc branch."""
    import notio.present.cite_preresolve as mod

    monkeypatch.setattr(mod, "find_pandoc", lambda: None)
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{x, author={A}, title={T}, year={2024}}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="pandoc not found"):
        preresolve_citations("body @x", bib_file=bib)
