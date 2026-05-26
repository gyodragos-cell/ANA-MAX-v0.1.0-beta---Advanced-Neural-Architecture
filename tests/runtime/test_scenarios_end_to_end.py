"""ANA MAX v22 scenario simulator end-to-end scaffolding tests."""

from core import ai_engine, ana_runtime, context_builder, execution_layer, observability, scenario_simulator, tool_router


def test_dirty_git_tree_scenario():
    """Simulator should run the dirty git tree scenario with fake results."""
    simulator = scenario_simulator.ScenarioSimulator()

    result = simulator.run_scenario("dirty_git_tree", {"task": "audit repo"}).to_dict()

    assert result["name"] == "dirty_git_tree"
    assert result["success"] is True
    assert result["router_decision"]["selected_tool"] == "git_operations"


def test_public_release_hygiene_scenario():
    """Simulator should run the public release hygiene scenario safely."""
    simulator = scenario_simulator.ScenarioSimulator()

    result = simulator.run_scenario("public_release_hygiene", {"task": "check public safety"}).to_dict()

    assert result["name"] == "public_release_hygiene"
    assert result["success"] is True
    assert "release_boundary_check" in result["notes"][0]


# TODO(v22): expand scenario coverage for CI bundles.
# TODO(v22): add deterministic replay fixtures and multi-step pipeline scenarios.