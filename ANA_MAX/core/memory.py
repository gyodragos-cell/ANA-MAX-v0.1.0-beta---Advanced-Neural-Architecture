# core.memory module
"""Core memory abstraction for ANA MAX.
Provides a simple `get_memory` function that returns a memory store instance.
Currently wraps the vector memory implementation.
"""

from .vector_memory import get_vector_memory, VectorMemoryCortex

# Alias for backward compatibility
Memory = VectorMemoryCortex

def get_memory(db_path: str | None = None) -> Memory:
    """Return a memory store instance.

    Args:
        db_path: Optional path to the SQLite DB file. If None, the default location is used.
    """
    return get_vector_memory(db_path)
