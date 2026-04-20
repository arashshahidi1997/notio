"""DeckSpec dataclass and YAML loading for presentio.

Mirrors :mod:`notio.manuscript.schema`. Reuses ``Author`` and the render-yml
inheritance pattern from manuscript, but has deck-specific fields (format,
theme, slide ratio, per-section imports, figure source routing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from notio.manuscript.schema import Author


VALID_FORMATS = ("marp", "revealjs")  # revealjs implemented in phase 3


@dataclass
class DeckSectionImport:
    """Cross-project import descriptor. Phase 4 — stored but not resolved yet."""

    from_project: str = ""
    deck: str = ""
    section: str = ""
    mode: str = "reference"  # "reference" or "freeze"


@dataclass
class DeckSection:
    key: str
    path: str
    order: int
    import_: DeckSectionImport | None = None


@dataclass
class DeckFigure:
    id: str
    source: str = "figio"  # "figio" or "worklog" (phase 4)
    figure: str = ""  # figio figure id
    project: str = ""  # cross-project (phase 4)
    caption: str = ""
    mode: str = "reference"  # "reference" or "freeze"


@dataclass
class DeckOutput:
    format: str  # "html", "pdf", "pptx"
    path: str = ""


@dataclass
class DeckRender:
    """Renderer settings declared per-deck."""

    output_dir: str = "build/"
    theme: str = "default"
    ratio: str = "16:9"
    paginate: bool = True
    header: str = ""
    footer: str = ""
    speaker_notes: bool = True
    marp_args: list[str] = field(default_factory=list)
    # Reveal.js-only (phase 3)
    revealjs_args: list[str] = field(default_factory=list)


@dataclass
class DeckBibConfig:
    """Per-deck bibliography override. Usually empty — inherits from render.yml."""

    bib_file: str = ""
    csl: str = ""


@dataclass
class DeckSpec:
    name: str
    title: str = ""
    subtitle: str = ""
    author: list[Author] = field(default_factory=list)
    date: str = ""
    venue: str = ""
    format: str = "marp"  # "marp" or "revealjs"
    sections: list[DeckSection] = field(default_factory=list)
    figures: list[DeckFigure] = field(default_factory=list)
    bibliography: DeckBibConfig = field(default_factory=DeckBibConfig)
    render: DeckRender = field(default_factory=DeckRender)
    outputs: list[DeckOutput] = field(default_factory=list)
    defaults_from: str = "../../../.projio/render.yml"

    @classmethod
    def from_yaml(cls, path: Path) -> DeckSpec:
        """Load a DeckSpec from a YAML file."""
        import yaml

        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeckSpec:
        """Build a DeckSpec from a parsed dict."""
        authors_raw = data.get("author") or data.get("authors") or []
        if isinstance(authors_raw, str):
            authors_raw = [authors_raw]
        authors = [
            Author(**a) if isinstance(a, dict) else Author(name=str(a))
            for a in authors_raw
        ]

        sections: list[DeckSection] = []
        for i, s in enumerate(data.get("sections", []) or [], start=1):
            imp_raw = s.get("import") or None
            imp = (
                DeckSectionImport(
                    from_project=imp_raw.get("from_project", ""),
                    deck=imp_raw.get("deck", ""),
                    section=imp_raw.get("section", ""),
                    mode=imp_raw.get("mode", "reference"),
                )
                if imp_raw
                else None
            )
            sections.append(
                DeckSection(
                    key=s["key"],
                    path=s.get("path", f"sections/{s['key']}.md"),
                    order=int(s.get("order", i * 10)),
                    import_=imp,
                )
            )

        figures = [
            DeckFigure(
                id=f["id"],
                source=f.get("source", "figio"),
                figure=f.get("figure", f["id"]),
                project=f.get("project", ""),
                caption=f.get("caption", ""),
                mode=f.get("mode", "reference"),
            )
            for f in data.get("figures", []) or []
        ]

        bib_raw = data.get("bibliography") or {}
        bib = DeckBibConfig(
            bib_file=bib_raw.get("bib_file", ""),
            csl=bib_raw.get("csl", ""),
        )

        render_raw = data.get("render") or {}
        render = DeckRender(
            output_dir=render_raw.get("output_dir", "build/"),
            theme=render_raw.get("theme", data.get("theme", "default")),
            ratio=render_raw.get("ratio", data.get("ratio", "16:9")),
            paginate=render_raw.get("paginate", True),
            header=render_raw.get("header", ""),
            footer=render_raw.get("footer", ""),
            speaker_notes=render_raw.get("speaker_notes", True),
            marp_args=render_raw.get("marp_args", []) or [],
            revealjs_args=render_raw.get("revealjs_args", []) or [],
        )

        outputs = [
            DeckOutput(format=o["format"], path=o.get("path", ""))
            for o in data.get("outputs", []) or []
        ]

        fmt = data.get("format", "marp")
        if fmt not in VALID_FORMATS:
            raise ValueError(
                f"Unknown deck format: {fmt!r}. Choose from: {VALID_FORMATS}"
            )

        return cls(
            name=data.get("name", ""),
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            author=authors,
            date=str(data.get("date", "")),
            venue=data.get("venue", ""),
            format=fmt,
            sections=sections,
            figures=figures,
            bibliography=bib,
            render=render,
            outputs=outputs,
            defaults_from=data.get("defaults_from", "../../../.projio/render.yml"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for YAML output."""
        result: dict[str, Any] = {
            "name": self.name,
            "title": self.title,
        }
        if self.subtitle:
            result["subtitle"] = self.subtitle
        if self.author:
            result["author"] = [
                {"name": a.name, "affiliation": a.affiliation, "email": a.email}
                for a in self.author
            ]
        if self.date:
            result["date"] = self.date
        if self.venue:
            result["venue"] = self.venue
        result["format"] = self.format
        if self.sections:
            result["sections"] = []
            for s in self.sections:
                entry: dict[str, Any] = {
                    "key": s.key,
                    "path": s.path,
                    "order": s.order,
                }
                if s.import_:
                    entry["import"] = {
                        "from_project": s.import_.from_project,
                        "deck": s.import_.deck,
                        "section": s.import_.section,
                        "mode": s.import_.mode,
                    }
                result["sections"].append(entry)
        if self.figures:
            result["figures"] = [
                {
                    "id": f.id,
                    "source": f.source,
                    "figure": f.figure,
                    "project": f.project,
                    "caption": f.caption,
                    "mode": f.mode,
                }
                for f in self.figures
            ]
        result["bibliography"] = {
            "bib_file": self.bibliography.bib_file,
            "csl": self.bibliography.csl,
        }
        result["render"] = {
            "output_dir": self.render.output_dir,
            "theme": self.render.theme,
            "ratio": self.render.ratio,
            "paginate": self.render.paginate,
            "header": self.render.header,
            "footer": self.render.footer,
            "speaker_notes": self.render.speaker_notes,
            "marp_args": self.render.marp_args,
            "revealjs_args": self.render.revealjs_args,
        }
        if self.outputs:
            result["outputs"] = [
                {"format": o.format, "path": o.path} for o in self.outputs
            ]
        if self.defaults_from:
            result["defaults_from"] = self.defaults_from
        return result


DEFAULT_SECTION_TEMPLATES = {
    "lab-meeting": [
        ("title", 10),
        ("context", 20),
        ("approach", 30),
        ("results", 40),
        ("next-steps", 50),
    ],
    "journal-club": [
        ("title", 10),
        ("motivation", 20),
        ("methods", 30),
        ("results", 40),
        ("discussion", 50),
        ("takeaways", 60),
    ],
    "conference-talk": [
        ("title", 10),
        ("problem", 20),
        ("related-work", 30),
        ("approach", 40),
        ("experiments", 50),
        ("analysis", 60),
        ("contributions", 70),
        ("future-work", 80),
    ],
    "progress-report": [
        ("title", 10),
        ("summary", 20),
        ("progress", 30),
        ("blockers", 40),
        ("next-steps", 50),
    ],
}


def scaffold_deck(
    name: str,
    base_dir: Path,
    *,
    format: str = "marp",
    template: str = "lab-meeting",
    title: str = "",
) -> DeckSpec:
    """Create a default DeckSpec and write it along with section stubs.

    Writes ``deck.yml`` at *base_dir* and one empty-body section file per
    entry in the chosen template under ``base_dir/sections/``. Section files
    include a notio-compatible frontmatter so notio indexing can pick them
    up once ``docs/deliverables/presentations/`` is added to the indexed paths.

    Returns the spec.
    """
    import yaml

    if format not in VALID_FORMATS:
        raise ValueError(
            f"Unknown deck format: {format!r}. Choose from: {VALID_FORMATS}"
        )
    if template not in DEFAULT_SECTION_TEMPLATES:
        raise ValueError(
            f"Unknown template: {template!r}. "
            f"Choose from: {sorted(DEFAULT_SECTION_TEMPLATES)}"
        )

    sections_dir = base_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    entries: list[DeckSection] = []
    for key, order in DEFAULT_SECTION_TEMPLATES[template]:
        rel = f"sections/{key}.md"
        section_path = base_dir / rel
        if not section_path.exists():
            section_title = key.replace("-", " ").replace("_", " ").capitalize()
            section_path.write_text(
                f"---\n"
                f'title: "{section_title}"\n'
                f"order: {order}\n"
                f"deck: {name}\n"
                f"status: draft\n"
                f"tags: [presentation, section]\n"
                f"---\n\n"
                f"# {section_title}\n\n",
                encoding="utf-8",
            )
        entries.append(DeckSection(key=key, path=rel, order=order))

    defaults_from = "../../../.projio/render.yml"
    render_yml_path = (base_dir / defaults_from).resolve()
    has_project_render = render_yml_path.is_file()

    display_title = title or name.replace("-", " ").replace("_", " ").title()
    spec = DeckSpec(
        name=name,
        title=display_title,
        format=format,
        sections=entries,
        defaults_from=defaults_from if has_project_render else "",
    )

    spec_path = base_dir / "deck.yml"
    spec_path.write_text(
        yaml.dump(spec.to_dict(), default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return spec


def _load_project_render_yml(root: Path) -> dict[str, Any]:
    """Load .projio/render.yml from *root*. Re-exported convenience wrapper."""
    from notio.manuscript.schema import _load_project_render_yml as _manuscript_load

    return _manuscript_load(root)


def resolve_deck_render(spec: DeckSpec, base_dir: Path) -> dict[str, Any]:
    """Resolve deck render settings merged with project render.yml defaults.

    Returns a dict with ``bib_file``, ``csl``, ``output_dir``, ``theme``,
    ``ratio``, ``paginate``, ``marp_args``. Paths are re-relativized so they
    resolve correctly from *base_dir*.
    """
    from notio.manuscript.schema import _rerelativize
    from notio.repo import repo_root

    project_root = repo_root(base_dir)
    project_defaults: dict[str, Any] = {}
    if project_root:
        project_defaults = _load_project_render_yml(project_root)

    def _resolve_path(deck_val: str, default_key: str) -> str:
        if deck_val:
            return deck_val
        raw = project_defaults.get(default_key, "")
        if raw and project_root:
            return _rerelativize(raw, project_root, base_dir)
        return raw

    return {
        "bib_file": _resolve_path(spec.bibliography.bib_file, "bibliography"),
        "csl": _resolve_path(spec.bibliography.csl, "csl"),
        "output_dir": spec.render.output_dir,
        "theme": spec.render.theme,
        "ratio": spec.render.ratio,
        "paginate": spec.render.paginate,
        "header": spec.render.header,
        "footer": spec.render.footer,
        "speaker_notes": spec.render.speaker_notes,
        "marp_args": list(spec.render.marp_args),
    }
