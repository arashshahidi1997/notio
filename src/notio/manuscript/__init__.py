"""Manuscript assembly and rendering — ordered sections to paper."""

__all__ = [
    "ManuscriptSpec",
    "ResolvedRender",
    "ValidationResult",
    "assemble",
    "resolve_render_config",
    "write_assembled",
    "render",
    "resolve_figure_paths",
    "validate_figures",
    "validate_manuscript",
]

from notio.manuscript.schema import ManuscriptSpec, ResolvedRender, resolve_render_config
from notio.manuscript.assembly import assemble, write_assembled
from notio.manuscript.render import render
from notio.manuscript.figures import resolve_figure_paths, validate_figures
from notio.manuscript.validate import ValidationResult, validate_manuscript
