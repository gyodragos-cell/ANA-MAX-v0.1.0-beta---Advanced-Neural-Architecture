from __future__ import annotations

import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "ana.os22.desktop_workspace.v1"
DESKTOP_INVENTORY_SCHEMA = "ana.os22.desktop_inventory.v1"
DESKTOP_FOLDER_INSPECTION_SCHEMA = "ana.os22.desktop_folder_inspection.v1"
DESKTOP_TEXT_FILE_SCHEMA = "ana.os22.desktop_text_file.v1"
DESKTOP_WRITE_TEXT_FILE_SCHEMA = "ana.os22.desktop_write_text_file.v1"
TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".css",
    ".csv",
    ".htm",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".log",
    ".md",
    ".php",
    ".ps1",
    ".py",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def _ascii_text(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def _safe_name(value: str, fallback: str) -> str:
    text = _ascii_text(value).strip() or fallback
    text = text.replace("\\", " ").replace("/", " ").replace(":", " ")
    text = re.sub(r"[^A-Za-z0-9_. -]+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def _desktop_dir() -> Path:
    return Path.home() / "Desktop"


def _is_hidden(path: Path) -> bool:
    name = path.name
    return name.startswith(".") or name.lower() == "desktop.ini"


def _path_kind(path: Path) -> str:
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def _iso_modified(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return ""


def _file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size) if path.is_file() else 0
    except OSError:
        return 0


def _child_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    try:
        return sum(1 for _ in path.iterdir())
    except OSError:
        return 0


def _desktop_item(path: Path) -> dict[str, Any]:
    kind = _path_kind(path)
    return {
        "name": _ascii_text(path.name),
        "path": _ascii_text(str(path)),
        "type": kind,
        "extension": _ascii_text(path.suffix.lower()) if kind == "file" else "",
        "size_bytes": _file_size(path),
        "child_count": _child_count(path),
        "modified_utc": _iso_modified(path),
    }


def list_desktop_items(
    *,
    desktop_dir: str | Path | None = None,
    max_items: int = 200,
    include_hidden: bool = False,
) -> dict[str, Any]:
    root = Path(desktop_dir) if desktop_dir is not None else _desktop_dir()
    limit = max(1, min(int(max_items or 200), 500))

    if not root.exists():
        return {
            "schema": DESKTOP_INVENTORY_SCHEMA,
            "success": False,
            "local_only": True,
            "metadata_only": True,
            "desktop_dir": str(root),
            "count": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
            "error": "desktop_dir_not_found",
        }

    try:
        candidates = [
            item
            for item in root.iterdir()
            if include_hidden or not _is_hidden(item)
        ]
    except OSError as exc:
        return {
            "schema": DESKTOP_INVENTORY_SCHEMA,
            "success": False,
            "local_only": True,
            "metadata_only": True,
            "desktop_dir": str(root),
            "count": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
            "error": _ascii_text(exc),
        }

    candidates.sort(key=lambda item: (0 if item.is_dir() else 1, item.name.lower()))
    items = [_desktop_item(item) for item in candidates[:limit]]

    return {
        "schema": DESKTOP_INVENTORY_SCHEMA,
        "success": True,
        "local_only": True,
        "metadata_only": True,
        "desktop_dir": str(root),
        "count": len(candidates),
        "returned": len(items),
        "truncated": len(candidates) > limit,
        "items": items,
    }


def inspect_desktop_folder(
    *,
    folder_name: str,
    desktop_dir: str | Path | None = None,
    max_items: int = 200,
    include_hidden: bool = False,
) -> dict[str, Any]:
    root = Path(desktop_dir) if desktop_dir is not None else _desktop_dir()
    safe_folder_name = _safe_name(folder_name, "")
    limit = max(1, min(int(max_items or 200), 500))
    if not safe_folder_name:
        return {
            "schema": DESKTOP_FOLDER_INSPECTION_SCHEMA,
            "success": False,
            "local_only": True,
            "metadata_only": True,
            "desktop_dir": str(root),
            "folder_name": "",
            "folder_path": "",
            "count": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
            "error": "folder_name_required",
        }

    folder = root / safe_folder_name
    try:
        root_resolved = root.resolve()
        folder_resolved = folder.resolve()
        if folder_resolved != root_resolved and root_resolved not in folder_resolved.parents:
            raise ValueError("folder_outside_desktop")
    except Exception as exc:
        return {
            "schema": DESKTOP_FOLDER_INSPECTION_SCHEMA,
            "success": False,
            "local_only": True,
            "metadata_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "folder_path": str(folder),
            "count": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
            "error": _ascii_text(exc),
        }

    if not folder.exists() or not folder.is_dir():
        return {
            "schema": DESKTOP_FOLDER_INSPECTION_SCHEMA,
            "success": False,
            "local_only": True,
            "metadata_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "folder_path": str(folder),
            "count": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
            "error": "desktop_folder_not_found",
        }

    try:
        candidates = [
            item
            for item in folder.iterdir()
            if include_hidden or not _is_hidden(item)
        ]
    except OSError as exc:
        return {
            "schema": DESKTOP_FOLDER_INSPECTION_SCHEMA,
            "success": False,
            "local_only": True,
            "metadata_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "folder_path": str(folder),
            "count": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
            "error": _ascii_text(exc),
        }

    candidates.sort(key=lambda item: (0 if item.is_dir() else 1, item.name.lower()))
    items = [_desktop_item(item) for item in candidates[:limit]]
    return {
        "schema": DESKTOP_FOLDER_INSPECTION_SCHEMA,
        "success": True,
        "local_only": True,
        "metadata_only": True,
        "desktop_dir": str(root),
        "folder_name": safe_folder_name,
        "folder_path": str(folder),
        "count": len(candidates),
        "returned": len(items),
        "truncated": len(candidates) > limit,
        "items": items,
    }


def read_desktop_text_file(
    *,
    file_name: str,
    folder_name: str = "",
    desktop_dir: str | Path | None = None,
    max_chars: int = 6000,
) -> dict[str, Any]:
    root = Path(desktop_dir) if desktop_dir is not None else _desktop_dir()
    safe_file_name = _safe_name(file_name, "")
    safe_folder_name = _safe_name(folder_name, "")
    limit = max(1, min(int(max_chars or 6000), 50000))

    if not safe_file_name:
        return {
            "schema": DESKTOP_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": "",
            "file_path": "",
            "text": "",
            "text_length": 0,
            "truncated": False,
            "error": "file_name_required",
        }

    target_dir = root / safe_folder_name if safe_folder_name else root
    target = target_dir / safe_file_name
    extension = target.suffix.lower()
    if extension not in TEXT_EXTENSIONS:
        return {
            "schema": DESKTOP_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "text": "",
            "text_length": 0,
            "truncated": False,
            "allowed_extensions": sorted(TEXT_EXTENSIONS),
            "error": "unsupported_extension",
        }

    try:
        root_resolved = root.resolve()
        target_resolved = target.resolve()
        if target_resolved != root_resolved and root_resolved not in target_resolved.parents:
            raise ValueError("file_outside_desktop")
    except Exception as exc:
        return {
            "schema": DESKTOP_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "text": "",
            "text_length": 0,
            "truncated": False,
            "error": _ascii_text(exc),
        }

    if not target.exists() or not target.is_file():
        return {
            "schema": DESKTOP_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "text": "",
            "text_length": 0,
            "truncated": False,
            "error": "desktop_text_file_not_found",
        }

    try:
        raw_text = target.read_text(encoding="utf-8-sig", errors="ignore")
        text = _ascii_text(raw_text)
        truncated = len(text) > limit
        if truncated:
            text = text[:limit]
        return {
            "schema": DESKTOP_TEXT_FILE_SCHEMA,
            "success": True,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "extension": extension,
            "size_bytes": _file_size(target),
            "modified_utc": _iso_modified(target),
            "text": text,
            "text_length": len(text),
            "truncated": truncated,
            "error": "",
        }
    except OSError as exc:
        return {
            "schema": DESKTOP_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "text": "",
            "text_length": 0,
            "truncated": False,
            "error": _ascii_text(exc),
        }


def write_desktop_text_file(
    *,
    file_name: str,
    content: str,
    folder_name: str = "",
    desktop_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(desktop_dir) if desktop_dir is not None else _desktop_dir()
    safe_file_name = _safe_name(file_name, "")
    safe_folder_name = _safe_name(folder_name, "")
    if safe_file_name and not Path(safe_file_name).suffix:
        safe_file_name = f"{safe_file_name}.md"

    if not safe_file_name:
        return {
            "schema": DESKTOP_WRITE_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": "",
            "file_path": "",
            "backup_path": "",
            "bytes_written": 0,
            "error": "file_name_required",
        }

    target_dir = root / safe_folder_name if safe_folder_name else root
    target = target_dir / safe_file_name
    extension = target.suffix.lower()
    if extension not in TEXT_EXTENSIONS:
        return {
            "schema": DESKTOP_WRITE_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "backup_path": "",
            "bytes_written": 0,
            "allowed_extensions": sorted(TEXT_EXTENSIONS),
            "error": "unsupported_extension",
        }

    try:
        root.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)
        root_resolved = root.resolve()
        target_resolved = target.resolve()
        if target_resolved != root_resolved and root_resolved not in target_resolved.parents:
            raise ValueError("file_outside_desktop")
    except Exception as exc:
        return {
            "schema": DESKTOP_WRITE_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "backup_path": "",
            "bytes_written": 0,
            "error": _ascii_text(exc),
        }

    text = _ascii_text(content)
    backup_path = ""
    try:
        if target.exists() and target.read_text(encoding="utf-8", errors="ignore") != text:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = target.with_suffix(target.suffix + f".{stamp}.bak")
            shutil.copy2(target, backup)
            backup_path = str(backup)
        target.write_text(text, encoding="utf-8")
        return {
            "schema": DESKTOP_WRITE_TEXT_FILE_SCHEMA,
            "success": True,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "backup_path": backup_path,
            "bytes_written": len(text.encode("utf-8")),
            "error": "",
        }
    except OSError as exc:
        return {
            "schema": DESKTOP_WRITE_TEXT_FILE_SCHEMA,
            "success": False,
            "local_only": True,
            "desktop_only": True,
            "desktop_dir": str(root),
            "folder_name": safe_folder_name,
            "file_name": safe_file_name,
            "file_path": str(target),
            "backup_path": backup_path,
            "bytes_written": 0,
            "error": _ascii_text(exc),
        }


def _default_script_content(script_name: str) -> str:
    label = _safe_name(script_name, "binoclu")
    return (
        "from __future__ import annotations\n\n"
        "def main() -> None:\n"
        f"    print(\"ANA_MAX {label} ready\")\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    main()\n"
    )


def create_desktop_python_script(
    *,
    folder_name: str = "ANA_MAX",
    script_name: str = "binoclu",
    content: str | None = None,
    desktop_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(desktop_dir) if desktop_dir is not None else _desktop_dir()
    folder = root / _safe_name(folder_name, "ANA_MAX")
    script_base = _safe_name(script_name, "binoclu")
    if not script_base.lower().endswith(".py"):
        script_base = f"{script_base}.py"
    script_path = folder / script_base
    script_content = content if content is not None else _default_script_content(script_path.stem)

    backup_path = ""
    root.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    if script_path.exists() and script_path.read_text(encoding="utf-8", errors="ignore") != script_content:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = script_path.with_suffix(script_path.suffix + f".{stamp}.bak")
        shutil.copy2(script_path, backup)
        backup_path = str(backup)
    script_path.write_text(script_content, encoding="utf-8")

    return {
        "schema": SCHEMA,
        "success": True,
        "local_only": True,
        "desktop_dir": str(root),
        "folder_path": str(folder),
        "script_path": str(script_path),
        "backup_path": backup_path,
        "bytes_written": len(script_content.encode("utf-8")),
    }
