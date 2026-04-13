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

import shutil
import subprocess
from pathlib import Path


def find_pandoc() -> Path | None:
    """Locate the pandoc binary via PATH lookup."""
    result = shutil.which("pandoc")
    return Path(result) if result else None


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
