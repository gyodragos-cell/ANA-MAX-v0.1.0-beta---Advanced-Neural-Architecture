"""ANA MAX v22 tool router integration scaffolding tests."""

from core import ai_engine, ana_runtime, context_builder, execution_layer, observability, scenario_simulator, tool_router


def test_router_scores_tools():
    """Router should return a complete score shape for a fake tool."""
    router = tool_router.ToolRouter()

    score = router.score_tool("grep_file", {"task": "read files"}, {"confidence": 0.8}).to_dict()

    assert score["tool"] == "grep_file"
    assert "total" in score
    assert "requires_confirmation" in score
    assert isinstance(score["rationale"], str)


def test_router_selects_best_tool():
    """Router should pick a deterministic best candidate from fake tools."""
    router = tool_router.ToolRouter()

    decision = router.select_tool(
        ["file_operations", "grep_file", "desktop_control"],
        {"task": "read project files"},
        {"confidence": 0.8},
    ).to_dict()

    assert decision["selected_tool"] == "grep_file"
    assert len(decision["candidates"]) == 3
    assert decision["selected_score"]["requires_confirmation"] is False


# TODO(v22): add adaptive scoring and noisy-tool feedback tests.
# TODO(v22): add CI bundles for router policy scenarios.