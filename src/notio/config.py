from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_CONFIG_TEXT = """version = 1
notes_root = "docs/log"
template_root = ".notio/templates"

[types.daily]
mode = "period"
template = "daily.md"
filename = "daily-{owner}-{date}.md"

[types.weekly]
mode = "period"
template = "weekly.md"
filename = "weekly-{owner}-{year}-W{week}.md"

[types.commit]
mode = "event"
template = "commit.md"
filename = "commit-{owner}-{timestamp}.md"
toc_keys = ["title"]

[types.idea]
mode = "event"
template = "idea.md"
filename = "idea-{owner}-{timestamp}.md"
toc_keys = ["title"]

[types.issue]
mode = "event"
template = "issue.md"
filename = "issue-{owner}-{timestamp}.md"
toc_keys = ["status"]
toc_groupby = "status"

[types.meeting]
mode = "event"
template = "meeting.md"
filename = "meeting-{owner}-{timestamp}.md"
toc_keys = ["participants"]

[types.personal]
mode = "event"
template = "personal.md"
filename = "personal-{owner}-{timestamp}.md"
toc_keys = ["title"]

# [diataxis]
# docs_root = "docs"
# sections = ["tutorials", "how-to", "explanation", "reference"]
"""


@dataclass(frozen=True)
class DiataxisConfig:
    docs_root: str = "docs"
    sections: tuple[str, ...] = ("tutorials", "how-to", "explanation", "reference")


@dataclass(frozen=True)
class NoteTypeConfig:
    name: str
    mode: str
    template: str
    filename: str
    toc_keys: tuple[str, ...] = ()
    toc_groupby: str | None = None


@dataclass(frozen=True)
class Config:
    root: Path
    notes_root: Path
    template_root: Path
    note_types: dict[str, NoteTypeConfig]
    diataxis: DiataxisConfig


def _default_mapping() -> dict:
    return tomllib.loads(DEFAULT_CONFIG_TEXT)


def _load_pyproject(path: Path) -> dict | None:
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data.get("tool", {}).get("notio")


def _load_notio_toml(path: Path) -> dict | None:
    config_path = path / "notio.toml"
    if not config_path.exists():
        return None
    return tomllib.loads(config_path.read_text(encoding="utf-8"))


def load_config(
    root: Path,
    *,
    template_root: str | Path | None = None,
) -> Config:
    """Load notio configuration.

    *template_root* overrides the default template directory.  When called
    from ``projio add notio`` this is typically ``.projio/notio/templates``.
    """
    raw = _default_mapping()
    loaded = _load_notio_toml(root)
    if loaded is None:
        loaded = _load_pyproject(root)
    if loaded is not None:
        raw.update({k: v for k, v in loaded.items() if k != "types"})
        raw_types = dict(raw.get("types", {}))
        raw_types.update(loaded.get("types", {}))
        raw["types"] = raw_types

    notes_root = root / raw["notes_root"]
    if template_root is not None:
        _tpl = Path(template_root)
        template_root_resolved = _tpl if _tpl.is_absolute() else root / _tpl
    else:
        template_root_resolved = root / raw["template_root"]
    note_types = {
        name: NoteTypeConfig(
            name=name,
            mode=entry["mode"],
            template=entry["template"],
            filename=entry["filename"],
            toc_keys=tuple(entry.get("toc_keys", [])),
            toc_groupby=entry.get("toc_groupby"),
        )
        for name, entry in raw["types"].items()
    }
    raw_dx = raw.get("diataxis", {})
    diataxis = DiataxisConfig(
        docs_root=raw_dx.get("docs_root", "docs"),
        sections=tuple(raw_dx.get("sections", ["tutorials", "how-to", "explanation", "reference"])),
    )

    return Config(
        root=root,
        notes_root=notes_root,
        template_root=template_root_resolved,
        note_types=note_types,
        diataxis=diataxis,
    )

