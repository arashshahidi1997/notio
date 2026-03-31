"""Pandoc-based manuscript rendering."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from notio.manuscript.assembly import write_assembled
from notio.manuscript.schema import ManuscriptSpec


def find_pandoc() -> Path | None:
    """Locate the pandoc binary via PATH lookup."""
    result = shutil.which("pandoc")
    return Path(result) if result else None


def build_pandoc_command(
    input_path: Path,
    output_path: Path,
    fmt: str,
    spec: ManuscriptSpec,
    base_dir: Path,
) -> list[str]:
    """Build the pandoc CLI argument list."""
    cmd = ["pandoc", str(input_path), "-o", str(output_path)]

    # Bibliography
    bib_file = spec.bibliography.bib_file
    if bib_file:
        bib_path = base_dir / bib_file
        if bib_path.is_file():
            cmd.extend(["--citeproc", f"--bibliography={bib_path}"])
    csl = spec.bibliography.csl
    if csl:
        csl_path = base_dir / csl
        if csl_path.is_file():
            cmd.extend([f"--csl={csl_path}"])

    # Template
    if spec.render.template:
        template_path = base_dir / spec.render.template
        if template_path.is_file():
            cmd.extend([f"--template={template_path}"])

    # Variables
    for k, v in spec.render.variables.items():
        cmd.extend(["-V", f"{k}={v}"])

    # Extra args
    cmd.extend(spec.render.pandoc_args)

    return cmd


def render_single(
    input_path: Path,
    output_path: Path,
    fmt: str,
    *,
    bib_file: Path | None = None,
    csl: Path | None = None,
    template: Path | None = None,
    extra_args: list[str] | None = None,
    variables: dict[str, str] | None = None,
) -> Path:
    """Render a single output format via pandoc.

    Raises :class:`RuntimeError` on pandoc failure.
    """
    pandoc = find_pandoc()
    if pandoc is None:
        raise RuntimeError("pandoc not found — install pandoc to render manuscripts")

    cmd = [str(pandoc), str(input_path), "-o", str(output_path)]
    if bib_file and bib_file.is_file():
        cmd.extend(["--citeproc", f"--bibliography={bib_file}"])
    if csl and csl.is_file():
        cmd.extend([f"--csl={csl}"])
    if template and template.is_file():
        cmd.extend([f"--template={template}"])
    for k, v in (variables or {}).items():
        cmd.extend(["-V", f"{k}={v}"])
    cmd.extend(extra_args or [])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"pandoc failed (exit {result.returncode}):\n{result.stderr}"
        )
    return output_path


def render(
    spec: ManuscriptSpec,
    base_dir: Path,
    *,
    formats: list[str] | None = None,
) -> list[Path]:
    """Assemble sections then render via pandoc.

    Returns list of output file paths.
    """
    assembled_path = write_assembled(spec, base_dir)
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    target_formats = formats or spec.render.formats
    bib_path = (base_dir / spec.bibliography.bib_file) if spec.bibliography.bib_file else None
    csl_path = (base_dir / spec.bibliography.csl) if spec.bibliography.csl else None
    template_path = (base_dir / spec.render.template) if spec.render.template else None

    outputs: list[Path] = []
    for fmt in target_formats:
        output_path = output_dir / f"{spec.name}.{fmt}"
        render_single(
            assembled_path,
            output_path,
            fmt,
            bib_file=bib_path,
            csl=csl_path,
            template=template_path,
            extra_args=spec.render.pandoc_args,
            variables=spec.render.variables,
        )
        outputs.append(output_path)

    return outputs
