from __future__ import annotations

import os
from pathlib import Path


def dotenv_dict(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def load_project_dotenv(path: str | Path, *, override: bool = False) -> dict[str, str]:
    values = dotenv_dict(path)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values
