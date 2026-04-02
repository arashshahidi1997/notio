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


# --- Manuscript tools ---


@server.tool("manuscript_init")
def manuscript_init_tool(name: str, template: str = "generic") -> dict:
    """Scaffold a new manuscript with default sections."""
    try:
        from notio.manuscript.schema import scaffold_spec

        root = get_notio_root()
        base_dir = root / "docs" / "manuscript" / name
        base_dir.mkdir(parents=True, exist_ok=True)
        spec = scaffold_spec(name, base_dir)
        return json_dict({
            "name": spec.name,
            "title": spec.title,
            "path": str(base_dir.relative_to(root)),
            "sections": [s.key for s in spec.sections],
            "spec_file": str((base_dir / "manuscript.yml").relative_to(root)),
        })
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("manuscript_list")
def manuscript_list_tool() -> dict:
    """List all manuscripts in the project."""
    try:
        root = get_notio_root()
        manuscript_dir = root / "docs" / "manuscript"
        if not manuscript_dir.is_dir():
            return json_dict({"manuscripts": [], "count": 0})

        manuscripts = []
        for child in sorted(manuscript_dir.iterdir()):
            spec_path = child / "manuscript.yml"
            if child.is_dir() and spec_path.is_file():
                from notio.manuscript.schema import ManuscriptSpec
                spec = ManuscriptSpec.from_yaml(spec_path)
                manuscripts.append({
                    "name": spec.name,
                    "title": spec.title,
                    "path": str(child.relative_to(root)),
                    "sections": len(spec.sections),
                    "formats": spec.render.formats,
                })
        return json_dict({"manuscripts": manuscripts, "count": len(manuscripts)})
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("manuscript_status")
def manuscript_status_tool(name: str) -> dict:
    """Show manuscript sections, figures, and completion status."""
    try:
        root = get_notio_root()
        base_dir = root / "docs" / "manuscript" / name
        spec_path = base_dir / "manuscript.yml"
        if not spec_path.is_file():
            return json_dict({"error": f"Manuscript '{name}' not found"})

        from notio.manuscript.schema import ManuscriptSpec
        from notio.manuscript.assembly import strip_frontmatter
        from notio.manuscript.figures import resolve_figure_paths, validate_figures

        spec = ManuscriptSpec.from_yaml(spec_path)

        sections_status = []
        for entry in sorted(spec.sections, key=lambda s: s.order):
            section_path = base_dir / entry.path
            exists = section_path.is_file()
            word_count = 0
            if exists:
                text = section_path.read_text(encoding="utf-8")
                body = strip_frontmatter(text)
                word_count = len(body.split())
            sections_status.append({
                "key": entry.key,
                "path": entry.path,
                "order": entry.order,
                "exists": exists,
                "word_count": word_count,
            })

        missing_figs = validate_figures(spec, base_dir)
        resolved_figs = resolve_figure_paths(spec, base_dir)

        return json_dict({
            "name": spec.name,
            "title": spec.title,
            "sections": sections_status,
            "total_words": sum(s["word_count"] for s in sections_status),
            "figures": {
                "total": len(spec.figures.mappings),
                "resolved": len(resolved_figs),
                "missing": missing_figs,
            },
            "render_formats": spec.render.formats,
        })
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("manuscript_build")
def manuscript_build_tool(name: str, format: str = "pdf") -> dict:
    """Assemble sections and render to PDF/LaTeX/Markdown."""
    try:
        root = get_notio_root()
        base_dir = root / "docs" / "manuscript" / name
        spec_path = base_dir / "manuscript.yml"
        if not spec_path.is_file():
            return json_dict({"error": f"Manuscript '{name}' not found"})

        from notio.manuscript.schema import ManuscriptSpec
        from notio.manuscript.render import render

        spec = ManuscriptSpec.from_yaml(spec_path)
        outputs = render(spec, base_dir, formats=[format])
        return json_dict({
            "name": spec.name,
            "format": format,
            "outputs": [str(p.relative_to(root)) for p in outputs],
        })
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("manuscript_validate")
def manuscript_validate_tool(name: str) -> dict:
    """Validate citations, figures, sections, and pandoc availability."""
    try:
        root = get_notio_root()
        base_dir = root / "docs" / "manuscript" / name
        spec_path = base_dir / "manuscript.yml"
        if not spec_path.is_file():
            return json_dict({"error": f"Manuscript '{name}' not found"})

        from notio.manuscript.schema import ManuscriptSpec
        from notio.manuscript.validate import validate_manuscript

        spec = ManuscriptSpec.from_yaml(spec_path)
        result = validate_manuscript(spec, base_dir)
        return json_dict({
            "name": spec.name,
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
        })
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("manuscript_assemble")
def manuscript_assemble_tool(name: str) -> dict:
    """Generate assembled markdown without rendering."""
    try:
        root = get_notio_root()
        base_dir = root / "docs" / "manuscript" / name
        spec_path = base_dir / "manuscript.yml"
        if not spec_path.is_file():
            return json_dict({"error": f"Manuscript '{name}' not found"})

        from notio.manuscript.schema import ManuscriptSpec
        from notio.manuscript.assembly import write_assembled

        spec = ManuscriptSpec.from_yaml(spec_path)
        output_path = write_assembled(spec, base_dir)
        return json_dict({
            "name": spec.name,
            "output": str(output_path.relative_to(root)),
        })
    except Exception as exc:
        return json_dict({"error": str(exc)})


@server.tool("manuscript_figure_insert")
def manuscript_figure_insert_tool(name: str, section: str, figure_id: str, position: str = "end") -> dict:
    """Insert a figio figure reference into a manuscript section."""
    try:
        root = get_notio_root()
        base_dir = root / "docs" / "manuscript" / name
        spec_path = base_dir / "manuscript.yml"
        if not spec_path.is_file():
            return json_dict({"error": f"Manuscript '{name}' not found"})

        from notio.manuscript.schema import ManuscriptSpec
        spec = ManuscriptSpec.from_yaml(spec_path)

        target = None
        for entry in spec.sections:
            if entry.key == section:
                target = entry
                break
        if target is None:
            return json_dict({"error": f"Section '{section}' not found in manuscript '{name}'"})

        section_path = base_dir / target.path
        if not section_path.is_file():
            return json_dict({"error": f"Section file not found: {target.path}"})

        fig_ref = f"\n![](fig:{figure_id})\n"
        text = section_path.read_text(encoding="utf-8")

        if position == "start":
            from notio.manuscript.assembly import FRONTMATTER_RE
            match = FRONTMATTER_RE.match(text)
            if match:
                insert_pos = match.end()
                text = text[:insert_pos] + fig_ref + text[insert_pos:]
            else:
                text = fig_ref + text
        else:
            text = text.rstrip() + "\n" + fig_ref

        section_path.write_text(text, encoding="utf-8")
        return json_dict({
            "name": name,
            "section": section,
            "figure_id": figure_id,
            "position": position,
            "path": str(section_path.relative_to(root)),
        })
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
