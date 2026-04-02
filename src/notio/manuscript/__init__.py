"""Manuscript assembly and rendering — ordered sections to paper."""

__all__ = [
    "ManuscriptSpec",
    "ValidationResult",
    "assemble",
    "write_assembled",
    "render",
    "resolve_figure_paths",
    "validate_figures",
    "validate_manuscript",
]

from notio.manuscript.schema import ManuscriptSpec
from notio.manuscript.assembly import assemble, write_assembled
from notio.manuscript.render import render
from notio.manuscript.figures import resolve_figure_paths, validate_figures
from notio.manuscript.validate import ValidationResult, validate_manuscript
