__all__ = [
    "__version__",
    "list_notes",
    "latest_note",
    "read_note",
    "resolve_note",
    "search_notes",
    "update_note_frontmatter",
]

__version__ = "0.2.0"  # single source: pyproject.toml reads it

from notio.query import (
    latest_note,
    list_notes,
    read_note,
    resolve_note,
    search_notes,
    update_note_frontmatter,
)
