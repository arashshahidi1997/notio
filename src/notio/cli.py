from __future__ import annotations

import argparse
from pathlib import Path
import sys

from notio import __version__
from notio.config import DEFAULT_CONFIG_TEXT, load_config
from notio.core import build_root_index, build_type_index, create_note, init_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notio", description="Templated notes and log indexes")
    parser.add_argument("--root", default=".", help="Project root containing notio.toml or pyproject.toml")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Scaffold config, templates, and log folders")
    init_parser.add_argument("--force", action="store_true", help="Overwrite default templates if they exist")
    init_parser.add_argument(
        "--write-config",
        action="store_true",
        help="Write a default notio.toml if none exists",
    )

    note_parser = subparsers.add_parser("note", help="Create or update a note")
    note_parser.add_argument("type", help="Configured note type")
    note_parser.add_argument("--owner")
    note_parser.add_argument("--title")
    note_parser.add_argument("--date", dest="note_date")
    note_parser.add_argument("--timestamp")
    note_parser.add_argument("--force", action="store_true", help="Allow overwriting period notes or existing paths")

    toc_parser = subparsers.add_parser("toc", help="Regenerate indexes")
    toc_parser.add_argument("type", nargs="?", help="Configured note type")
    toc_parser.add_argument("--all", action="store_true", help="Regenerate every configured note index")

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

    if args.command == "init":
        written_config = maybe_write_default_config(root) if args.write_config else None
        config = load_config(root)
        created = init_workspace(config, force=args.force)
        if written_config is not None:
            print(written_config)
        for path in created:
            print(path)
        return 0

    config = load_config(root)

    if args.command == "note":
        if args.type not in config.note_types:
            parser.error(f"Unknown note type: {args.type}")
        path = create_note(
            config,
            args.type,
            owner=args.owner,
            title=args.title,
            note_date=args.note_date,
            timestamp=args.timestamp,
            force=args.force,
        )
        print(path)
        return 0

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

    parser.print_help(sys.stderr)
    return 2
