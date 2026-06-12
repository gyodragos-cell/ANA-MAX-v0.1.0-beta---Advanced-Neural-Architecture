"""Lab-only Windows input API probe wrapper.

This tool is for authorized local diagnostics of how an app uses Windows input
APIs, such as Raw Input registration. It is not a keylogger: execution is short,
target-whitelisted, confirmation-gated, and aggregate-only.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


ANA_ROOT = Path(__file__).resolve().parents[1]
SPEC_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_input_probe_spec.py"
AUTHORIZED_TARGETS_FILE = ANA_ROOT / "config" / "input_probe_authorized_targets.json"


def _load_spec_module():
    spec = importlib.util.spec_from_file_location("ana_input_probe_spec_runtime", SPEC_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Input probe spec script not found: {SPEC_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _authorized_targets() -> list[str]:
    if not AUTHORIZED_TARGETS_FILE.exists():
        return []
    try:
        payload = json.loads(AUTHORIZED_TARGETS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    targets = payload.get("authorized_targets", [])
    if not isinstance(targets, list):
        return []
    return sorted({str(item).strip() for item in targets if str(item).strip()})


def _is_authorized(target: str, authorized: list[str]) -> bool:
    target_norm = str(target).strip().lower()
    return any(target_norm == item.lower() for item in authorized)


class InputApiProbeTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="input_api_probe",
            description=(
                "Lab-only authorized probe for Windows input API usage. Generates or executes "
                "short Frida aggregate-only specs for Raw Input / keyboard-state APIs."
            ),
            parameters=[
                ToolParameter("operation", "list_authorized, spec, execute", "string", False, "spec", choices=["list_authorized", "spec", "execute"]),
                ToolParameter("target_process", "Authorized process name or PID", "string", False, ""),
                ToolParameter(
                    "api_name",
                    "Windows input API to inspect",
                    "string",
                    False,
                    "RegisterRawInputDevices",
                    choices=["RegisterRawInputDevices", "GetAsyncKeyState", "GetKeyboardState"],
                ),
                ToolParameter("duration", "Max probe duration in seconds, capped at 10", "integer", False, 5),
                ToolParameter("sample_limit", "Max aggregate samples, capped at 200", "integer", False, 100),
                ToolParameter("confirm", "Required true for execute", "boolean", False, False),
            ],
            category="diagnostics",
        )

    @property
    def run_in_worker_thread(self) -> bool:
        return False

    def execute(self, **kwargs: Any) -> ToolResult:
        operation = str(kwargs.get("operation") or "spec")
        target = str(kwargs.get("target_process") or "").strip()
        api_name = str(kwargs.get("api_name") or "RegisterRawInputDevices")
        duration = max(1, min(int(kwargs.get("duration") or 5), 10))
        sample_limit = max(1, min(int(kwargs.get("sample_limit") or 100), 200))
        confirm = self._bool(kwargs.get("confirm", False))
        authorized = _authorized_targets()

        if operation == "list_authorized":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "schema": "ana.input_api_probe.authorized.v1",
                    "authorized_targets": authorized,
                    "config_file": str(AUTHORIZED_TARGETS_FILE),
                    "lab_only": True,
                },
                message=f"{len(authorized)} authorized input probe targets.",
            )

        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="target_process is required")

        try:
            spec = _load_spec_module().build_spec(target, api_name, duration, sample_limit)
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to build input probe spec: {exc}")

        if operation == "spec":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "schema": "ana.input_api_probe.spec_result.v1",
                    "authorized": _is_authorized(target, authorized),
                    "spec": spec,
                },
                message="Generated lab-only input API probe spec.",
            )

        if operation != "execute":
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown operation: {operation}")

        if not _is_authorized(target, authorized):
            return ToolResult(
                status=ToolStatus.BLOCKED,
                error=f"Target {target} is not authorized for input API instrumentation.",
                data={"authorized_targets": authorized, "config_file": str(AUTHORIZED_TARGETS_FILE)},
            )
        if not confirm:
            return ToolResult(
                status=ToolStatus.REQUIRES_CONFIRMATION,
                message=f"Input API probe requires confirm=True for authorized target {target}.",
                data={"target_process": target, "api_name": api_name, "duration": duration},
            )

        return self._run_frida_probe(target, spec, duration)

    def _run_frida_probe(self, target: str, spec: dict[str, Any], duration: int) -> ToolResult:
        try:
            import frida
        except ImportError:
            return ToolResult(status=ToolStatus.ERROR, error="Frida not installed. Install frida for lab-only execution.")

        messages: list[Any] = []
        errors: list[str] = []
        session = None
        script_obj = None
        try:
            device = frida.get_local_device()
            session = device.attach(int(target) if str(target).isdigit() else target)
            script_obj = session.create_script(spec["frida_template"])

            def on_message(message, data):
                if message.get("type") == "send":
                    messages.append(message.get("payload"))
                elif message.get("type") == "error":
                    errors.append(str(message.get("stack") or message))

            script_obj.on("message", on_message)
            script_obj.load()
            time.sleep(duration + 0.25)
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Input API probe failed: {exc}")
        finally:
            try:
                if script_obj:
                    script_obj.unload()
            except Exception:
                pass
            try:
                if session:
                    session.detach()
            except Exception:
                pass

        summary = self._aggregate_messages(messages, spec)
        if errors:
            return ToolResult(status=ToolStatus.ERROR, error="\n".join(errors), data={"summary": summary})

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "schema": "ana.input_api_probe.result.v1",
                "mode": "lab-only",
                "policy": spec["policy"],
                "target_process": target,
                "api": spec["api"],
                "duration_sec": duration,
                "summary": summary,
            },
            message=f"Input API probe complete: {summary.get('calls_total', 0)} aggregate calls.",
        )

    def _aggregate_messages(self, messages: list[Any], spec: dict[str, Any]) -> dict[str, Any]:
        summary = {
            "target_process": spec["target"],
            "api": spec["api"],
            "calls_total": 0,
            "unique_codes_count": 0,
            "top_codes": [],
        }
        for payload in messages:
            if not isinstance(payload, dict) or payload.get("type") != "ana_input_probe_summary":
                continue
            summary["calls_total"] = int(payload.get("calls_total") or payload.get("calls_total".replace("_", "")) or 0)
            summary["unique_codes_count"] = int(payload.get("unique_codes_count") or 0)
            top_codes = payload.get("top_codes") or []
            if isinstance(top_codes, list):
                summary["top_codes"] = [
                    {"vk_code": int(item[0]), "count": int(item[1])}
                    for item in top_codes[:10]
                    if isinstance(item, (list, tuple)) and len(item) == 2
                ]
        return summary

    def _bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
