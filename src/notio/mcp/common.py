"""Shared JSON serialization helpers for notio MCP tools."""
from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Union, cast

JsonValue = Union[
    None,
    bool,
    int,
    float,
    str,
    List["JsonValue"],
    Dict[str, "JsonValue"],
]
JsonDict = Dict[str, JsonValue]


def get_notio_root() -> Path:
    """Return the project root from NOTIO_ROOT env var, defaulting to cwd."""
    raw = os.environ.get("NOTIO_ROOT", ".")
    return Path(raw).expanduser().resolve()


def ensure_json_serializable(value: Any) -> JsonValue:
    """Convert known data structures into JSON-serializable types."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return ensure_json_serializable(asdict(value))
    if isinstance(value, dict):
        return {str(key): ensure_json_serializable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [ensure_json_serializable(item) for item in value]
    raise TypeError(f"Unsupported value for JSON serialization: {value!r}")


def json_dict(payload: Dict[str, Any]) -> JsonDict:
    return cast(JsonDict, ensure_json_serializable(payload))


def _iso_dates(value: Any) -> Any:
    """YAML reads 2026-11-06 as a date; keep it the string JSON would give."""
    import datetime

    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _iso_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_iso_dates(v) for v in value]
    return value


def parse_fields(value: Union[str, Dict[str, Any], None], param: str) -> Dict[str, Any] | None:
    """Parse frontmatter fields given as a dict, a JSON object string or YAML.

    Notes store YAML frontmatter, so agents often pass YAML; a bare
    ``json.loads`` turned that into "Expecting value: line 1 column 1".
    Returns ``None`` for an empty value; raises ``ValueError`` naming *param*
    when the value is not a mapping.
    """
    if value is None or isinstance(value, dict):
        return value or None
    if not isinstance(value, str):
        raise ValueError(f"{param} must be a mapping, got {type(value).__name__}")
    if not value.strip():
        return None
    import json

    import yaml

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        try:
            parsed = _iso_dates(yaml.safe_load(value))
        except yaml.YAMLError as exc:
            raise ValueError(f"{param} is neither a JSON object nor YAML mapping: {exc}") from None
    if not isinstance(parsed, dict):
        raise ValueError(
            f"{param} must be a mapping of fields, e.g. "
            f'\'{{"tags": ["result"], "series": "x"}}\' or "series: x", '
            f"got {type(parsed).__name__}: {value[:80]!r}"
        )
    return parsed
