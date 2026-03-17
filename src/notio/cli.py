from __future__ import annotations

import argparse
from pathlib import Path
import sys

from notio import __version__
from notio.config import DEFAULT_CONFIG_TEXT, load_config
from notio.core import build_root_index, build_type_index, create_note, init_workspace


# ---------------------------------------------------------------------------
# Helpers for note creation args (shared across note subcommands)
# ---------------------------------------------------------------------------

def _add_note_flags(p: argparse.ArgumentParser) -> None:
    """Add shared flags for any note-creation command."""
    p.add_argument("--owner")
    p.add_argument("--title")
    p.add_argument("--date", dest="note_date")
    p.add_argument("--timestamp")
    p.add_argument("--force", action="store_true", help="Allow overwriting")
    p.add_argument("--source", help="Capture source (e.g. telegram-voice, cli-text)")
    p.add_argument("--transcript", help="Raw transcript text")
    p.add_argument("--summary", help="Summary text")
    p.add_argument("--project", help="Source project id (stored in frontmatter)")
    p.add_argument("--metadata", help="JSON string of extra frontmatter fields")
    p.add_argument("--body", help="Note body (replaces template body)")
    p.add_argument("--enrich", action="store_true", help="Use LLM to structure the note body")


def _build_extra_frontmatter(args: argparse.Namespace) -> dict:
    import json
    fm: dict = {}
    if getattr(args, "source", None):
        fm["source"] = args.source
    if getattr(args, "project", None):
        fm["project_primary"] = args.project
    md = getattr(args, "metadata", None)
    if md:
        fm.update(json.loads(md))
    return fm


def _build_note_body(args: argparse.Namespace, note_type: str) -> str | None:
    body = getattr(args, "body", None)
    if body:
        return body
    transcript = getattr(args, "transcript", None)
    summary = getattr(args, "summary", None)
    if not transcript and not summary:
        return None

    # If --enrich, try LLM structuring
    if getattr(args, "enrich", False) and transcript:
        from notio.llm import enrich_body
        root = Path(getattr(args, "root", ".")).resolve()
        from notio.llm import load_config as load_llm_config
        llm_cfg = load_llm_config(root)
        title = getattr(args, "title", None) or note_type
        enriched = enrich_body(transcript, title, note_type, config=llm_cfg)
        if enriched:
            return enriched

    # Fallback: simple structure
    parts = [f"# {args.title or note_type}\n"]
    if transcript:
        parts.append("## Transcript\n")
        parts.append(transcript + "\n")
    if summary:
        parts.append("## Summary\n")
        parts.append(summary + "\n")
    parts.append("## Follow-up\n- \n")
    return "\n".join(parts)


def _run_note(args: argparse.Namespace, note_type: str) -> int:
    """Shared note creation logic for all note type commands."""
    root = Path(args.root).resolve()
    config = load_config(root)
    if note_type not in config.note_types:
        print(f"Unknown note type: {note_type}", file=sys.stderr)
        return 2
    extra_fm = _build_extra_frontmatter(args)
    body = _build_note_body(args, note_type)
    path = create_note(
        config,
        note_type,
        owner=args.owner,
        title=args.title,
        note_date=args.note_date,
        timestamp=args.timestamp,
        force=args.force,
        extra_frontmatter=extra_fm or None,
        body=body,
    )
    print(path)
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notio", description="Templated notes and log indexes")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # -- init --
    p = sub.add_parser("init", help="Scaffold config, templates, and log folders")
    p.add_argument("--force", action="store_true")
    p.add_argument("--write-config", action="store_true")

    # -- flat note commands: notio idea, notio issue, notio meeting, etc. --
    for note_type in ("idea", "issue", "meeting", "daily", "weekly", "commit", "personal", "task"):
        p = sub.add_parser(note_type, help=f"Create a {note_type} note")
        _add_note_flags(p)

    # -- note (generic, for programmatic use or custom types) --
    p = sub.add_parser("note", help="Create a note by type name")
    p.add_argument("type", help="Note type")
    _add_note_flags(p)

    # -- toc --
    p = sub.add_parser("toc", help="Regenerate indexes")
    p.add_argument("type", nargs="?")
    p.add_argument("--all", action="store_true")

    # -- links --
    p = sub.add_parser("links", help="Suggest wikilinks for a note")
    p.add_argument("note_path", help="Path to the note file (relative to root)")
    p.add_argument("--apply", action="store_true", help="Append suggested links to the note")

    # -- warmup --
    sub.add_parser("warmup", help="Pre-load LLM model into memory")

    # -- llm --
    sub.add_parser("llm", help="Check LLM connectivity")

    # -- diataxis --
    dx = sub.add_parser("diataxis", help="Manage Diataxis documentation")
    dx_sub = dx.add_subparsers(dest="diataxis_command", required=True)
    p = dx_sub.add_parser("init")
    p.add_argument("--mkdocs", action="store_true")
    p = dx_sub.add_parser("add")
    p.add_argument("section")
    p.add_argument("slug")
    p.add_argument("--title")
    p = dx_sub.add_parser("toc")
    p.add_argument("section", nargs="?")
    p.add_argument("--all", action="store_true")

    # -- mcp --
    sub.add_parser("mcp", help="Start the FastMCP server (stdio)")

    return parser


def maybe_write_default_config(root: Path) -> Path | None:
    notio_toml = root / "notio.toml"
    if notio_toml.exists():
        return None
    notio_toml.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
    return notio_toml


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    # -- init --
    if args.command == "init":
        written_config = maybe_write_default_config(root) if args.write_config else None
        config = load_config(root)
        created = init_workspace(config, force=args.force)
        if written_config is not None:
            print(written_config)
        for path in created:
            print(path)
        return 0

    # -- flat note commands --
    note_types = {"idea", "issue", "meeting", "daily", "weekly", "commit", "personal", "task"}
    if args.command in note_types:
        return _run_note(args, args.command)

    # -- note (generic) --
    if args.command == "note":
        return _run_note(args, args.type)

    config = load_config(root)

    # -- toc --
    if args.command == "toc":
        if args.all or not args.type:
            print(build_root_index(config))
            for note_name in config.note_types:
                print(build_type_index(config, note_name))
            return 0
        if args.type not in config.note_types:
            parser.error(f"Unknown note type: {args.type}")
        print(build_type_index(config, args.type))
        print(build_root_index(config))
        return 0

    # -- links --
    if args.command == "links":
        return _cmd_links(args, root, config)

    # -- warmup --
    if args.command == "warmup":
        from notio.llm import load_config as load_llm_config, warmup as llm_warmup
        llm_cfg = load_llm_config(root)
        print(f"Loading {llm_cfg.model} on {llm_cfg.url}...")
        if llm_warmup(llm_cfg):
            print("Model warm (keep-alive: 30m)")
            return 0
        print("Failed to warm up model", file=sys.stderr)
        return 1

    # -- llm --
    if args.command == "llm":
        return _cmd_llm(root)

    # -- mcp --
    if args.command == "mcp":
        import os
        os.environ.setdefault("NOTIO_ROOT", str(root))
        from notio.mcp.server import main as mcp_main
        mcp_main()
        return 0

    # -- diataxis --
    if args.command == "diataxis":
        from notio.diataxis import diataxis_add, diataxis_init, diataxis_toc
        if args.diataxis_command == "init":
            created, snippet = diataxis_init(config, mkdocs=args.mkdocs)
            for path in created:
                print(path)
            if snippet:
                print()
                print(snippet)
            return 0
        if args.diataxis_command == "add":
            path = diataxis_add(config, args.section, args.slug, title=args.title)
            print(path)
            return 0
        if args.diataxis_command == "toc":
            section = args.section if args.section and not args.all else None
            paths = diataxis_toc(config, section)
            for path in paths:
                print(path)
            return 0

    parser.print_help(sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Link suggestion command
# ---------------------------------------------------------------------------

def _cmd_links(args: argparse.Namespace, root: Path, config) -> int:
    from notio.llm import load_config as load_llm_config, suggest_links
    from notio.query import list_notes
    from notio.core import parse_frontmatter

    note_path = root / args.note_path
    if not note_path.exists():
        print(f"Note not found: {args.note_path}", file=sys.stderr)
        return 1

    content = note_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(content)

    # Determine note type from path
    note_type = None
    rel = note_path.relative_to(config.notes_root) if note_path.is_relative_to(config.notes_root) else None
    if rel and len(rel.parts) >= 2:
        note_type = rel.parts[0]

    siblings = list_notes(root, note_type=note_type, limit=30)
    # Exclude the note itself
    rel_path = str(note_path.relative_to(root))
    siblings = [s for s in siblings if s["path"] != rel_path]

    if not siblings:
        print("No other notes to link to.")
        return 0

    llm_cfg = load_llm_config(root)
    links = suggest_links(note_path, content, siblings, config=llm_cfg)

    if links is None:
        print("LLM unavailable — cannot suggest links.", file=sys.stderr)
        return 1

    if not links:
        print("No related notes found.")
        return 0

    print("Suggested links:")
    for link in links:
        target = link.get("target", "?")
        reason = link.get("reason", "")
        print(f"  [[{target}]] — {reason}")

    if args.apply and links:
        # Append a links section to the note
        link_lines = ["\n## Related Notes\n"]
        for link in links:
            target = link.get("target", "?")
            reason = link.get("reason", "")
            link_lines.append(f"- [[{target}]] — {reason}")
        link_lines.append("")
        with open(note_path, "a", encoding="utf-8") as f:
            f.write("\n".join(link_lines))
        print(f"\nAppended {len(links)} links to {args.note_path}")

    return 0


def _cmd_llm(root: Path) -> int:
    import json
    import urllib.request
    import urllib.error
    from notio.llm import load_config as load_llm_config, available
    cfg = load_llm_config(root)
    print(f"Ollama URL:   {cfg.url}")
    print(f"Model:        {cfg.model}")
    print(f"Timeout:      {cfg.timeout}s")
    try:
        url = f"{cfg.url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        print(f"Server:       reachable")
        print(f"Models:       {', '.join(models) if models else '(none)'}")
        model_ok = any(m == cfg.model or m.startswith(f"{cfg.model}:") for m in models)
        print(f"Model ready:  {'yes' if model_ok else 'NO'}")
        return 0 if model_ok else 1
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"Server:       unreachable ({exc})")
        return 1
