"""ANA MAX v22 observability scaffolding tests."""

from core import ai_engine, ana_runtime, context_builder, execution_layer, observability, scenario_simulator, tool_router


def test_event_recording():
    """Observability should record compact event payloads."""
    obs = observability.Observability()

    event = obs.record_event("runtime_start", {"stage": "test"}).to_dict()
    health = obs.get_health_snapshot()

    assert event["event_type"] == "runtime_start"
    assert health["event_count"] == 1
    assert health["status"] == "ok"


def test_tool_metrics_accumulation():
    """Observability should aggregate fake tool metrics."""
    obs = observability.Observability()

    obs.record_tool_metrics("grep_file", latency_ms=10, output_bytes=800, success=True)
    obs.record_tool_metrics("grep_file", latency_ms=20, output_bytes=400, success=False)
    stats = obs.get_tool_stats("grep_file")

    assert stats["calls"] == 2
    assert stats["successes"] == 1
    assert stats["failures"] == 1
    assert stats["estimated_tokens_saved"] > 0


# TODO(v22): integrate observability feedback with router scoring.
# TODO(v22): add long-term storage and dashboard export tests.