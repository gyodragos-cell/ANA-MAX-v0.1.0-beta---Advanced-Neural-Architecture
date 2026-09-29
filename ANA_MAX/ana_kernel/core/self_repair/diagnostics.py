from __future__ import annotations

from ana.core.error_model.errors import ErrorPacket


def pattern_from_packet(packet: ErrorPacket) -> str:
    capability = packet.details.get("capability") or packet.details.get("service") or "unknown"
    return f"{packet.code}:{capability}"


def description_for_packet(packet: ErrorPacket) -> str:
    if packet.code == "ROUTING_FAILURE":
        return "Routing failure detected: no registered tool or skill matches the requested capability."
    if packet.code == "VALIDATION_ERROR":
        return "Input validation failed for the requested capability."
    if packet.code == "SANDBOX_VIOLATION":
        return "Sandbox policy rejected the request due to an unauthorized capability or payload size."
    return "A recoverable or fatal error occurred; review the packet details for diagnostics."
