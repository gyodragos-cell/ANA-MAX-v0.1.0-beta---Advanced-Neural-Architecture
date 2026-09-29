from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ana.config.loader import ConfigLoader


@dataclass(frozen=True)
class LearnedRulesStore:
    path: Path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"learned_patterns": [], "skill_mappings": [], "fallback_mappings": []}
        data = ConfigLoader()._parse_simple_yaml(self.path.read_text(encoding="utf-8"))
        return {
            "learned_patterns": list(data.get("learned_patterns", [])),
            "skill_mappings": list(data.get("skill_mappings", [])),
            "fallback_mappings": list(data.get("fallback_mappings", [])),
        }

    def append_learning(self, entry: dict[str, Any]) -> None:
        data = self.load()
        data["learned_patterns"].append(entry)
        self.path.write_text(self._dump(data), encoding="utf-8")

    def find_pattern(self, pattern: str) -> dict[str, Any] | None:
        data = self.load()
        for item in data.get("learned_patterns", []):
            if item.get("pattern") == pattern:
                return item
        return None

    def _dump(self, data: dict[str, Any]) -> str:
        lines: list[str] = []
        for key, value in data.items():
            lines.append(f"{key}:")
            if isinstance(value, list):
                if not value:
                    lines.append("  []")
                else:
                    for item in value:
                        lines.append("  -")
                        if isinstance(item, dict):
                            for field_name, field_value in item.items():
                                lines.append(f"      {field_name}: {field_value}")
                        else:
                            lines.append(f"    {item}")
            else:
                lines.append(f"  {value}")
        return "\n".join(lines) + "\n"
