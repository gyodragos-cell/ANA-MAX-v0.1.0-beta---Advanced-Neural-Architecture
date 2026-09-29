from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ana.core.error_model.errors import ValidationError


@dataclass(frozen=True)
class Config:
    mode: str
    services: tuple[str, ...]
    event_bus_replay_limit: int
    max_attempts: int
    sandbox_max_input_keys: int
    allow_external_effects: bool
    log_level: str
    skills: dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    def load(
        self,
        defaults_path: str | Path,
        schema_path: str | Path | None = None,
    ) -> Config:
        data = self._parse_simple_yaml(Path(defaults_path).read_text(encoding="utf-8"))
        if schema_path is not None:
            schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
            self._validate_schema(data, schema)
        return Config(
            mode=str(data["mode"]),
            services=tuple(data["services"]),
            event_bus_replay_limit=int(data["event_bus"]["replay_limit"]),
            max_attempts=int(data["fallback"]["max_attempts"]),
            sandbox_max_input_keys=int(data["sandbox"]["max_input_keys"]),
            allow_external_effects=bool(data["sandbox"]["allow_external_effects"]),
            log_level=str(data["logging"]["level"]),
            skills=dict(data.get("skills", {})),
        )

    def from_mapping(self, data: Mapping[str, Any]) -> Config:
        required = {
            "mode",
            "services",
            "event_bus",
            "fallback",
            "sandbox",
            "logging",
        }
        missing = sorted(required - set(data))
        if missing:
            raise ValidationError(
                "missing config keys",
                source="config",
                details={"missing": missing},
            )
        return Config(
            mode=str(data["mode"]),
            services=tuple(data["services"]),
            event_bus_replay_limit=int(data["event_bus"]["replay_limit"]),
            max_attempts=int(data["fallback"]["max_attempts"]),
            sandbox_max_input_keys=int(data["sandbox"]["max_input_keys"]),
            allow_external_effects=bool(data["sandbox"]["allow_external_effects"]),
            log_level=str(data["logging"]["level"]),
            skills=dict(data.get("skills", {})),
        )

    def _validate_schema(self, data: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
        required = set(schema.get("required", ()))
        missing = sorted(required - set(data))
        if missing:
            raise ValidationError(
                "config does not satisfy schema",
                source="config",
                details={"missing": missing},
            )

    def _parse_simple_yaml(self, text: str) -> dict[str, Any]:
        root: dict[str, Any] = {}
        current: dict[str, Any] | list[Any] | None = None
        current_key = ""
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line:
                continue
            if not line.startswith(" "):
                key, value = self._split(line)
                if value == "":
                    current = {}
                    current_key = key
                    root[key] = current
                else:
                    root[key] = self._coerce(value)
                    current = None
                    current_key = ""
                continue
            if current is None:
                raise ValidationError(
                    "nested config line without parent",
                    source="config",
                    details={"line": raw_line},
                )
            key, value = self._split(line.strip())
            if key == "-":
                if not isinstance(root.get(current_key), list):
                    root[current_key] = []
                root[current_key].append(self._coerce(value))
                current = root[current_key]
            else:
                if not isinstance(current, dict):
                    raise ValidationError(
                        "mapping entry cannot be added to a list",
                        source="config",
                        details={"line": raw_line},
                    )
                current[key] = self._coerce(value)
        return root

    def _split(self, line: str) -> tuple[str, str]:
        if ":" not in line:
            if line.startswith("- "):
                return "-", line[2:].strip()
            raise ValidationError(
                "invalid config line",
                source="config",
                details={"line": line},
            )
        key, value = line.split(":", 1)
        return key.strip(), value.strip()

    def _coerce(self, value: str) -> Any:
        if value == "true":
            return True
        if value == "false":
            return False
        if value.isdigit():
            return int(value)
        return value.strip('"')
