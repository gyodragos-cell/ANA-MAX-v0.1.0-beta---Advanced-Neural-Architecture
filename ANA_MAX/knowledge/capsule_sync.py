"""OS-21.5 capsule sync planner.

This module is metadata-only. It compares in-memory capsule sets and produces
deterministic sync actions without writing files or contacting transports.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Iterable, Mapping

from .capsule_merge import CapsuleMergeEngine
from .capsule_schema import ReconCapsuleSchema


SYNC_PLAN_SCHEMA = "ana.os21.capsule_sync_plan.v1"
SYNC_PREVIEW_SCHEMA = "ana.os21.capsule_sync_preview.v1"


def _coerce_capsule(capsule: Any) -> dict[str, Any]:
    if isinstance(capsule, ReconCapsuleSchema):
        return capsule.to_dict()
    if isinstance(capsule, Mapping):
        return ReconCapsuleSchema.from_dict(capsule).to_dict()
    raise TypeError("capsule must be a mapping or ReconCapsuleSchema")


def _capsule_map(capsules: Iterable[Any] | None) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for capsule in capsules or []:
        capsule_dict = _coerce_capsule(capsule)
        capsule_id = str(capsule_dict.get("capsule_id", "")).strip()
        if capsule_id:
            mapped[capsule_id] = capsule_dict
    return mapped


def _fingerprint(capsule: dict[str, Any] | None) -> str:
    if capsule is None:
        return ""
    return json.dumps(capsule, ensure_ascii=True, sort_keys=True)


class CapsuleSyncEngine:
    """Build deterministic in-memory capsule sync plans."""

    def __init__(self, merge_engine: CapsuleMergeEngine | None = None) -> None:
        self.merge_engine = merge_engine or CapsuleMergeEngine()

    def build_sync_plan(
        self,
        local_capsules: Iterable[Any],
        remote_capsules: Iterable[Any],
        base_capsules: Iterable[Any] | None = None,
    ) -> dict[str, Any]:
        local_map = _capsule_map(local_capsules)
        remote_map = _capsule_map(remote_capsules)
        base_map = _capsule_map(base_capsules)
        capsule_ids = sorted(set(local_map) | set(remote_map) | set(base_map))

        actions = [
            self._build_action(capsule_id, base_map.get(capsule_id), local_map.get(capsule_id), remote_map.get(capsule_id))
            for capsule_id in capsule_ids
        ]

        summary = {
            "schema": SYNC_PLAN_SCHEMA,
            "capsule_count": len(capsule_ids),
            "action_count": len(actions),
            "noop_count": len([item for item in actions if item["action"] == "noop"]),
            "create_local_count": len([item for item in actions if item["action"] == "create_local"]),
            "create_remote_count": len([item for item in actions if item["action"] == "create_remote"]),
            "update_local_count": len([item for item in actions if item["action"] == "update_local"]),
            "update_remote_count": len([item for item in actions if item["action"] == "update_remote"]),
            "merge_required_count": len([item for item in actions if item["action"] == "merge_required"]),
        }

        return {
            "schema": SYNC_PLAN_SCHEMA,
            "local_only": True,
            "metadata_only": True,
            "transport": "in-memory",
            "actions": actions,
            "summary": summary,
        }

    def apply_plan_preview(
        self,
        plan: dict[str, Any],
        local_capsules: Iterable[Any],
        remote_capsules: Iterable[Any],
    ) -> dict[str, Any]:
        local_map = _capsule_map(local_capsules)
        remote_map = _capsule_map(remote_capsules)

        for action in plan.get("actions", []) or []:
            capsule_id = str(action.get("capsule_id", ""))
            action_type = str(action.get("action", ""))
            capsule = action.get("capsule")
            merged = action.get("merged_capsule")
            if action_type == "create_local" and capsule:
                local_map[capsule_id] = _coerce_capsule(capsule)
            elif action_type == "create_remote" and capsule:
                remote_map[capsule_id] = _coerce_capsule(capsule)
            elif action_type == "update_local" and capsule:
                local_map[capsule_id] = _coerce_capsule(capsule)
            elif action_type == "update_remote" and capsule:
                remote_map[capsule_id] = _coerce_capsule(capsule)
            elif action_type == "merge_required" and merged:
                local_map[capsule_id] = _coerce_capsule(merged)
                remote_map[capsule_id] = _coerce_capsule(merged)

        return {
            "schema": SYNC_PREVIEW_SCHEMA,
            "local_only": True,
            "metadata_only": True,
            "writes_performed": False,
            "local_ids": sorted(local_map),
            "remote_ids": sorted(remote_map),
            "local_count": len(local_map),
            "remote_count": len(remote_map),
        }

    def _build_action(
        self,
        capsule_id: str,
        base: dict[str, Any] | None,
        local: dict[str, Any] | None,
        remote: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if local is None and remote is not None:
            return self._action(capsule_id, "create_local", remote)
        if remote is None and local is not None:
            return self._action(capsule_id, "create_remote", local)
        if local is None and remote is None:
            return self._action(capsule_id, "noop", base)
        if _fingerprint(local) == _fingerprint(remote):
            return self._action(capsule_id, "noop", local)

        if base is None:
            base = local
        merge_result = self.merge_engine.merge(base, local, remote)
        if not merge_result["success"]:
            action = self._action(capsule_id, "merge_required", merge_result["merged_capsule"])
            action["conflicts"] = merge_result["conflicts"]
            action["conflict_count"] = merge_result["conflict_count"]
            action["merged_capsule"] = merge_result["merged_capsule"]
            return action

        if _fingerprint(local) == _fingerprint(base):
            return self._action(capsule_id, "update_local", remote)
        if _fingerprint(remote) == _fingerprint(base):
            return self._action(capsule_id, "update_remote", local)

        action = self._action(capsule_id, "merge_required", merge_result["merged_capsule"])
        action["conflicts"] = []
        action["conflict_count"] = 0
        action["merged_capsule"] = merge_result["merged_capsule"]
        return action

    def _action(self, capsule_id: str, action: str, capsule: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "capsule_id": capsule_id,
            "action": action,
            "capsule": deepcopy(capsule) if capsule else None,
            "metadata_only": True,
        }

