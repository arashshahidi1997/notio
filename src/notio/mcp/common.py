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
