"""OS-21.5 capsule merge engine.

This module is metadata-only. It performs deterministic in-memory capsule
merge planning and conflict reporting without file writes or transport calls.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping

from .capsule_schema import RECON_CAPSULE_SCHEMA, ReconCapsuleSchema


MERGE_SCHEMA = "ana.os21.capsule_merge.v1"
CONFLICT_SCHEMA = "ana.os21.capsule_conflicts.v1"
MISSING = object()


def _normalize_value(value: Any) -> Any:
    if value is MISSING:
        return None
    if isinstance(value, dict):
        return {str(key): _normalize_value(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, set):
        return [_normalize_value(item) for item in sorted(value, key=lambda item: repr(item))]
    return value


def _coerce_capsule(capsule: Any) -> dict[str, Any]:
    if isinstance(capsule, ReconCapsuleSchema):
        return capsule.to_dict()
    if isinstance(capsule, Mapping):
        return ReconCapsuleSchema.from_dict(capsule).to_dict()
    raise TypeError("capsule must be a mapping or ReconCapsuleSchema")


def _item_key(value: Any) -> str:
    return json.dumps(_normalize_value(value), ensure_ascii=True, sort_keys=True)


def _merge_lists(*values: Any) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value is MISSING or value is None:
            continue
        items = value if isinstance(value, list) else [value]
        for item in items:
            normalized = _normalize_value(item)
            key = _item_key(normalized)
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
    return merged


def _path_join(parent: str, key: str) -> str:
    return key if not parent else f"{parent}.{key}"


def _changed(base: Any, value: Any) -> bool:
    return _normalize_value(base) != _normalize_value(value)


def _capsule_ref(capsule: dict[str, Any]) -> str:
    capsule_id = str(capsule.get("capsule_id", "")).strip()
    version = str(capsule.get("version", "")).strip()
    if capsule_id and version:
        return f"{capsule_id}@{version}"
    return capsule_id


class CapsuleMergeEngine:
    """Deterministic three-way merge engine for recon capsules."""

    def detect_conflicts(self, base: Any, left: Any, right: Any) -> dict[str, Any]:
        base_capsule = _coerce_capsule(base)
        left_capsule = _coerce_capsule(left)
        right_capsule = _coerce_capsule(right)
        conflicts = self._detect_conflicts_at_path(base_capsule, left_capsule, right_capsule, "")
        return {
            "schema": CONFLICT_SCHEMA,
            "capsule_id": left_capsule.get("capsule_id") or right_capsule.get("capsule_id") or base_capsule.get("capsule_id", ""),
            "metadata_only": True,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
        }

    def merge(self, base: Any, left: Any, right: Any) -> dict[str, Any]:
        base_capsule = _coerce_capsule(base)
        left_capsule = _coerce_capsule(left)
        right_capsule = _coerce_capsule(right)
        conflicts = self._detect_conflicts_at_path(base_capsule, left_capsule, right_capsule, "")
        merged = self._merge_at_path(base_capsule, left_capsule, right_capsule, "")
        merged["schema"] = merged.get("schema") or RECON_CAPSULE_SCHEMA
        merged["capsule_id"] = str(left_capsule.get("capsule_id") or right_capsule.get("capsule_id") or base_capsule.get("capsule_id", ""))
        merged["lineage"] = self._merged_lineage(base_capsule, left_capsule, right_capsule, merged)

        validation = ReconCapsuleSchema.from_dict(merged).validate()
        return {
            "schema": MERGE_SCHEMA,
            "capsule_id": merged["capsule_id"],
            "success": not conflicts and validation["valid"],
            "metadata_only": True,
            "local_only": True,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "merged_capsule": merged,
            "validation": validation,
        }

    def _detect_conflicts_at_path(self, base: Any, left: Any, right: Any, path: str) -> list[dict[str, Any]]:
        if left is not MISSING and right is not MISSING and _normalize_value(left) == _normalize_value(right):
            return []

        if isinstance(base, dict) or isinstance(left, dict) or isinstance(right, dict):
            keys = sorted(
                set(base.keys() if isinstance(base, dict) else ())
                | set(left.keys() if isinstance(left, dict) else ())
                | set(right.keys() if isinstance(right, dict) else ()),
                key=str,
            )
            conflicts: list[dict[str, Any]] = []
            for key in keys:
                conflicts.extend(
                    self._detect_conflicts_at_path(
                        base.get(key, MISSING) if isinstance(base, dict) else MISSING,
                        left.get(key, MISSING) if isinstance(left, dict) else MISSING,
                        right.get(key, MISSING) if isinstance(right, dict) else MISSING,
                        _path_join(path, str(key)),
                    )
                )
            return conflicts

        if isinstance(base, list) or isinstance(left, list) or isinstance(right, list):
            return []

        left_changed = _changed(base, left)
        right_changed = _changed(base, right)
        if left_changed and right_changed and _normalize_value(left) != _normalize_value(right):
            return [
                {
                    "path": path,
                    "base": _normalize_value(base),
                    "left": _normalize_value(left),
                    "right": _normalize_value(right),
                    "resolution": "prefer_left_metadata",
                }
            ]
        return []

    def _merge_at_path(self, base: Any, left: Any, right: Any, path: str) -> Any:
        if left is not MISSING and right is not MISSING and _normalize_value(left) == _normalize_value(right):
            return _normalize_value(left)

        if isinstance(base, dict) or isinstance(left, dict) or isinstance(right, dict):
            merged: dict[str, Any] = {}
            keys = sorted(
                set(base.keys() if isinstance(base, dict) else ())
                | set(left.keys() if isinstance(left, dict) else ())
                | set(right.keys() if isinstance(right, dict) else ()),
                key=str,
            )
            for key in keys:
                value = self._merge_at_path(
                    base.get(key, MISSING) if isinstance(base, dict) else MISSING,
                    left.get(key, MISSING) if isinstance(left, dict) else MISSING,
                    right.get(key, MISSING) if isinstance(right, dict) else MISSING,
                    _path_join(path, str(key)),
                )
                if value is not MISSING:
                    merged[str(key)] = value
            return merged

        if isinstance(base, list) or isinstance(left, list) or isinstance(right, list):
            return _merge_lists(base, left, right)

        left_changed = _changed(base, left)
        right_changed = _changed(base, right)
        if left_changed:
            return _normalize_value(left)
        if right_changed:
            return _normalize_value(right)
        return _normalize_value(base)

    def _merged_lineage(
        self,
        base: dict[str, Any],
        left: dict[str, Any],
        right: dict[str, Any],
        merged: dict[str, Any],
    ) -> list[str]:
        lineage: list[str] = []
        for capsule in (base, left, right, merged):
            for item in capsule.get("lineage", []) or []:
                item_text = str(item)
                if item_text and item_text not in lineage:
                    lineage.append(item_text)
        for capsule in (base, left, right):
            ref = _capsule_ref(capsule)
            if ref and ref not in lineage:
                lineage.append(ref)
        return deepcopy(lineage)

