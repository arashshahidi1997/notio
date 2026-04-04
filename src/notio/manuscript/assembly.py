"""Section ordering, frontmatter stripping, and concatenation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from notio.manuscript.schema import ManuscriptSpec, SectionEntry

FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s", re.MULTILINE)


@dataclass
class Section:
    """A loaded manuscript section with its content and metadata."""

    entry: SectionEntry
    content: str  # body text with frontmatter stripped


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from Markdown text."""
    return FRONTMATTER_RE.sub("", text).lstrip("\n")


def adjust_headings(text: str, level_offset: int) -> str:
    """Shift Markdown heading levels by *level_offset*.

    A positive offset demotes headings (# → ##), negative promotes.
    Heading levels are clamped to 1–6.
    """
    if level_offset == 0:
        return text

    def _shift(m: re.Match) -> str:
        hashes = m.group(1)
        new_level = max(1, min(6, len(hashes) + level_offset))
        return "#" * new_level + " "

    return HEADING_RE.sub(_shift, text)


def load_sections(spec: ManuscriptSpec, base_dir: Path) -> list[Section]:
    """Load and order section files.

    Returns :class:`Section` objects sorted by ``order``.
    Raises :class:`FileNotFoundError` for missing section files.
    """
    sections: list[Section] = []
    for entry in sorted(spec.sections, key=lambda s: s.order):
        section_path = base_dir / entry.path
        if not section_path.is_file():
            raise FileNotFoundError(
                f"Section '{entry.key}' not found: {section_path}"
            )
        raw = section_path.read_text(encoding="utf-8")
        body = strip_frontmatter(raw)
        if entry.heading_level != 1:
            body = adjust_headings(body, entry.heading_level - 1)
        sections.append(Section(entry=entry, content=body))
    return sections


def assemble(spec: ManuscriptSpec, base_dir: Path) -> str:
    """Concatenate sections in order into a single Markdown document.

    Strips frontmatter, adjusts heading levels, resolves figure references,
    and inserts blank lines between sections.
    """
    sections = load_sections(spec, base_dir)
    parts: list[str] = []

    # Optional YAML metadata block for pandoc
    if spec.title or spec.authors:
        meta_lines = ["---"]
        if spec.title:
            meta_lines.append(f'title: "{spec.title}"')
        if spec.authors:
            meta_lines.append("author:")
            for author in spec.authors:
                line = f'  - name: "{author.name}"'
                if author.affiliation:
                    line = f"  - name: \"{author.name}\"\n    affiliation: \"{author.affiliation}\""
                meta_lines.append(line)
        meta_lines.append("---")
        parts.append("\n".join(meta_lines))

    for section in sections:
        parts.append(section.content.rstrip())

    text = "\n\n".join(parts) + "\n"

    # Resolve fig:<id> references to actual file paths
    if spec.figures.mappings:
        from notio.manuscript.figures import resolve_figure_paths, insert_figure_references

        figures = resolve_figure_paths(spec, base_dir)
        if figures:
            text = insert_figure_references(text, figures, base_dir)

    return text


def write_assembled(spec: ManuscriptSpec, base_dir: Path) -> Path:
    """Assemble and write to output_dir/assembled.md.

    Returns the path to the assembled file.
    """
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "assembled.md"
    text = assemble(spec, base_dir)
    output_path.write_text(text, encoding="utf-8")
    return output_path
