"""Remote platform integration — promote, capture, pull for GitHub/GitLab issues.

Uses ``gh`` / ``glab`` CLI tools for API access.  No separate token management.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notio.config import load_config
from notio.core import parse_frontmatter, FRONTMATTER_RE
from notio.query import update_note_frontmatter

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

REMOTE_RE = re.compile(r"^(github|gitlab)#(\d+)$")

THREAD_START = "<!-- notio:remote-thread {remote} -->"
THREAD_END = "<!-- /notio:remote-thread -->"


@dataclass
class PlatformInfo:
    platform: str          # "github" or "gitlab"
    owner_repo: str        # "user/repo"
    cli: str               # "gh" or "glab"
    host: str = ""         # e.g. "gitlab.lrz.de" (empty = default: github.com / gitlab.com)


def detect_platform(root: Path) -> PlatformInfo | None:
    """Detect platform from git remotes.

    Checks all remotes (not just origin) for GitHub/GitLab URLs.  Prefers a
    remote named ``github`` or ``gitlab`` if present, then falls back to any
    remote whose URL matches.
    """
    try:
        result = subprocess.run(
            ["git", "remote"],
            capture_output=True, text=True, cwd=root,
        )
        remotes = result.stdout.strip().splitlines()
    except Exception:
        return None
    if not remotes:
        return None

    # Collect all remote URLs
    remote_urls: list[tuple[str, str]] = []
    for name in remotes:
        try:
            r = subprocess.run(
                ["git", "remote", "get-url", name],
                capture_output=True, text=True, cwd=root,
            )
            url = r.stdout.strip()
            if url:
                remote_urls.append((name, url))
        except Exception:
            continue

    # Prefer remotes named "github" or "gitlab", then any matching URL
    def _priority(item: tuple[str, str]) -> int:
        name, url = item
        if name in ("github", "gitlab"):
            return 0
        if "github" in url or "gitlab" in url:
            return 1
        return 2

    remote_urls.sort(key=_priority)

    for _name, url in remote_urls:
        repo_match = re.search(r"[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
        if not repo_match:
            continue
        owner_repo = repo_match.group(1)

        # Extract host from SSH (git@host:...) or HTTPS (https://host/...)
        host_match = re.match(r"(?:https?://|git@)([^/:]+)", url)
        host = host_match.group(1) if host_match else ""

        if "github" in url or _name == "github":
            return PlatformInfo("github", owner_repo, "gh", host)
        if "gitlab" in url or _name == "gitlab":
            return PlatformInfo("gitlab", owner_repo, "glab", host)

    return None


def _parse_remote(remote: str) -> tuple[str, str] | None:
    """Parse ``github#42`` into ``("github", "42")``."""
    m = REMOTE_RE.match(remote.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def _issue_url(platform: PlatformInfo, number: str) -> str:
    if platform.platform == "github":
        host = platform.host or "github.com"
        return f"https://{host}/{platform.owner_repo}/issues/{number}"
    host = platform.host or "gitlab.com"
    return f"https://{host}/{platform.owner_repo}/-/issues/{number}"


# ---------------------------------------------------------------------------
# Promote: note -> platform issue
# ---------------------------------------------------------------------------


def promote(
    root: Path,
    note_path: str,
    *,
    labels: list[str] | None = None,
    assignee: str = "",
    milestone: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Promote a local note to a platform issue.

    Returns dict with ``remote``, ``url``, ``note_path`` on success.
    """
    root = Path(root).resolve()
    full_path = root / note_path
    if not full_path.is_file():
        raise FileNotFoundError(f"Note not found: {note_path}")

    text = full_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)

    if meta.get("remote"):
        raise ValueError(f"Note already linked to {meta['remote']}")

    platform = detect_platform(root)
    if not platform:
        raise RuntimeError("Cannot detect platform from git remote origin")

    title = str(meta.get("title", full_path.stem)).strip().strip('"')
    title = re.sub(r"^#+\s*", "", title).strip()

    # Build body from note content (strip frontmatter)
    fm_match = FRONTMATTER_RE.match(text)
    body = text[fm_match.end():].strip() if fm_match else text.strip()
    body += f"\n\n---\n_Tracked in repo: `{note_path}`_"

    # Resolve labels from note tags if not overridden
    if labels is None:
        tags = meta.get("tags", [])
        if isinstance(tags, list):
            labels = [str(t) for t in tags if str(t) not in (note_path.split("/")[0],)]
        else:
            labels = []

    if dry_run:
        return {
            "dry_run": True,
            "platform": platform.platform,
            "title": title,
            "body_preview": body[:200],
            "labels": labels,
            "assignee": assignee,
            "milestone": milestone,
        }

    # Create issue via CLI
    if platform.platform == "github":
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        if platform.host and platform.host != "github.com":
            cmd.extend(["--repo", f"{platform.host}/{platform.owner_repo}"])
        for label in labels:
            cmd.extend(["--label", label])
        if assignee:
            cmd.extend(["--assignee", assignee])
        if milestone:
            cmd.extend(["--milestone", milestone])
    else:
        cmd = ["glab", "issue", "create", "--title", title, "--description", body]
        if platform.host and platform.host != "gitlab.com":
            cmd.extend(["--repo", f"{platform.owner_repo}"])
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        if assignee:
            cmd.extend(["--assignee", assignee])
        if milestone:
            cmd.extend(["--milestone", milestone])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    if result.returncode != 0:
        raise RuntimeError(f"{platform.cli} failed: {result.stderr.strip()}")

    # Extract issue number from output
    output = result.stdout.strip()
    number_match = re.search(r"/issues/(\d+)", output)
    if not number_match:
        # gh sometimes returns just the URL
        number_match = re.search(r"(\d+)\s*$", output)
    if not number_match:
        raise RuntimeError(f"Could not parse issue number from: {output}")

    number = number_match.group(1)
    remote_ref = f"{platform.platform}#{number}"

    # Write remote field back to note
    update_note_frontmatter(root, note_path, {"remote": remote_ref})

    return {
        "remote": remote_ref,
        "url": _issue_url(platform, number),
        "note_path": note_path,
    }


# ---------------------------------------------------------------------------
# Capture: platform issue -> note
# ---------------------------------------------------------------------------


def capture(
    root: Path,
    remote_ref: str,
    *,
    note_type: str = "issue",
    owner: str = "",
) -> dict[str, Any]:
    """Create a local note from a platform issue.

    Returns dict with ``note_path``, ``remote``, ``title``.
    """
    root = Path(root).resolve()
    parsed = _parse_remote(remote_ref)
    if not parsed:
        raise ValueError(f"Invalid remote reference: {remote_ref}. Expected format: github#42")

    platform_name, number = parsed
    platform = detect_platform(root)
    if not platform:
        raise RuntimeError("Cannot detect platform from git remote origin")

    # Check no existing note links to this remote
    config = load_config(root)
    for name in config.note_types:
        folder = config.notes_root / name
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file() or path.suffix != ".md" or path.name == "index.md":
                continue
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            if str(meta.get("remote", "")).strip() == remote_ref:
                raise ValueError(
                    f"Already captured as {path.relative_to(root)}"
                )

    # Fetch issue via CLI
    if platform.platform == "github":
        result = subprocess.run(
            ["gh", "issue", "view", number, "--json", "title,body,labels"],
            capture_output=True, text=True, cwd=root,
        )
    else:
        result = subprocess.run(
            ["glab", "issue", "view", number, "--output", "json"],
            capture_output=True, text=True, cwd=root,
        )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch {remote_ref}: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    title = data.get("title", f"Issue {number}")
    body = data.get("body") or data.get("description") or ""
    issue_labels = data.get("labels", [])
    tags = [note_type]
    for label in issue_labels:
        label_name = label.get("name", label) if isinstance(label, dict) else str(label)
        if label_name:
            tags.append(label_name)

    # Create note
    from notio.core import create_note

    extra_fm = {"remote": remote_ref, "tags": tags}
    path = create_note(
        config,
        note_type,
        owner=owner or None,
        title=title,
        body=body or None,
        extra_frontmatter=extra_fm,
    )

    # Pull thread into the new note
    _pull_thread_for_note(root, path, platform, number, remote_ref)

    return {
        "note_path": str(path.relative_to(root)),
        "remote": remote_ref,
        "title": title,
    }


# ---------------------------------------------------------------------------
# Pull: fetch remote thread -> note
# ---------------------------------------------------------------------------


def _fetch_comments(platform: PlatformInfo, number: str, cwd: Path) -> list[dict[str, str]]:
    """Fetch comments from a platform issue. Returns list of {author, date, body}."""
    if platform.platform == "github":
        result = subprocess.run(
            ["gh", "issue", "view", number, "--json", "comments"],
            capture_output=True, text=True, cwd=cwd,
        )
    else:
        result = subprocess.run(
            ["glab", "issue", "note", "list", number, "--output", "json"],
            capture_output=True, text=True, cwd=cwd,
        )

    if result.returncode != 0:
        return []

    data = json.loads(result.stdout)
    comments = []

    if platform.platform == "github":
        for c in data.get("comments", []):
            author = c.get("author", {}).get("login", "unknown")
            created = c.get("createdAt", "")[:10]
            body = c.get("body", "").strip()
            if body:
                comments.append({"author": author, "date": created, "body": body})
    else:
        entries = data if isinstance(data, list) else data.get("notes", [])
        for c in entries:
            author = c.get("author", {}).get("username", "unknown")
            created = str(c.get("created_at", ""))[:10]
            body = c.get("body", "").strip()
            if body:
                comments.append({"author": author, "date": created, "body": body})

    return comments


def _render_thread(comments: list[dict[str, str]], remote_ref: str) -> str:
    """Render comments into the markdown thread section."""
    lines = [THREAD_START.format(remote=remote_ref), ""]
    for c in comments:
        # Indent multi-line comment bodies under the blockquote
        body_lines = c["body"].splitlines()
        lines.append(f"> **@{c['author']}** ({c['date']}):")
        for bl in body_lines:
            lines.append(f"> {bl}")
        lines.append("")
    lines.append(THREAD_END)
    return "\n".join(lines)


def _pull_thread_for_note(
    root: Path,
    note_path: Path,
    platform: PlatformInfo,
    number: str,
    remote_ref: str,
) -> int:
    """Fetch and write thread for a single note. Returns comment count."""
    comments = _fetch_comments(platform, number, cwd=root)

    text = note_path.read_text(encoding="utf-8")

    thread_section = _render_thread(comments, remote_ref)

    # Replace existing thread section or append
    start_marker = THREAD_START.format(remote=remote_ref)
    if start_marker in text:
        # Replace between markers
        pattern = re.escape(start_marker) + r".*?" + re.escape(THREAD_END)
        text = re.sub(pattern, thread_section, text, flags=re.DOTALL)
    else:
        # Append new section
        text = text.rstrip() + "\n\n## Remote Thread\n\n" + thread_section + "\n"

    note_path.write_text(text, encoding="utf-8")
    return len(comments)


def pull(
    root: Path,
    *,
    note_path: str = "",
    note_type: str = "",
    all_notes: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fetch remote thread updates for linked notes.

    Exactly one of ``note_path``, ``note_type``, or ``all_notes`` must be given.
    """
    root = Path(root).resolve()
    platform = detect_platform(root)
    if not platform:
        raise RuntimeError("Cannot detect platform from git remote origin")

    config = load_config(root)

    # Collect notes to pull
    targets: list[tuple[Path, str, str, str]] = []  # (full_path, rel_path, platform, number)

    if note_path:
        full = root / note_path
        if not full.is_file():
            raise FileNotFoundError(f"Note not found: {note_path}")
        meta = parse_frontmatter(full.read_text(encoding="utf-8"))
        remote = str(meta.get("remote", "")).strip()
        parsed = _parse_remote(remote)
        if not parsed:
            raise ValueError(f"Note has no valid remote field: {note_path}")
        targets.append((full, note_path, parsed[0], parsed[1]))
    else:
        types_to_scan = (
            {note_type: config.note_types[note_type]}
            if note_type and note_type in config.note_types
            else config.note_types
        ) if (note_type or all_notes) else {}

        if not types_to_scan:
            raise ValueError("Specify --path, --type, or --all")

        for name in types_to_scan:
            folder = config.notes_root / name
            if not folder.is_dir():
                continue
            for path in folder.iterdir():
                if not path.is_file() or path.suffix != ".md" or path.name == "index.md":
                    continue
                meta = parse_frontmatter(path.read_text(encoding="utf-8"))
                remote = str(meta.get("remote", "")).strip()
                parsed = _parse_remote(remote)
                if parsed:
                    targets.append((path, str(path.relative_to(root)), parsed[0], parsed[1]))

    if dry_run:
        return {
            "dry_run": True,
            "notes": [{"path": rel, "remote": f"{p}#{n}"} for _, rel, p, n in targets],
            "count": len(targets),
        }

    total_comments = 0
    updated: list[dict[str, Any]] = []
    for full_path, rel_path, _platform, number in targets:
        count = _pull_thread_for_note(root, full_path, platform, number, f"{_platform}#{number}")
        total_comments += count
        updated.append({"path": rel_path, "remote": f"{_platform}#{number}", "comments": count})

    return {
        "updated": updated,
        "notes_count": len(updated),
        "total_comments": total_comments,
    }


# ---------------------------------------------------------------------------
# Remote status
# ---------------------------------------------------------------------------


def remote_status(root: Path) -> dict[str, Any]:
    """List all notes with remote links and their status."""
    root = Path(root).resolve()
    config = load_config(root)

    entries: list[dict[str, Any]] = []
    for name in sorted(config.note_types):
        folder = config.notes_root / name
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir(), reverse=True):
            if not path.is_file() or path.suffix != ".md" or path.name == "index.md":
                continue
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            remote = str(meta.get("remote", "")).strip()
            if not remote:
                continue
            entries.append({
                "type": name,
                "path": str(path.relative_to(root)),
                "remote": remote,
                "title": str(meta.get("title", path.stem)).strip().strip('"'),
                "status": str(meta.get("status", "")),
            })

    return {"notes": entries, "count": len(entries)}
