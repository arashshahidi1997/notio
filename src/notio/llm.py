"""LLM integration for note enrichment and linking.

Used for:
- Structuring raw transcripts into well-organized note bodies
- Suggesting wikilinks to related notes in the same project

Backends:
- **claude** (default): Uses ``claude -p`` CLI with OAuth auth.
- **ollama**: Local Ollama server, configured via OLLAMA_URL env var
  or ``[tool.notio.ollama]`` in notio.toml / pyproject.toml.

Config: ``[tool.notio.llm]`` in notio.toml / pyproject.toml sets ``backend``.
Falls back gracefully if the chosen backend is unreachable.

No dependencies beyond stdlib (urllib, subprocess).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_OLLAMA_DEFAULTS = {
    "url": "http://theta:11434",
    "model": "llama3",
    "timeout": 180,
}

_CLAUDE_DEFAULTS = {
    "model": "sonnet",
    "timeout": 120,
}


@dataclass
class LLMConfig:
    """Unified LLM configuration supporting multiple backends."""
    backend: str = "claude"  # "claude" or "ollama"
    # Ollama settings
    ollama_url: str = _OLLAMA_DEFAULTS["url"]
    ollama_model: str = _OLLAMA_DEFAULTS["model"]
    ollama_timeout: int = _OLLAMA_DEFAULTS["timeout"]
    # Claude settings
    claude_model: str = _CLAUDE_DEFAULTS["model"]
    claude_timeout: int = _CLAUDE_DEFAULTS["timeout"]

    @property
    def generate_url(self) -> str:
        """Ollama generate endpoint (kept for backwards compat)."""
        return f"{self.ollama_url.rstrip('/')}/api/generate"


# Backwards-compatible alias
OllamaConfig = LLMConfig


def load_config(
    root: Optional[Path] = None,
) -> LLMConfig:
    """Load LLM config from env → notio.toml → pyproject.toml → defaults."""
    backend = os.environ.get("NOTIO_LLM_BACKEND")
    ollama_url = os.environ.get("OLLAMA_URL")
    ollama_model = None
    ollama_timeout = None
    claude_model = None
    claude_timeout = None

    if root:
        # New unified [llm] section
        llm_cfg = _load_section(root, "llm")
        if llm_cfg:
            backend = backend or llm_cfg.get("backend")
            claude_model = llm_cfg.get("claude_model")
            claude_timeout = llm_cfg.get("claude_timeout")
        # Legacy [ollama] section
        ollama_cfg = _load_section(root, "ollama")
        if ollama_cfg:
            ollama_url = ollama_url or ollama_cfg.get("url")
            ollama_model = ollama_cfg.get("model")
            ollama_timeout = ollama_cfg.get("timeout")

    return LLMConfig(
        backend=backend or "claude",
        ollama_url=ollama_url or _OLLAMA_DEFAULTS["url"],
        ollama_model=ollama_model or _OLLAMA_DEFAULTS["model"],
        ollama_timeout=int(ollama_timeout or _OLLAMA_DEFAULTS["timeout"]),
        claude_model=claude_model or _CLAUDE_DEFAULTS["model"],
        claude_timeout=int(claude_timeout or _CLAUDE_DEFAULTS["timeout"]),
    )


def _load_section(root: Path, section: str) -> Optional[Dict[str, Any]]:
    """Load a [tool.notio.<section>] from notio.toml or pyproject.toml."""
    cfg = _load_from_toml(root / "notio.toml", section)
    if cfg:
        return cfg
    return _load_from_pyproject(root / "pyproject.toml", section)


def _load_from_toml(path: Path, section: str = "ollama") -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return data.get(section)
    except Exception:
        return None


def _load_from_pyproject(path: Path, section: str = "ollama") -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return data.get("tool", {}).get("notio", {}).get(section)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Backend: Claude CLI (``claude -p``)
# ---------------------------------------------------------------------------

def _call_claude(config: LLMConfig, prompt: str, max_tokens: int = 1024) -> Optional[str]:
    """Call ``claude -p`` (print mode) and return the response, or None on failure."""
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        logger.warning("claude CLI not found on PATH")
        return None

    cmd = [claude_bin, "-p", "--model", config.claude_model, "--max-turns", "1"]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=config.claude_timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        logger.warning("claude CLI returned %d: %s", result.returncode, result.stderr[:200])
        return None
    except subprocess.TimeoutExpired:
        logger.warning("claude CLI timed out after %ds", config.claude_timeout)
        return None
    except (OSError, FileNotFoundError) as exc:
        logger.warning("claude CLI call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Backend: Ollama
# ---------------------------------------------------------------------------

def _call_ollama(config: LLMConfig, prompt: str, max_tokens: int = 512) -> Optional[str]:
    """Send a prompt to Ollama and return the response, or None on failure."""
    payload = json.dumps({
        "model": config.ollama_model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "num_predict": max_tokens},
    }).encode()

    req = urllib.request.Request(
        config.generate_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=config.ollama_timeout) as resp:
            body = json.loads(resp.read())
        return body.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Ollama call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Unified dispatch
# ---------------------------------------------------------------------------

def _call_llm(config: LLMConfig, prompt: str, max_tokens: int = 1024) -> Optional[str]:
    """Dispatch to the configured backend."""
    if config.backend == "ollama":
        return _call_ollama(config, prompt, max_tokens)
    return _call_claude(config, prompt, max_tokens)


def _parse_json_response(raw: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from an LLM response that may include markdown fences."""
    text = raw.strip()
    # Strip markdown fences
    if "```" in text:
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.strip().startswith("```"))
    # Fix triple-quoted strings (common LLM mistake)
    text = text.replace('"""', '"')
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    fragment = text[start:end]
    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        # Try fixing unescaped newlines in string values
        import re
        fixed = re.sub(r'(?<=: ")(.*?)(?="[,}])', lambda m: m.group(0).replace('\n', '\\n'), fragment, flags=re.DOTALL)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None


# ---------------------------------------------------------------------------
# Enrich: structure a note body from raw transcript
# ---------------------------------------------------------------------------

_ENRICH_PROMPTS = {
    "idea": """Convert this transcript into a structured idea note. Output ONLY markdown, no explanation.

Title: {title}

Transcript: {transcript}

Use exactly these sections:

## Overview
(1-2 sentence summary)

## Key Points
(bullet points)

## Possible Next Steps
(bullet points)

## Raw Transcript
(include the full original transcript)""",

    "issue": """Convert this transcript into a structured issue note. Output ONLY markdown, no explanation.

Title: {title}

Transcript: {transcript}

Use exactly these sections:

## Problem
(clear statement of the issue)

## Context
(relevant background)

## Possible Causes
(bullet points)

## Suggested Actions
(bullet points)

## Raw Transcript
(include the full original transcript)""",

    "task": """Convert this note into a structured task with an agent-executable prompt. Output ONLY markdown, no explanation.

Title: {title}

Source content: {transcript}

Use exactly these sections:

## Goal
(1-2 sentence description of what needs to be accomplished)

## Context
(relevant background — what exists, what was tried, why this matters)

## Prompt
> (A clear, self-contained instruction that an AI agent could execute in the project directory. Be specific about what to do, not how to think about it.)

## Acceptance Criteria
- [ ] (concrete, verifiable conditions for success)

## Result
(leave empty — filled after execution)""",

    "meeting": """Convert this transcript into structured meeting notes. Output ONLY markdown, no explanation.

Title: {title}

Transcript: {transcript}

Use exactly these sections:

## Summary
(2-3 sentence summary)

## Discussion Points
(bullet points)

## Decisions
(bullet points, or "None" if unclear)

## Action Items
- [ ] (checklist items)

## Raw Transcript
(include the full original transcript)""",
}


def enrich_body(
    transcript: str,
    title: str,
    kind: str,
    config: Optional[LLMConfig] = None,
) -> Optional[str]:
    """Use LLM to structure a transcript into a well-organized note body.

    Returns the structured markdown body, or None if LLM is unavailable.
    """
    if config is None:
        config = load_config()

    prompt_template = _ENRICH_PROMPTS.get(kind, _ENRICH_PROMPTS["idea"])
    prompt = prompt_template.format(transcript=transcript, title=title)

    raw = _call_llm(config, prompt, max_tokens=1024)
    if raw is None:
        return None

    # The prompt asks for markdown directly — strip any preamble before first ##
    body = _extract_markdown(raw)
    if body:
        return body

    logger.warning("LLM returned no usable markdown: %s", raw[:200])
    return None


def _extract_markdown(raw: str) -> Optional[str]:
    """Extract markdown body from LLM response, stripping preamble."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()

    # Find the first ## heading
    idx = text.find("\n## ")
    if idx < 0:
        idx = text.find("## ")
        if idx == 0:
            return text
        if idx < 0:
            return text if text.startswith("#") else None

    # Include content from first ## onward
    return text[idx:].lstrip("\n")


# ---------------------------------------------------------------------------
# Links: suggest wikilinks to related notes
# ---------------------------------------------------------------------------

def suggest_links(
    note_path: Path,
    note_content: str,
    sibling_notes: List[Dict[str, Any]],
    config: Optional[LLMConfig] = None,
) -> Optional[List[Dict[str, str]]]:
    """Suggest wikilinks from this note to related sibling notes.

    Returns a list of {"target": "<filename>", "reason": "<why>"} dicts,
    or None if LLM is unavailable.
    """
    if config is None:
        config = load_config()

    if not sibling_notes:
        return []

    siblings_desc = "\n".join(
        f"- {n['path']}: {n.get('title', '(untitled)')}"
        for n in sibling_notes[:30]  # limit context size
    )

    prompt = f"""You are a note linking assistant. Given a note and a list of other notes in the same project, suggest which notes are related and should be linked.

Current note:
\"\"\"{note_content[:2000]}\"\"\"

Other notes in this project:
{siblings_desc}

Return ONLY a JSON object with targets as exact filenames (with .md extension):
{{"links": [{{"target": "issue-arash-20260211-143022-123456.md", "reason": "<brief reason for linking>"}}]}}

Only suggest links where there is a genuine topical connection. Return an empty list if nothing is related. Maximum 5 links."""

    raw = _call_llm(config, prompt, max_tokens=512)
    if raw is None:
        return None

    result = _parse_json_response(raw)
    if result is None:
        return None

    links = result.get("links", [])
    # Normalise targets: strip directory prefixes and ensure .md extension
    for link in links:
        target = link.get("target", "")
        # Use only the filename part (strip any path prefix)
        if "/" in target:
            target = target.rsplit("/", 1)[-1]
        # Ensure .md extension
        if not target.endswith(".md"):
            target = target + ".md"
        link["target"] = target
    return links


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------

def available(config: Optional[LLMConfig] = None) -> bool:
    """Check if the configured LLM backend is reachable."""
    if config is None:
        config = load_config()
    if config.backend == "claude":
        return shutil.which("claude") is not None
    # Ollama
    try:
        url = f"{config.ollama_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def warmup(config: Optional[LLMConfig] = None) -> bool:
    """Pre-load the model into memory. Returns True on success (ollama only)."""
    if config is None:
        config = load_config()
    if config.backend == "claude":
        return True  # no warmup needed
    payload = json.dumps({
        "model": config.ollama_model,
        "prompt": "",
        "keep_alive": "30m",
    }).encode()
    req = urllib.request.Request(
        config.generate_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.ollama_timeout) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
