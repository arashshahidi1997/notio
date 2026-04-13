"""Marp-CLI rendering pipeline for presentio decks.

Pipeline:
1. Assemble sections via :func:`notio.present.assembly.assemble_marp`.
2. Resolve figure references via :mod:`notio.present.figures`.
3. Pre-resolve citations via :mod:`notio.present.cite_preresolve` (pandoc
   citeproc; only runs when the deck inherits a bibliography).
4. Write the transformed markdown to ``build/deck.processed.md``.
5. Shell out to ``marp-cli`` to render to html/pdf/pptx.

Format dispatch for reveal.js lives in a future ``render_revealjs.py``
(phase 3). This file stays Marp-only to keep the Marp path free of
pandoc dependencies.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from notio.present.assembly import assemble_marp
from notio.present.cite_preresolve import preresolve_citations
from notio.present.figures import insert_figure_references, resolve_figure_paths
from notio.present.schema import DeckSpec, resolve_deck_render


MARP_EXT = {
    "html": ".html",
    "pdf": ".pdf",
    "pptx": ".pptx",
}


def find_marp() -> Path | None:
    """Locate the marp-cli binary."""
    result = shutil.which("marp")
    return Path(result) if result else None


def build_marp_command(
    marp: Path,
    input_path: Path,
    output_path: Path,
    spec: DeckSpec,
    *,
    allow_local_files: bool = True,
) -> list[str]:
    """Construct the marp-cli command line."""
    cmd: list[str] = [str(marp), str(input_path), "-o", str(output_path)]
    if spec.render.theme:
        cmd.extend(["--theme", spec.render.theme])
    if allow_local_files:
        cmd.append("--allow-local-files")
    if spec.render.marp_args:
        cmd.extend(spec.render.marp_args)
    return cmd


def prepare_deck_markdown(spec: DeckSpec, base_dir: Path) -> tuple[str, Path]:
    """Run the full assembly → figure resolution → citation preresolve pipe.

    Writes ``build/assembled.md`` (raw, with citekeys intact) and
    ``build/deck.processed.md`` (ready for marp-cli). Returns the
    processed markdown text and the processed path.
    """
    text = assemble_marp(spec, base_dir)

    # Figure resolution — insert real paths in place of fig:<id> placeholders.
    figures = resolve_figure_paths(spec, base_dir, format="marp")
    if figures:
        text = insert_figure_references(text, figures, base_dir)

    # Write the raw assembled output (unresolved citations) for inspection
    # and for phase 3 reveal.js to reuse the same source.
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    assembled_path = output_dir / "assembled.md"
    assembled_path.write_text(text, encoding="utf-8")

    # Citation preresolve — only if a bibliography is configured.
    resolved_render = resolve_deck_render(spec, base_dir)
    bib_rel = resolved_render["bib_file"]
    csl_rel = resolved_render["csl"]
    bib_path = (base_dir / bib_rel).resolve() if bib_rel else None
    csl_path = (base_dir / csl_rel).resolve() if csl_rel else None

    if bib_path and bib_path.is_file():
        text = preresolve_citations(
            text,
            bib_file=bib_path,
            csl=csl_path if (csl_path and csl_path.is_file()) else None,
            work_dir=base_dir,
        )

    processed_path = output_dir / "deck.processed.md"
    processed_path.write_text(text, encoding="utf-8")
    return text, processed_path


def render_marp(
    spec: DeckSpec,
    base_dir: Path,
    *,
    formats: list[str] | None = None,
) -> list[Path]:
    """Assemble, preresolve, and shell out to marp-cli.

    Returns the list of output files written. Raises
    :class:`RuntimeError` if marp-cli is missing or fails, or if the
    deck format is not ``marp``.
    """
    if spec.format != "marp":
        raise RuntimeError(
            f"render_marp called on deck with format={spec.format!r}; "
            f"use the corresponding renderer (reveal.js arrives in phase 3)."
        )

    marp = find_marp()
    if marp is None:
        raise RuntimeError(
            "marp-cli not found on PATH. "
            "Install with: npm install -g @marp-team/marp-cli"
        )

    _, processed_path = prepare_deck_markdown(spec, base_dir)

    target_formats = formats or [o.format for o in spec.outputs] or ["html"]
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for fmt in target_formats:
        ext = MARP_EXT.get(fmt)
        if ext is None:
            raise RuntimeError(
                f"Unsupported Marp output format: {fmt!r}. "
                f"Choose from: {sorted(MARP_EXT)}"
            )
        output_path = output_dir / f"{spec.name}{ext}"
        cmd = build_marp_command(marp, processed_path, output_path, spec)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"marp-cli failed ({fmt}, exit {result.returncode}):\n{result.stderr}"
            )
        outputs.append(output_path)

    return outputs
