"""OS-21 capsule store.

This module is metadata-only. It keeps recon capsules in-memory so future
OS-21 slices can build sync, diff, and merge flows without touching OS-20.1
runtime behavior.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping

from .capsule_schema import RECON_CAPSULE_SCHEMA, ReconCapsuleSchema


STORE_SCHEMA = "ana.os21.capsule_store.v1"
DIFF_SCHEMA = "ana.os21.capsule_diff.v1"


def _normalize_value(value: Any) -> Any:
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


def _merge_lists(left: list[Any], right: list[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for item in left + right:
        normalized = _normalize_value(item)
        key = json.dumps(normalized, ensure_ascii=True, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _merge_values(left: Any, right: Any) -> Any:
    if isinstance(left, dict) and isinstance(right, dict):
        merged: dict[str, Any] = {}
        for key in sorted(set(left) | set(right), key=str):
            if key in left and key in right:
                merged[key] = _merge_values(left[key], right[key])
            elif key in left:
                merged[key] = _normalize_value(left[key])
            else:
                merged[key] = _normalize_value(right[key])
        return merged
    if isinstance(left, list) and isinstance(right, list):
        return _merge_lists(left, right)
    return _normalize_value(right)


class CapsuleStore:
    """Simple in-memory capsule registry."""

    def __init__(self, initial_capsules: list[Any] | None = None) -> None:
        self._capsules: dict[str, dict[str, Any]] = {}
        for capsule in initial_capsules or []:
            self.save_capsule(capsule)

    def save_capsule(self, capsule: Any) -> dict[str, Any]:
        capsule_dict = _coerce_capsule(capsule)
        capsule_id = str(capsule_dict.get("capsule_id", "")).strip()
        if not capsule_id:
            raise ValueError("capsule_id is required")

        existing = self._capsules.get(capsule_id)
        if existing is not None:
            merged = self.merge_capsules(existing, capsule_dict)
            previous_version = str(existing.get("version", "")).strip()
            previous_ref = f"{capsule_id}@{previous_version}" if previous_version else capsule_id
            lineage = list(merged.get("lineage") or [])
            if previous_ref not in lineage:
                lineage.append(previous_ref)
            merged["lineage"] = lineage
            capsule_dict = merged
        else:
            capsule_dict = _normalize_value(capsule_dict)

        capsule_dict["schema"] = capsule_dict.get("schema") or RECON_CAPSULE_SCHEMA
        self._capsules[capsule_id] = deepcopy(capsule_dict)
        return deepcopy(capsule_dict)

    def load_capsule(self, capsule_id: str) -> dict[str, Any] | None:
        capsule = self._capsules.get(str(capsule_id))
        if capsule is None:
            return None
        return deepcopy(capsule)

    def list_capsules(self) -> list[str]:
        return sorted(self._capsules)

    def diff_capsules(self, left: Any, right: Any) -> dict[str, Any]:
        left_capsule = _coerce_capsule(left)
        right_capsule = _coerce_capsule(right)

        left_keys = set(left_capsule)
        right_keys = set(right_capsule)
        all_keys = sorted(left_keys | right_keys, key=str)
        changed: list[str] = []
        added: list[str] = []
        removed: list[str] = []
        field_diffs: dict[str, Any] = {}

        for key in all_keys:
            if key not in left_capsule:
                added.append(key)
                continue
            if key not in right_capsule:
                removed.append(key)
                continue
            left_value = _normalize_value(left_capsule[key])
            right_value = _normalize_value(right_capsule[key])
            if left_value != right_value:
                changed.append(key)
                field_diffs[key] = {"left": left_value, "right": right_value}

        return {
            "schema": DIFF_SCHEMA,
            "left_id": left_capsule.get("capsule_id", ""),
            "right_id": right_capsule.get("capsule_id", ""),
            "added_keys": added,
            "removed_keys": removed,
            "changed_keys": changed,
            "field_diffs": field_diffs,
        }

    def merge_capsules(self, left: Any, right: Any) -> dict[str, Any]:
        left_capsule = _coerce_capsule(left)
        right_capsule = _coerce_capsule(right)
        merged = _merge_values(left_capsule, right_capsule)

        merged_id = str(left_capsule.get("capsule_id") or right_capsule.get("capsule_id") or "").strip()
        if merged_id:
            merged["capsule_id"] = merged_id
        merged["schema"] = merged.get("schema") or RECON_CAPSULE_SCHEMA
        merged["version"] = str(merged.get("version", "1.0"))
        merged["lineage"] = list(merged.get("lineage") or [])
        return merged

