"""Section ordering, loading, and Marp assembly for presentio.

Mirrors :mod:`notio.manuscript.assembly`. Reuses ``strip_frontmatter``,
``FRONTMATTER_RE``, ``adjust_headings``, and ``HEADING_RE`` from
manuscript; parallel ``load_sections`` because ``DeckSection`` doesn't
carry ``heading_level``. ``assemble_marp`` emits Marp-style frontmatter,
not pandoc YAML frontmatter — the two are incompatible and ``assemble``
cannot be a single branching function.

``load_sections`` accepts a ``resolver`` callable even though phase 1
only implements the local resolver — this prevents a breaking signature
change when phase 4 adds cross-project imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from notio.manuscript.assembly import FRONTMATTER_RE, HEADING_RE  # noqa: F401
from notio.manuscript.assembly import adjust_headings, strip_frontmatter
from notio.present.schema import DeckSection, DeckSpec

# Re-export for test visibility and for callers that want the regexes.
__all__ = [
    "Section",
    "LocalResolver",
    "local_resolver",
    "load_sections",
    "assemble_marp",
    "assemble_pandoc",
    "write_assembled",
    "write_assembled_pandoc",
    "strip_frontmatter",
    "adjust_headings",
    "FRONTMATTER_RE",
    "HEADING_RE",
]


@dataclass
class Section:
    """A loaded deck section with its content and metadata."""

    entry: DeckSection
    content: str  # body text with frontmatter stripped


# A resolver takes a (DeckSection, base_dir) pair and returns the absolute
# path to the section file. Phase 1 only has the local resolver; phase 4
# plugs in a worklog-backed resolver for cross-project imports without
# changing load_sections itself.
LocalResolver = Callable[[DeckSection, Path], Path]


def local_resolver(entry: DeckSection, base_dir: Path) -> Path:
    """Default resolver: section path is relative to *base_dir*."""
    return base_dir / entry.path


def load_sections(
    spec: DeckSpec,
    base_dir: Path,
    resolver: LocalResolver | None = None,
) -> list[Section]:
    """Load and order section files.

    Returns :class:`Section` objects sorted by ``order``. Raises
    :class:`FileNotFoundError` for missing section files.
    """
    resolve = resolver or local_resolver
    sections: list[Section] = []
    for entry in sorted(spec.sections, key=lambda s: s.order):
        section_path = resolve(entry, base_dir)
        if not section_path.is_file():
            raise FileNotFoundError(
                f"Deck section '{entry.key}' not found: {section_path}"
            )
        raw = section_path.read_text(encoding="utf-8")
        body = strip_frontmatter(raw)
        sections.append(Section(entry=entry, content=body))
    return sections


def _build_marp_frontmatter(spec: DeckSpec) -> str:
    """Build Marp YAML frontmatter from a DeckSpec.

    Keeps this simple — Marp's frontmatter is a YAML-ish block the Marp
    parser reads, not a full pandoc YAML metadata block.
    """
    lines: list[str] = ["---", "marp: true"]
    if spec.render.theme:
        lines.append(f"theme: {spec.render.theme}")
    if spec.render.paginate:
        lines.append("paginate: true")
    # Marp 'size' accepts '16:9' as '16:9' in later versions; default 4:3
    # Older Marp uses 'size: 16:9' directly.
    if spec.render.ratio:
        lines.append(f"size: {spec.render.ratio}")
    if spec.render.header:
        lines.append(f'header: "{_escape_quotes(spec.render.header)}"')
    elif spec.title:
        lines.append(f'header: "{_escape_quotes(spec.title)}"')
    if spec.render.footer:
        lines.append(f'footer: "{_escape_quotes(spec.render.footer)}"')
    elif spec.author:
        names = ", ".join(a.name for a in spec.author)
        if names:
            lines.append(f'footer: "{_escape_quotes(names)}"')
    lines.append("---")
    return "\n".join(lines)


def _escape_quotes(text: str) -> str:
    return text.replace('"', '\\"')


def _build_title_slide(spec: DeckSpec) -> str:
    """Build an optional title slide body from spec metadata.

    Only used when the first section file doesn't already start with a
    heading. Phase 1 keeps this off by default — users scaffold a
    ``title`` section stub via ``scaffold_deck`` and author it themselves.
    """
    lines: list[str] = []
    if spec.title:
        lines.append(f"# {spec.title}")
    if spec.subtitle:
        lines.append("")
        lines.append(f"## {spec.subtitle}")
    if spec.author:
        lines.append("")
        lines.append(", ".join(a.name for a in spec.author))
    if spec.date:
        lines.append("")
        lines.append(str(spec.date))
    if spec.venue:
        lines.append("")
        lines.append(f"_{spec.venue}_")
    return "\n".join(lines)


def assemble_marp(spec: DeckSpec, base_dir: Path) -> str:
    """Concatenate sections into a single Marp-formatted Markdown document.

    - Prepends Marp frontmatter derived from *spec*.
    - Joins sections with ``\\n\\n---\\n\\n`` (Marp slide separator between
      sections).
    - Intra-file ``---`` separators in section bodies are preserved as
      additional slide breaks.
    - Does not touch citation keys. Citation pre-resolution is a
      render-stage transform, not an assembly-stage one.
    """
    sections = load_sections(spec, base_dir)

    frontmatter = _build_marp_frontmatter(spec)
    parts: list[str] = [frontmatter]

    # Inline title slide if the spec has metadata and the first section
    # doesn't already begin with an h1.
    if sections and spec.title:
        first = sections[0].content.lstrip()
        if not first.startswith("# "):
            title_slide = _build_title_slide(spec)
            if title_slide:
                parts.append(title_slide)

    for section in sections:
        parts.append(section.content.rstrip())

    # Marp slide separator between parts. The frontmatter block is followed
    # by a blank line (no leading "---" needed because Marp treats the
    # frontmatter as the first slide header itself; slide breaks are
    # between *body* parts only).
    text = parts[0] + "\n\n" + "\n\n---\n\n".join(parts[1:])
    if not text.endswith("\n"):
        text += "\n"
    return text


def _build_pandoc_frontmatter(spec: DeckSpec) -> str:
    """Build a pandoc YAML metadata block from a DeckSpec.

    Pandoc frontmatter is semantically different from Marp's — it carries
    document metadata (title, author, date) that citeproc and templates
    consume. Does NOT include Marp-specific keys.
    """
    lines: list[str] = ["---"]
    if spec.title:
        lines.append(f'title: "{_escape_quotes(spec.title)}"')
    if spec.subtitle:
        lines.append(f'subtitle: "{_escape_quotes(spec.subtitle)}"')
    if spec.author:
        lines.append("author:")
        for author in spec.author:
            if author.affiliation:
                lines.append(
                    f'  - name: "{_escape_quotes(author.name)}"\n'
                    f'    affiliation: "{_escape_quotes(author.affiliation)}"'
                )
            else:
                lines.append(f'  - "{_escape_quotes(author.name)}"')
    if spec.date:
        lines.append(f'date: "{_escape_quotes(str(spec.date))}"')
    if spec.venue:
        lines.append(f'venue: "{_escape_quotes(spec.venue)}"')
    # Reveal.js-specific metadata (pandoc reads these via -V or frontmatter
    # when format: revealjs is used at render time).
    if spec.render.theme and spec.render.theme != "default":
        lines.append(f"theme: {spec.render.theme}")
    if spec.render.ratio:
        # pandoc-revealjs uses width/height, but we pass ratio through as a
        # custom variable that the renderer can expand via -V if desired.
        lines.append(f"ratio: {spec.render.ratio}")
    lines.append("---")
    return "\n".join(lines)


def assemble_pandoc(spec: DeckSpec, base_dir: Path) -> str:
    """Concatenate sections into a single pandoc-Markdown document.

    Used by the reveal.js backend. Differs from :func:`assemble_marp`
    in two ways:

    1. Emits a **pandoc YAML metadata block** (title/author/date) instead
       of a Marp frontmatter block.
    2. Does not need a synthetic title slide — pandoc-revealjs uses the
       frontmatter ``title:`` to render the first slide automatically
       when the body doesn't start with a heading.

    Same section join logic: ``\\n\\n---\\n\\n`` between sections;
    intra-file ``---`` separators survive as slide breaks when pandoc
    runs with ``--slide-level=0``.

    Keeps raw ``@key`` citation markers intact — pandoc citeproc resolves
    them natively at render time.
    """
    sections = load_sections(spec, base_dir)
    frontmatter = _build_pandoc_frontmatter(spec)
    parts: list[str] = [frontmatter]
    for section in sections:
        parts.append(section.content.rstrip())
    text = parts[0] + "\n\n" + "\n\n---\n\n".join(parts[1:])
    if not text.endswith("\n"):
        text += "\n"
    return text


def write_assembled(spec: DeckSpec, base_dir: Path) -> Path:
    """Assemble and write to ``{render.output_dir}/assembled.md``.

    Dispatches by ``spec.format`` — Marp decks get ``assemble_marp``,
    revealjs decks get ``assemble_pandoc``. The file name stays
    ``assembled.md`` for both so downstream tooling (diff, status) can
    locate it without knowing the format.
    """
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "assembled.md"
    if spec.format == "revealjs":
        text = assemble_pandoc(spec, base_dir)
    else:
        text = assemble_marp(spec, base_dir)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def write_assembled_pandoc(spec: DeckSpec, base_dir: Path) -> Path:
    """Assemble via ``assemble_pandoc`` and write to ``assembled.md``.

    Explicit companion to :func:`write_assembled` for callers that want
    the pandoc form without relying on ``spec.format`` dispatch.
    """
    output_dir = base_dir / spec.render.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "assembled.md"
    text = assemble_pandoc(spec, base_dir)
    output_path.write_text(text, encoding="utf-8")
    return output_path
