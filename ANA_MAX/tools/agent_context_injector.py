#!/usr/bin/env python3
"""
ANA Mirror Brain - Agent Context Injector
==========================================
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
ANA_MAX_ROOT = _HERE.parents[1]
WORKSPACE_ROOT = ANA_MAX_ROOT.parent
TOOLS_DIR = ANA_MAX_ROOT / "tools"
DOCS_DIR = WORKSPACE_ROOT / "docs"
MIRROR_SNAPSHOT = TOOLS_DIR / "mirror_context.json"
SNAPSHOT_TTL_SEC = 300

sys.path.insert(0, str(ANA_MAX_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT))

FULL_TOOL_CATALOGUE = [
    ("tools.files","FilesTool","file_operations","Citire, scriere, editare, cautare fisiere"),
    ("tools.system","SystemTool","system_control","Procese, memorie, CPU, info sistem"),
    ("tools.code","CodeTool","code","Executie si analiza cod Python"),
    ("tools.web","WebTool","web","HTTP requests, scraping web"),
    ("tools.memory_tool","MemoryTool","memory","Memorie persistenta cheie-valoare"),
    ("tools.memory_cortex","MemoryCortexTool","memory_cortex","Memorie semantica avansata cu embedding"),
    ("tools.smart_search_tool","SmartSearchTool","smart_search","Cautare inteligenta in codebase si docs"),
    ("tools.ana_context_tool","AnaContextTool","ana_identity","Identitate si context ANA"),
    ("tools.desktop_capture","DesktopCaptureTool","desktop_capture","Screenshot ecran, captura fereastra"),
    ("tools.windows_uia_bridge","WindowsUiaBridgeTool","windows_uia","Automatizare UI Windows prin UIA"),
    ("tools.foreground_ui_snapshot","ForegroundUISnapshotTool","foreground_snapshot","Snapshot UI fereastra activa"),
    ("tools.frida_automation","FridaTool","frida","Instrumentare dinamica procese cu Frida"),
    ("tools.windows_deep_sight","WindowsDeepSightTool","windows_deep_sight","Analiza profunda procese Windows"),
    ("tools.windows_insight_tool","WindowsInsightTool","windows_insight","Insight procese, ferestre, resurse"),
    ("tools.security_tool","SecurityTool","security_audit","Audit securitate, scanare vulnerabilitati"),
    ("tools.terminal_tool","TerminalTool","terminal","Executie comenzi shell PowerShell/CMD"),
    ("tools.debugger_tool","DebuggerTool","debugger","Debugging procese, breakpoints, stack"),
    ("tools.edit_tool","EditTool","edit","Editare fisiere text cu diff preview"),
    ("tools.task_tool","TaskTool","task","Gestionare task-uri si todo-uri"),
    ("tools.code_search","CodeSearchTool","code_search","Cautare semantica in cod sursa"),
    ("tools.browser_control","BrowserControlTool","browser","Control browser web"),
    ("tools.live_desktop_viewer","LiveDesktopViewerTool","live_desktop","Viewer live desktop cu actualizare"),
    ("tools.desktop_control_tool","DesktopControlTool","desktop_control","Control mouse/tastatura desktop"),
    ("tools.edge_tts_voice","EdgeTTSVoice","voice_tts","Text-to-speech cu Edge TTS"),
    ("tools.network_tool","NetworkTool","network","Ping, port scan, info retea"),
    ("tools.clipboard_manager","ClipboardManagerTool","clipboard","Clipboard Windows read/write/history"),
    ("tools.ocr_tool","OcrTool","ocr","OCR imagini cu PaddleOCR"),
    ("tools.qa_tool","QATool","qa","QA testing automatizat"),
    ("tools.todo_tool","TodoTool","todo","Gestionare lista TODO persistenta"),
    ("tools.session_log_miner_tool","SessionLogMinerTool","session_log_miner","Minerare si analiza log-uri sesiune"),
    ("tools.conversation_learning_tool","ConversationLearningTool","conversation_learning","Invatare din conversatii"),
    ("tools.project_navigator_tool","ProjectNavigatorTool","project_navigator","Navigare structura proiect"),
    ("tools.codebase_understanding_tool","CodebaseUnderstandingTool","codebase_understanding","Intelegere arhitectura codebase"),
    ("tools.workspace_situational_awareness","WorkspaceSituationalAwarenessTool","workspace_awareness","Awareness situational workspace"),
    ("tools.file_patch_tool","FilePatchTool","file_patch","Patch minimal fisiere cu rollback"),
    ("tools.error_radar_tool","ErrorRadarTool","error_radar","Detectie erori recente, logs, anomalii"),
    ("tools.tool_router_tool","ToolRouterTool","tool_router","Router inteligent alegere tool optim"),
    ("tools.window_manager","WindowManagerTool","window_manager","Gestionare ferestre Windows"),
    ("tools.web_scraper","WebScraperTool","web_scraper","Scraping web avansat cu parsing HTML"),
    ("tools.hardware_scanner_tool","HardwareScannerTool","hardware_scanner","Scanare hardware GPU CPU RAM disk"),
    ("tools.system_optimization_tool","SystemOptimizationTool","system_optimization","Optimizare sistem, curatare, benchmark"),
    ("tools.agent_coach_tool","AgentCoachTool","agent_coach","Coach agent: recomanda tool stack optim"),
    ("tools.science_tool","ScienceTool","science","Calcule stiintifice, matematica, statistici"),
    ("tools.autonomous_tool","AutonomousTool","autonomous","Motor executie autonoma plan-execute-verify"),
    ("tools.ana_orchestrator","AnaOrchestratorTool","orchestrator","Orchestrator task-uri complexe multi-tool"),
    ("tools.adb_tool","AdbTool","adb","ADB Android debug bridge"),
    ("tools.uia_click_tool","UiaClickTool","uia_click","Click UIA element pe ecran"),
    ("tools.uia_type_tool","UiaTypeTool","uia_type","Tastare text in element UIA"),
    ("tools.vision_fallback_tool","VisionFallbackTool","vision_fallback","Fallback vizual cand UIA esueaza"),
    ("tools.vision_find_element_tool","VisionFindElementTool","vision_find","Gasire element vizual pe ecran"),
    ("tools.vision_region_capture_tool","VisionRegionCaptureTool","vision_capture","Captura regiune ecran specificata"),
    ("tools.session_checkpoint_tool","SessionCheckpointTool","session_checkpoint","Salvare checkpoint sesiune"),
    ("tools.session_rem_sleep_tool","SessionRemSleepTool","session_rem","REM sleep: consolidare memorie sesiune"),
    ("tools.session_lifecycle_tool","SessionLifecycleTool","session_lifecycle","Ciclu viata sesiune start/pause/end"),
    ("tools.smoke_test_runner","SmokeTestRunnerTool","smoke_test","Rulare smoke tests ANA"),
    ("tools.tool_healthcheck","ToolHealthcheckTool","tool_healthcheck","Healthcheck toate tools active"),
    ("tools.live_debug_console","LiveDebugConsoleTool","live_debug","Consola debug live cu output stream"),
    ("tools.voice_commentary","VoiceCommentaryTool","voice_commentary","Comentariu vocal actiuni agent"),
    ("tools.text_to_speech","TextToSpeechTool","tts","Text to speech generic"),
    ("tools.web_ai_bridge","WebAiBridgeTool","web_ai","Bridge AI web Gemini OpenAI Anthropic"),
    ("tools.swarm_tool","SwarmTool","swarm","Swarm agenti paraleli pentru task-uri"),
    ("tools.advanced_scanner","AdvancedScannerTool","advanced_scanner","Scanare avansata fisiere duplicati junk"),
    ("tools.live_tool_healer","LiveToolHealerTool","tool_healer","Auto-repair tools defecte la runtime"),
    ("tools.context_engine","ContextEngineTool","context_engine","Motor context: compileaza context relevant"),
    ("tools.ana_runtime_inspector","AnaRuntimeInspectorTool","runtime_inspector","Inspector runtime ANA stare metrici"),
    ("tools.event_stream_tool","EventStreamTool","event_stream","Stream eventi sistem in timp real"),
    ("tools.vector_memory_tool","VectorMemoryTool","vector_memory","Memorie vectoriala RAG cu ChromaDB"),
    ("tools.apk_analyzer","ApkAnalyzerTool","apk_analyzer","Analiza APK Android manifest dex resurse"),
    ("tools.mitm_analyzer_tool","MitmAnalyzerTool","mitm_analyzer","Analiza trafic MITM cu mitmproxy"),
    ("tools.network_pentest_tool","NetworkPentestTool","network_pentest","Pentest retea nmap whois CVE"),
    ("tools.privacy","PrivacyTool","privacy_shield","Shield date private redactare audit"),
    ("tools.skill_tool","SkillTool","skill","Skills system ANA list/execute/validate"),
    ("tools.large_file_reader","LargeFileReaderTool","large_file_reader","Citire fisiere mari pana la 10k linii"),
    ("tools.project_reader_tool","ProjectReaderTool","project_reader","Citire si analiza proiect complet"),
    ("tools.git_tool","GitTool","git","Operatii Git status diff commit log"),
    ("tools.black_box_recorder","BlackBoxRecorderTool","black_box","Recorder actiuni agent pentru replay/audit"),
    ("tools.proactive_interrupt","ProactiveInterruptTool","proactive_interrupt","Intrerupere proactiva agent la anomalii"),
    ("tools.self_evolving_tool","SelfEvolvingTool","self_evolving","Auto-evolutie tool patch test deploy"),
    ("tools.session_audit_tool","SessionAuditTool","session_audit","Audit complet sesiune actiuni erori fix"),
    ("tools.windows_local_tools","WindowsLocalTools","windows_local","Tools locale Windows registry events svc"),
    ("tools.windows_frida_telemetry","WindowsFridaTelemetryTool","frida_telemetry","Telemetrie Frida hooks traces memory"),
    ("tools.desktop_workspace","DesktopWorkspaceTool","desktop_workspace","Workspace desktop layout grid snap"),
    ("tools.browser_pack","BrowserPackTool","browser_pack","Pack browser cookies storage history"),
    ("tools.procmon_monitor","ProcmonMonitorTool","procmon","Monitor procese CPU RAM IO in timp real"),
    ("tools.agent_context_injector","AgentContextInjectorTool","agent_context","Mirror Brain context complet pentru agenti"),
]


def collect_tool_manifest():
    return [{"name": name, "description": desc} for _, _, name, desc in FULL_TOOL_CATALOGUE]


def collect_session_state(max_lines=60):
    memory_path = DOCS_DIR / "ANA_MEMORY.md"
    if not memory_path.exists():
        return {"error": "ANA_MEMORY.md not found", "last_checkpoint": None}
    try:
        text = memory_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        checkpoint_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            if "SESSION CHECKPOINT" in lines[i]:
                checkpoint_idx = i
                break
        if checkpoint_idx == -1:
            return {"last_checkpoint": None, "note": "No checkpoint found"}
        snippet_lines = lines[checkpoint_idx: checkpoint_idx + max_lines]
        snippet = "\n".join(snippet_lines)
        date_match = re.search(r"SESSION CHECKPOINT[^-\n]*[-]+\s*(\d{4}-\d{2}-\d{2}[^\n:]*)", lines[checkpoint_idx])
        checkpoint_date = date_match.group(1).strip() if date_match else "unknown"
        next_step = None
        for line in snippet_lines:
            if "NEXT STEP" in line or "Next Step" in line:
                next_step = line.strip().lstrip("#> ").strip()
                break
        return {
            "last_checkpoint": checkpoint_date,
            "next_step": next_step,
            "snippet": snippet[:2000],
            "total_lines_memory": len(lines),
        }
    except Exception as exc:
        return {"error": str(exc), "last_checkpoint": None}


def collect_roadmap(max_items=5):
    roadmap_path = DOCS_DIR / "ROADMAP.md"
    if not roadmap_path.exists():
        return {"error": "ROADMAP.md not found", "priorities": []}
    try:
        text = roadmap_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        priorities = []
        for line in lines:
            if "|" in line and any(kw in line for kw in ["Identificat","asteptare","progress","Pending","TODO","[ ]","[/]"]):
                clean = re.sub(r"\|+", "|", line).strip("|").strip()
                parts = [p.strip() for p in clean.split("|") if p.strip()]
                if parts:
                    priorities.append(parts[0] if len(parts) == 1 else f"{parts[0]} -> {parts[1]}")
                if len(priorities) >= max_items:
                    break
        if not priorities:
            priorities = [l for l in lines if l.strip() and not l.startswith("#")][:max_items]
        return {"priorities": priorities[:max_items], "full_digest": "\n".join(lines[:30])}
    except Exception as exc:
        return {"error": str(exc), "priorities": []}


def collect_errors(max_errors=10):
    error_log = ANA_MAX_ROOT / "logs" / "direct_bridge_errors.jsonl"
    if error_log.exists():
        try:
            lines = error_log.read_text(encoding="utf-8", errors="replace").splitlines()
            recent = []
            for l in lines[-max_errors:]:
                if l.strip():
                    try:
                        recent.append(json.loads(l))
                    except Exception:
                        pass
            return {"status": "ok", "errors": recent, "source": str(error_log)}
        except Exception as exc:
            return {"status": "log_error", "error": str(exc), "errors": []}
    return {"status": "no_log", "errors": []}


def _check_ollama():
    try:
        from urllib import request as url_req
        req = url_req.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with url_req.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"running": True, "models": models}
    except Exception as exc:
        return {"running": False, "error": str(exc)}


def _count_bridge_tools():
    try:
        from tools.base import registry
        return len(registry.list_tools())
    except Exception:
        return 0


def collect_os_status():
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "os_version": "ANA_MAX OS-27",
        "workspace": str(WORKSPACE_ROOT),
        "ollama": _check_ollama(),
        "tool_catalogue_size": len(FULL_TOOL_CATALOGUE),
        "bridge_tools_loaded": _count_bridge_tools(),
    }


def _load_dynamic_skills():
    skills = []
    roots = [Path(r"C:\Users\billy\.gemini\config\skills"), WORKSPACE_ROOT / ".agents" / "skills"]
    for root in roots:
        if not root.exists():
            continue
        for skill_dir in root.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8", errors="ignore")
                    name, desc = skill_dir.name, ""
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            for line in parts[1].splitlines():
                                if line.startswith("name:"):
                                    name = line.split(":", 1)[1].strip()
                                elif line.startswith("description:"):
                                    desc = line.split(":", 1)[1].strip()
                    skills.append({"name": name, "description": desc})
                except Exception:
                    pass
def _inject_lessons_learned() -> str:
    import sqlite3
    db_path = WORKSPACE_ROOT / "ana_memory.db"
    if not db_path.exists():
        return ""
    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT * FROM known_errors ORDER BY rowid DESC LIMIT 3;")
        errors = c.fetchall()
        if not errors:
            return ""
        
        lines = ["## LESSONS LEARNED (Din Memorie)"]
        for row in errors:
            # Presupunem schema (id, eroare, solutie) sau list(row)
            if len(row) >= 2:
                err_text = str(row[1])[:100]
                sol_text = str(row[2])[:100] if len(row) > 2 else "Unknown"
                lines.append(f"- [Eroare]: {err_text} -> [Solutie]: {sol_text}")
            else:
                lines.append(f"- {row}")
        return "\n".join(lines) + "\n"
    except Exception:
        return ""


def build_system_prompt(ctx):
    tools = ctx.get("tools", [])
    session = ctx.get("session", {})
    roadmap = ctx.get("roadmap", {})
    os_status = ctx.get("os_status", {})
    skills = ctx.get("skills", [])
    ollama_ok = os_status.get("ollama", {}).get("running", False)
    ollama_status = "RUNNING" if ollama_ok else "OFFLINE"
    models = ", ".join(os_status.get("ollama", {}).get("models", [])) or "N/A"
    tool_count = os_status.get("tool_catalogue_size", len(tools))
    bridge_count = os_status.get("bridge_tools_loaded", 0)
    tool_lines = "\n".join(f"  - {t['name']}: {t['description']}" for t in tools)
    checkpoint = session.get("last_checkpoint", "unknown")
    next_step = session.get("next_step", "vezi ROADMAP.md")
    prio_lines = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(roadmap.get("priorities", [])))
    
    skill_block = ""
    if skills:
        s_lines = "\n".join(f"  - {s['name']}: {s['description']}" for s in skills)
        skill_block = f"\n## Abilitati dinamice disponibile (.agents/skills)\nFoloseste `skill_tool action=execute capability=<name>` pentru a le utiliza.\n{s_lines}\n"

    lessons_block = _inject_lessons_learned()

    return f"""# ANA MAX OS-27 Mirror Brain
Generat: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## Identitate
Esti ANA MAX OS-27, AI agent local cu {tool_count} tool-uri disponibile.
Workspace: {os_status.get('workspace', 'unknown')}
Ollama: {ollama_status} | Modele: {models}
Tools in registry: {bridge_count}/{tool_count}

{lessons_block}
## Reguli de baza
1. TOOL-FIRST: foloseste tools inaintea oricarui rationament propriu
2. NU LUCRA ORB: ruleaza agent_coach sau tool_router inainte de task major
3. PATCH-ONLY: modifica minimal, verifica dupa fiecare schimbare
4. FORMAT: ACTION -> RESULT -> NEXT STEP
5. SECURITY FIRST: scaneaza vulnerabilitati inainte de features noi
6. ARTIFACT ENGINE (PILONUL 3): Pentru arhitectura si planuri, foloseste `artifact_tool` pentru a salva fisiere (ex: .md) in loc sa tiparesti in chat.

## Sesiunea curenta
Ultimul checkpoint: {checkpoint}
Next step: {next_step}

## Prioritati active (ROADMAP.md)
{prio_lines or "  citeste docs/ROADMAP.md"}
{skill_block}
## Tool-uri disponibile ({tool_count} total)
{tool_lines}

## Apel tool
  TOOL_CALL: <tool_name> {{"action": "<action>", "param": "value"}}
  python ANA_MAX/bridge/direct_bridge.py --execute --tool <name> --payload '{{"action":"<act>"}}'
""".strip()


def collect_full_context(fast=False):
    t0 = time.monotonic()
    tools = collect_tool_manifest()
    session = collect_session_state()
    roadmap = collect_roadmap()
    os_status = collect_os_status()
    skills = _load_dynamic_skills()
    errors = {} if fast else collect_errors()
    ctx = {
        "schema": "ana.mirror_brain.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": round((time.monotonic() - t0) * 1000, 1),
        "tools": tools,
        "tool_count": len(tools),
        "session": session,
        "roadmap": roadmap,
        "os_status": os_status,
        "skills": skills,
        "errors": errors,
    }
    ctx["system_prompt"] = build_system_prompt(ctx)
    return ctx


def save_snapshot(ctx=None):
    if ctx is None:
        ctx = collect_full_context(fast=True)
    MIRROR_SNAPSHOT.write_text(json.dumps(ctx, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return MIRROR_SNAPSHOT


def load_snapshot_if_fresh():
    if not MIRROR_SNAPSHOT.exists():
        return None
    age = time.time() - MIRROR_SNAPSHOT.stat().st_mtime
    if age > SNAPSHOT_TTL_SEC:
        return None
    try:
        return json.loads(MIRROR_SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        return None


try:
    from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

    class AgentContextInjectorTool(Tool):
        """Mirror Brain - context complet pentru agenti."""

        def get_definition(self):
            return ToolDefinition(
                name="agent_context",
                description="Mirror Brain: genereaza context complet (tool manifest, session, roadmap, erori, OS status) pentru injectare in orice agent local sau MCP. Actiuni: mirror, system_prompt, snapshot, tools, session, roadmap, status.",
                parameters=[
                    ToolParameter(name="action", type="string", description="mirror|system_prompt|snapshot|tools|session|roadmap|status", required=False),
                    ToolParameter(name="fast", type="boolean", description="Skip error_radar pentru raspuns mai rapid", required=False),
                ],
                category="meta",
            )

        def execute(self, **kwargs):
            action = str(kwargs.get("action", "mirror")).lower()
            fast = bool(kwargs.get("fast", False))
            cached = load_snapshot_if_fresh()

            if action == "tools":
                tools = collect_tool_manifest()
                return ToolResult(status=ToolStatus.SUCCESS, data={"tools": tools, "count": len(tools)}, message=f"{len(tools)} tools in ANA catalogue.")
            if action == "session":
                return ToolResult(status=ToolStatus.SUCCESS, data=collect_session_state(), message="Session state loaded.")
            if action == "roadmap":
                return ToolResult(status=ToolStatus.SUCCESS, data=collect_roadmap(), message="Roadmap digest loaded.")
            if action == "status":
                return ToolResult(status=ToolStatus.SUCCESS, data=collect_os_status(), message="OS status loaded.")
            if action == "system_prompt":
                ctx = cached or collect_full_context(fast=True)
                return ToolResult(status=ToolStatus.SUCCESS, data={"system_prompt": ctx["system_prompt"], "tool_count": ctx["tool_count"]}, message="System prompt ready.")
            if action == "snapshot":
                ctx = collect_full_context(fast=fast)
                path = save_snapshot(ctx)
                return ToolResult(status=ToolStatus.SUCCESS, data={"path": str(path), "tool_count": ctx["tool_count"]}, message=f"Snapshot saved: {path}")
            ctx = collect_full_context(fast=fast)
            return ToolResult(status=ToolStatus.SUCCESS, data=ctx, message=f"Mirror Brain: {ctx['tool_count']} tools, {ctx['elapsed_ms']}ms.")

except ImportError:
    class AgentContextInjectorTool:
        pass


def main():
    parser = argparse.ArgumentParser(description="ANA Mirror Brain - context complet pentru agenti")
    parser.add_argument("--dump", action="store_true")
    parser.add_argument("--system-prompt", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--tools", action="store_true")
    parser.add_argument("--session", action="store_true")
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    if args.tools:
        tools = collect_tool_manifest()
        for t in tools:
            print(f"  {t['name']:<40} {t['description']}")
        print(f"\nTotal: {len(tools)} tools")
        return 0
    if args.session:
        print(json.dumps(collect_session_state(), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.system_prompt:
        ctx = collect_full_context(fast=True)
        print(ctx["system_prompt"])
        return 0
    if args.snapshot:
        ctx = collect_full_context(fast=args.fast)
        path = save_snapshot(ctx)
        print(f"Snapshot saved: {path}")
        print(f"Tools: {ctx['tool_count']} | Elapsed: {ctx['elapsed_ms']}ms")
        return 0
    ctx = collect_full_context(fast=args.fast)
    out = {k: v for k, v in ctx.items() if k != "system_prompt"}
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(f"\n--- SYSTEM PROMPT ({len(ctx['system_prompt'])} chars) ---")
    print(ctx["system_prompt"][:600] + "...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
