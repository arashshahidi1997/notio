#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List


FRONT_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str, yaml_keys: List[str]) -> dict[str, str]:
    m = FRONT_RE.match(text)
    meta = {k: "" for k in yaml_keys}
    if not m:
        return meta
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key in meta:
            meta[key] = value
    return meta


def build_index(folder: Path, prefix: str, yaml_keys: List[str] | None, groupby: str | None) -> None:
    files = sorted(
        [p for p in folder.iterdir() if p.is_file() and p.name.startswith(prefix) and p.name != "index.md"],
        reverse=True,
    )

    if groupby is not None:
        assert yaml_keys is not None, "yaml_keys must be provided if groupby is used"
        assert groupby in yaml_keys, f"groupby='{groupby}' must be in yaml_keys={yaml_keys}"

    entries = []
    for f in files:
        if yaml_keys is not None:
            meta = parse_frontmatter(f.read_text(encoding="utf-8"), yaml_keys)
            extras = " ".join(f"{k}:{meta[k]}" for k in yaml_keys if meta.get(k, ""))
            label = f"{f.stem} {extras}".rstrip()
            entries.append((f, meta, label))
        else:
            entries.append((f, {}, f.stem))

    out: list[str] = [f"# {folder.name.capitalize()}", ""]

    if groupby is None:
        out.append("## Contents\n")
        for f, meta, label in entries:
            out.append(f"- [{label}]({f.name})")
    else:
        groups: Dict[str, List[tuple]] = {}
        for f, meta, label in entries:
            keyval = meta.get(groupby, "") or "unset"
            groups.setdefault(keyval, []).append((f, meta, label))

        for keyval in sorted(groups.keys()):
            out.append(f"## {groupby}: {keyval}\n")
            for f, meta, label in groups[keyval]:
                out.append(f"- [{label}]({f.name})")
            out.append("")

    out.append("")
    (folder / "index.md").write_text("\n".join(out), encoding="utf-8")
    print(f"Updated {folder}/index.md")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: toc-index.py <folder> <prefix> [yaml_key ...] [groupby=<key>]")
        return 2

    folder = Path(argv[1])
    prefix = argv[2]

    if len(argv) < 4:
        build_index(folder, prefix, yaml_keys=None, groupby=None)
        return 0

    yaml_keys = argv[3:]
    groupby = None
    if yaml_keys and yaml_keys[-1].startswith("groupby="):
        groupby = yaml_keys.pop().split("=", 1)[1]

    build_index(folder, prefix, yaml_keys=yaml_keys, groupby=groupby)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

