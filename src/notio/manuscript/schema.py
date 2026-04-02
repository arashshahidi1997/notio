"""ManuscriptSpec dataclass and YAML loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Author:
    name: str
    affiliation: str = ""
    email: str = ""


@dataclass
class SectionEntry:
    key: str
    path: str
    order: int
    heading_level: int = 1  # default: keep headings as-is


@dataclass
class BibConfig:
    bib_file: str = ""
    csl: str = ""


@dataclass
class FigureMapping:
    id: str
    label: str = ""
    caption: str = ""
    spec: str = ""


@dataclass
class FiguresConfig:
    dir: str = "figures/"
    mappings: list[FigureMapping] = field(default_factory=list)


@dataclass
class RenderConfig:
    output_dir: str = "_build/"
    formats: list[str] = field(default_factory=lambda: ["pdf"])
    template: str | None = None
    pandoc_args: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)


@dataclass
class ResolvedRender:
    """Fully resolved render settings (project defaults merged with manuscript overrides)."""

    bib_file: str = ""
    csl: str = ""
    pdf_engine: str = "xelatex"
    lua_filter: str = ""
    conda_env: str = ""
    resource_path: list[str] = field(default_factory=list)
    # Manuscript-specific settings carried through
    output_dir: str = "_build/"
    formats: list[str] = field(default_factory=lambda: ["pdf"])
    template: str | None = None
    pandoc_args: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)


@dataclass
class ManuscriptSpec:
    name: str
    title: str = ""
    authors: list[Author] = field(default_factory=list)
    sections: list[SectionEntry] = field(default_factory=list)
    bibliography: BibConfig = field(default_factory=BibConfig)
    figures: FiguresConfig = field(default_factory=FiguresConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    defaults_from: str = "../../.projio/render.yml"

    @classmethod
    def from_yaml(cls, path: Path) -> ManuscriptSpec:
        """Load a ManuscriptSpec from a YAML file."""
        import yaml

        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManuscriptSpec:
        """Build a ManuscriptSpec from a parsed dict."""
        authors = [
            Author(**a) if isinstance(a, dict) else Author(name=str(a))
            for a in data.get("authors", [])
        ]
        sections = [
            SectionEntry(
                key=s["key"],
                path=s["path"],
                order=int(s.get("order", i)),
                heading_level=int(s.get("heading_level", 1)),
            )
            for i, s in enumerate(data.get("sections", []), start=1)
        ]
        bib_raw = data.get("bibliography", {}) or {}
        bib = BibConfig(
            bib_file=bib_raw.get("bib_file", ""),
            csl=bib_raw.get("csl", ""),
        )
        fig_raw = data.get("figures", {}) or {}
        fig_mappings = [
            FigureMapping(
                id=m["id"],
                label=m.get("label", ""),
                caption=m.get("caption", ""),
                spec=m.get("spec", ""),
            )
            for m in fig_raw.get("mappings", [])
        ]
        figures = FiguresConfig(
            dir=fig_raw.get("dir", "figures/"),
            mappings=fig_mappings,
        )
        render_raw = data.get("render", {}) or {}
        render_cfg = RenderConfig(
            output_dir=render_raw.get("output_dir", "_build/"),
            formats=render_raw.get("formats", ["pdf"]),
            template=render_raw.get("template"),
            pandoc_args=render_raw.get("pandoc_args", []),
            variables=render_raw.get("variables", {}),
        )
        return cls(
            name=data.get("name", ""),
            title=data.get("title", ""),
            authors=authors,
            sections=sections,
            bibliography=bib,
            figures=figures,
            render=render_cfg,
            defaults_from=data.get("defaults_from", "../../.projio/render.yml"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for YAML output."""
        result: dict[str, Any] = {"name": self.name, "title": self.title}
        if self.authors:
            result["authors"] = [
                {"name": a.name, "affiliation": a.affiliation, "email": a.email}
                for a in self.authors
            ]
        if self.sections:
            result["sections"] = [
                {
                    "key": s.key,
                    "path": s.path,
                    "order": s.order,
                    "heading_level": s.heading_level,
                }
                for s in self.sections
            ]
        result["bibliography"] = {
            "bib_file": self.bibliography.bib_file,
            "csl": self.bibliography.csl,
        }
        result["figures"] = {
            "dir": self.figures.dir,
            "mappings": [
                {"id": m.id, "label": m.label, "caption": m.caption, "spec": m.spec}
                for m in self.figures.mappings
            ],
        }
        result["render"] = {
            "output_dir": self.render.output_dir,
            "formats": self.render.formats,
            "template": self.render.template,
            "pandoc_args": self.render.pandoc_args,
            "variables": self.render.variables,
        }
        if self.defaults_from:
            result["defaults_from"] = self.defaults_from
        return result


def _load_project_render_yml(path: Path) -> dict[str, Any]:
    """Load .projio/render.yml as a plain dict. Returns {} if not found."""
    import yaml

    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_render_config(spec: ManuscriptSpec, base_dir: Path) -> ResolvedRender:
    """Merge project render.yml defaults with manuscript-level overrides.

    Priority: manuscript.yml values win when non-empty, otherwise fall back
    to project defaults from .projio/render.yml.
    """
    project_defaults: dict[str, Any] = {}
    if spec.defaults_from:
        render_yml_path = (base_dir / spec.defaults_from).resolve()
        project_defaults = _load_project_render_yml(render_yml_path)

    # Resolve bibliography: manuscript wins if non-empty
    bib_file = spec.bibliography.bib_file or project_defaults.get("bibliography", "")
    csl = spec.bibliography.csl or project_defaults.get("csl", "")
    pdf_engine = project_defaults.get("pdf_engine", "xelatex")
    lua_filter = project_defaults.get("lua_filter", "")
    conda_env = project_defaults.get("conda_env", "")
    resource_path = project_defaults.get("resource_path", [])

    return ResolvedRender(
        bib_file=bib_file,
        csl=csl,
        pdf_engine=pdf_engine,
        lua_filter=lua_filter,
        conda_env=conda_env,
        resource_path=resource_path,
        output_dir=spec.render.output_dir,
        formats=spec.render.formats,
        template=spec.render.template,
        pandoc_args=spec.render.pandoc_args,
        variables=spec.render.variables,
    )


DEFAULT_SECTIONS = [
    ("abstract", 1),
    ("introduction", 2),
    ("methods", 3),
    ("results", 4),
    ("discussion", 5),
]


def scaffold_spec(name: str, base_dir: Path) -> ManuscriptSpec:
    """Create a default ManuscriptSpec and write it along with section stubs.

    If .projio/render.yml exists relative to base_dir, leaves bib/csl fields
    empty (they'll inherit from project defaults) and sets defaults_from.
    Otherwise fills in empty defaults.

    Returns the spec. Files are written under *base_dir*.
    """
    import yaml

    sections_dir = base_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    entries: list[SectionEntry] = []
    for key, order in DEFAULT_SECTIONS:
        rel = f"sections/{key}.md"
        section_path = base_dir / rel
        if not section_path.exists():
            title = key.replace("_", " ").capitalize()
            section_path.write_text(
                f"---\ntitle: \"{title}\"\norder: {order}\n"
                f"manuscript: {name}\nstatus: draft\n"
                f"tags: [manuscript, section]\n---\n\n# {title}\n\n",
                encoding="utf-8",
            )
        entries.append(SectionEntry(key=key, path=rel, order=order))

    # Check if project-level render.yml exists
    defaults_from = "../../.projio/render.yml"
    render_yml_path = (base_dir / defaults_from).resolve()
    has_project_render = render_yml_path.is_file()

    spec = ManuscriptSpec(
        name=name,
        title=name.replace("-", " ").replace("_", " ").title(),
        sections=entries,
        defaults_from=defaults_from if has_project_render else "",
    )

    spec_path = base_dir / "manuscript.yml"
    spec_path.write_text(
        yaml.dump(spec.to_dict(), default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return spec
