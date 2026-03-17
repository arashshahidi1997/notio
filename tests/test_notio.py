from __future__ import annotations

from pathlib import Path

import pytest

from notio.config import Config, DiataxisConfig, NoteTypeConfig, load_config
from notio.core import (
    build_root_index,
    build_type_index,
    create_note,
    init_workspace,
    parse_frontmatter,
    render_template,
)
from notio.diataxis import diataxis_add, diataxis_init, diataxis_toc
from notio.query import latest_note, list_notes, read_note


# ---- import -------------------------------------------------------------------


def test_import() -> None:
    import notio

    assert notio.__name__ == "notio"


# ---- config -------------------------------------------------------------------


def test_load_default_config(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.root == tmp_path
    assert config.notes_root == tmp_path / "docs" / "log"
    assert config.template_root == tmp_path / ".projio" / "notio" / "templates"
    assert "daily" in config.note_types
    assert "weekly" in config.note_types
    assert config.note_types["daily"].mode == "period"
    assert config.note_types["meeting"].mode == "event"


def test_load_custom_config(tmp_path: Path) -> None:
    (tmp_path / "notio.toml").write_text(
        """
version = 1
notes_root = "notes"
template_root = "tmpl"

[types.standup]
mode = "event"
template = "standup.md"
filename = "standup-{timestamp}.md"
""",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.notes_root == tmp_path / "notes"
    assert config.template_root == tmp_path / "tmpl"
    assert "standup" in config.note_types


def test_diataxis_config_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.diataxis.docs_root == "docs"
    assert config.diataxis.sections == ("tutorials", "how-to", "explanation", "reference")


def test_diataxis_config_custom(tmp_path: Path) -> None:
    (tmp_path / "notio.toml").write_text(
        """
version = 1
notes_root = "docs/log"
template_root = ".projio/notio/templates"

[diataxis]
docs_root = "documentation"
sections = ["tutorials", "reference"]
""",
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    assert config.diataxis.docs_root == "documentation"
    assert config.diataxis.sections == ("tutorials", "reference")


# ---- core: template rendering -------------------------------------------------


def test_render_template() -> None:
    result = render_template("Hello $name, today is $date", {"name": "world", "date": "2026-01-01"})
    assert result == "Hello world, today is 2026-01-01"


def test_render_template_safe_substitute() -> None:
    result = render_template("$present and $missing", {"present": "yes"})
    assert "$missing" in result
    assert "yes" in result


# ---- core: frontmatter ---------------------------------------------------------


def test_parse_frontmatter() -> None:
    text = "---\ntitle: Hello World\ndate: 2026-01-01\n---\n\n# Content"
    meta = parse_frontmatter(text)
    assert meta["title"] == "Hello World"
    assert meta["date"] == "2026-01-01"


def test_parse_frontmatter_empty() -> None:
    assert parse_frontmatter("no frontmatter here") == {}


def test_parse_frontmatter_list() -> None:
    text = '---\ntags: ["a", "b"]\n---\n'
    meta = parse_frontmatter(text)
    assert meta["tags"] == ["a", "b"]


# ---- core: workspace -----------------------------------------------------------


def test_init_workspace(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    created = init_workspace(config)
    assert any("templates" in str(p) for p in created)
    assert (tmp_path / "docs" / "log" / "index.md").exists()
    assert (tmp_path / "docs" / "log" / "daily" / "index.md").exists()
    assert (tmp_path / ".projio" / "notio" / "templates" / "daily.md").exists()


def test_init_workspace_idempotent(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    init_workspace(config)
    assert (tmp_path / "docs" / "log" / "index.md").exists()


# ---- core: note creation -------------------------------------------------------


def test_create_period_note(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    path = create_note(config, "daily", owner="tester", note_date="2026-03-01")
    assert path.exists()
    assert "daily-tester-2026-03-01.md" == path.name
    content = path.read_text(encoding="utf-8")
    assert "2026-03-01" in content


def test_create_event_note(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    path = create_note(config, "meeting", owner="tester", title="Sync")
    assert path.exists()
    assert path.name.startswith("meeting-tester-")
    content = path.read_text(encoding="utf-8")
    assert "Sync" in content


def test_event_note_no_overwrite(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    path = create_note(config, "idea", owner="tester", timestamp="20260301-120000-000000")
    assert path.exists()
    with pytest.raises(FileExistsError):
        create_note(config, "idea", owner="tester", timestamp="20260301-120000-000000")


def test_period_note_overwrite(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    path1 = create_note(config, "daily", owner="tester", note_date="2026-03-01")
    path2 = create_note(config, "daily", owner="tester", note_date="2026-03-01")
    assert path1 == path2


# ---- core: indexes --------------------------------------------------------------


def test_build_type_index(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    create_note(config, "idea", owner="tester", title="Alpha")
    create_note(config, "idea", owner="tester", title="Beta")
    index = build_type_index(config, "idea")
    content = index.read_text(encoding="utf-8")
    # idea has toc_keys=["title"], so titles appear in the index
    assert "Alpha" in content
    assert "Beta" in content


def test_build_root_index(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    index = build_root_index(config)
    content = index.read_text(encoding="utf-8")
    assert "daily" in content.lower()
    assert "meeting" in content.lower()


# ---- diataxis: init -------------------------------------------------------------


def test_diataxis_init(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    created, snippet = diataxis_init(config)
    assert any(str(p).endswith("tutorials") for p in created)
    assert (tmp_path / "docs" / "tutorials" / "index.md").exists()
    assert (tmp_path / "docs" / "how-to" / "index.md").exists()
    assert (tmp_path / "docs" / "explanation" / "index.md").exists()
    assert (tmp_path / "docs" / "reference" / "index.md").exists()
    assert (tmp_path / "docs" / "index.md").exists()
    assert snippet is None


def test_diataxis_init_mkdocs(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    _, snippet = diataxis_init(config, mkdocs=True)
    assert snippet is not None
    assert "Tutorials" in snippet
    assert "tutorials/index.md" in snippet


def test_diataxis_init_idempotent(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    created2, _ = diataxis_init(config)
    # Dirs are returned but indexes are not re-created
    assert not any(str(p).endswith("index.md") for p in created2)


# ---- diataxis: add --------------------------------------------------------------


def test_diataxis_add(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    path = diataxis_add(config, "tutorials", "quickstart", title="Getting Started")
    assert path.exists()
    assert path.name == "quickstart.md"
    content = path.read_text(encoding="utf-8")
    assert "Getting Started" in content
    assert "What you will learn" in content


def test_diataxis_add_alias(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    path = diataxis_add(config, "ref", "api")
    assert path.parent.name == "reference"
    content = path.read_text(encoding="utf-8")
    assert "Synopsis" in content


def test_diataxis_add_default_title(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    path = diataxis_add(config, "how-to", "deploy-to-prod")
    content = path.read_text(encoding="utf-8")
    assert "Deploy To Prod" in content


def test_diataxis_add_no_overwrite(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    diataxis_add(config, "tutorials", "intro")
    with pytest.raises(FileExistsError):
        diataxis_add(config, "tutorials", "intro")


def test_diataxis_add_bad_section(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    with pytest.raises(ValueError, match="Unknown section"):
        diataxis_add(config, "nonexistent", "page")


def test_diataxis_add_updates_index(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    diataxis_add(config, "tutorials", "first", title="First Page")
    index = (tmp_path / "docs" / "tutorials" / "index.md").read_text(encoding="utf-8")
    assert "First Page" in index
    assert "first.md" in index


# ---- diataxis: toc ---------------------------------------------------------------


def test_diataxis_toc_all(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    diataxis_add(config, "tutorials", "a", title="Page A")
    diataxis_add(config, "reference", "b", title="Page B")
    paths = diataxis_toc(config)
    assert len(paths) == 5  # 4 sections + root
    tut_index = (tmp_path / "docs" / "tutorials" / "index.md").read_text(encoding="utf-8")
    assert "Page A" in tut_index


def test_diataxis_toc_single(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    diataxis_init(config)
    diataxis_add(config, "tutorials", "x", title="X")
    paths = diataxis_toc(config, "tutorials")
    assert len(paths) == 1
    content = paths[0].read_text(encoding="utf-8")
    assert "X" in content


# ---- CLI -----------------------------------------------------------------------


def test_cli_help() -> None:
    from notio.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_init(tmp_path: Path) -> None:
    from notio.cli import main

    rc = main(["--root", str(tmp_path), "init"])
    assert rc == 0
    assert (tmp_path / "docs" / "log" / "index.md").exists()


def test_cli_diataxis_init(tmp_path: Path) -> None:
    from notio.cli import main

    rc = main(["--root", str(tmp_path), "diataxis", "init"])
    assert rc == 0
    assert (tmp_path / "docs" / "tutorials" / "index.md").exists()


def test_cli_diataxis_add(tmp_path: Path) -> None:
    from notio.cli import main

    main(["--root", str(tmp_path), "diataxis", "init"])
    rc = main(["--root", str(tmp_path), "diataxis", "add", "tutorial", "intro", "--title", "Intro"])
    assert rc == 0
    assert (tmp_path / "docs" / "tutorials" / "intro.md").exists()


def test_cli_diataxis_toc(tmp_path: Path) -> None:
    from notio.cli import main

    main(["--root", str(tmp_path), "diataxis", "init"])
    rc = main(["--root", str(tmp_path), "diataxis", "toc", "--all"])
    assert rc == 0


# ---- query -------------------------------------------------------------------


def test_list_notes_all(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    create_note(config, "meeting", owner="tester", title="Alpha")
    create_note(config, "idea", owner="tester", title="Beta")
    notes = list_notes(tmp_path)
    assert len(notes) == 2
    types = {n["type"] for n in notes}
    assert types == {"meeting", "idea"}


def test_list_notes_by_type(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    create_note(config, "meeting", owner="tester", title="Alpha")
    create_note(config, "idea", owner="tester", title="Beta")
    notes = list_notes(tmp_path, note_type="idea")
    assert len(notes) == 1
    assert notes[0]["type"] == "idea"
    assert notes[0]["title"] == "Beta"


def test_list_notes_limit(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    create_note(config, "idea", owner="tester", title="One")
    create_note(config, "idea", owner="tester", title="Two")
    create_note(config, "idea", owner="tester", title="Three")
    notes = list_notes(tmp_path, limit=2)
    assert len(notes) == 2


def test_list_notes_empty(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    notes = list_notes(tmp_path)
    assert notes == []


def test_latest_note(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    create_note(config, "idea", owner="tester", title="First")
    create_note(config, "idea", owner="tester", title="Second")
    note = latest_note(tmp_path, note_type="idea")
    assert note is not None
    assert "content" in note
    assert note["type"] == "idea"


def test_latest_note_empty(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    assert latest_note(tmp_path) is None


def test_read_note(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    init_workspace(config)
    path = create_note(config, "meeting", owner="tester", title="Sync")
    rel = str(path.relative_to(tmp_path))
    note = read_note(tmp_path, rel)
    assert note is not None
    assert note["title"] == "Sync"
    assert "content" in note


def test_read_note_missing(tmp_path: Path) -> None:
    assert read_note(tmp_path, "nonexistent.md") is None


def test_top_level_imports() -> None:
    from notio import latest_note as ln, list_notes as lsn, read_note as rn

    assert callable(lsn)
    assert callable(ln)
    assert callable(rn)
