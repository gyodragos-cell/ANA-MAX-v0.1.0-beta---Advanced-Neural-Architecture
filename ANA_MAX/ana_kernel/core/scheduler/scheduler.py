from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ana.core.error_model.errors import ValidationError


@dataclass(frozen=True)
class ScheduledTask:
    name: str
    dependencies: tuple[str, ...] = field(default_factory=tuple)


class DeterministicScheduler:
    def order(self, tasks: Iterable[ScheduledTask]) -> list[str]:
        task_map = {task.name: task for task in tasks}
        if len(task_map) == 0:
            return []
        for task in task_map.values():
            missing = [dep for dep in task.dependencies if dep not in task_map]
            if missing:
                raise ValidationError(
                    f"missing dependencies for {task.name}",
                    source="scheduler",
                    details={"missing": missing},
                )

        ordered: list[str] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                raise ValidationError(
                    "dependency cycle detected",
                    source="scheduler",
                    details={"task": name},
                )
            temporary.add(name)
            for dependency in sorted(task_map[name].dependencies):
                visit(dependency)
            temporary.remove(name)
            permanent.add(name)
            ordered.append(name)

        for name in sorted(task_map):
            visit(name)
        return ordered
