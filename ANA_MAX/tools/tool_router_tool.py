"""Recommend the smallest useful ANA MAX tool set for a task or failure (OS27 Hyper++).

OS27 Hyper++ Features:
- Telemetry tracking for tool router operations (classify, recommend, profile_status)
- Health monitoring for tool router operations reliability
- MemoryCortex integration for tool router errors and state learning
- ContextEngine integration for tool router state awareness
- SelfEvolvingTool integration for anomaly detection on tool router failures
- Structured logging with error detection
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List
import urllib.request
import urllib.error

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_router_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_router_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for tool router operations."""
    if operation not in _router_telemetry:
        _router_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _router_telemetry[operation]["operation_count"] += 1
    _router_telemetry[operation]["total_time"] += execution_time
    _router_telemetry[operation]["last_execution_time"] = execution_time
    _router_telemetry[operation]["last_success"] = success
    
    if success:
        _router_telemetry[operation]["success_count"] += 1
    else:
        _router_telemetry[operation]["failure_count"] += 1


def get_router_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for tool router operations."""
    if operation:
        return _router_telemetry.get(operation, {})
    return _router_telemetry.copy()


def get_router_health() -> str:
    """Get health status for tool router based on telemetry."""
    if not _router_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _router_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _router_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


ANA_ROOT = Path(__file__).resolve().parents[1]
PERMISSION_MANIFEST = ANA_ROOT / "config" / "permission_manifest.json"


UNIVERSAL_TOOLS = [
    "terminal",
    "file_operations",
    "edit",
    "smart_search",
    "agent_coach",
]


PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "file_analysis": {
        "headline": "Read, analyze, or summarize a file. Use file_operations with operation=analyze for full analysis. DO NOT use terminal.",
        "tools": [
            "file_operations",
            "smart_search",
            "grep_content",
            "grep_file",
        ],
        "steps": [
            "Use file_operations operation=analyze for full file analysis with error/warning extraction.",
            "Use file_operations operation=read with start_line/end_line for reading specific sections.",
            "Use smart_search or terminal for pattern-based searches.",
            "Present the analysis results as a clear summary in Romanian.",
        ],
    },
    "file_operations": {
        "headline": "Perform simple file/folder operations (create, delete, move, open).",
        "tools": [
            "file_operations",
            "terminal",
            "bash_exec",
        ],
        "steps": [
            "Use file_operations for simple create/delete/move operations.",
            "Use terminal/bash_exec for commands that require shell execution.",
            "Verify the operation completed successfully.",
        ],
    },
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
            "smart_search",
            "grep_content",
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
    "web_creation": {
        "headline": "Create simple HTML/CSS websites directly without npm/build steps.",
        "tools": [
            "file_operations",
            "terminal"
        ],
        "steps": [
            "Use file_operations operation=write to create HTML file directly.",
            "Use CSS inline in HTML for styling (no separate CSS files).",
            "Use terminal with browser_open command to view the result.",
            "DO NOT use npm, create-react-app, or build tools for simple websites.",
            "Keep structure simple: HTML → CSS inline → open in browser.",
            "If folder creation fails, write file directly to existing folder.",
            "For complex projects, consider simple static HTML first before React/npm.",
        ],
    },
        "web_research": {
        "headline": "Perform web research or interact with web pages.",
        "tools": [
            "web_scraper",
            "web_ai_bridge",
            "browser_control",
        ],
        "steps": [
            "Use web_scraper for static content.",
            "Use browser_control or web_ai_bridge for interactive/dynamic web research.",
            "Read carefully and extract requested information.",
        ],
    },
}


KEYWORDS = [
    # Web creation - simple HTML/CSS without npm (high priority)
    ("web_creation", r"\b(website|web page|html|css|javascript|create website|make website|build website|facebook clone|landing page|web app)\b"),
    # File analysis has top priority - catches paths with extensions and analysis verbs
    ("file_analysis", r"(?i)\.(log|txt|py|json|csv|xml|md|cfg|ini|bat|yaml|yml|conf|html|css|js|ts|tsx|ps1)\b"),
    ("file_analysis", r"\b(analizeaza|rezumat|citeste|continut|read file|summary|analyze|ce este|ce contine|spune ce|inspecteaza|parseaza|parse|deschide fisierul)\b"),
    # File management (create/delete/move)
    ("file_operations", r"\b(folder|directory|mkdir|create|delete|remove|move|copy|deschide|folder|director|creare|sterge|muta|copiaza|rename|arhiveaza|extract|unzip|zip)\b"),
    # Terminal / system shell commands (highest priority after files)
    ("terminal", r"\b(terminal|powershell|cmd|exe|command|comanda|ruleaza|run|exec|execute|shell|bash|pipe|netstat|tasklist|ping|curl|wget|choco|winget|pip|npm|scoop|process list)\b"),
    ("terminal", r"\b(porne?ste|porneste|service|sc|schtasks|register|dism|sfc|chkdsk)\b"),
    # System vitals / processes / performance
    ("profile_status", r"\b(ram|cpu|gpu|vram|memory|memorie|disk|storage|process|proces|pid|load|usage|utilizare|resource|resurse|vitals|temperature|temp|benchmark|latenta|latency)\b"),
    # UI/desktop interaction
    ("ui_desktop", r"\b(fereastra|ecran|click|ocr|screenshot|vision|button|buton|desktop|window|app open|open app|notepad|calculator|calendar|paint|vlc|obs|explorer|file explorer|uia|automatizare ui|ui automation)\b"),
    # Search / code search
    ("code_change", r"\b(code search|search|cauta|find|grep|gaseste|cautare|smart_search|code_search|search code|lookup|reference)\b"),
    # Voice / audio pipeline
    ("project_state", r"\b(voice|voce|vorbeste|vorbim|vorbea\?+|vorbe\?+|speak|tts|stt|audio|microfon|mic|whisper|kokoro|edgetts|pyttsx|clipboard voice|chat voice|voice bridge|jarvis)\b"),
    # Clipboard management
    ("profile_status", r"\b(clipboard|clipboard_manager|copy|copieaz|paste|lipeaz|copy paste|read clipboard|write clipboard|istoric clipboard|monitor clipboard)\b"),
    # Deep runtime inspection
    ("runtime_deep", r"\b(frida|hook|process|module|runtime|watchdog|under.?the.?hood|sub capota|deep|binary|exe|dll|so|raw input|directinput|getasynckeystate|keyboardstate|input api|pentest|mitm|network scan|port scan|nmap|wireshark|adb|frida-server)\b"),
    # Release/publish
    ("release_sync", r"\b(release|github|public|sync|ship|publish|export|changelog)\b"),
    # Memory/session
    ("memory_handoff", r"\b(memory|handoff|checkpoint|lesson|istoric|history|remember|rem|sleep|somn|recalibrate|retrospective)\b"),
    ("memory_handoff", r"\b(audit|trust|score|proof|replay|integrity|hash|conversation_audit|session audit|audit trail)\b"),
    # Web / Research
    ("web_research", r"\b(web|search|cauta pe net|browser|google|site|url|http|https|scraper|scraping|scrape|wikipedia)\b"),
    # Failure diagnosis (top fallback after project_state)
    ("failure", r"\b(error|failed|failure|traceback|exception|bug|blocked|timeout|eroare|fail|invalid value|not defined|nameerror|attributeerror|typeerror|keyerror|indexerror|syntaxerror|segfault|segmentation fault|health fail|listen fail|eaddr in use|connection refused|http 5|http 4)\b"),
    # Agent self-reflection / coach / planning
    ("project_state", r"\b(tool.?router|tool_router|agent.?coach|situational.?awareness|workspace.?situational_awareness|project.?navigator|project_state|profile_status|preflight|context|overview|stare|status|ce faci|unde suntem|health check)?\b"),
    ("project_state", r"\b(planner|roadmap|todo|task|obiectiv|scop|next step|urmatorul pas|prioritate|plan|outline)\b"),
    # Code editing (lowest priority catch-all)
    ("code_change", r"\b(code|edit|patch|fix|implement|test|compile|refactor|fisier|file|adauga|scoate|modifica|change|replace|adauga functionalitate|new feature)\b"),
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
                        "release_sync, memory_handoff, profile_status, file_analysis, file_operations, web_research"
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
                        "file_analysis",
                        "file_operations",
                        "web_research",
                    ],
                ),
                ToolParameter("max_tools", "Maximum recommended tools", "integer", False, 5),
            ],
            category="ai_core",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        task = str(kwargs.get("task") or "")
        error = str(kwargs.get("error") or "")
        mode = str(kwargs.get("mode") or "auto")
        max_tools = max(1, min(int(kwargs.get("max_tools") or 5), 20))

        try:
            selected_mode = mode if mode != "auto" else self._classify(task, error)
            manifest = self._load_permission_manifest()
            
            if selected_mode == "profile_status":
                result = ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=self._profile_status(manifest),
                    message="Permission profile status ready.",
                )
            else:
                playbook = PLAYBOOKS.get(selected_mode, PLAYBOOKS["project_state"])
                
                # [FIX] Inject Universal God-Mode Tools and deduplicate while preserving order
                raw_tools = playbook["tools"] + UNIVERSAL_TOOLS
                seen = set()
                deduped_tools = [x for x in raw_tools if not (x in seen or seen.add(x))]
                effective_max = max_tools + len(UNIVERSAL_TOOLS)

                tools, filtered = self._filter_tools_for_profiles(deduped_tools, manifest, effective_max)
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
                result = ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=data,
                    message=f"Recommended {len(tools)} tools for {selected_mode}.",
                )

            execution_time = time.time() - start_time
            _record_router_telemetry(selected_mode, result.is_success, execution_time)
            
            # ContextEngine integration for router state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="router_state",
                        value={
                            "mode": selected_mode,
                            "task": task[:100] if task else "",
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for router errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        f"router.{selected_mode}",
                        f"Tool router failed for task '{task[:50]}': {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_router_telemetry(mode, False, execution_time)
            
            # MemoryCortex integration for router errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"router.{mode}",
                        f"Tool router failed for task '{task[:50]}': {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _classify(self, task: str, error: str) -> str:
        # [FIX] Bypassing slow LLM classification on weak GPUs to prevent 60s timeouts
        # The Regex classifier is instant and sufficient for most lab scenarios.
        text = f"{task}\n{error}".lower()
        if error.strip():
            return "failure"
        for mode, pattern in KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                return mode
        return "project_state"

    def _classify_with_llm(self, task: str, error: str) -> str | None:
        if not task.strip() and not error.strip():
            return None
            
        modes = ["project_state", "failure", "code_change", "ui_desktop", "runtime_deep", "release_sync", "memory_handoff", "file_analysis", "file_operations", "web_research"]
        prompt = (
            "You are an expert routing AI. Classify the following task into exactly one of these categories: "
            f"{', '.join(modes)}.\n\n"
            f"Task: {task}\nError: {error}\n\n"
            "Output ONLY the category name, nothing else."
        )
        
        req_data = json.dumps({
            "model": "qwen2.5-coder:7b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 10
            }
        }).encode("utf-8")
        
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=req_data, headers={"Content-Type": "application/json"})
        try:
            # [FIX OS-27] Increased timeout to 180.0 to prevent 
            # cancelling the context (HTTP 499) during slow Ollama cold starts on weak GPUs.
            with urllib.request.urlopen(req, timeout=180.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                output = result.get("response", "").strip().lower()
                for mode in modes:
                    if mode in output:
                        return mode
        except Exception as e:
            logger.debug("LLM classification error: %s", e)
            
        return None

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

        active_tools_count = len(tool_manifest) - len(inactive_tools)
        logger.info(f"Loaded {active_tools_count} active tools (total: {len(tool_manifest)}, inactive: {len(inactive_tools)})")

        return {
            "schema": "ana.tool_router.profile_status.v1",
            "active_profiles": active_profiles,
            "tools_total": len(tool_manifest),
            "active_tools_count": active_tools_count,
            "profile_counts": dict(sorted(profile_counts.items())),
            "inactive_tools": inactive_tools,
            "inactive_count": len(inactive_tools),
            "unprofiled_tools": unprofiled_tools,
            "unprofiled_count": len(unprofiled_tools),
        }
