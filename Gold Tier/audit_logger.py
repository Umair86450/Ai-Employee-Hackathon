"""Structured audit logging helpers for Gold Tier workflows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def json_safe(value: Any) -> Any:
    """Convert arbitrary values into JSON-safe data."""
    return json.loads(json.dumps(value, default=str))


def _json_log_path(logs_dir: Path, *, now: datetime | None = None) -> Path:
    current = now or datetime.now()
    return logs_dir / f"{current.strftime('%Y-%m-%d')}.json"


def append_json_log(logs_dir: Path, entry: dict[str, Any], *, now: datetime | None = None) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = _json_log_path(logs_dir, now=now)

    payload: list[dict[str, Any]]
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = raw if isinstance(raw, list) else []
        except Exception:
            payload = []
    else:
        payload = []

    item = dict(entry)
    item.setdefault("timestamp", (now or datetime.now()).isoformat())
    payload.append(json_safe(item))
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return path
