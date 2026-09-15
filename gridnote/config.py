"""Preferências do usuário em %APPDATA%\\GridNote\\config.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "GridNote"
APP_VERSION = "1.0.0"


def _path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


def load() -> dict:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(cfg: dict) -> None:
    try:
        _path().write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
