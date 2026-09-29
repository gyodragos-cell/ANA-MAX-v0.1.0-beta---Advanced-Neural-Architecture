from __future__ import annotations

from pathlib import Path
from typing import Any

from ana.core.self_repair.persistence import LearnedRulesStore


class SelfRepairPatcher:
    def __init__(self, store: LearnedRulesStore) -> None:
        self.store = store

    def record_suggestion(self, pattern: str, suggestion: str, source: str) -> None:
        self.store.append_learning(
            {
                "pattern": pattern,
                "suggestion": suggestion,
                "source": source,
            }
        )

    def apply_skill_mapping(self, skill_name: str, capability: str, skills_path: Path) -> None:
        skills_yaml = skills_path
        if not skills_yaml.exists():
            skills_yaml.write_text("skills: {}\n", encoding="utf-8")
        content = skills_yaml.read_text(encoding="utf-8")
        lines = content.splitlines()
        if f"{skill_name}:" in content:
            return
        with skills_yaml.open("a", encoding="utf-8") as handle:
            handle.write(f"  {skill_name}:\n")
            handle.write(f"    capability: \"{capability}\"\n")
            handle.write(f"    description: \"auto-applied mapping\"\n")
