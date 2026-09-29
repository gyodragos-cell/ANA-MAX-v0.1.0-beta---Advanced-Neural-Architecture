from __future__ import annotations

from typing import Any, Callable, Mapping

from ana.core.error_model.errors import RoutingFailure, ValidationError


ShellHandler = Callable[[tuple[str, ...]], Mapping[str, Any]]


class DeterministicShellService:
    def __init__(self) -> None:
        self._handlers: dict[tuple[str, ...], ShellHandler] = {}

    def register(self, command: tuple[str, ...], handler: ShellHandler) -> None:
        if not command:
            raise ValidationError("command must not be empty", source="shell")
        self._handlers[tuple(command)] = handler

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        command = payload.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            raise ValidationError("command must be a list of strings", source="shell")
        key = tuple(command)
        handler = self._handlers.get(key)
        if handler is None:
            raise RoutingFailure(
                "command is not registered for deterministic shell execution",
                source="shell",
                details={"command": command},
            )
        return dict(handler(key))
