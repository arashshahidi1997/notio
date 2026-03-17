"""LLM integration via Ollama for note enrichment and linking.

Used for:
- Structuring raw transcripts into well-organized note bodies
- Suggesting wikilinks to related notes in the same project

Config: OLLAMA_URL env var, or [tool.notio.ollama] in pyproject.toml / notio.toml.
Falls back gracefully if Ollama is unreachable.

No dependencies beyond urllib (stdlib).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "url": "http://theta:11434",
    "model": "llama3",
    "timeout": 180,
}


@dataclass
class OllamaConfig:
    url: str
    model: str
    timeout: int

    @property
    def generate_url(self) -> str:
        return f"{self.url.rstrip('/')}/api/generate"


def load_config(
    root: Optional[Path] = None,
) -> OllamaConfig:
    """Load Ollama config from env → notio.toml → pyproject.toml → defaults."""
    url = os.environ.get("OLLAMA_URL")
    model = None
    timeout = None

    # Try notio.toml
    if root:
        cfg = _load_from_toml(root / "notio.toml") or _load_from_pyproject(root / "pyproject.toml")
        if cfg:
            url = url or cfg.get("url")
            model = cfg.get("model")
            timeout = cfg.get("timeout")

    return OllamaConfig(
        url=url or _DEFAULTS["url"],
        model=model or _DEFAULTS["model"],
        timeout=int(timeout or _DEFAULTS["timeout"]),
    )


def _load_from_toml(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return data.get("ollama")
    except Exception:
        return None


def _load_from_pyproject(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return data.get("tool", {}).get("notio", {}).get("ollama")
    except Exception:
        return None


def _call_ollama(config: OllamaConfig, prompt: str, max_tokens: int = 512) -> Optional[str]:
    """Send a prompt to Ollama and return the response, or None on failure."""
    payload = json.dumps({
        "model": config.model,
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
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            body = json.loads(resp.read())
        return body.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Ollama call failed: %s", exc)
        return None


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
    config: Optional[OllamaConfig] = None,
) -> Optional[str]:
    """Use LLM to structure a transcript into a well-organized note body.

    Returns the structured markdown body, or None if LLM is unavailable.
    """
    if config is None:
        config = load_config()

    prompt_template = _ENRICH_PROMPTS.get(kind, _ENRICH_PROMPTS["idea"])
    prompt = prompt_template.format(transcript=transcript, title=title)

    raw = _call_ollama(config, prompt, max_tokens=1024)
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
    config: Optional[OllamaConfig] = None,
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

Return ONLY a JSON object:
{{"links": [{{"target": "<filename.md>", "reason": "<brief reason for linking>"}}]}}

Only suggest links where there is a genuine topical connection. Return an empty list if nothing is related. Maximum 5 links."""

    raw = _call_ollama(config, prompt, max_tokens=512)
    if raw is None:
        return None

    result = _parse_json_response(raw)
    if result is None:
        return None

    return result.get("links", [])


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------

def available(config: Optional[OllamaConfig] = None) -> bool:
    """Check if Ollama is reachable."""
    if config is None:
        config = load_config()
    try:
        url = f"{config.url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def warmup(config: Optional[OllamaConfig] = None) -> bool:
    """Pre-load the model into memory. Returns True on success."""
    if config is None:
        config = load_config()
    payload = json.dumps({
        "model": config.model,
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
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
