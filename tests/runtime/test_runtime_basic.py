"""Basic ANA MAX v22 runtime integration scaffolding tests."""

from core import ai_engine, ana_runtime, context_builder, execution_layer, observability, scenario_simulator, tool_router
from core.input_layer import InputLayer


class FakeRegistry:
    """Small fake registry that never calls real tools."""

    def execute(self, tool_name, **arguments):
        """Return a deterministic fake tool result."""
        return {
            "success": True,
            "data": {"tool": tool_name, "arguments": arguments},
            "message": "fake execution ok",
        }


def _runtime():
    """Build a fully fake runtime for scaffold tests."""
    return ana_runtime.ANAMaxRuntime(
        InputLayer("C:/Users/billy/Desktop/ana_dev"),
        context_builder.ContextBuilder(),
        ai_engine.AIEngine(),
        tool_router.ToolRouter(),
        execution_layer.ExecutionLayer(FakeRegistry()),
        observability.Observability(),
    )


def test_runtime_initialization():
    """Runtime should keep injected modules and initial state."""
    runtime = _runtime()

    assert runtime.input_layer is not None
    assert runtime.context_builder is not None
    assert runtime.runtime_state["runs"] == 0
    assert runtime.safety_envelope["allow_mutation"] is False


def test_runtime_single_run():
    """Runtime should complete one fake observe-plan-route-execute cycle."""
    runtime = _runtime()

    summary = runtime.run({"task": "inspect workspace", "workspace": "C:/Users/billy/Desktop/ana_dev"})
    data = summary.to_dict()

    assert data["success"] is True
    assert data["route"]["selected_tool"]
    assert data["result"]["success"] is True
    assert len(data["audit_events"]) >= 4


# TODO(v22): add full integration tests with real registry in a controlled lab.
# TODO(v22): add multi-step pipeline runtime tests.
