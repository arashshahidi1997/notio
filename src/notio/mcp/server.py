"""FastMCP stdio server — registers all notio tools."""
from __future__ import annotations

from fastmcp import FastMCP

from .common import JsonDict, get_notio_root, json_dict

server = FastMCP("notio")


# --- Note query tools ---


@server.tool("note_list")
def note_list_tool(note_type: str = "", limit: int = 20) -> JsonDict:
    """List recent notes, optionally filtered by type."""
    try:
        from notio.query import list_notes

        root = get_notio_root()
        notes = list_notes(root, note_type=note_type or None, limit=limit)
        return json_dict({"notes": notes, "count": len(notes)})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_latest")
def note_latest_tool(note_type: str = "") -> JsonDict:
    """Content of the most recent note of a given type."""
    try:
        from notio.query import latest_note

        root = get_notio_root()
        note = latest_note(root, note_type=note_type or None)
        return json_dict(note or {"error": "no notes found"})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_read")
def note_read_tool(path: str) -> JsonDict:
    """Read a specific note by its relative path."""
    try:
        from notio.query import read_note

        root = get_notio_root()
        note = read_note(root, path)
        return json_dict(note or {"error": f"note not found: {path}"})
    except Exception as exc:
        return json_dict({"error": str(exc)})


# --- Note creation tools ---


@server.tool("note_create")
def note_create_tool(
    note_type: str,
    owner: str = "",
    title: str = "",
    date: str = "",
) -> JsonDict:
    """Create a new note of the given type."""
    try:
        from notio.config import load_config
        from notio.core import create_note

        root = get_notio_root()
        config = load_config(root)
        path = create_note(
            config,
            note_type,
            owner=owner or None,
            title=title or None,
            note_date=date or None,
        )
        return json_dict({"path": str(path.relative_to(root)), "type": note_type})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_types")
def note_types_tool() -> JsonDict:
    """List all configured note types."""
    try:
        from notio.config import load_config

        root = get_notio_root()
        config = load_config(root)
        types = {
            name: {
                "mode": t.mode,
                "template": t.template,
                "filename": t.filename,
                "toc_keys": list(t.toc_keys),
            }
            for name, t in config.note_types.items()
        }
        return json_dict({"types": types})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("toc_rebuild")
def toc_rebuild_tool(note_type: str = "") -> JsonDict:
    """Regenerate note indexes."""
    try:
        from notio.config import load_config
        from notio.core import build_root_index, build_type_index

        root = get_notio_root()
        config = load_config(root)
        paths = []
        if note_type and note_type in config.note_types:
            paths.append(str(build_type_index(config, note_type)))
        else:
            for name in config.note_types:
                paths.append(str(build_type_index(config, name)))
        paths.append(str(build_root_index(config)))
        return json_dict({"rebuilt": paths})
    except Exception as exc:
        return json_dict({"error": str(exc)})


# --- Diataxis tools ---


@server.tool("diataxis_init")
def diataxis_init_tool(mkdocs: bool = False) -> JsonDict:
    """Scaffold Diataxis documentation structure."""
    try:
        from notio.config import load_config
        from notio.diataxis import diataxis_init

        root = get_notio_root()
        config = load_config(root)
        created, snippet = diataxis_init(config, mkdocs=mkdocs)
        result: dict = {"created": [str(p) for p in created]}
        if snippet:
            result["mkdocs_snippet"] = snippet
        return json_dict(result)
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("diataxis_add")
def diataxis_add_tool(section: str, slug: str, title: str = "") -> JsonDict:
    """Add a page to a Diataxis section."""
    try:
        from notio.config import load_config
        from notio.diataxis import diataxis_add

        root = get_notio_root()
        config = load_config(root)
        path = diataxis_add(config, section, slug, title=title or None)
        return json_dict({"path": str(path.relative_to(root)), "section": section})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("diataxis_toc")
def diataxis_toc_tool(section: str = "") -> JsonDict:
    """Regenerate Diataxis section indexes."""
    try:
        from notio.config import load_config
        from notio.diataxis import diataxis_toc

        root = get_notio_root()
        config = load_config(root)
        paths = diataxis_toc(config, section or None)
        return json_dict({"rebuilt": [str(p) for p in paths]})
    except Exception as exc:
        return json_dict({"error": str(exc)})


# --- Config tools ---


@server.tool("config_show")
def config_show_tool() -> JsonDict:
    """Show the current notio configuration."""
    try:
        from notio.config import load_config

        root = get_notio_root()
        config = load_config(root)
        return json_dict({
            "root": str(config.root),
            "notes_root": str(config.notes_root),
            "template_root": str(config.template_root),
            "note_types": {
                name: {
                    "mode": t.mode,
                    "template": t.template,
                    "filename": t.filename,
                    "toc_keys": list(t.toc_keys),
                    "toc_groupby": t.toc_groupby,
                }
                for name, t in config.note_types.items()
            },
            "diataxis": {
                "docs_root": config.diataxis.docs_root,
                "sections": list(config.diataxis.sections),
            },
        })
    except Exception as exc:
        return json_dict({"error": str(exc)})


def main() -> None:
    """Run the MCP server over stdio."""
    server.run()


if __name__ == "__main__":
    main()
