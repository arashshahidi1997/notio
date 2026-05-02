"""Citation pre-resolution for Marp decks.

Marp has no citeproc. Phase 1 pre-resolves ``@citekey`` syntax to
formatted inline text by shelling out to pandoc with ``--citeproc``
and writing markdown output, then handing the transformed markdown
to marp-cli.

This is a **render-stage** transform, not an assembly-stage one.
``assembled.md`` keeps raw ``@key`` literals so phase 3 reveal.js can
hand the same assembled.md to pandoc with native citeproc support.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_pandoc() -> Path | None:
    """Locate the pandoc binary.

    Tries (in order):
    1. ``shutil.which("pandoc")`` — standard PATH lookup
    2. ``~/.pixi/bin/pandoc`` — pixi-global install (when exposed via the
       quarto env or a dedicated pandoc env)
    3. ``~/.local/bin/pandoc`` — user-level install or symlink

    The fallbacks make pandoc resolvable in non-interactive contexts (MCP
    servers, hooks, CI) where the parent shell may not have sourced the
    user's rc files. Returns ``None`` only when pandoc is genuinely
    unavailable.
    """
    result = shutil.which("pandoc")
    if result:
        return Path(result)

    home = Path.home()
    for candidate in (home / ".pixi" / "bin" / "pandoc", home / ".local" / "bin" / "pandoc"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    return None


def preresolve_citations(
    text: str,
    *,
    bib_file: Path | None = None,
    csl: Path | None = None,
    work_dir: Path | None = None,
) -> str:
    """Resolve ``@citekey`` markers in *text* via pandoc citeproc.

    Pipes *text* through ``pandoc -f markdown -t markdown --citeproc``
    with the given bibliography and CSL style. Returns the transformed
    markdown (citations rendered inline, references block appended).

    If pandoc is unavailable, raises :class:`RuntimeError`. If no
    bibliography is configured, returns *text* unchanged (citekeys
    remain as literals, which marp-cli will render verbatim).
    """
    if not bib_file:
        return text

    pandoc = find_pandoc()
    if pandoc is None:
        raise RuntimeError(
            "pandoc not found — install pandoc to resolve citations before "
            "Marp rendering, or configure the deck to avoid citation keys."
        )

    cmd: list[str] = [
        str(pandoc),
        "-f",
        "markdown",
        "-t",
        "markdown",
        "--citeproc",
        f"--bibliography={bib_file}",
        # Wrap preserve to avoid hard-wrapping Marp content.
        "--wrap=preserve",
    ]
    if csl and csl.is_file():
        cmd.append(f"--csl={csl}")

    result = subprocess.run(
        cmd,
        input=text,
        capture_output=True,
        text=True,
        cwd=str(work_dir) if work_dir else None,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pandoc citeproc failed (exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout
