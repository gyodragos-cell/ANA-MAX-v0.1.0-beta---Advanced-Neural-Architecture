"""Pipeline manager for model and agent chains."""

from __future__ import annotations

from typing import Any, Callable


class PipelineManager:
    """Run simple synchronous pipelines."""

    def __init__(self, inference_dispatcher: Any = None, agent_manager: Any = None) -> None:
        """Initialize pipeline dependencies."""
        self.inference_dispatcher = inference_dispatcher
        self.agent_manager = agent_manager

    def run_model_pipeline(self, steps: list[str], value: Any) -> dict[str, Any]:
        """Run a sequence of fake model steps."""
        current = value
        request_ids = []
        for model in steps:
            request_id = self.inference_dispatcher.submit_inference(model, current) if self.inference_dispatcher else model
            request_ids.append(request_id)
            current = {"from": model, "input": current}
        return {"success": True, "output": current, "request_ids": request_ids}

    def run_agentic_pipeline(self, steps: list[Callable[[Any], Any]], value: Any) -> dict[str, Any]:
        """Run a chain of local callables."""
        current = value
        for step in steps:
            current = step(current)
        return {"success": True, "output": current}


__all__ = ["PipelineManager"]

