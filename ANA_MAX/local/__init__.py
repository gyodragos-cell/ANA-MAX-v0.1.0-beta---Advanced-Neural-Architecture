"""ANA MAX optional local runtime helpers."""

__all__ = [
    "LocalLLMBackend",
    "LocalLLMConfig",
    "OS22BootSequence",
    "run_os22_doctor",
    "RAGBridge",
    "build_agent_boot_banner",
    "get_agent_foundation_status",
    "get_self_healing_status",
    "load_agent_foundation",
    "diagnose_tool_request",
    "diagnose_rag_context",
    "preflight_diagnostics",
    "resolve_rag_conflicts",
    "stabilize_reasoning_text",
    "summarize_agent_foundation",
    "compose_system_prompt",
    "available_prompt_profiles",
    "get_profile",
    "get_rag_bridge",
    "get_system_prompt",
    "get_tool_specs",
    "load_tool_manifest",
    "get_tool_manifest",
]


def __getattr__(name: str):
    if name == "LocalLLMBackend":
        from .local_llm_backend import LocalLLMBackend

        return LocalLLMBackend
    if name == "LocalLLMConfig":
        from .local_llm_backend import LocalLLMConfig

        return LocalLLMConfig
    if name == "OS22BootSequence":
        from .os22_boot import OS22BootSequence

        return OS22BootSequence
    if name == "run_os22_doctor":
        from .os22_doctor import run_os22_doctor

        return run_os22_doctor
    if name == "RAGBridge":
        from .rag_bridge import RAGBridge

        return RAGBridge
    if name == "build_agent_boot_banner":
        from .agent_boot_banner import build_agent_boot_banner

        return build_agent_boot_banner
    if name == "get_agent_foundation_status":
        from .agent_foundation import get_agent_foundation_status

        return get_agent_foundation_status
    if name == "get_self_healing_status":
        from .agent_self_healing import get_self_healing_status

        return get_self_healing_status
    if name == "diagnose_tool_request":
        from .agent_self_healing import diagnose_tool_request

        return diagnose_tool_request
    if name == "diagnose_rag_context":
        from .agent_self_healing import diagnose_rag_context

        return diagnose_rag_context
    if name == "preflight_diagnostics":
        from .agent_self_healing import preflight_diagnostics

        return preflight_diagnostics
    if name == "resolve_rag_conflicts":
        from .agent_self_healing import resolve_rag_conflicts

        return resolve_rag_conflicts
    if name == "stabilize_reasoning_text":
        from .agent_self_healing import stabilize_reasoning_text

        return stabilize_reasoning_text
    if name == "load_agent_foundation":
        from .agent_foundation import load_agent_foundation

        return load_agent_foundation
    if name == "summarize_agent_foundation":
        from .agent_foundation import summarize_agent_foundation

        return summarize_agent_foundation
    if name == "compose_system_prompt":
        from .prompt_engine import compose_system_prompt

        return compose_system_prompt
    if name == "available_prompt_profiles":
        from .prompt_profiles import available_prompt_profiles

        return available_prompt_profiles
    if name == "get_profile":
        from .prompt_profiles import get_profile

        return get_profile
    if name == "get_rag_bridge":
        from .rag_bridge import get_rag_bridge

        return get_rag_bridge
    if name == "get_system_prompt":
        from .prompt_profiles import get_system_prompt

        return get_system_prompt
    if name == "get_tool_specs":
        from .prompt_engine import get_tool_specs

        return get_tool_specs
    if name == "load_tool_manifest":
        from ANA_MAX.tools.tool_manifest_loader import load_tool_manifest

        return load_tool_manifest
    if name == "get_tool_manifest":
        from ANA_MAX.tools.tool_manifest_loader import get_tool_manifest

        return get_tool_manifest
    raise AttributeError(name)
