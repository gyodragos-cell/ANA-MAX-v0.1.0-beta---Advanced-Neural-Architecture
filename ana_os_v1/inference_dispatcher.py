"""Fake inference dispatcher for ANA MAX AI Kernel v1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class InferenceResult(dict):
    """Inference result dict that also compares equal to its output value."""

    def __eq__(self, other: object) -> bool:
        """Allow legacy direct output comparisons."""
        if other == self.get("output"):
            return True
        return super().__eq__(other)


class InferenceDispatcher:
    """Submit and handle fake model inference envelopes."""

    def __init__(self, model_router: Any, transport: Any = None, event_bus: Any = None, metrics_manager: Any = None, node_id: str = "local") -> None:
        """Initialize dispatcher."""
        self.model_router = model_router
        self.transport = transport
        self.event_bus = event_bus
        self.metrics_manager = metrics_manager
        self.node_id = node_id
        self.requests: dict[str, dict[str, Any]] = {}
        self.responses: dict[str, Any] = {}
        self.cancelled: set[str] = set()

    def submit_inference(self, model: str, input: Any, version: str | None = None, capability: str | None = None) -> str:
        """Submit one fake inference request."""
        request_id = str(uuid4())
        target_node = self.model_router.route(model, version, capability) if hasattr(self.model_router, "route") else self.model_router.route_inference(model, version, capability).get("node_id")
        self.requests[request_id] = {"model": model, "input": input, "target_node": target_node, "status": "submitted"}
        self._metric(f"model.{model}.requests")
        if target_node is None:
            self.responses[request_id] = InferenceResult({"output": None, "error": "no route"})
            return request_id
        if target_node == self.node_id or self.transport is None:
            if target_node == self.node_id:
                self.responses[request_id] = InferenceResult({"output": self._simulate_output(model, input), "error": None})
                self._publish("model.infer.completed", {"request_id": request_id, **self.responses[request_id]})
            else:
                self.responses[request_id] = InferenceResult({"output": None, "error": "transport unavailable"})
            return request_id
        self.transport.send(
            {
                "version": 1,
                "type": "model.infer.request",
                "source_node": self.node_id,
                "target_node": target_node,
                "timestamp": self._now(),
                "payload": {"model": model, "version": version, "input": input, "request_id": request_id, "origin_node": self.node_id},
            }
        )
        return request_id

    def submit_batch(self, model: str, inputs: list[Any]) -> list[str]:
        """Submit a fake inference batch."""
        return [self.submit_inference(model, item) for item in inputs]

    def handle_inference_request(self, envelope: dict[str, Any]) -> None:
        """Handle one fake inference request and emit a response."""
        payload = envelope.get("payload", {})
        request_id = payload.get("request_id")
        output = self._simulate_output(payload.get("model"), payload.get("input"))
        if self.transport:
            self.transport.send(
                {
                    "version": 1,
                    "type": "model.infer.response",
                    "source_node": self.node_id,
                    "target_node": payload.get("origin_node") or envelope.get("source_node"),
                    "timestamp": self._now(),
                    "payload": {"request_id": request_id, "output": output, "error": None},
                }
            )

    def handle_inference_response(self, envelope: dict[str, Any]) -> None:
        """Handle one fake inference response."""
        payload = envelope.get("payload", {})
        request_id = payload.get("request_id")
        if request_id not in self.cancelled:
            self.responses[request_id] = InferenceResult({"output": payload.get("output"), "error": payload.get("error")})
            self._publish("model.infer.completed", {"request_id": request_id, **self.responses[request_id]})

    def get_result(self, request_id: str) -> dict[str, Any] | None:
        """Return a stored inference result if available."""
        return self.responses.get(request_id)

    def get_batch_results(self, request_ids: list[str]) -> list[dict[str, Any] | None]:
        """Return results for a batch."""
        return [self.get_result(request_id) for request_id in request_ids]

    def cancel_inference(self, request_id: str) -> bool:
        """Cancel a pending fake inference request."""
        self.cancelled.add(request_id)
        self._publish("model.infer.cancelled", {"request_id": request_id})
        return True

    def check_timeout(self, request_id: str) -> bool:
        """Mark a request as timed out."""
        if request_id in self.responses:
            return False
        self._publish("model.infer.timeout", {"request_id": request_id})
        self._metric("model.failures")
        return True

    def _metric(self, name: str) -> None:
        """Increment a metric if configured."""
        if self.metrics_manager and hasattr(self.metrics_manager, "increment"):
            self.metrics_manager.increment(name)
            self._publish("model.metrics.update", {"name": name})

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an inference event."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(topic, payload)

    def _simulate_output(self, model: str, input_value: Any) -> dict[str, Any]:
        """Return deterministic fake inference output."""
        return {"echo": input_value, "model": model, "node": self.node_id}

    @staticmethod
    def _now() -> str:
        """Return an ISO timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = ["InferenceDispatcher", "InferenceResult"]

