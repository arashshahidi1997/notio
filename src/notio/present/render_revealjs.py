"""Reveal.js rendering pipeline for presentio decks (phase 3).

Shells out to pandoc with ``-t revealjs --slide-level=0``. The
``slide-level=0`` choice is deliberate: at slide-level 0, pandoc uses
horizontal rules (``---``) as slide separators — exactly the same
convention Marp uses. That means section source files can be reused
**unchanged** between the Marp and reveal.js backends; only the
frontmatter differs, and ``assemble_pandoc`` handles that.

Pandoc citeproc resolves ``@citekey`` markers natively — no preresolve
pass is needed for this backend. Bibliography and CSL are inherited
from ``.projio/render.yml`` via ``resolve_deck_render``.

Figure references are resolved before handing to pandoc, same as the
Marp path.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from notio.manuscript.render import find_pandoc
from notio.present.assembly import write_assembled_pandoc
from notio.present.figures import insert_figure_references, resolve_figure_paths
from notio.present.schema import DeckSpec, resolve_deck_render


REVEALJS_EXT = {
    "html": ".html",
}


def build_pandoc_revealjs_command(
    pandoc: Path,
    input_path: Path,
    output_path: Path,
    spec: DeckSpec,
    base_dir: Path,
) -> list[str]:
    """Construct the pandoc reveal.js command line.

    Pulls bibliography/CSL from the inherited render config and passes
    ``--slide-level=0`` so horizontal rules act as slide separators.
    """
    resolved = resolve_deck_render(spec, base_dir)

    cmd: list[str] = [
        str(pandoc),
        str(input_path),
        "-o",
        str(output_path),
        "-t",
        "revealjs",
        "--standalone",
        "--slide-level=0",
    ]

    # Bibliography + CSL via pandoc citeproc
    bib_rel = resolved["bib_file"]
    if bib_rel:
        bib_path = (base_dir / bib_rel).resolve()
        if bib_path.is_file():
            cmd.extend(["--citeproc", f"--bibliography={bib_path}"])
    csl_rel = resolved["csl"]
    if csl_rel:
        csl_path = (base_dir / csl_rel).resolve()
        if csl_path.is_file():
            cmd.append(f"--csl={csl_path}")

    # Reveal.js theme (pandoc variable)
    theme = spec.render.theme or "white"
    cmd.extend(["-V", f"theme={theme}"])

    # 16:9 ratio → common reveal.js dimensions
    if spec.render.ratio == "16:9":
        cmd.extend(["-V", "width=1280", "-V", "height=720"])
    elif spec.render.ratio == "4:3":
        cmd.extend(["-V", "width=960", "-V", "height=700"])

    # Pagination / slide numbering
    if spec.render.paginate:
        cmd.extend(["-V", "slideNumber=true"])

    # Chalkboard / speaker-notes plugins would be added here; phase 5.

    # Extra args passed through
    if spec.render.revealjs_args:
        cmd.extend(spec.render.revealjs_args)

    return cmd


def prepare_deck_markdown(spec: DeckSpec, base_dir: Path) -> tuple[str, Path]:
    """Assemble, resolve figures, and write to ``build/deck.processed.md``.

    No citation preresolve step — pandoc handles ``@key`` natively.
    """
    assembled_path = write_assembled_pandoc(spec, base_dir)
    text = assembled_path.read_text(encoding="utf-8")

    figures = resolve_figure_paths(spec, base_dir, format="revealjs")
    if figures:
        text = insert_figure_references(text, figures, base_dir)

    output_dir = base_dir / spec.render.output_dir
    processed_path = output_dir / "deck.processed.md"
    processed_path.write_text(text, encoding="utf-8")
    return text, processed_path


def render_revealjs(
    spec: DeckSpec,
    base_dir: Path,
    *,
    formats: list[str] | None = None,
) -> list[Path]:
    """Assemble and render a deck via pandoc ``-t revealjs``.

    Returns the list of output files. Raises :class:`RuntimeError` if
    pandoc is missing, if the format isn't ``revealjs``, or if pandoc
    itself fails.
    """
    if spec.format != "revealjs":
        raise RuntimeError(
            f"render_revealjs called on deck with format={spec.format!r}; "
            f"use render_marp for Marp decks."
        )

    pandoc = find_pandoc()
    if pandoc is None:
        raise RuntimeError(
            "pandoc not found on PATH. "
            "Install pandoc >= 2.19 to render reveal.js decks."
        )

    _, processed_path = prepare_deck_markdown(spec, base_dir)

    target_formats = formats or [o.format for o in spec.outputs] or ["html"]
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for fmt in target_formats:
        ext = REVEALJS_EXT.get(fmt)
        if ext is None:
            raise RuntimeError(
                f"Unsupported reveal.js output format: {fmt!r}. "
                f"Only 'html' is supported by the pandoc reveal.js backend."
            )
        output_path = output_dir / f"{spec.name}{ext}"
        cmd = build_pandoc_revealjs_command(
            pandoc, processed_path, output_path, spec, base_dir
        )
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"pandoc revealjs failed ({fmt}, exit {result.returncode}):\n"
                f"{result.stderr}"
            )
        outputs.append(output_path)

    return outputs
