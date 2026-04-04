"""Repository root discovery and path resolution.

Provides ``repo_root``, ``repo_abs``, and ``repo_rel`` for converting between
project-root-relative and absolute paths. Root is discovered by walking up
from a start directory looking for ``.git``, ``.projio/``, or ``pyproject.toml``.
"""
from __future__ import annotations

import os
from pathlib import Path


def repo_root(start: Path | str | None = None) -> Path:
    """Find the repository root by walking up from *start*.

    Primary marker is ``.projio/`` (projio workspace). Falls back to
    ``.git`` or ``pyproject.toml`` if no ``.projio/`` is found.
    Returns *start* (or cwd) if no marker is found at all.
    """
    p = Path(start).resolve() if start else Path.cwd().resolve()
    # First pass: look for .projio/ (strongest signal)
    for candidate in [p, *p.parents]:
        if (candidate / ".projio").is_dir():
            return candidate
    # Second pass: fall back to .git or pyproject.toml
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").is_file():
            return candidate
    return p


def repo_abs(relative_path: str, start: Path | str | None = None) -> Path:
    """Convert a path relative to the repo root into an absolute path."""
    return repo_root(start) / relative_path


def repo_rel(absolute_path: Path | str, start: Path | str | None = None) -> str:
    """Convert an absolute path into a path relative to the repo root."""
    return os.path.relpath(Path(absolute_path).resolve(), repo_root(start))
