"""Recommend the smallest useful ANA MAX tool set for a task or failure."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


ANA_ROOT = Path(__file__).resolve().parents[1]
PERMISSION_MANIFEST = ANA_ROOT / "config" / "permission_manifest.json"


PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "project_state": {
        "headline": "Understand the current project state before editing.",
        "tools": [
            "code_context_pack",
            "workspace_situational_awareness",
            "project_navigator",
            "error_radar",
        ],
        "steps": [
            "Capture compact workspace/error context.",
            "Open only the relevant docs or files.",
            "Decide the smallest next action.",
        ],
    },
    "failure": {
        "headline": "Diagnose the first real failure and avoid retry loops.",
        "tools": [
            "error_radar",
            "agent_coach",
            "ana_memory",
            "debugger",
            "tool_healthcheck",
        ],
        "steps": [
            "Read the normalized error and auto_guidance if present.",
            "Search known fixes before another retry.",
            "Retry once with changed input, then verify.",
        ],
    },
    "code_change": {
        "headline": "Make a scoped code change and verify it.",
        "tools": [
            "code_context_pack",
            "graph_context_pack",
            "project_navigator",
            "code_search",
            "file_patch",
            "edit",
            "qa_testing",
            "tool_healthcheck",
        ],
        "steps": [
            "Build a compact UI + code-map + graph context pack.",
            "Inspect only the top matching file and nearby symbols.",
            "Patch the smallest safe surface.",
            "Run compile/tests or targeted healthcheck.",
        ],
    },
    "ui_desktop": {
        "headline": "Observe the UI before acting on it.",
        "tools": [
            "code_context_pack",
            "foreground_ui_snapshot",
            "windows_uia_bridge",
            "desktop_capture",
            "ocr_tool",
            "window_manager",
            "uia_click",
            "uia_type",
        ],
        "steps": [
            "Read visible UI state first.",
            "Choose one target and one action.",
            "Verify with a fresh snapshot after acting.",
        ],
        "guardrail": "UI mutation tools require explicit confirmation.",
    },
    "runtime_deep": {
        "headline": "Use under-the-hood diagnostics only when normal evidence is not enough.",
        "tools": [
            "tool_healthcheck",
            "event_stream",
            "binary_map",
            "input_api_probe",
            "windows_deep_sight",
            "windows_insight",
            "frida_instrument",
        ],
        "steps": [
            "Start with health and logs.",
            "Use binary_map for static executable/library insight before dynamic instrumentation.",
            "Inspect runtime/process state if the issue is below source-level visibility.",
            "For authorized game/input architecture research, generate an input_api_probe spec before any Frida execution.",
            "Use Frida only for authorized runtime instrumentation.",
        ],
        "guardrail": "Frida and deep diagnostics are controlled lab tools.",
    },
    "release_sync": {
        "headline": "Keep the public release clean and synced only when ship-safe.",
        "tools": [
            "privacy_shield",
            "tool_healthcheck",
            "session_checkpoint",
        ],
        "steps": [
            "Decide ship-safe vs lab-only.",
            "Remove private paths, logs, memory, screenshots, and secrets.",
            "Update README/setup/changelog/project map and tests.",
        ],
    },
    "memory_handoff": {
        "headline": "Persist useful context without saving raw private chat.",
        "tools": [
            "session_audit",
            "session_checkpoint",
            "session_rem_sleep",
            "conversation_learning",
            "ana_memory",
            "session_log_miner",
        ],
        "steps": [
            "Write a compact handoff or lesson.",
            "Include current goal, files changed, validation, risks, and sync status.",
            "Avoid private raw logs unless explicitly needed.",
        ],
    },
}


KEYWORDS = [
    ("ui_desktop", r"\b(ui|window|screen|desktop|click|type|ocr|screenshot|vision|button|fereastra|ecran)\b"),
    ("runtime_deep", r"\b(frida|hook|process|module|runtime|watchdog|under.?the.?hood|sub capota|deep|binary|exe|dll|so|raw input|directinput|getasynckeystate|keyboardstate|input api)\b"),
    ("release_sync", r"\b(release|github|public|sync|ship|publish|export|changelog)\b"),
    ("memory_handoff", r"\b(memory|handoff|checkpoint|lesson|istoric|history|remember|rem|sleep|somn|recalibrate|retrospective)\b"),
    ("memory_handoff", r"\b(audit|trust|score|proof|replay|integrity|hash)\b"),
    ("failure", r"\b(error|failed|failure|traceback|exception|bug|blocked|timeout|eroare|fail)\b"),
    ("code_change", r"\b(code|edit|patch|fix|implement|test|compile|refactor|fisier|file)\b"),
]


class ToolRouterTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="tool_router",
            description=(
                "Recommend a compact ANA MAX MCP tool stack for a task, error, "
                "or context. Read-only. Helps agents avoid using all tools blindly."
            ),
            parameters=[
                ToolParameter("task", "Task, goal, or problem description", "string", False, ""),
                ToolParameter("error", "Optional error text or failed tool result", "string", False, ""),
                ToolParameter(
                    "mode",
                    (
                        "auto, project_state, failure, code_change, ui_desktop, runtime_deep, "
                        "release_sync, memory_handoff, profile_status"
                    ),
                    "string",
                    False,
                    "auto",
                    choices=[
                        "auto",
                        "project_state",
                        "failure",
                        "code_change",
                        "ui_desktop",
                        "runtime_deep",
                        "release_sync",
                        "memory_handoff",
                        "profile_status",
                    ],
                ),
                ToolParameter("max_tools", "Maximum recommended tools", "integer", False, 5),
            ],
            category="ai_core",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        task = str(kwargs.get("task") or "")
        error = str(kwargs.get("error") or "")
        mode = str(kwargs.get("mode") or "auto")
        max_tools = max(1, min(int(kwargs.get("max_tools") or 5), 10))

        selected_mode = mode if mode != "auto" else self._classify(task, error)
        manifest = self._load_permission_manifest()
        if selected_mode == "profile_status":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=self._profile_status(manifest),
                message="Permission profile status ready.",
            )

        playbook = PLAYBOOKS.get(selected_mode, PLAYBOOKS["project_state"])
        tools, filtered = self._filter_tools_for_profiles(playbook["tools"], manifest, max_tools)
        profiles = self._tool_profile_map(tools, manifest)

        data = {
            "schema": "ana.tool_router.v1",
            "mode": selected_mode,
            "headline": playbook["headline"],
            "recommended_tools": tools,
            "tool_profiles": profiles,
            "active_profiles": manifest.get("global_settings", {}).get("active_profiles", []),
            "filtered_by_profile": filtered,
            "steps": playbook["steps"],
            "guardrail": playbook.get("guardrail", ""),
            "why_not_all_tools": "Use the smallest useful stack; escalate only when evidence requires it.",
        }
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=data,
            message=f"Recommended {len(tools)} tools for {selected_mode}.",
        )

    def _classify(self, task: str, error: str) -> str:
        text = f"{task}\n{error}".lower()
        if error.strip():
            return "failure"
        for mode, pattern in KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                return mode
        return "project_state"

    def _load_permission_manifest(self) -> Dict[str, Any]:
        try:
            return json.loads(PERMISSION_MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            return {"global_settings": {}, "tools": {}}

    def _filter_tools_for_profiles(
        self,
        tools: List[str],
        manifest: Dict[str, Any],
        max_tools: int,
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        active_profiles = manifest.get("global_settings", {}).get("active_profiles", [])
        tool_manifest = manifest.get("tools", {})
        recommended: List[str] = []
        filtered: List[Dict[str, Any]] = []

        for tool in tools:
            conf = tool_manifest.get(tool, {})
            profile = conf.get("profile")
            profiles = conf.get("profiles") or ([profile] if profile else [])
            allowed = conf.get("allowed", True)
            profile_active = not active_profiles or not profiles or bool(set(profiles) & set(active_profiles))
            if allowed and profile_active:
                recommended.append(tool)
                if len(recommended) >= max_tools:
                    break
                continue
            filtered.append({
                "tool": tool,
                "profiles": profiles,
                "allowed": allowed,
                "reason": "disabled" if not allowed else "inactive_profile",
            })

        return recommended, filtered

    def _tool_profile_map(self, tools: List[str], manifest: Dict[str, Any]) -> Dict[str, List[str]]:
        tool_manifest = manifest.get("tools", {})
        profiles: Dict[str, List[str]] = {}
        for tool in tools:
            conf = tool_manifest.get(tool, {})
            profile = conf.get("profile")
            values = conf.get("profiles") or ([profile] if profile else [])
            profiles[tool] = values
        return profiles

    def _profile_status(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        active_profiles = manifest.get("global_settings", {}).get("active_profiles", [])
        tool_manifest = manifest.get("tools", {})
        profile_counts: Dict[str, int] = {}
        inactive_tools: List[Dict[str, Any]] = []
        unprofiled_tools: List[str] = []

        for tool, conf in sorted(tool_manifest.items()):
            profile = conf.get("profile")
            profiles = conf.get("profiles") or ([profile] if profile else [])
            if not profiles:
                unprofiled_tools.append(tool)
            for item in profiles:
                profile_counts[item] = profile_counts.get(item, 0) + 1
            if active_profiles and profiles and not (set(profiles) & set(active_profiles)):
                inactive_tools.append({"tool": tool, "profiles": profiles})

        return {
            "schema": "ana.tool_router.profile_status.v1",
            "active_profiles": active_profiles,
            "tools_total": len(tool_manifest),
            "profile_counts": dict(sorted(profile_counts.items())),
            "inactive_tools": inactive_tools,
            "inactive_count": len(inactive_tools),
            "unprofiled_tools": unprofiled_tools,
            "unprofiled_count": len(unprofiled_tools),
        }
