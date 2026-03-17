from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from notio.config import load_config
from notio.core import FRONTMATTER_RE, parse_frontmatter, _format_frontmatter_value


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


def search_notes(
    root: Path | str,
    query: str,
    *,
    note_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search notes by keyword matching against title, tags, and content.

    Returns notes sorted by relevance (number of query term hits), newest first
    for ties.
    """
    root = Path(root).resolve()
    terms = [t.lower() for t in query.split() if t.strip()]
    if not terms:
        return []

    config = load_config(root)
    types_to_scan = (
        {note_type: config.note_types[note_type]}
        if note_type and note_type in config.note_types
        else config.note_types
    )

    scored: list[tuple[int, float, dict[str, Any]]] = []
    for name, _type_cfg in types_to_scan.items():
        folder = config.notes_root / name
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file() or path.suffix != ".md" or path.name == "index.md":
                continue
            text = path.read_text(encoding="utf-8")
            meta = parse_frontmatter(text)
            # Build searchable text from title, tags, and body
            title = str(meta.get("title", "")).lower()
            tags = " ".join(str(t) for t in meta.get("tags", [])).lower() if isinstance(meta.get("tags"), list) else str(meta.get("tags", "")).lower()
            body = text.lower()
            hits = sum(1 for t in terms if t in title or t in tags or t in body)
            if hits == 0:
                continue
            entry: dict[str, Any] = {
                "path": str(path.relative_to(root)),
                "type": name,
            }
            entry.update(meta)
            scored.append((hits, path.stat().st_mtime, entry))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [e for _, _, e in scored[:limit]]


def update_note_frontmatter(
    root: Path | str,
    path: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Update frontmatter fields of an existing note. Returns updated metadata.

    Merges *fields* into the existing frontmatter. Existing keys are
    overwritten; new keys are appended.
    """
    root = Path(root).resolve()
    note_path = root / path
    if not note_path.is_file():
        raise FileNotFoundError(f"Note not found: {path}")

    text = note_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"Note has no frontmatter: {path}")

    fm_text = match.group(1)
    after_fm = text[match.end():]

    # Parse existing keys to preserve order, update values
    existing_keys: list[str] = []
    existing_lines: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        existing_keys.append(key)
        existing_lines[key] = line

    # Update existing and track new keys
    new_keys: list[str] = []
    for k, v in fields.items():
        formatted = f"{k}: {_format_frontmatter_value(v)}"
        if k in existing_lines:
            existing_lines[k] = formatted
        else:
            new_keys.append(k)
            existing_lines[k] = formatted

    # Rebuild frontmatter preserving order, appending new keys
    fm_lines = [existing_lines[k] for k in existing_keys if k in existing_lines]
    fm_lines.extend(existing_lines[k] for k in new_keys)

    result = f"---\n" + "\n".join(fm_lines) + "\n---\n" + after_fm
    note_path.write_text(result, encoding="utf-8")

    return parse_frontmatter(result)
