import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any
import os

# yaml used for reading global settings (optional)
try:
    import yaml
except Exception:
    yaml = None

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).parent / "reflex_rules.json"


def _load_rules() -> list:
    try:
        with open(_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("rules", [])
    except Exception as e:
        logger.warning(f"Could not load reflex_rules.json: {e}")
        return []


class ReflexDispatcher:
    """
    Autonomous reflex action dispatcher.
    Analyzes telemetry events against configurable rules from reflex_rules.json
    and fires alerts or remediation actions.
    """
    def __init__(self):
        self.rules = _load_rules()
        # Rolling window counters: {rule_id: [timestamps]}
        self._counters: Dict[str, list] = defaultdict(list)
        # Alert log (accessible by reflex_core / agent)
        self.alerts: list[Dict[str, Any]] = []

    def reload_rules(self):
        self.rules = _load_rules()

    def process_event(self, event: Dict[str, Any]):
        """Evaluates an event against all active reflex rules."""
        evt_type = event.get('type')
        data = event.get('data', {})

        if evt_type != 'API_CALL':
            return

        api = data.get('api', '')
        details = data.get('details', {})
        now = time.time()

        for rule in self.rules:
            trigger = rule.get('trigger', {})
            if trigger.get('api') != api:
                continue

            # --- Text-based rules (e.g. SetWindowTextW contains "Error") ---
            text_contains = trigger.get('text_contains')
            if text_contains:
                text_value = str(details.get('text', ''))
                if not any(pattern in text_value for pattern in text_contains):
                    continue
                self._fire_alert(rule, data)
                continue

            # --- Subkey-based rules (e.g. RegOpenKeyExW on Run keys) ---
            subkey_contains = trigger.get('subkey_contains')
            if subkey_contains:
                subkey_value = str(details.get('subkey', ''))
                if not any(pattern in subkey_value for pattern in subkey_contains):
                    continue
                self._fire_alert(rule, data)
                continue

            # --- Frequency-based rules (e.g. >20 CreateFileW in 3 seconds) ---
            window_seconds = trigger.get('window_seconds')
            min_occurrences = trigger.get('min_occurrences')
            if window_seconds and min_occurrences:
                rule_id = rule['id']
                self._counters[rule_id].append(now)
                # Prune old entries
                cutoff = now - window_seconds
                self._counters[rule_id] = [t for t in self._counters[rule_id] if t > cutoff]
                if len(self._counters[rule_id]) >= min_occurrences:
                    self._fire_alert(rule, data)
                    self._counters[rule_id] = []  # reset after alert
                continue

    def _fire_alert(self, rule: dict, data: dict):
        alert = {
            "timestamp": time.strftime('%H:%M:%S'),
            "rule_id": rule["id"],
            "severity": rule.get("severity", "info"),
            "message": rule.get("message", "Unknown reflex alert"),
            "trigger_data": data,
        }
        self.alerts.append(alert)
        # Keep alerts bounded
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-30:]

        severity = rule.get("severity", "info")
        if severity == "critical":
            logger.critical(f"[REFLEX CRITICAL] {alert['message']} | data={data}")
        elif severity == "high":
            logger.warning(f"[REFLEX HIGH] {alert['message']} | data={data}")
        else:
            logger.info(f"[REFLEX] {alert['message']} | data={data}")

        # OS-26 Auto-Remediation
        self._execute_remediation(rule, data)

    def _execute_remediation(self, rule: dict, data: dict):
        remediation = rule.get("remediation", {})
        if not remediation.get("enabled"):
            return

        action = remediation.get("action")
        pid = data.get("pid")
        if not pid:
            return

        # Helper to write audit lines
        def _write_audit(audit_path, rule_id, pid_val, proc_name_val, action_val, outcome, message):
            try:
                if not audit_path:
                    return
                audit_path.parent.mkdir(parents=True, exist_ok=True)
                entry = {
                    "ts": time.time(),
                    "rule_id": rule_id,
                    "pid": pid_val,
                    "proc_name": proc_name_val,
                    "action": action_val,
                    "outcome": outcome,
                    "message": message
                }
                with open(audit_path, "a", encoding="utf-8") as af:
                    af.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                logger.debug("Failed to write OS-26 audit log", exc_info=True)

        # Load global OS-26 config from settings.yaml if available
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        dry_run_default = True
        allow_kill = False
        rate_limit_seconds = 60
        audit_log_path = Path(__file__).parent.parent / "logs" / "os26_audit.jsonl"
        try:
            if yaml and settings_path.exists():
                with open(settings_path, "r", encoding="utf-8") as sf:
                    cfg = yaml.safe_load(sf) or {}
                    os26_cfg = cfg.get("os26", {}) if isinstance(cfg, dict) else {}
                    dry_run_default = os26_cfg.get("dry_run_default", dry_run_default)
                    allow_kill = os26_cfg.get("allow_kill", allow_kill)
                    rate_limit_seconds = os26_cfg.get("rate_limit_seconds", rate_limit_seconds)
                    audit_log_cfg = os26_cfg.get("audit_log")
                    if audit_log_cfg:
                        audit_log_path = Path(audit_log_cfg)
        except Exception as e:
            logger.warning(f"[OS-26 CONFIG] Failed to read settings.yaml: {e}")

        # rule-level override
        rule_dry_run = remediation.get("dry_run")
        dry_run = bool(dry_run_default) if rule_dry_run is None else bool(rule_dry_run)

        # If global policy forbids kill, force dry-run for kill actions
        if action == "kill_process" and not allow_kill:
            logger.warning(f"[OS-26 POLICY] kill_process requested but OS26 allow_kill is False. Simulating (dry-run).")
            dry_run = True

        try:
            import psutil
            process = psutil.Process(pid)
            proc_name = process.name().lower()

            SYSTEM_PROCESS_WHITELIST = {
                "explorer.exe", "svchost.exe", "csrss.exe", "winlogon.exe",
                "smss.exe", "services.exe", "lsass.exe", "wininit.exe",
                "system", "registry", "conhost.exe"
            }
            if proc_name in SYSTEM_PROCESS_WHITELIST:
                msg = f"[OS-26 GUARDRAIL] Blocked {action} on critical process: {proc_name} ({pid})"
                logger.warning(msg)
                _write_audit(audit_log_path, rule.get('id'), pid, proc_name, action, "blocked", msg)
                return

            # initialize last action tracker
            if not hasattr(self, "_last_action_time"):
                self._last_action_time = {}

            now_ts = time.time()
            last_ts = self._last_action_time.get(pid)
            if last_ts and (now_ts - last_ts) < rate_limit_seconds:
                msg = f"[OS-26 RATE] Skipping remediation for PID {pid}; cooldown active."
                logger.info(msg)
                _write_audit(audit_log_path, rule.get('id'), pid, proc_name, action, "throttled", msg)
                return

            if dry_run:
                msg = f"[OS-26 DRY_RUN] Would perform {action} on PID {pid} ({proc_name}) for rule {rule.get('id')}"
                logger.warning(msg)
                _write_audit(audit_log_path, rule.get('id'), pid, proc_name, action, "dry_run", msg)
                return

            if action == "kill_process":
                process.kill()
                msg = f"[OS-26 REMEDIATION] Terminated PID {pid} ({proc_name}) due to rule: {rule.get('id')}"
                logger.critical(msg)
                _write_audit(audit_log_path, rule.get('id'), pid, proc_name, action, "killed", msg)
            elif action == "suspend_process":
                process.suspend()
                msg = f"[OS-26 REMEDIATION] Suspended PID {pid} ({proc_name}) due to rule: {rule.get('id')}"
                logger.critical(msg)
                _write_audit(audit_log_path, rule.get('id'), pid, proc_name, action, "suspended", msg)

            # record action time
            self._last_action_time[pid] = now_ts

        except ImportError:
            logger.error("[OS-26 REMEDIATION] psutil is not installed; cannot remediate.")
            _write_audit(audit_log_path, rule.get('id'), pid, None, action, "error", "psutil missing")
        except Exception as e:
            logger.error(f"[OS-26 REMEDIATION] Failed to execute {action} on PID {pid}: {e}")
            _write_audit(audit_log_path, rule.get('id'), pid, None, action, "error", str(e))

    def get_active_alerts(self, max_age_seconds: int = 30) -> list:
        """Returns recent alerts for injection into agent context."""
        return self.alerts[-10:]


# Global dispatcher instance
dispatcher = ReflexDispatcher()
