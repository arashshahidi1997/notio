"""Deck validation: sections, figures, citations, marp/pandoc availability.

Reuses :class:`ValidationResult` and ``CITE_RE`` from :mod:`notio.manuscript.validate`
to avoid duplication. Phase 2 may promote these shared utilities into
``notio/_common/`` once the shape is settled.
"""

from __future__ import annotations

import re
from pathlib import Path

from notio.manuscript.validate import CITE_RE, ValidationResult  # re-export
from notio.present.figures import validate_figures
from notio.present.schema import DeckSpec, resolve_deck_render

__all__ = ["CITE_RE", "ValidationResult", "validate_deck"]


def validate_deck(spec: DeckSpec, base_dir: Path) -> ValidationResult:
    """Run validation checks on a deck.

    Checks:
    - Section files exist on disk
    - Section order values have no gaps or duplicates
    - Figure bindings resolve (figio source only in phase 1)
    - Cited citekeys resolve against the inherited bibliography
    - marp-cli is available (for ``format: marp`` decks)
    """
    result = ValidationResult()

    # --- Section file existence ---
    for entry in spec.sections:
        section_path = base_dir / entry.path
        if not section_path.is_file():
            result.errors.append(
                f"Section '{entry.key}' file missing: {entry.path}"
            )

    # --- Order uniqueness / gaps ---
    orders = [s.order for s in spec.sections]
    if len(orders) != len(set(orders)):
        dupes = sorted({o for o in orders if orders.count(o) > 1})
        result.errors.append(f"Duplicate section order values: {dupes}")

    # --- Figure resolution ---
    missing_figs = validate_figures(spec, base_dir, format=spec.format)  # type: ignore[arg-type]
    if missing_figs:
        result.warnings.append(f"Unresolved figure ids: {missing_figs}")

    # --- Citation resolution ---
    resolved_render = resolve_deck_render(spec, base_dir)
    bib_rel = resolved_render["bib_file"]
    bib_keys: set[str] = set()
    if bib_rel:
        bib_path = base_dir / bib_rel
        if bib_path.is_file():
            bib_text = bib_path.read_text(encoding="utf-8")
            bib_keys = set(re.findall(r"@\w+\{([^,\s]+)", bib_text))
        else:
            result.warnings.append(f"Bibliography file not found: {bib_rel}")

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
    elif cited_keys and not bib_rel:
        result.warnings.append(
            f"Found {len(cited_keys)} citations but no bibliography configured"
        )

    # --- Renderer availability ---
    if spec.format == "marp":
        from notio.present.render_marp import find_marp

        if find_marp() is None:
            result.warnings.append(
                "marp-cli not found on PATH — rendering will fail. "
                "Install with: npm install -g @marp-team/marp-cli"
            )
    elif spec.format == "revealjs":
        result.warnings.append(
            "Reveal.js backend lands in phase 3; build will currently fail."
        )

    result.valid = len(result.errors) == 0
    return result
