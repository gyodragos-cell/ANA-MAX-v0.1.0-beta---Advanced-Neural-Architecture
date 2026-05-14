# ===========================================================================
# PATCH main.py - adauga blocul de mai jos in _register_all_tools()
# INAINTE de linia:  return loaded
# (dupa blocul desktop_tools, in jurul liniei 249)
# ===========================================================================

    # AI Core adapters (context_engine, proactive_interrupt, self_evolving,
    # memory_cortex, orchestrator, context_bridge, window_manager)
    try:
        from tools.tool_adapters import ANA_ADAPTER_CLASSES
        for AdapterClass in ANA_ADAPTER_CLASSES:
            try:
                instance = AdapterClass()
                registry.register(instance)
                loaded += 1
                print(f"  [OK] {instance.get_definition().name} (AI CORE)")
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "AI Core adapter skipped %s: %s", AdapterClass.__name__, e
                )
    except ImportError as e:
        logging.getLogger(__name__).warning("tool_adapters.py nu a putut fi incarcat: %s", e)

    return loaded


# ===========================================================================
# Unde exact se adauga in main.py:
#
#   ...
#   # Incarca AI Desktop Control tools (2026-05-13)
#   for module_path, class_name in desktop_tools:
#       try:
#           ...
#       except Exception as e:
#           logging.getLogger(__name__).warning(...)
#
#   ← ADAUGA BLOCUL DE MAI SUS AICI
#
#   return loaded         ← linia existenta, ramane la sfarsit
# ===========================================================================
