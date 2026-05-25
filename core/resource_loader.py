"""Lightweight resource loading for public ANA MAX UI surfaces."""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_ROOT = PROJECT_ROOT / "resources"

DEFAULT_TEXTS: dict[str, str] = {
    "dashboard_title": "ANA MAX v20 Autonomy Dashboard",
    "dashboard_intro": "Manual, read-only view of v20 autonomy tool outputs. No writes. No auto-run.",
    "run_tool": "Run tool",
    "stop_tool": "Stop tool",
    "status_ready": "Ready",
    "status_running": "Running",
    "status_error": "Error",
    "status_label": "Status",
}

DEFAULT_THEME: dict[str, str] = {
    "background": "#f7f9fc",
    "text": "#1f2937",
    "muted": "#526071",
    "panel_background": "#ffffff",
    "panel_border": "#d7dee8",
    "status": "#0b6bcb",
    "pre_background": "#eef2f7",
}

_texts_cache: dict[str, dict[str, str]] = {}
_theme_cache: dict[str, dict[str, str]] = {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_language(value: str | None) -> str:
    if not value:
        return "en"
    normalized = value.strip().split(".")[0].split("_")[0].split("-")[0].lower()
    return normalized or "en"


def detect_language() -> str:
    """Return a short language code, defaulting safely to English."""
    for key in ("ANA_LANG", "LANGUAGE", "LANG"):
        value = os.environ.get(key)
        if value:
            return _normalize_language(value)
    try:
        return _normalize_language(locale.getlocale()[0])
    except (ValueError, TypeError):
        return "en"


def load_texts(lang: str | None) -> dict[str, str]:
    """Load localized text with English and built-in fallback values."""
    requested = _normalize_language(lang)
    if requested in _texts_cache:
        return dict(_texts_cache[requested])

    english = DEFAULT_TEXTS | {
        key: str(value)
        for key, value in _read_json(RESOURCES_ROOT / "texts" / "en.json").items()
    }
    selected = english
    if requested != "en":
        localized = {
            key: str(value)
            for key, value in _read_json(
                RESOURCES_ROOT / "texts" / f"{requested}.json"
            ).items()
        }
        selected = english | localized

    _texts_cache[requested] = selected
    return dict(selected)


def t(key: str) -> str:
    """Translate a UI key using the detected language."""
    texts = load_texts(detect_language())
    return texts.get(key, load_texts("en").get(key, key))


def load_theme(name: str | None) -> dict[str, str]:
    """Load a theme by name with a safe light-theme fallback."""
    requested = (name or "light").strip().lower() or "light"
    if requested in _theme_cache:
        return dict(_theme_cache[requested])

    light = DEFAULT_THEME | {
        key: str(value)
        for key, value in _read_json(RESOURCES_ROOT / "themes" / "light.json").items()
    }
    selected = light
    if requested != "light":
        custom = {
            key: str(value)
            for key, value in _read_json(
                RESOURCES_ROOT / "themes" / f"{requested}.json"
            ).items()
        }
        selected = light | custom

    _theme_cache[requested] = selected
    return dict(selected)


def load_icon(name: str) -> str:
    """Return icon text content, or an empty string when unavailable."""
    safe_name = Path(name).name
    if not safe_name:
        return ""
    icon_path = RESOURCES_ROOT / "icons" / safe_name
    try:
        return icon_path.read_text(encoding="utf-8")
    except OSError:
        return ""
