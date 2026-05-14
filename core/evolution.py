"""
ANA MAX - Evolution Engine

Lightweight self-evolution support used by tests and MCP integrations.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SafetyMode(Enum):
    """Safety levels for automated changes."""

    OBSERVE = "observe"
    SUGGEST = "suggest"
    SUPERVISED = "supervised"
    AUTONOMOUS = "autonomous"


@dataclass
class LearningEntry:
    """A single learning observation."""

    timestamp: float
    category: str
    source: str
    content: str
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionConfig:
    """Configuration for the evolution engine."""

    enabled: bool = False
    safety_mode: SafetyMode = SafetyMode.OBSERVE
    autonomous_study: bool = False
    learn_from_conversations: bool = True
    generate_capabilities: bool = False
    auto_evolve_tools: bool = False
    study_interval_minutes: int = 60
    max_changes_per_day: int = 10
    require_human_review: bool = True
    require_backup: bool = True
    auto_rollback_on_error: bool = True
    evolution_log_path: str = "logs/evolution.jsonl"
    backup_directory: str = "backups"


class SelfEvolutionEngine:
    """Minimal evolution engine for observations and safe proposals."""

    def __init__(
        self,
        config: Optional[EvolutionConfig] = None,
        memory: Any = None,
        sandbox: Any = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self.memory = memory
        self.sandbox = sandbox
        self.learning_queue: List[LearningEntry] = []
        self.pending_improvements: List[Dict[str, Any]] = []
        self.changes_today = 0
        self.total_observations = 0
        self.total_improvements_proposed = 0
        self._study_thread: Optional[threading.Thread] = None
        self._stop_study = threading.Event()
        self._ensure_runtime_paths()

    def _ensure_runtime_paths(self) -> None:
        Path(self.config.backup_directory).mkdir(parents=True, exist_ok=True)
        log_path = Path(self.config.evolution_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def observe_conversation(
        self,
        user_message: str,
        ai_response: str,
        tool_calls: Optional[List[Any]] = None,
        success: bool = True,
    ) -> LearningEntry:
        """Record a conversation outcome for later analysis."""

        category = "success" if success else "failure"
        entry = LearningEntry(
            timestamp=time.time(),
            category=category,
            source="conversation",
            content=f"USER: {user_message}\nAI: {ai_response}",
            confidence=0.8 if success else 0.6,
            metadata={"tool_calls": tool_calls or [], "success": success},
        )
        self.learning_queue.append(entry)
        self.total_observations += 1
        self._append_log({"event": "observe_conversation", "entry": asdict(entry)})
        return entry

    def start_autonomous_study(self) -> None:
        """Start a lightweight background study loop."""

        if self._study_thread and self._study_thread.is_alive():
            return

        self._stop_study.clear()
        self._study_thread = threading.Thread(target=self._study_loop, daemon=True)
        self._study_thread.start()

    def stop_autonomous_study(self) -> None:
        """Stop the background study loop."""

        self._stop_study.set()
        if self._study_thread and self._study_thread.is_alive():
            self._study_thread.join(timeout=1.0)

    def _study_loop(self) -> None:
        interval = max(1, int(self.config.study_interval_minutes * 60))
        while not self._stop_study.wait(interval):
            self._append_log({"event": "autonomous_study_tick", "timestamp": time.time()})

    def propose_new_capability(self, description: str, code_template: str) -> Dict[str, Any]:
        """Create a capability proposal without applying it."""

        proposal = {
            "id": f"cap_{uuid.uuid4().hex[:8]}",
            "description": description,
            "code": code_template,
            "status": "proposed",
            "created_at": time.time(),
            "safety_mode": self.config.safety_mode.value,
        }
        self.pending_improvements.append(proposal)
        self.total_improvements_proposed += 1
        self._append_log({"event": "propose_capability", "proposal": proposal})
        return proposal

    def propose_capability(self, description: str, code_template: str) -> Dict[str, Any]:
        """Backward-compatible alias used by older integrations."""

        return self.propose_new_capability(description, code_template)

    def set_mode(self, mode: SafetyMode) -> None:
        self.config.safety_mode = mode
        self._append_log({"event": "set_mode", "mode": mode.value})

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "mode": self.config.safety_mode.value,
            "learning_queue_size": len(self.learning_queue),
            "pending_improvements": len(self.pending_improvements),
            "changes_today": self.changes_today,
            "autonomous_study_running": bool(self._study_thread and self._study_thread.is_alive()),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_observations": self.total_observations,
            "total_improvements_proposed": self.total_improvements_proposed,
            "learning_queue_size": len(self.learning_queue),
            "pending_improvements": len(self.pending_improvements),
            "changes_today": self.changes_today,
        }

    def _create_backup(self) -> str:
        """Create a lightweight backup marker."""

        backup_id = f"backup_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        target = Path(self.config.backup_directory) / f"{backup_id}.json"
        payload = {
            "backup_id": backup_id,
            "created_at": time.time(),
            "status": self.get_status(),
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._append_log({"event": "create_backup", "backup_id": backup_id, "path": str(target)})
        return backup_id

    def _generate_plugin_code(self, proposal: Dict[str, Any]) -> str:
        """Generate a simple plugin file from a proposal."""

        description = proposal.get("description", "Generated plugin")
        return (
            "PLUGIN_INFO = {\n"
            f"    'id': '{proposal.get('id', 'generated')}',\n"
            f"    'description': {description!r},\n"
            "    'version': '0.1.0',\n"
            "}\n\n"
            "def plugin_function(*args, **kwargs):\n"
            "    return {\n"
            "        'success': True,\n"
            "        'message': 'Plugin executed',\n"
            "        'args': args,\n"
            "        'kwargs': kwargs,\n"
            "    }\n"
        )

    def _append_log(self, payload: Dict[str, Any]) -> None:
        try:
            with Path(self.config.evolution_log_path).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Evolution log write skipped: %s", exc)


_ENGINE: Optional[SelfEvolutionEngine] = None


def get_evolution_engine() -> SelfEvolutionEngine:
    """Return a singleton evolution engine using project config."""

    global _ENGINE
    if _ENGINE is None:
        from core.config import config as app_config
        from core.memory import get_memory

        cfg = EvolutionConfig(
            enabled=bool(app_config.get("evolution.enabled", False)),
            safety_mode=SafetyMode(app_config.get("evolution.mode", "observe")),
            autonomous_study=bool(app_config.get("evolution.autonomous_study", False)),
            generate_capabilities=bool(app_config.get("evolution.auto_evolve_tools", False)),
            max_changes_per_day=int(app_config.get("evolution.max_changes_per_day", 10) or 10),
            require_backup=bool(app_config.get("evolution.require_backup", True)),
            evolution_log_path=str(app_config.get("evolution.evolution_log_path", "logs/evolution.jsonl")),
            backup_directory=str(app_config.get("evolution.backup_directory", "backups")),
        )
        _ENGINE = SelfEvolutionEngine(config=cfg, memory=get_memory(), sandbox=None)
    return _ENGINE

