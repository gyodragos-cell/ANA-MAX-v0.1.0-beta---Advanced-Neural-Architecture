"""ANA MAX OS-21 metadata kernel layer."""

__all__ = [
    "AgentCapabilityRegistry",
    "OS21Finalizer",
    "OS21BaselineLock",
    "ToolVirtualizationContracts",
]


def __getattr__(name: str):
    if name == "AgentCapabilityRegistry":
        from .agent_capability_registry import AgentCapabilityRegistry

        return AgentCapabilityRegistry
    if name == "ToolVirtualizationContracts":
        from .tool_virtualization_contracts import ToolVirtualizationContracts

        return ToolVirtualizationContracts
    if name == "OS21Finalizer":
        from .os21_finalizer import OS21Finalizer

        return OS21Finalizer
    if name == "OS21BaselineLock":
        from .os21_baseline_lock import OS21BaselineLock

        return OS21BaselineLock
    raise AttributeError(name)
