"""Manuscript validation: sections, citations, figures, pandoc."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from notio.manuscript.schema import ManuscriptSpec, resolve_render_config


@dataclass
class ValidationResult:
    """Result of manuscript validation checks."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Matches [@citekey] or [@citekey1; @citekey2] pandoc citation syntax
CITE_RE = re.compile(r"@([a-zA-Z0-9_:.\-]+)")


def validate_manuscript(spec: ManuscriptSpec, base_dir: Path) -> ValidationResult:
    """Run all validation checks on a manuscript.

    Checks:
    - Section files exist on disk
    - Section order values have no gaps or duplicates
    - Citations in section text resolve against the bib file
    - Figure bindings have corresponding built outputs
    - Pandoc is available in PATH
    """
    result = ValidationResult()

    # --- Section file existence ---
    for entry in spec.sections:
        section_path = base_dir / entry.path
        if not section_path.is_file():
            result.errors.append(f"Section '{entry.key}' file missing: {entry.path}")

    # --- Order uniqueness and gaps ---
    orders = [s.order for s in spec.sections]
    if len(orders) != len(set(orders)):
        dupes = [o for o in orders if orders.count(o) > 1]
        result.errors.append(f"Duplicate section order values: {sorted(set(dupes))}")

    if orders:
        expected = list(range(min(orders), max(orders) + 1))
        gaps = sorted(set(expected) - set(orders))
        if gaps:
            result.warnings.append(f"Gaps in section order: {gaps}")

    # --- Citation resolution (uses resolved config for project defaults) ---
    resolved = resolve_render_config(spec, base_dir)
    bib_file = resolved.bib_file
    bib_keys: set[str] = set()
    if bib_file:
        bib_path = base_dir / bib_file
        if bib_path.is_file():
            bib_text = bib_path.read_text(encoding="utf-8")
            bib_keys = set(re.findall(r"@\w+\{([^,\s]+)", bib_text))
        else:
            result.warnings.append(f"Bibliography file not found: {bib_file}")

    cited_keys: set[str] = set()
    for entry in spec.sections:
        section_path = base_dir / entry.path
        if section_path.is_file():
            text = section_path.read_text(encoding="utf-8")
            cited_keys.update(CITE_RE.findall(text))

    if cited_keys and bib_keys:
        missing_cites = sorted(cited_keys - bib_keys)
        if missing_cites:
            result.warnings.append(f"Unresolved citations: {missing_cites}")
    elif cited_keys and not bib_keys and not bib_file:
        result.warnings.append(
            f"Found {len(cited_keys)} citations but no bibliography configured"
        )

    # --- Figure validation ---
    from notio.manuscript.figures import validate_figures

    missing_figs = validate_figures(spec, base_dir)
    if missing_figs:
        result.warnings.append(f"Missing figure outputs: {missing_figs}")

    # --- Pandoc availability ---
    from notio.manuscript.render import find_pandoc

    if find_pandoc() is None:
        result.warnings.append("pandoc not found in PATH — rendering will fail")

    # Set valid based on errors (warnings don't invalidate)
    result.valid = len(result.errors) == 0

    return result
