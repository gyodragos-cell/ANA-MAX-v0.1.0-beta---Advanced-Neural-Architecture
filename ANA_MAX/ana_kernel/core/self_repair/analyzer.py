from __future__ import annotations

from ana.core.error_model.errors import ErrorPacket
from ana.core.self_repair.diagnostics import description_for_packet, pattern_from_packet
from ana.core.self_repair.persistence import LearnedRulesStore


class SelfRepairAnalyzer:
    def __init__(self, store: LearnedRulesStore) -> None:
        self.store = store

    def analyze(self, packet: ErrorPacket) -> dict[str, str]:
        pattern = pattern_from_packet(packet)
        record = self.store.find_pattern(pattern)
        if record:
            return {
                "pattern": pattern,
                "suggestion": record.get("suggestion", "Review learned repair guidance."),
                "source": "learned",
            }
        return {
            "pattern": pattern,
            "suggestion": description_for_packet(packet),
            "source": "diagnosis",
        }
