"""ANA MAX reasoning graph layer."""

__all__ = ["ReasoningGraphBuilder", "ReasoningGraphQuery"]


def __getattr__(name: str):
    if name == "ReasoningGraphBuilder":
        from .reasoning_graph_builder import ReasoningGraphBuilder

        return ReasoningGraphBuilder
    if name == "ReasoningGraphQuery":
        from .reasoning_graph_query import ReasoningGraphQuery

        return ReasoningGraphQuery
    raise AttributeError(name)
