from __future__ import annotations

from pathlib import Path
from typing import Any

from notio.config import load_config
from notio.core import parse_frontmatter


def list_notes(
    root: Path | str,
    *,
    note_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent notes, optionally filtered by type.

    Returns a list of dicts with keys: path, type, and frontmatter fields.
    Sorted by modification time, newest first.
    """
    root = Path(root).resolve()
    config = load_config(root)

    types_to_scan = (
        {note_type: config.note_types[note_type]}
        if note_type and note_type in config.note_types
        else config.note_types
    )

    entries: list[tuple[float, dict[str, Any]]] = []
    for name, _type_cfg in types_to_scan.items():
        folder = config.notes_root / name
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file() or path.suffix != ".md" or path.name == "index.md":
                continue
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            entry: dict[str, Any] = {
                "path": str(path.relative_to(root)),
                "type": name,
            }
            entry.update(meta)
            entries.append((path.stat().st_mtime, entry))

    entries.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in entries[:limit]]


def latest_note(
    root: Path | str,
    *,
    note_type: str | None = None,
) -> dict[str, Any] | None:
    """Return the most recent note with its full content included."""
    notes = list_notes(root, note_type=note_type, limit=1)
    if not notes:
        return None
    entry = notes[0]
    root = Path(root).resolve()
    note_path = root / entry["path"]
    entry["content"] = note_path.read_text(encoding="utf-8")
    return entry


def read_note(
    root: Path | str,
    path: str,
) -> dict[str, Any] | None:
    """Read a specific note by its relative path."""
    root = Path(root).resolve()
    note_path = root / path
    if not note_path.is_file():
        return None
    text = note_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    result: dict[str, Any] = {
        "path": path,
        "content": text,
    }
    result.update(meta)
    return result
