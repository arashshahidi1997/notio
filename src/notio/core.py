from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from string import Template
from typing import Any
import getpass
import re

from notio.config import Config, NoteTypeConfig


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
ROOT_INDEX_TITLE = "Project Logs"


DEFAULT_TEMPLATES: dict[str, str] = {
    "idea.md": """---
title: "${title}"
date: ${date}
timestamp: ${timestamp}
series: ""
refs: []
tags: [idea]
---

# ${title}

## Overview
-

## Tasks
- [ ]

## Notes
-
""",
    "issue.md": """---
title: "${title}"
status: open
created: ${date}
updated: ${date}
timestamp: ${timestamp}
series: ""
refs: []
tags: [issue]
---

# ${title}

## Summary
-

## Context
-

## Tasks
- [ ]

## Notes
-
""",
    "task.md": """---
title: "${title}"
date: ${date}
timestamp: ${timestamp}
status: pending
actionable: true
prompt: ""
source_note: ""
project_primary: ""
series: ""
refs: []
tags: [task]
---

# ${title}

## Goal

-

## Context

-

## Prompt

> (The instruction for an agent to execute this task)

## Acceptance Criteria

- [ ]

## Result

(Filled in after execution)
""",
    "meeting.md": """---
title: "${title}"
date: ${date}
timestamp: ${timestamp}
participants: []
series: ""
refs: []
tags: [meeting]
---

# ${title} - ${date}

## Notes
-

## Action Items
- [ ]
""",
}


@dataclass(frozen=True)
class NoteContext:
    owner: str
    title: str
    when: date
    timestamp: str

    @property
    def template_vars(self) -> dict[str, str]:
        week = self.when.strftime("%V")
        year = self.when.strftime("%Y")
        month = self.when.strftime("%m")
        day = self.when.strftime("%d")
        iso_date = self.when.isoformat()
        values = {
            "owner": self.owner,
            "title": self.title,
            "date": iso_date,
            "timestamp": self.timestamp,
            "year": year,
            "month": month,
            "day": day,
            "week": week,
            "datetime": f"{iso_date}T{self.timestamp}",
            "FOAM_TITLE": self.title,
            "FOAM_DATE_YEAR": year,
            "FOAM_DATE_MONTH": month,
            "FOAM_DATE_DATE": day,
            "FOAM_DATE_WEEK": week,
            "FOAM_TIMESTAMP": self.timestamp,
        }
        return values


def default_owner() -> str:
    return getpass.getuser()


def parse_date(value: str | None) -> date:
    if value is None:
        return date.today()
    return date.fromisoformat(value)


def make_timestamp(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return current.strftime("%Y%m%d-%H%M%S-%f")


def default_title(note_name: str, when: date) -> str:
    return note_name


def ensure_default_templates(config: Config, *, force: bool = False) -> list[Path]:
    config.template_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for template_name, content in DEFAULT_TEMPLATES.items():
        path = config.template_root / template_name
        if path.exists() and not force:
            continue
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def ensure_note_dirs(config: Config) -> list[Path]:
    created: list[Path] = []
    config.notes_root.mkdir(parents=True, exist_ok=True)
    created.append(config.notes_root)
    for note_type in config.note_types:
        folder = config.notes_root / note_type
        folder.mkdir(parents=True, exist_ok=True)
        created.append(folder)
    return created


def render_template(template_text: str, values: dict[str, str]) -> str:
    return Template(template_text).safe_substitute(values)


def build_note_path(config: Config, note_type: NoteTypeConfig, context: NoteContext) -> Path:
    values = context.template_vars
    return config.notes_root / note_type.name / note_type.filename.format(**values)


def create_note(
    config: Config,
    note_name: str,
    *,
    owner: str | None = None,
    title: str | None = None,
    note_date: str | None = None,
    timestamp: str | None = None,
    force: bool = False,
    extra_frontmatter: dict[str, Any] | None = None,
    body: str | None = None,
) -> Path:
    """Create a note from template.

    If *body* is provided, it replaces the template body (everything after
    the frontmatter closing ``---``).  Extra frontmatter fields are appended
    inside the ``---`` block.
    """
    note_type = config.note_types[note_name]
    when = parse_date(note_date)
    resolved_owner = owner or default_owner()
    resolved_title = title or default_title(note_name, when)
    resolved_timestamp = timestamp or make_timestamp()
    context = NoteContext(
        owner=resolved_owner,
        title=resolved_title,
        when=when,
        timestamp=resolved_timestamp,
    )
    path = build_note_path(config, note_type, context)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force and note_type.mode == "event":
        raise FileExistsError(f"Refusing to overwrite existing event note: {path}")

    template_path = config.template_root / note_type.template
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template: {template_path}")

    rendered = render_template(template_path.read_text(encoding="utf-8"), context.template_vars)

    # Inject extra frontmatter and/or body
    if extra_frontmatter or body is not None:
        rendered = _inject_into_note(rendered, extra_frontmatter, body)

    path.write_text(rendered, encoding="utf-8")
    build_type_index(config, note_name)
    build_root_index(config)
    return path


def _inject_into_note(
    rendered: str,
    extra_frontmatter: dict[str, Any] | None,
    body: str | None,
) -> str:
    """Inject extra frontmatter fields and/or replace the body of a rendered note."""
    match = FRONTMATTER_RE.match(rendered)
    if not match:
        # No frontmatter — just prepend body
        if body is not None:
            return body
        return rendered

    fm_text = match.group(1)
    after_fm = rendered[match.end():]

    if extra_frontmatter:
        # Replace existing keys in-place; append new keys at the end
        fm_lines = fm_text.splitlines()
        existing_keys: dict[str, int] = {}
        for i, line in enumerate(fm_lines):
            if ":" in line and not line.startswith((" ", "\t")):
                key = line.split(":", 1)[0].strip()
                existing_keys[key] = i
        append_lines: list[str] = []
        for k, v in extra_frontmatter.items():
            formatted = f"{k}: {_format_frontmatter_value(v)}"
            if k in existing_keys:
                fm_lines[existing_keys[k]] = formatted
            else:
                append_lines.append(formatted)
        fm_text = "\n".join(fm_lines).rstrip()
        if append_lines:
            fm_text += "\n" + "\n".join(append_lines)

    result = f"---\n{fm_text}\n---\n"
    if body is not None:
        result += "\n" + body + "\n"
    else:
        result += after_fm
    return result


def _format_frontmatter_value(value: Any) -> str:
    """Format a value for YAML frontmatter.

    Lists of dicts (e.g. refs) are rendered as multi-line YAML::

        refs:
          - note: idea-arash-20260211
          - plan: 03-Questions
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        # Check for list-of-dicts (refs-style)
        if value and isinstance(value[0], dict):
            lines = []
            for item in value:
                if isinstance(item, dict):
                    for k, v in item.items():
                        lines.append(f"\n  - {k}: {v}")
                else:
                    lines.append(f"\n  - {item}")
            return "".join(lines)
        return "[" + ", ".join(str(v) for v in value) + "]"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    s = str(value)
    # Quote strings that contain special YAML characters
    if any(c in s for c in ":#{}[]|>&*!%@`"):
        return f'"{s}"'
    return s


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if value[0] in "\"'[":
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value.strip("\"'")
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    meta: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[Any] | None = None

    for line in match.group(1).splitlines():
        # Indented list continuation (e.g. "  - note: foo" under a key)
        stripped = line.strip()
        if line.startswith(("  -", "\t-")) and current_key is not None and current_list is not None:
            item = stripped.lstrip("- ").strip()
            if ":" in item:
                k, v = item.split(":", 1)
                current_list.append({k.strip(): _parse_scalar(v)})
            else:
                current_list.append(_parse_scalar(item))
            meta[current_key] = current_list
            continue

        # Top-level key: value
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = _parse_scalar(raw_value)
        # Start tracking multi-line list if value is an empty list or empty
        # (empty string occurs when list items follow on indented lines)
        if (isinstance(value, list) and len(value) == 0) or value == "":
            current_key = key
            current_list = []
            meta[key] = value
        else:
            current_key = None
            current_list = None
            meta[key] = value
    return meta


def _format_meta_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _entry_label(path: Path, metadata: dict[str, Any], keys: tuple[str, ...]) -> str:
    if not keys:
        return path.stem
    extras = " ".join(
        f"{key}:{_format_meta_value(metadata.get(key))}"
        for key in keys
        if _format_meta_value(metadata.get(key))
    )
    return f"{path.stem} {extras}".rstrip()


def build_type_index(config: Config, note_name: str) -> Path:
    note_type = config.note_types[note_name]
    folder = config.notes_root / note_name
    folder.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_file() and path.name != "index.md" and path.name.startswith(note_name)
        ],
        reverse=True,
    )

    lines = [f"# {note_name.capitalize()}", ""]
    if note_type.toc_groupby:
        grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
        for path in files:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            group = _format_meta_value(meta.get(note_type.toc_groupby)) or "unset"
            grouped.setdefault(group, []).append((path, meta))
        for group in sorted(grouped):
            lines.append(f"## {note_type.toc_groupby}: {group}")
            lines.append("")
            for path, meta in grouped[group]:
                lines.append(f"- [{_entry_label(path, meta, note_type.toc_keys)}]({path.name})")
            lines.append("")
    else:
        lines.append("## Contents")
        lines.append("")
        for path in files:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            lines.append(f"- [{_entry_label(path, meta, note_type.toc_keys)}]({path.name})")
    lines.append("")
    index_path = folder / "index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def build_root_index(config: Config) -> Path:
    lines = [f"# {ROOT_INDEX_TITLE}", "", "## Contents", ""]
    for note_name in sorted(config.note_types):
        lines.append(f"- [{note_name.capitalize()}]({note_name}/index.md)")
    lines.append("")
    index_path = config.notes_root / "index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def init_workspace(config: Config, *, force: bool = False) -> list[Path]:
    created: list[Path] = []
    created.extend(ensure_note_dirs(config))
    created.extend(ensure_default_templates(config, force=force))
    created.append(build_root_index(config))
    for note_name in config.note_types:
        created.append(build_type_index(config, note_name))
    return created
