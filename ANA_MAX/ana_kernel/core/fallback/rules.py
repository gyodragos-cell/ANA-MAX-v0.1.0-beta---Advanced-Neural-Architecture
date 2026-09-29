from ana.tools.registry.registry import FallbackToolSpec

# Declarative fallback rules for ANA MAX OS v2
# These rules are consumed by FallbackEngine and SelfRepairEngine.

def get_fallback_rules():
    return {
        "llm.complete": [
            FallbackToolSpec(
                name="llm_fallback_1",
                capability="llm.complete",
                tool="llm",
                reason="primary llm failure"
            ),
            FallbackToolSpec(
                name="llm_fallback_2",
                capability="llm.complete",
                tool="http",
                reason="llm unavailable, using http fallback"
            ),
        ],

        "http.get": [
            FallbackToolSpec(
                name="http_fallback_1",
                capability="http.get",
                tool="fs",
                reason="http unavailable, using fs fallback"
            )
        ],

        "shell.run": [
            FallbackToolSpec(
                name="shell_fallback_1",
                capability="shell.run",
                tool="fs",
                reason="shell unavailable, using fs fallback"
            )
        ],
    }


def resolve_declarative_fallbacks(capability, registry, rules=None):
    """
    Resolve declarative fallback rules for a given capability.
    Returns a list of registered FallbackToolSpec objects from the registry
    that match the declared fallback rules.
    
    This function looks up what has been declared for a capability,
    then returns any already-registered fallbacks from the registry.
    """
    declared = get_fallback_rules()
    fallback_specs = []
    
    # Get declared rules for this capability (for reference/logging)
    declared_rules = declared.get(capability, [])
    
    # Return already-registered fallbacks from the registry
    # These are the ones with actual handlers attached
    already_registered = registry.fallbacks_for(capability)
    
    return already_registered

