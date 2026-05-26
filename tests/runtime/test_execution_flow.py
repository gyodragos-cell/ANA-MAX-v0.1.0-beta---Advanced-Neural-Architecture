"""ANA MAX v22 execution layer scaffolding tests."""

from core import ai_engine, ana_runtime, context_builder, execution_layer, observability, scenario_simulator, tool_router


class FakeRegistry:
    """Fake registry for execution tests."""

    def __init__(self, payload: object):
        """Store the payload returned by fake executions."""
        self.payload = payload

    def execute(self, tool_name, **arguments):
        """Return a configured fake payload."""
        return self.payload


def test_execution_normalization():
    """Execution layer should normalize fake registry responses."""
    layer = execution_layer.ExecutionLayer(FakeRegistry({"success": True, "data": "ok", "message": "done"}))

    result = layer.execute("fake_tool", {"value": 1}).to_dict()

    assert result["tool"] == "fake_tool"
    assert result["success"] is True
    assert result["summary"] == "done"
    assert len(layer.audit_events) == 2


def test_execution_output_limits():
    """Execution layer should summarize output beyond the byte limit."""
    layer = execution_layer.ExecutionLayer(
        FakeRegistry({"success": True, "data": "x" * 80, "message": "large"}),
        {"max_text_bytes": 20, "summary_bytes": 16},
    )

    result = layer.execute("fake_tool", {}).to_dict()

    assert result["success"] is True
    assert result["truncated"] is True
    assert result["output_bytes"] == 80


# TODO(v22): add fallback tool execution tests.
# TODO(v22): add streaming output handling tests.
