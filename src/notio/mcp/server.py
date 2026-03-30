"""FastMCP stdio server — registers all notio tools."""

from fastmcp import FastMCP

from .common import get_notio_root, json_dict

server = FastMCP("notio")


# --- Note query tools ---


@server.tool("note_list")
def note_list_tool(note_type: str = "", series: str = "", limit: int = 20) -> dict:
    """List recent notes, optionally filtered by type and/or series."""
    try:
        from notio.query import list_notes

        root = get_notio_root()
        notes = list_notes(root, note_type=note_type or None, series=series or None, limit=limit)
        return json_dict({"notes": notes, "count": len(notes)})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_latest")
def note_latest_tool(note_type: str = "") -> dict:
    """Content of the most recent note of a given type."""
    try:
        from notio.query import latest_note

        root = get_notio_root()
        note = latest_note(root, note_type=note_type or None)
        return json_dict(note or {"error": "no notes found"})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_read")
def note_read_tool(path: str) -> dict:
    """Read a specific note by its relative path."""
    try:
        from notio.query import read_note

        root = get_notio_root()
        note = read_note(root, path)
        return json_dict(note or {"error": f"note not found: {path}"})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_resolve")
def note_resolve_tool(note_id: str) -> dict:
    """Resolve a note by its timestamp ID, capture ID, or filename fragment."""
    try:
        from notio.query import resolve_note

        root = get_notio_root()
        note = resolve_note(root, note_id)
        return json_dict(note or {"error": f"no note matching '{note_id}'"})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_search")
def note_search_tool(query: str, note_type: str = "", series: str = "", limit: int = 10) -> dict:
    """Search notes by keyword matching against title, tags, series, and content."""
    try:
        from notio.query import search_notes

        root = get_notio_root()
        notes = search_notes(root, query, note_type=note_type or None, series=series or None, limit=limit)
        return json_dict({"notes": notes, "count": len(notes)})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_update")
def note_update_tool(path: str, fields: str) -> dict:
    """Update frontmatter fields of an existing note. Pass fields as a JSON string, e.g. '{"status": "done", "actionable": true}'."""
    try:
        import json
        from notio.query import update_note_frontmatter

        root = get_notio_root()
        parsed_fields = json.loads(fields)
        meta = update_note_frontmatter(root, path, parsed_fields)
        return json_dict({"path": path, "updated_fields": list(parsed_fields.keys()), "frontmatter": meta})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_links")
def note_links_tool(path: str, apply: bool = False) -> dict:
    """Suggest wikilinks from a note to related notes. Set apply=true to append them."""
    try:
        from notio.llm import load_config as load_llm_config, suggest_links
        from notio.query import list_notes, read_note

        root = get_notio_root()
        note = read_note(root, path)
        if note is None:
            return json_dict({"error": f"Note not found: {path}"})

        # Gather sibling notes for context
        siblings = list_notes(root, limit=30)
        # Exclude the note itself
        siblings = [s for s in siblings if s["path"] != path]

        llm_config = load_llm_config(root)
        links = suggest_links(
            root / path,
            note["content"],
            siblings,
            config=llm_config,
        )
        if links is None:
            return json_dict({"error": "LLM unavailable"})

        if apply and links:
            note_path = root / path
            text = note_path.read_text(encoding="utf-8")
            link_section = "\n\n## Related Notes\n\n" + "\n".join(
                f"- [[{link['target']}]] — {link.get('reason', '')}"
                for link in links
            ) + "\n"
            note_path.write_text(text.rstrip() + link_section, encoding="utf-8")

        return json_dict({"links": links, "applied": apply and bool(links)})
    except Exception as exc:
        return json_dict({"error": str(exc)})


# --- Note creation tools ---


@server.tool("note_create")
def note_create_tool(
    note_type: str,
    owner: str = "",
    title: str = "",
    date: str = "",
    series: str = "",
    refs: str = "",
) -> dict:
    """Create a new note of the given type. Pass refs as a JSON array, e.g. '[{"note": "idea-arash-20260211"}]'."""
    try:
        import json as _json
        from notio.config import load_config
        from notio.core import create_note

        root = get_notio_root()
        config = load_config(root)
        extra_fm: dict = {}
        if series:
            extra_fm["series"] = series
        if refs:
            extra_fm["refs"] = _json.loads(refs)
        path = create_note(
            config,
            note_type,
            owner=owner or None,
            title=title or None,
            note_date=date or None,
            extra_frontmatter=extra_fm or None,
        )
        return json_dict({"path": str(path.relative_to(root)), "type": note_type})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("note_types")
def note_types_tool() -> dict:
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
def toc_rebuild_tool(note_type: str = "") -> dict:
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
def diataxis_init_tool(mkdocs: bool = False) -> dict:
    """Scaffold Diataxis documentation structure."""
    try:
        from notio.config import load_config
        from notio.diataxis import diataxis_init

        root = get_notio_root()
        config = load_config(root)
        created, snippet = diataxis_init(config, mkdocs=mkdocs)
        result = {"created": [str(p) for p in created]}
        if snippet:
            result["mkdocs_snippet"] = snippet
        return json_dict(result)
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("diataxis_add")
def diataxis_add_tool(section: str, slug: str, title: str = "") -> dict:
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
def diataxis_toc_tool(section: str = "") -> dict:
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
def config_show_tool() -> dict:
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
