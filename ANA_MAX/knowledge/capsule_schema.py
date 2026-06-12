"""OS-21 recon capsule schema.

This module is metadata-only. It defines a compact, JSON-friendly capsule
shape for recon artifacts without changing OS-20.1 runtime behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping


RECON_CAPSULE_SCHEMA = "ana.os21.recon_capsule.v1"


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_value(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, set):
        return [_normalize_value(item) for item in sorted(value, key=lambda item: repr(item))]
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    return {}


def _as_tuple_of_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if value is None:
        return ()
    return (str(value),)


@dataclass(frozen=True)
class ReconCapsuleSchema:
    capsule_id: str
    url: str
    mode: str = "passive"
    timestamp: str = ""
    passive_phases: tuple[str, ...] = ()
    active_phases: tuple[str, ...] = ()
    artifacts: dict[str, Any] = field(default_factory=dict)
    capability_contracts: dict[str, Any] = field(default_factory=dict)
    reasoning_graph_hints: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    lineage: tuple[str, ...] = ()
    schema: str = RECON_CAPSULE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema or RECON_CAPSULE_SCHEMA,
            "capsule_id": self.capsule_id,
            "url": self.url,
            "mode": self.mode,
            "timestamp": self.timestamp,
            "passive_phases": list(self.passive_phases),
            "active_phases": list(self.active_phases),
            "artifacts": _normalize_value(self.artifacts),
            "capability_contracts": _normalize_value(self.capability_contracts),
            "reasoning_graph_hints": _normalize_value(self.reasoning_graph_hints),
            "version": self.version,
            "lineage": list(self.lineage),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReconCapsuleSchema":
        payload = dict(data)
        return cls(
            capsule_id=str(payload.get("capsule_id", "")),
            url=str(payload.get("url", "")),
            mode=str(payload.get("mode", "passive")),
            timestamp=str(payload.get("timestamp", "")),
            passive_phases=_as_tuple_of_strings(payload.get("passive_phases", ())),
            active_phases=_as_tuple_of_strings(payload.get("active_phases", ())),
            artifacts=_as_dict(payload.get("artifacts", {})),
            capability_contracts=_as_dict(payload.get("capability_contracts", {})),
            reasoning_graph_hints=_as_dict(payload.get("reasoning_graph_hints", {})),
            version=str(payload.get("version", "1.0")),
            lineage=_as_tuple_of_strings(payload.get("lineage", ())),
            schema=str(payload.get("schema", RECON_CAPSULE_SCHEMA)),
        )

    def validate(self) -> dict[str, Any]:
        payload = self.to_dict()
        issues: list[str] = []

        if not payload["capsule_id"]:
            issues.append("missing_capsule_id")
        if not payload["url"]:
            issues.append("missing_url")
        if payload["mode"] not in {"passive", "active"}:
            issues.append("invalid_mode")
        if not payload["timestamp"]:
            issues.append("missing_timestamp")
        if not payload["version"]:
            issues.append("missing_version")

        if not isinstance(payload["passive_phases"], list):
            issues.append("passive_phases_not_list")
        if not isinstance(payload["active_phases"], list):
            issues.append("active_phases_not_list")
        if not isinstance(payload["artifacts"], dict):
            issues.append("artifacts_not_dict")
        if not isinstance(payload["capability_contracts"], dict):
            issues.append("capability_contracts_not_dict")
        if not isinstance(payload["reasoning_graph_hints"], dict):
            issues.append("reasoning_graph_hints_not_dict")
        if not isinstance(payload["lineage"], list):
            issues.append("lineage_not_list")

        try:
            json.dumps(payload, ensure_ascii=True, sort_keys=True)
        except Exception as exc:  # pragma: no cover - defensive
            issues.append(f"serialization_failed:{exc}")

        return {
            "schema": RECON_CAPSULE_SCHEMA,
            "capsule_id": payload["capsule_id"],
            "valid": not issues,
            "issues": issues,
            "summary": {
                "mode": payload["mode"],
                "version": payload["version"],
                "field_count": len(payload),
            },
        }

