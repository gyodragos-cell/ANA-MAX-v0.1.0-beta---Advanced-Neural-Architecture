from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ana.config.loader import ConfigLoader
from ana.core.error_model.errors import ValidationError
from ana.tools.registry.registry import ToolRegistry, ToolSpec


@dataclass(frozen=True)
class SkillSpec:
    title: str
    sections: tuple[str, ...]
    tasks: tuple[str, ...]
    version: str | None = None
    path: Path | None = None


class SkillEngine:
    required_sections = (
        "Context",
        "Scop",
        "Structura directoare",
        "Componente OS v2",
        "Discipline OS v2",
        "Taskuri pentru implementare",
        "Reguli pentru Codex",
        "Output asteptat",
    )

    def __init__(self) -> None:
        self._skills: dict[str, SkillSpec] = {}
        self._config: dict[str, Any] = {}
        # Performance: Cache for normalized headings
        self._heading_cache: dict[str, str] = {}

    def parse(self, text: str, path: Path | None = None) -> SkillSpec:
        title = ""
        sections: list[str] = []
        tasks: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# ") and not title:
                title = stripped[2:].strip()
            if stripped.startswith("## "):
                sections.append(self._normalize_heading(stripped[3:]))
            if stripped.startswith("### ") and ". " in stripped:
                label = stripped[4:].split(".", 1)[0].strip()
                if len(label) == 1 and label.isalpha():
                    tasks.append(label)
        if not title:
            raise ValidationError("skill title is required", source="skill_engine")
        version = self._extract_version(text)
        return SkillSpec(
            title=title,
            sections=tuple(sections),
            tasks=tuple(tasks),
            version=version,
            path=path,
        )

    def validate_os_v2_skill(self, text: str, path: Path | None = None) -> SkillSpec:
        spec = self.parse(text, path=path)
        
        # Check for required sections - always validate when explicitly called
        # Normalize to lowercase for comparison
        spec_sections_lower = set(s.lower() for s in spec.sections)
        required_lower = set(s.lower() for s in self.required_sections)
        
        missing_sections = required_lower - spec_sections_lower
        if missing_sections:
            raise ValidationError(
                "skill is missing required sections",
                source="skill_engine",
                details={"missing": sorted(missing_sections), "path": str(path) if path else None},
            )
        
        # Check version if in declarative skills directory
        if path and "ana" in str(path.parts) and "skills" in str(path.parts):
            if not spec.version:
                raise ValidationError(
                    "skill version is required for declarative skills",
                    source="skill_engine",
                    details={"path": str(path)},
                )
        
        return spec

    def load_skill_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        data = ConfigLoader()._parse_simple_yaml(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValidationError("skill config must be a mapping", source="skill_engine")
        skills = data.get("skills", {})
        if not isinstance(skills, dict):
            raise ValidationError("skills config section must be a mapping", source="skill_engine")
        return skills

    def load_skills(self, root: Path, mapping: Mapping[str, Any] | None = None) -> dict[str, SkillSpec]:
        self._config = dict(mapping or {})
        self._skills = {}
        if not root.exists():
            return self._skills
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_path = skill_dir / "SKILL.md"
            if not skill_path.exists():
                continue
            spec = self.validate_os_v2_skill(skill_path.read_text(encoding="utf-8"), path=skill_path)
            self._skills[skill_dir.name] = spec
        return self._skills

    def register_skills(self, registry: ToolRegistry) -> None:
        for skill_name, spec in self._skills.items():
            metadata = None
            capability = None
            for key, entry in self._config.items():
                if key == skill_name and entry.get("capability"):
                    metadata = entry
                    capability = entry["capability"]
                    break
                if entry.get("skill") == skill_name:
                    metadata = entry
                    capability = key
                    break
                if key == skill_name:
                    metadata = entry
                    capability = entry.get("capability", key)
                    break
            if metadata is None:
                continue
            if not metadata.get("enabled", True):
                continue
            if not capability:
                capability = metadata.get("capability")
            if not capability:
                continue
            registry.register_skill(
                ToolSpec(
                    name=f"skill.{skill_name}",
                    capability=capability,
                    handler=self._make_skill_handler(skill_name, spec, capability),
                    priority=200,
                )
            )

    def has_capability(self, capability: str) -> bool:
        return any(
            entry.get("capability") == capability
            for entry in self._config.values()
        )

    def skill_name_for_capability(self, capability: str) -> str | None:
        for skill_name, metadata in self._config.items():
            if metadata.get("capability") == capability:
                return skill_name
        return None

    def _make_skill_handler(self, skill_name: str, spec: SkillSpec, capability: str):
        def handler(payload: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "skill": skill_name,
                "title": spec.title,
                "version": spec.version,
                "capability": capability,
                "payload": dict(payload),
            }

        return handler

    def _extract_version(self, text: str) -> str | None:
        match = re.search(r"^## Version\s*$\n([^\n]+)", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _normalize_heading(self, heading: str) -> str:
        # Performance: Use cache for normalized headings
        if heading in self._heading_cache:
            return self._heading_cache[heading]
        
        # Remove everything after opening parenthesis (e.g., "Structura directoare (obligatorie)" -> "Structura directoare")
        if "(" in heading:
            heading = heading.split("(")[0].strip()
        
        # Remove numbered prefix (e.g., "1. Context" -> "Context")
        if ". " in heading:
            heading = heading.split(". ", 1)[1].strip()
        
        # Normalize diacritics to ASCII
        normalized = self._ascii(heading)
        
        # Cache the result
        self._heading_cache[heading] = normalized
        return normalized.strip()

    def _ascii(self, value: str) -> str:
        replacements = {
            "a": "a",
            "a": "a",
            "i": "i",
            "s": "s",
            "s": "s",
            "t": "t",
            "t": "t",
            "A": "A",
            "": "A",
            "I": "I",
            "S": "S",
            "T": "T",
        }
        normalized = "".join(replacements.get(char, char) for char in value)
        return normalized.lower()
