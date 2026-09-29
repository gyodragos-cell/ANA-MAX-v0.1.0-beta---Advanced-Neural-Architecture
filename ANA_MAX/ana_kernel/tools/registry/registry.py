from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from ana.core.error_model.errors import ValidationError


ToolHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: str
    handler: ToolHandler
    priority: int = 100
    requirements: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FallbackToolSpec:
    name: str
    capability: str
    handler: ToolHandler | None = None
    tool: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            fallback_name = self.tool or self.capability
            object.__setattr__(self, "name", fallback_name or "fallback")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, list[ToolSpec]] = {}
        self._fallbacks: dict[str, list[FallbackToolSpec]] = {}
        # Performance: Cache for capability lookups
        self._capability_cache: dict[str, list[ToolSpec]] = {}
        self._cache_dirty = True

    def register(self, spec: ToolSpec) -> None:
        self._validate(spec.name, spec.capability)
        self._tools.setdefault(spec.capability, []).append(spec)
        self._tools[spec.capability].sort(key=lambda item: (item.priority, item.name))
        self._cache_dirty = True

    def register_skill(self, spec: ToolSpec) -> None:
        self._validate(spec.name, spec.capability)
        # Skill handlers are registered as regular tool entries with lower priority
        self._tools.setdefault(spec.capability, []).append(spec)
        self._tools[spec.capability].sort(key=lambda item: (item.priority, item.name))
        self._cache_dirty = True

    def register_fallback(self, spec: FallbackToolSpec) -> None:
        self._validate(spec.name, spec.capability)
        self._fallbacks.setdefault(spec.capability, []).append(spec)

    def tools_for(self, capability: str) -> list[ToolSpec]:
        # Performance: Use cache when available
        if self._cache_dirty:
            self._rebuild_cache()
        return list(self._capability_cache.get(capability, ()))

    def fallbacks_for(self, capability: str) -> list[FallbackToolSpec]:
        return list(self._fallbacks.get(capability, ()))

    def capabilities(self) -> list[str]:
        return sorted(self._tools)

    def fallback_capabilities(self) -> list[str]:
        return sorted(self._fallbacks)

    def all_capabilities(self) -> list[str]:
        return sorted(set(self._tools) | set(self._fallbacks))

    def _rebuild_cache(self) -> None:
        """Rebuild the capability cache."""
        self._capability_cache = {k: list(v) for k, v in self._tools.items()}
        self._cache_dirty = False

    def _validate(self, name: str, capability: str) -> None:
        if not name or not capability:
            raise ValidationError("tool name and capability are required", source="registry")
        # Security: Validate name doesn't contain dangerous characters
        dangerous_chars = ['|', '&', ';', '`', '$', '(', ')', '<', '>']
        if any(char in name for char in dangerous_chars):
            raise ValidationError("tool name contains dangerous characters", source="registry")
        if any(char in capability for char in dangerous_chars):
            raise ValidationError("tool capability contains dangerous characters", source="registry")
