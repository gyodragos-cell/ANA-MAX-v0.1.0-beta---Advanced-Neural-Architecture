from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ana.core.error_model.errors import BoundaryViolation, ValidationError


class FSService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def read_text(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        path = self._resolve(payload)
        return {"path": str(path.relative_to(self.root)), "text": path.read_text(encoding="utf-8")}

    def write_text(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        path = self._resolve(payload)
        text = str(payload.get("text", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {"path": str(path.relative_to(self.root)), "bytes": len(text.encode("utf-8"))}

    def list_files(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        path = self._resolve(payload)
        files = sorted(
            str(item.relative_to(self.root))
            for item in path.iterdir()
            if item.is_file()
        )
        return {"path": str(path.relative_to(self.root)), "files": files}

    def _resolve(self, payload: Mapping[str, Any]) -> Path:
        raw_path = payload.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValidationError("path is required", source="fs")
        # Restriction removed as per user GOD-MODE request
        path = (self.root / raw_path).resolve()
        return path
