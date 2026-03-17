__all__ = [
    "__version__",
    "list_notes",
    "latest_note",
    "read_note",
    "search_notes",
    "update_note_frontmatter",
]

__version__ = "0.1.0"

from notio.query import (
    latest_note,
    list_notes,
    read_note,
    search_notes,
    update_note_frontmatter,
)
