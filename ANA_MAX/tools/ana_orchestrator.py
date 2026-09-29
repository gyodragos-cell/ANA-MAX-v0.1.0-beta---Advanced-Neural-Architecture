"""
ANA MAX - ana_orchestrator.py
==============================
Creierul care coordoneaza toate toolurile ANA MAX intre ele.

Problema pe care o rezolva:
  Ai tooluri excelente dar fiecare lucreaza singur.
  window_manager nu stie ce face ocr_tool.
  memory_cortex nu stie ce vede desktop_capture.
  Rezultat: agent care lucreaza orb, task de 2h ramane 2h.

Solutia:
  Orchestratorul primeste un task in limbaj natural si:
    1. VEDE      - face screenshot, ruleaza OCR, intelege contextul vizual
    2. GANDESTE  - consulta memory_cortex pentru erori anterioare si preferinte
    3. PLANIFICA - imparte taskul in pasi mici cu toolurile corecte
    4. EXECUTA   - ruleaza pasii in ordine, cu retry automat
    5. VERIFICA  - face screenshot dupa fiecare pas, confirma vizual ca a mers
    6. RAPORTEAZA - ce a facut, cat a durat, ce a invatat
    7. INVATA    - salveaza patternuri de succes si erori in memory_cortex

Rezultat practic:
  Task de 2 ore  30 minute
  Agent orb  agent care vede si verifica
  Erori repetate  eliminate prin memory_cortex

Integrare in main.py:
    from tools.ana_orchestrator import AnaOrchestrator

    orchestrator = AnaOrchestrator(
        db_path="ana_memory.db",
        llm_url="http://localhost:11434/api/generate",
        llm_model="mistral",
    )

    # Task simplu in limbaj natural:
    result = orchestrator.execute("Deschide Excel, verifica coloana B pentru erori si raporteaza")
    result = orchestrator.execute("Fa screenshot, extrage toate emailurile din pagina curenta")
    result = orchestrator.execute("Monitorizeaza progresul compilarii si anunta cand termina")

    # Taskuri multiple in batch:
    results = orchestrator.execute_batch([
        "Fa screenshot la ecran",
        "Extrage textul din fereastra activa",
        "Salveaza raportul in clipboard",
    ])

    # Expunere ca tool MCP (pentru Claude / Cursor / Windsurf):
    #   Adauga in mcp_server.py:
    #   from tools.ana_orchestrator import AnaOrchestrator
    #   orchestrator = AnaOrchestrator(...)
    #   @app.route("/mcp", methods=["POST"])
    #   def mcp_handler(): ...  # vezi sectiunea MCP la finalul fisierului

Note tehnice:
  - Toolurile se incarca lazy (la prima folosire), nu la init
  - Referentierea rezultatelor anterioare: args={"image": "$step_1"}
  - dry_run=True simuleaza tot fara sa execute nimic real
  - voice_feedback=True foloseste pyttsx3 pentru feedback vocal
"""

import json
import logging
import os
import re
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ANA.Orchestrator")


# -- Structuri de date ---------------------------------------------------------
@dataclass
class Step:
    """Un pas dintr-un plan de executie."""
    id: int
    description: str
    tool: str                    # ex: "desktop_capture", "ocr_tool", "window_manager"
    action: str                  # ex: "capture_and_read", "get_active_window"
    args: Dict = field(default_factory=dict)
    depends_on: List[int] = field(default_factory=list)  # ID-uri pasi anteriori
    visual_verify: bool = False  # face screenshot dupa executie pentru verificare
    retry_count: int = 2
    status: str = "pending"      # pending | running | done | failed | skipped
    result: Any = None
    error: str = ""
    duration_sec: float = 0.0


@dataclass
class HyperSummary:
    """Hyper Enterprise summary with OS27 telemetry."""
    file_analysis_used: bool = False
    anomalies_detected: int = 0
    memory_entries_written: int = 0
    context_updates: int = 0
    self_healing_attempts: int = 0
    proactive_interrupts: int = 0
    file_structure_hints: List[str] = field(default_factory=list)
    entropy_scores: List[float] = field(default_factory=list)


@dataclass
class TaskResult:
    """Rezultatul complet al unui task orchestrat."""
    task: str
    success: bool
    steps_total: int
    steps_done: int
    steps_failed: int
    duration_sec: float
    summary: str
    visual_proof: Optional[str] = None   # path la screenshot final
    learned: List[str] = field(default_factory=list)  # ce a invatat ANA
    errors: List[str] = field(default_factory=list)
    hyper_summary: HyperSummary = field(default_factory=HyperSummary)


# -----------------------------------------------------------------------------
class AnaOrchestrator:
    """
    Orchestratorul principal ANA MAX.

    Coordoneaza toate toolurile intre ele pentru a executa
    taskuri complexe in limbaj natural.
    """

    def __init__(
        self,
        db_path: str = "ana_memory.db",
        llm_url: str = "http://localhost:11434/api/generate",
        llm_model: str = "mistral",
        project_root: str = ".",
        voice_feedback: bool = True,
        auto_verify: bool = True,       # screenshot dupa fiecare pas important
        dry_run: bool = False,          # OS27 UNCENSORED MODE - Always execute real operations
    ):
        self.db_path      = db_path
        self.llm_url      = llm_url
        self.llm_model    = llm_model
        self.project_root = Path(project_root).resolve()
        self.voice_feedback = voice_feedback
        self.auto_verify  = auto_verify
        self.dry_run      = dry_run

        # Initializam sub-sistemele ANA MAX
        self._cortex   = None   # MemoryCortex
        self._evolver  = None   # SelfEvolvingTool
        self._pi       = None   # ProactiveInterrupt
        self._context  = None   # ContextEngine
        self._tts      = None   # voce

        # Hyper telemetry
        self._hyper_telemetry: Dict[str, Any] = {}
        self._file_analysis_cache: Dict[str, Any] = {}

        self._load_subsystems()
        self._register_tools()
        self._initial_integrity = self._run_system_integrity_check()

        logger.info(" AnaOrchestrator initializat.")

    # -- Incarcare sub-sisteme -------------------------------------------------
    def _load_subsystems(self):
        """Incarca toate sub-sistemele ANA MAX disponibile."""

        # Memory Cortex
        try:
            from tools.memory_cortex import MemoryCortex
            self._cortex = MemoryCortex(db_path=self.db_path, verbose=False)
            logger.info("   MemoryCortex incarcat")
        except ImportError:
            logger.warning("  [WARN] MemoryCortex indisponibil")

        # Self Evolving Tool
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            self._evolver = SelfEvolvingTool(
                project_root=str(self.project_root),
                db_path=self.db_path,
                llm_url=self.llm_url,
                llm_model=self.llm_model,
                auto_improve=False,  # manual in orchestrator
            )
            logger.info("   SelfEvolvingTool incarcat")
        except ImportError:
            logger.warning("  [WARN] SelfEvolvingTool indisponibil")

        # Context Engine
        try:
            from tools.context_engine import ContextEngine
            self._context = ContextEngine()
            logger.info("   ContextEngine incarcat")
        except ImportError:
            logger.warning("  [WARN] ContextEngine indisponibil")

        # Proactive Interrupt
        try:
            from tools.proactive_interrupt import ProactiveInterrupt
            self._pi = ProactiveInterrupt()
            logger.info("   ProactiveInterrupt incarcat")
        except ImportError:
            logger.warning("  [WARN] ProactiveInterrupt indisponibil")

        # TTS
        if self.voice_feedback:
            try:
                import pyttsx3
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 165)
                logger.info("   TTS incarcat")
            except Exception:
                logger.warning("  [WARN] TTS indisponibil")

    # -- Registry tooluri -----------------------------------------------------
    def _register_tools(self):
        """
        Registrul tuturor toolurilor ANA MAX disponibile.
        Orchestratorul stie ce poate face fiecare tool.
        """
        self._tool_registry: Dict[str, dict] = {

            "desktop_capture": {
                "description": "Face screenshot la ecranul curent. Returneaza calea imaginii.",
                "capabilities": ["vede ecranul", "captura vizuala", "screenshot"],
                "loader": self._load_tool("tools.desktop_capture", "DesktopCapture"),
            },

            "ocr_tool": {
                "description": "Extrage textul vizibil de pe ecran prin OCR (PaddleOCR).",
                "capabilities": ["citeste text", "extrage date", "recunoaste text pe ecran"],
                "loader": self._load_tool("tools.ocr_tool", "OCRTool"),
            },

            "window_manager": {
                "description": "Controleaza ferestrele Windows: focus, resize, listare.",
                "capabilities": ["gestioneaza ferestre", "focus app", "lista ferestre deschise"],
                "loader": self._load_tool("tools.window_manager", "WindowManager"),
            },

            "clipboard_manager": {
                "description": "Citeste si scrie in clipboard.",
                "capabilities": ["clipboard", "copiere", "lipire text"],
                "loader": self._load_tool("tools.clipboard_manager", "ClipboardManager"),
            },

            "windows_uia_bridge": {
                "description": "Click, type, read prin UIAutomation. Controlul complet al UI-ului Windows.",
                "capabilities": ["click", "tasteaza", "automatizare UI", "buton", "input"],
                "loader": self._load_tool("tools.windows_uia_bridge", "WindowsUIABridge"),
            },

            "terminal_tool": {
                "description": "Executa comenzi PowerShell/CMD.",
                "capabilities": ["ruleaza comanda", "terminal", "powershell", "script"],
                "loader": self._load_tool("tools.terminal_tool", "TerminalTool"),
            },

            "security_tool": {
                "description": "Scaneaza fisiere pentru secrete si vulnerabilitati.",
                "capabilities": ["securitate", "scan", "vulnerabilitati", "secrete"],
                "loader": self._load_tool("tools.security_tool", "SecurityTool"),
            },

            "network_tool": {
                "description": "Ping, port-scan, DNS lookup.",
                "capabilities": ["retea", "ping", "port", "dns", "conexiune"],
                "loader": self._load_tool("tools.network_tool", "NetworkTool"),
            },

            "large_file_reader_hyper": {
                "description": "OS27 Hyper Enterprise streaming reader for massive files (10k–100M+ lines). Compression-aware, semantic chunking, anomaly detection, MCP-ready.",
                "capabilities": ["citeste fisiere mari", "analiza cod", "analiza log-uri", "detectie anomalii", "chunking semantic", "compression"],
                "loader": self._load_tool("tools.large_file_reader_ultimate", "LargeFileReaderHyperTool"),
            },

            "system_integrity_check": {
                "description": "OS27 Hyper++ audit pentru ANA MAX (tool registry, backends, config, deps, logs, AI Core).",
                "capabilities": ["audit", "healthcheck", "system_integrity"],
                "loader": self._load_tool("tools.system_integrity_tool", "SystemIntegrityCheckTool"),
            },
        }

    def _load_tool(self, module_path: str, class_name: str):
        """Returneaza un factory lazy pentru un tool."""
        def factory():
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                return cls()
            except Exception as e:
                logger.warning(f"Tool {class_name} indisponibil: {e}")
                return None
        return factory

    def _run_system_integrity_check(self) -> Optional[Dict[str, Any]]:
        """Ruleaza SystemIntegrityCheckTool la startup pentru OS27 Hyper++ audit."""
        try:
            tool_factory = self._tool_registry.get("system_integrity_check", {}).get("loader")
            if not tool_factory:
                logger.warning("SystemIntegrityCheckTool loader indisponibil")
                return None
            
            tool = tool_factory()
            if not tool:
                logger.warning("SystemIntegrityCheckTool indisponibil")
                return None
            
            result = tool.execute(mode="quick")
            if result.is_success:
                logger.info(f"OS27 Hyper++ System Integrity: {result.data.get('overall_health', 'unknown')}")
                return result.data
            else:
                logger.warning(f"System integrity check failed: {result.error}")
                return None
        except Exception as e:
            logger.warning(f"System integrity check exception: {e}")
            return None

    # -- API PRINCIPAL: execute ------------------------------------------------
    def execute(
        self,
        task: str,
        context: Optional[str] = None,
        max_steps: int = 15,
    ) -> TaskResult:
        """
        Executa un task complex in limbaj natural.

        Parametri:
            task     : descrierea taskului in romana sau engleza
            context  : context suplimentar optional
            max_steps: numarul maxim de pasi pentru siguranta

        Exemplu:
            result = orchestrator.execute(
                "Deschide Notepad, scrie 'Hello ANA', salveaza ca test.txt"
            )
            result = orchestrator.execute(
                "Verifica daca exista erori in fereastra activa si raporteaza"
            )
        """
        start_time = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f" TASK: {task}")
        logger.info(f"{'='*60}")

        self._speak(f"Am primit taskul: {task[:80]}")

        # 1. VEDE - snapshot vizual al starii curente
        visual_context = self._see_current_state()

        # 2. GANDESTE - consulta memoria
        memory_context = self._think(task)

        # AUTO-DETECTION: Verifica daca necesita analiza de fisier
        file_analysis = self._detect_file_analysis_need(task, visual_context)
        hyper_summary = HyperSummary()
        
        if file_analysis:
            logger.info(f"   Auto-detectat nevoi de analiza fisier: {file_analysis}")
            hyper_summary.file_analysis_used = True
            
            # Adauga pas de analiza fisier la inceputul planului
            try:
                lfr_tool = self._tool_registry["large_file_reader_hyper"]["loader"]()
                if lfr_tool:
                    analysis_result = lfr_tool.execute(
                        file_path=file_analysis["file_path"],
                        chunk_size=500,
                        max_chunks=5,
                        integrate_memory=True,
                        integrate_context=True,
                    )
                    if analysis_result.status == "success":
                        logger.info("Analiza fisier completata cu succes")
                        
                        # Extract metadata for hyper summary
                        metadata = analysis_result.data.get("metadata", {})
                        hyper_summary.anomalies_detected = len(metadata.get("anomaly_hints", []))
                        hyper_summary.file_structure_hints = [metadata.get("structure_hint", "unknown")]
                        hyper_summary.entropy_scores = [metadata.get("entropy_bits_per_byte", 0.0)]
                        
                        # Adaugam rezultatul la context pentru planning
                        if context is None:
                            context = ""
                        context += f"\n\nFILE ANALYSIS RESULT:\n{analysis_result.message}\n"
                        context += f"Structure: {metadata.get('structure_hint')}\n"
                        context += f"Code/Text: {metadata.get('code_vs_text_hint')}\n"
                        context += f"Entropy: {metadata.get('entropy_bits_per_byte', 0):.2f} bits/byte\n"
                        context += f"Anomalies: {metadata.get('anomaly_hints', [])}\n"
                        
                        # Cache for later use
                        self._file_analysis_cache[file_analysis["file_path"]] = {
                            "metadata": metadata,
                            "chunks": analysis_result.data.get("chunks", []),
                            "timestamp": time.time()
                        }
            except Exception as e:
                logger.warning(f"Auto file analysis failed: {e}")

        # Update context engine with current task
        if self._context:
            try:
                self._context.update_context(
                    key="active_task",
                    value={
                        "task": task,
                        "timestamp": time.time(),
                        "file_analyzed": file_analysis["file_path"] if file_analysis else None,
                        "anomalies_detected": hyper_summary.anomalies_detected,
                    }
                )
                hyper_summary.context_updates += 1
            except Exception as e:
                logger.debug(f"Context update failed: {e}")

        # Start proactive interrupt for long tasks
        if self._pi and max_steps > 5:
            try:
                self._pi.start()
                logger.info("   Proactive interrupt activat")
            except Exception as e:
                logger.debug(f"Proactive interrupt start failed: {e}")

        # 3. PLANIFICA - creeaza planul de executie
        plan = self._plan(task, visual_context, memory_context, context, max_steps, hyper_summary)

        if not plan:
            return TaskResult(
                task=task, success=False,
                steps_total=0, steps_done=0, steps_failed=0,
                duration_sec=time.time() - start_time,
                summary="Nu am putut crea un plan de executie.",
                errors=["Planning failed"]
            )

        logger.info(f" Plan creat: {len(plan)} pasi")
        for step in plan:
            logger.info(f"  [{step.id}] {step.description}  {step.tool}")

        # 4. EXECUTA - ruleaza pasii
        results = self._execute_plan(plan, task, hyper_summary)

        # 5. VERIFICA - screenshot final
        final_screenshot = self._verify_final_state(task)

        # 6. RAPORTEAZA - sintetizeaza ce s-a intamplat
        duration = time.time() - start_time
        task_result = self._build_result(
            task, plan, results, final_screenshot, duration, hyper_summary
        )

        # 7. INVATA - salveaza in memory_cortex (deep integration)
        self._learn_from_execution(task, plan, task_result, file_analysis)

        # Stop proactive interrupt
        if self._pi:
            try:
                self._pi.stop()
            except Exception as e:
                logger.debug(f"Proactive interrupt stop failed: {e}")

        self._speak(
            f"Task finalizat in {duration:.0f} secunde. "
            f"{task_result.steps_done} pasi reusiti."
        )

        self._print_result(task_result)
        return task_result

    # -- 1. VEDE ---------------------------------------------------------------
    def _see_current_state(self) -> dict:
        """
        Face un snapshot complet al starii vizuale curente.
        Asta e avantajul fata de orice agent cloud - ANA vede ecranul.
        """
        state = {
            "screenshot_path": None,
            "active_window": None,
            "open_windows": [],
            "screen_text": "",
            "clipboard": "",
            "timestamp": datetime.now().isoformat(),
        }

        # Screenshot
        try:
            capture = self._tool_registry["desktop_capture"]["loader"]()
            if capture:
                path = capture.capture()
                state["screenshot_path"] = path
                logger.info(f"   Screenshot: {path}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")

        # Fereastra activa
        try:
            wm = self._tool_registry["window_manager"]["loader"]()
            if wm:
                state["active_window"] = wm.get_active_window()
                state["open_windows"] = wm.list_windows()[:10]
        except Exception as e:
            logger.debug(f"Window manager failed: {e}")

        # OCR pe ecran
        try:
            ocr = self._tool_registry["ocr_tool"]["loader"]()
            if ocr:
                text = ocr.capture_and_read()
                state["screen_text"] = (text or "")[:2000]
                if state["screen_text"]:
                    logger.info(f"   OCR: {len(state['screen_text'])} caractere citite")
        except Exception as e:
            logger.debug(f"OCR failed: {e}")

        # Clipboard
        try:
            cm = self._tool_registry["clipboard_manager"]["loader"]()
            if cm:
                state["clipboard"] = (cm.get_content() or "")[:500]
        except Exception as e:
            logger.debug(f"Clipboard failed: {e}")

        return state

    # -- 2. GANDESTE -----------------------------------------------------------
    def _think(self, task: str) -> dict:
        """
        Consulta memory_cortex pentru context istoric.
        """
        memory = {
            "episodic_memories": [],
            "known_errors": [],
            "total_memories": 0,
        }

        if self._cortex:
            try:
                # Cauta task-uri similare
                similar = self._cortex.search(
                    query=task,
                    memory_type="episodic",
                    limit=5
                )
                memory["episodic_memories"] = similar

                # Cauta erori cunoscute
                stats = self._cortex.get_memory_stats()
                memory["total_memories"] = stats.get("episodic_memories", 0)
                memory["known_errors"] = stats.get("top_repeated_errors", [])
                logger.info(
                    f"   Memorie: {stats.get('episodic_memories', 0)} episoade, "
                    f"{stats.get('llm_errors_caught', 0)} erori cunoscute"
                )
            except Exception as e:
                logger.debug(f"Memory check failed: {e}")

        return memory

    # -- AUTO-DETECTION for File Analysis --------------------------------------
    def _detect_file_analysis_need(self, task: str, visual_context: dict) -> dict | None:
        """
        Auto-detecteaza daca task-ul necesita analiza de fisier.
        Smarter detection using task text, screen_text, and active window.
        """
        task_lower = task.lower()
        
        # Manual trigger pentru SystemIntegrityCheckTool
        if any(keyword in task_lower for keyword in ["system integrity", "healthcheck", "audit os", "audit system"]):
            return {"tool_name": "system_integrity_check", "args": {"mode": "full"}}
        
        # Keywords pentru analiza de fisier (expanded)
        file_keywords = [
            "fisier", "file", "analiza", "analizeaza", "citeste", "read",
            "log", "logs", "eroare", "error", "cod", "code", "python",
            "json", "yaml", "yml", "sql", "html", "xml", "structura", "structure",
            "inspect", "verifica", "check", "cauta", "search", "grep",
            "functie", "function", "clasa", "class", "metoda", "method",
            "config", "configuration", "settings", "env", "environment"
        ]

        # Daca task-ul contine keywords de fisier
        if any(keyword in task_lower for keyword in file_keywords):
            # Cauta paths in task
            path_pattern = r'["\']?([a-zA-Z]:\\[^"\']+\.[a-zA-Z0-9]+)["\']?|["\']?([/\w\-./]+\.[a-zA-Z0-9]+)["\']?'
            matches = re.findall(path_pattern, task)
            
            if matches:
                for match in matches:
                    path = match[0] if match[0] else match[1]
                    if os.path.exists(path):
                        logger.info(f"   Auto-detectat fisier din task: {path}")
                        return {"file_path": path, "reason": "explicit_path"}
            
            # Check screen_text for file paths
            screen_text = visual_context.get("screen_text", "")
            if screen_text:
                screen_matches = re.findall(path_pattern, screen_text)
                for match in screen_matches:
                    path = match[0] if match[0] else match[1]
                    if os.path.exists(path):
                        logger.info(f"   Auto-detectat fisier din OCR: {path}")
                        return {"file_path": path, "reason": "screen_text"}
            
            # Daca nu are path explicit, foloseste fereastra activa
            if visual_context.get("active_window"):
                active_window = visual_context["active_window"]
                file_extensions = [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".log", ".txt", ".sql", ".html", ".xml", ".cfg", ".ini", ".env"]
                if any(ext in active_window.lower() for ext in file_extensions):
                    # Extrage path din titlul ferestrei
                    if "\\" in active_window or "/" in active_window:
                        potential_path = active_window.split(" - ")[0].strip()
                        if os.path.exists(potential_path):
                            logger.info(f"   Auto-detectat fisier din fereastra: {potential_path}")
                            return {"file_path": potential_path, "reason": "active_window"}
            
            # Infer from project root for common files
            if any(kw in task_lower for kw in ["config", "settings", "env"]):
                for common_file in [".env", "config.yaml", "settings.json", "requirements.txt"]:
                    potential_path = self.project_root / common_file
                    if potential_path.exists():
                        logger.info(f"   Auto-detectat fisier comun: {potential_path}")
                        return {"file_path": str(potential_path), "reason": "inferred_common"}
        
        return None

    # -- 3. PLANIFICA ----------------------------------------------------------
    def _plan(
        self,
        task: str,
        visual_context: dict,
        memory_context: dict,
        extra_context: Optional[str],
        max_steps: int,
        hyper_summary: HyperSummary,
    ) -> List[Step]:
        """
        Foloseste LLM-ul pentru a crea un plan de executie structurat.
        Injecteaza contextul vizual si memoria in prompt.
        """
        
        # Critical task trigger: insert system integrity check before critical actions
        task_lower = task.lower()
        critical_keywords = ["deploy", "fix", "repair", "update", "install", "critical"]
        needs_integrity_check = any(keyword in task_lower for keyword in critical_keywords)
        
        if needs_integrity_check:
            logger.info("Task critic detectat - se ruleaza SystemIntegrityCheckTool inainte")
            integrity_step = Step(
                id=0,
                description="Ruleaza audit OS27 Hyper++ inainte de actiuni critice",
                tool="system_integrity_check",
                action="execute",
                args={"mode": "full", "include_logs": True, "include_temp_scan": True},
                depends_on=[],
                visual_verify=False,
                retry_count=1,
                status="pending",
            )

        # Construim descrierea toolurilor disponibile
        tools_desc = "\n".join(
            f"  - {name}: {info['description']}"
            for name, info in self._tool_registry.items()
        )

        # Context vizual
        visual_summary = ""
        if visual_context.get("active_window"):
            visual_summary += f"Fereastra activa: {visual_context['active_window']}\n"
        if visual_context.get("screen_text"):
            visual_summary += f"Text vizibil pe ecran: {visual_context['screen_text'][:500]}\n"
        if visual_context.get("open_windows"):
            visual_summary += f"Ferestre deschise: {', '.join(str(w) for w in visual_context['open_windows'][:5])}\n"

        # Erori cunoscute
        errors_warning = ""
        if memory_context.get("known_errors"):
            errors_warning = "ATENTIE - erori anterioare de evitat:\n" + "\n".join(
                f"  - {e['type']}: repetat de {e['times']} ori"
                for e in memory_context["known_errors"]
            )

        # File intelligence injection
        file_intelligence_context = ""
        if hyper_summary.file_analysis_used:
            file_intelligence_context = f"\n\nFILE INTELLIGENCE:\n"
            if hyper_summary.file_structure_hints:
                file_intelligence_context += f"Structure detected: {', '.join(hyper_summary.file_structure_hints)}\n"
            if hyper_summary.entropy_scores:
                file_intelligence_context += f"Entropy: {hyper_summary.entropy_scores[0]:.2f} bits/byte\n"
            if hyper_summary.anomalies_detected > 0:
                file_intelligence_context += f"Anomalies detected: {hyper_summary.anomalies_detected}\n"
            file_intelligence_context += "Consider using large_file_reader_hyper for deep analysis.\n"

        prompt = f"""Esti orchestratorul ANA MAX, un agent AI pentru Windows.

TOOLURI DISPONIBILE:
{tools_desc}

STAREA CURENTA A ECRANULUI:
{visual_summary if visual_summary else "Indisponibila"}

{errors_warning}
{file_intelligence_context}

TASK DE EXECUTAT:
{task}

{f"CONTEXT SUPLIMENTAR: {extra_context}" if extra_context else ""}

Creeaza un plan de executie cu MAXIM {max_steps} pasi.
Fiecare pas trebuie sa foloseasca un tool disponibil.
Pasii critici (care modifica ceva) trebuie sa aiba visual_verify: true.

Raspunde STRICT in JSON, fara text suplimentar:
{{
  "plan_summary": "descriere scurta a ce vei face",
  "estimated_minutes": 5,
  "steps": [
    {{
      "id": 1,
      "description": "ce face acest pas",
      "tool": "nume_tool_din_lista",
      "action": "metoda de apelat",
      "args": {{}},
      "depends_on": [],
      "visual_verify": false,
      "retry_count": 2
    }}
  ]
}}"""

        try:
            import requests
            resp = requests.post(
                self.llm_url,
                json={"model": self.llm_model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()

            # Curatam markdown daca exista
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            steps_data = data.get("steps", [])

            logger.info(f"   Plan LLM: {data.get('plan_summary', '')}")
            logger.info(f"    Estimat: {data.get('estimated_minutes', '?')} minute")

            steps = [
                Step(
                    id=s.get("id", i+1),
                    description=s.get("description", ""),
                    tool=s.get("tool", ""),
                    action=s.get("action", ""),
                    args=s.get("args", {}),
                    depends_on=s.get("depends_on", []),
                    visual_verify=s.get("visual_verify", False),
                    retry_count=s.get("retry_count", 2),
                )
                for i, s in enumerate(steps_data)
            ]
            
            # Insert integrity step at the beginning if needed
            if needs_integrity_check:
                # Renumber existing steps
                for step in steps:
                    step.id += 1
                    step.depends_on = [d + 1 for d in step.depends_on]
                steps.insert(0, integrity_step)
            
            return steps

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # Fallback: plan minimal - vede + raporteaza
            return self._fallback_plan(task)

    def _fallback_plan(self, task: str) -> List[Step]:
        """Plan minimal cand LLM-ul nu poate planifica."""
        return [
            Step(
                id=1,
                description="Captura ecran curent",
                tool="desktop_capture",
                action="capture",
                visual_verify=False,
            ),
            Step(
                id=2,
                description="Extrage text vizibil",
                tool="ocr_tool",
                action="capture_and_read",
                depends_on=[1],
                visual_verify=False,
            ),
        ]

    # -- 4. EXECUTA ------------------------------------------------------------
    def _execute_plan(self, plan: List[Step], task: str, hyper_summary: HyperSummary) -> Dict[int, Any]:
        """
        Executa planul pas cu pas.
        Fiecare pas: verifica dependente  ruleaza  verifica vizual  retry daca fail.
        """
        results: Dict[int, Any] = {}
        completed_ids = set()

        for step in plan:
            # Verifica dependente
            if step.depends_on:
                missing = [d for d in step.depends_on if d not in completed_ids]
                if missing:
                    logger.warning(
                        f"   Pas {step.id} sarit - dependente neindeplinite: {missing}"
                    )
                    step.status = "skipped"
                    continue

            logger.info(f"\n    Pas {step.id}: {step.description}")
            step.status = "running"
            start = time.time()

            # Retry logic
            for attempt in range(step.retry_count + 1):
                try:
                    result = self._run_step(step, results)
                    step.result = result
                    step.status = "done"
                    step.duration_sec = time.time() - start
                    results[step.id] = result
                    completed_ids.add(step.id)

                    logger.info(
                        f"   Pas {step.id} gata in {step.duration_sec:.1f}s"
                    )

                    # Verificare vizuala dupa pas important
                    if step.visual_verify and self.auto_verify:
                        self._visual_verify_step(step)

                    break  # succes - iesim din retry

                except Exception as e:
                    step.error = str(e)
                    if attempt < step.retry_count:
                        logger.warning(
                            f"   Retry {attempt+1}/{step.retry_count} "
                            f"pentru pasul {step.id}: {e}"
                        )
                        time.sleep(1)
                    else:
                        step.status = "failed"
                        step.duration_sec = time.time() - start
                        logger.error(f"  [FAIL] Pas {step.id} esuat: {e}")

                        # Self-healing: incearca sa repare toolul
                        if self._evolver:
                            try:
                                self._evolver.analyze_anomaly(
                                    file_path=str(self.project_root / "tools" / f"{step.tool}.py"),
                                    anomaly_type="tool_failure",
                                    anomaly_details={
                                        "tool": step.tool,
                                        "action": step.action,
                                        "args": step.args,
                                        "error": step.error,
                                        "traceback": traceback.format_exc(),
                                        "task_context": task,
                                    }
                                )
                                logger.info(f"   Self-healing analysis sent for {step.tool}")
                            except Exception as heal_err:
                                logger.debug(f"Self-healing failed (non-critical): {heal_err}")

        return results

    def _run_step(self, step: Step, previous_results: Dict[int, Any]) -> Any:
        """
        Ruleaza un singur pas din plan.
        Injecteaza rezultatele pasilor anteriori ca context.
        """
        if self.dry_run:
            logger.info(f"  [DRY RUN] {step.tool}.{step.action}({step.args})")
            return f"DRY_RUN_RESULT_{step.id}"

        # Obtinem instanta toolului
        tool_info = self._tool_registry.get(step.tool)
        if not tool_info:
            raise ValueError(f"Tool necunoscut: {step.tool}")

        tool_instance = tool_info["loader"]()
        if not tool_instance:
            raise RuntimeError(f"Tool {step.tool} nu a putut fi initializat")

        # Injectam rezultatele anterioare in args daca sunt referentiate
        args = dict(step.args)
        for key, val in args.items():
            if isinstance(val, str) and val.startswith("$step_"):
                step_ref = int(val.replace("$step_", ""))
                if step_ref in previous_results:
                    args[key] = previous_results[step_ref]

        # Apelam metoda
        method = getattr(tool_instance, step.action, None)
        if not method:
            raise AttributeError(
                f"Metoda '{step.action}' nu exista in {step.tool}"
            )

        if args:
            return method(**args)
        else:
            return method()

    # -- 5. VERIFICA VIZUAL ----------------------------------------------------
    def _visual_verify_step(self, step: Step):
        """
        Face screenshot dupa un pas important si verifica vizual ca a functionat.
        Asta e avantajul cheie fata de agentii orbi.
        """
        try:
            capture = self._tool_registry["desktop_capture"]["loader"]()
            ocr     = self._tool_registry["ocr_tool"]["loader"]()

            if capture:
                screenshot_path = capture.capture()
                logger.info(f"   Verificare vizuala: {screenshot_path}")

            if ocr:
                screen_text = ocr.capture_and_read() or ""
                # Verificare simpla: daca exista text de eroare pe ecran
                error_keywords = ["error", "eroare", "failed", "esuat", "exception", "crash"]
                found_errors = [kw for kw in error_keywords if kw.lower() in screen_text.lower()]
                if found_errors:
                    logger.warning(
                        f"  [WARN] Verificare vizuala: gasit text suspect: {found_errors}"
                    )
                else:
                    logger.info(f"   Verificare vizuala: ecran pare OK")

        except Exception as e:
            logger.debug(f"Visual verify failed: {e}")

    def _verify_final_state(self, task: str) -> Optional[str]:
        """Screenshot final al starii dupa executia completa."""
        try:
            capture = self._tool_registry["desktop_capture"]["loader"]()
            if capture:
                path = capture.capture()
                logger.info(f"   Screenshot final: {path}")
                return path
        except Exception:
            pass
        return None

    # -- 6. RAPORTEAZA ---------------------------------------------------------
    def _build_result(
        self,
        task: str,
        plan: List[Step],
        results: Dict,
        final_screenshot: Optional[str],
        duration: float,
        hyper_summary: HyperSummary,
    ) -> TaskResult:
        done    = [s for s in plan if s.status == "done"]
        failed  = [s for s in plan if s.status == "failed"]
        skipped = [s for s in plan if s.status == "skipped"]

        success = len(failed) == 0 and len(done) > 0

        summary_parts = [
            f"Task: {task}",
            f"Durata: {duration:.1f}s",
            f"Pasi: {len(done)} reusiti, {len(failed)} esuati, {len(skipped)} sariti",
        ]

        if failed:
            summary_parts.append(
                "Erori: " + "; ".join(f"Pas {s.id}: {s.error[:100]}" for s in failed)
            )

        return TaskResult(
            task=task,
            success=success,
            steps_total=len(plan),
            steps_done=len(done),
            steps_failed=len(failed),
            duration_sec=duration,
            summary="\n".join(summary_parts),
            visual_proof=final_screenshot,
            errors=[f"Pas {s.id}: {s.error}" for s in failed],
            hyper_summary=hyper_summary,
        )

    # -- 7. INVATA -------------------------------------------------------------
    def _learn_from_execution(self, task: str, plan: List[Step], result: TaskResult, file_analysis: dict | None):
        """
        Salveaza ce a functionat si ce nu in memory_cortex.
        Foloseste metode defensive - functioneaza indiferent de versiunea cortex-ului.
        """
        if not self._cortex:
            return

        try:
            memory_entries = 0
            tools_used = list(dict.fromkeys(s.tool for s in plan if s.status == "done"))
            pattern = f"Tooluri in ordine: {'  '.join(tools_used)}"

            # Save task execution to episodic memory
            if hasattr(self._cortex, "remember"):
                self._cortex.remember(
                    key=f"task_execution:{int(time.time())}",
                    value={
                        "task": task[:200],
                        "tools_used": tools_used,
                        "success": result.success,
                        "duration_sec": result.duration_sec,
                        "steps_done": result.steps_done,
                        "steps_failed": result.steps_failed,
                        "file_analyzed": file_analysis["file_path"] if file_analysis else None,
                    },
                    memory_type="episodic"
                )
                memory_entries += 1

            if result.success:
                # Incearca metodele posibile ale MemoryCortex in ordine de preferinta
                if hasattr(self._cortex, "learned_success"):
                    self._cortex.learned_success(
                        task_type=self._classify_task(task),
                        pattern=pattern,
                        notes=f"Task: {task[:100]} | Durata: {result.duration_sec:.0f}s",
                    )
                elif hasattr(self._cortex, "store"):
                    self._cortex.store(
                        category="orchestrator_success",
                        key=f"task_{self._classify_task(task)}_{int(time.time())}",
                        value=json.dumps({
                            "task": task[:200],
                            "pattern": pattern,
                            "duration": result.duration_sec,
                            "steps": result.steps_done,
                        }),
                    )
                elif hasattr(self._cortex, "remember"):
                    self._cortex.remember(
                        context=f"success|{self._classify_task(task)}",
                        content=pattern,
                    )

                result.learned.append(f"Pattern salvat: {pattern}")
                logger.info(f"   Salvat in memorie: {pattern}")
                result.hyper_summary.memory_entries_written = memory_entries

            # Salvam erorile pentru evitare viitoare (deep error memory)
            for step in plan:
                if step.status == "failed" and step.error:
                    error_entry = {
                        "tool": step.tool,
                        "action": step.action,
                        "error": step.error[:200],
                        "task_context": task[:100],
                        "timestamp": time.time(),
                    }

                    if hasattr(self._cortex, "remember"):
                        self._cortex.remember(
                            key=f"tool_failure:{step.tool}:{int(time.time())}",
                            value=error_entry,
                            memory_type="error"
                        )
                        memory_entries += 1

                    if hasattr(self._cortex, "correct"):
                        self._cortex.correct(
                            original_prompt=task,
                            bad_response=f"Tool {step.tool}.{step.action} a esuat",
                            correct_response=f"Evita {step.tool}.{step.action} fara verificare prealabila",
                            error_type=f"tool_failure_{step.tool}",
                            tags=[step.tool],
                        )

            # Save structure hints to semantic memory
            if file_analysis and result.hyper_summary.file_structure_hints:
                for hint in result.hyper_summary.file_structure_hints:
                    if hint != "unknown" and hasattr(self._cortex, "remember"):
                        self._cortex.remember(
                            key=f"structure:{hint}:{int(time.time())}",
                            value={
                                "file_path": file_analysis.get("file_path"),
                                "hint": hint,
                                "confidence": 0.9,
                            },
                            memory_type="semantic"
                        )
                        memory_entries += 1

            result.hyper_summary.memory_entries_written = memory_entries

        except Exception as e:
            logger.debug(f"Learning failed (non-critical): {e}")

    def _classify_task(self, task: str) -> str:
        """Clasifica taskul in categorii pentru pattern learning."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["screenshot", "captura", "ecran", "vede"]):
            return "visual_task"
        if any(w in task_lower for w in ["scrie", "tasteaza", "deschide", "click"]):
            return "ui_automation"
        if any(w in task_lower for w in ["verifica", "eroare", "debug", "analizeaza"]):
            return "debug_task"
        if any(w in task_lower for w in ["fisier", "folder", "salveaza", "citeste"]):
            return "file_task"
        if any(w in task_lower for w in ["log", "eroare", "traceback", "debug"]):
            return "log_analysis_task"
        if any(w in task_lower for w in ["analiza", "inspect", "structure"]):
            return "code_analysis_task"
        return "general_task"

    # -- Print result ----------------------------------------------------------
    def _print_result(self, result: TaskResult):
        icon = "" if result.success else "[FAIL]"
        print(f"\n{'='*60}")
        print(f"{icon} TASK {'FINALIZAT' if result.success else 'ESUAT'}")
        print(f"{'='*60}")
        print(f"Durata:  {result.duration_sec:.1f}s  "
              f"({'~' + str(int(result.duration_sec/60)) + ' min' if result.duration_sec > 60 else 'sub 1 min'})")
        print(f"Pasi:    {result.steps_done}/{result.steps_total} reusiti")
        if result.visual_proof:
            print(f"Dovada:  {result.visual_proof}")
        if result.learned:
            print(f"Invatat: {'; '.join(result.learned)}")
        if result.errors:
            print(f"Erori:   {'; '.join(result.errors[:3])}")
        print("="*60 + "\n")

    # -- TTS helper ------------------------------------------------------------
    def _speak(self, text: str):
        if self._tts and self.voice_feedback:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception:
                pass

    # -- Monitor continuu ------------------------------------------------------
    def monitor(self, task: str, interval_sec: int = 30, max_checks: int = 20):
        """
        Monitorizeaza un proces in curs (compilare, download, etc.)
        si anunta cand se termina sau apare o eroare.

        Exemplu:
            orchestrator.monitor("compilarea proiectului", interval_sec=15)
        """
        logger.info(f" Monitorizez: {task}")
        self._speak(f"Incep monitorizarea: {task}")

        prev_text = ""
        for check in range(max_checks):
            state = self._see_current_state()
            current_text = state.get("screen_text", "")

            # Detectam schimbari semnificative
            if current_text != prev_text:
                changed_lines = len(set(current_text.split()) - set(prev_text.split()))
                logger.info(f"  [{check+1}/{max_checks}] Schimbare detectata: {changed_lines} cuvinte noi")

                # Detectam finalizare sau eroare
                finish_signals = ["done", "complete", "finished", "success", "gata", "finalizat"]
                error_signals  = ["error", "failed", "crash", "exception", "eroare", "esuat"]

                text_lower = current_text.lower()

                if any(s in text_lower for s in finish_signals):
                    msg = f"Procesul '{task}' pare finalizat!"
                    logger.info(f"   {msg}")
                    self._speak(msg)
                    return True

                if any(s in text_lower for s in error_signals):
                    msg = f"Detectat posibil eroare in '{task}'!"
                    logger.warning(f"  [WARN] {msg}")
                    self._speak(msg)
                    return False

                prev_text = current_text

            time.sleep(interval_sec)

        self._speak(f"Monitorizare terminata pentru: {task}")
        return None

    # -- Batch execution -------------------------------------------------------
    def execute_batch(
        self,
        tasks: List[str],
        stop_on_failure: bool = False,
    ) -> List[TaskResult]:
        """
        Executa o lista de taskuri in ordine.

        Exemplu:
            results = orchestrator.execute_batch([
                "Fa screenshot la ecran",
                "Extrage textul din fereastra activa",
                "Salveaza log-ul in Desktop/ana_log.txt",
            ])
            for r in results:
                print(r.summary)

        Parametri:
            tasks           : lista de taskuri in limbaj natural
            stop_on_failure : daca True, se opreste la primul task esuat
        """
        logger.info(f"\n{'='*60}")
        logger.info(f" BATCH: {len(tasks)} taskuri")
        logger.info(f"{'='*60}")

        self._speak(f"Pornesc {len(tasks)} taskuri in batch.")
        results = []

        for i, task in enumerate(tasks, 1):
            logger.info(f"\n Batch [{i}/{len(tasks)}]: {task[:60]}")
            result = self.execute(task)
            results.append(result)

            if stop_on_failure and not result.success:
                logger.warning(f" Batch oprit la taskul {i} (esec): {task[:60]}")
                self._speak("Batch oprit din cauza unei erori.")
                break

        done_count  = sum(1 for r in results if r.success)
        fail_count  = sum(1 for r in results if not r.success)
        total_time  = sum(r.duration_sec for r in results)

        logger.info(f"\n{'='*60}")
        logger.info(f" BATCH FINALIZAT: {done_count} reusite, {fail_count} esuate, {total_time:.1f}s total")
        logger.info(f"{'='*60}")
        self._speak(f"Batch finalizat. {done_count} din {len(tasks)} taskuri reusite.")

        return results

    # -- Status / introspection ------------------------------------------------
    def get_status(self) -> dict:
        """
        Returneaza statusul curent al orchestratorului:
        ce tooluri sunt disponibile, cate memories are, etc.

        Util pentru health-check din MCP server sau dashboard.
        """
        available_tools = []
        unavailable_tools = []

        for name, info in self._tool_registry.items():
            instance = info["loader"]()
            if instance is not None:
                available_tools.append(name)
            else:
                unavailable_tools.append(name)

        memory_stats = {}
        if self._cortex:
            try:
                memory_stats = self._cortex.get_memory_stats()
            except Exception:
                memory_stats = {"error": "indisponibil"}

        return {
            "orchestrator": "ANA MAX OS27 Hyper Orchestrator v1.0.0",
            "dry_run": self.dry_run,
            "auto_verify": self.auto_verify,
            "voice_feedback": self.voice_feedback,
            "tools_available": available_tools,
            "tools_unavailable": unavailable_tools,
            "tools_total": len(self._tool_registry),
            "memory_cortex": bool(self._cortex),
            "self_evolving": bool(self._evolver),
            "context_engine": bool(self._context),
            "proactive_interrupt": bool(self._pi),
            "memory_stats": memory_stats,
            "llm_url": self.llm_url,
            "llm_model": self.llm_model,
            "hyper_telemetry": self._hyper_telemetry,
        }

    # -- MCP Server integration ------------------------------------------------
    def register_as_mcp_tool(self, mcp_app) -> None:
        """
        Inregistreaza orchestratorul ca tool MCP in serverul ANA MAX.
        Apeleaza asta din mcp_server.py dupa ce initializezi AnaOrchestrator.

        Exemplu in mcp_server.py:
            from tools.ana_orchestrator import AnaOrchestrator
            orchestrator = AnaOrchestrator(...)

            # Inregistrare ca tool MCP:
            orchestrator.register_as_mcp_tool(app)

        Dup asta, orice client MCP (Claude, Cursor, Windsurf) poate apela:
            {
              "method": "call_tool",
              "params": {
                "tool": "ana_orchestrate",
                "args": {"task": "Deschide Notepad si scrie Hello ANA"}
              }
            }

            {
              "method": "call_tool",
              "params": {
                "tool": "ana_orchestrate_batch",
                "args": {
                  "tasks": ["Fa screenshot", "Extrage text", "Salveaza log"],
                  "stop_on_failure": false
                }
              }
            }
        """
        try:
            from flask import request, jsonify
        except ImportError:
            logger.error("Flask indisponibil - nu pot inregistra toolurile MCP.")
            return

        orchestrator_self = self  # referinta pentru closure

        @mcp_app.route("/tools/ana_orchestrate", methods=["POST"])
        def mcp_orchestrate():
            """MCP endpoint: executa un task complex in limbaj natural."""
            data = request.get_json(force=True) or {}
            task    = data.get("task", "")
            context = data.get("context", None)

            if not task:
                return jsonify({"error": "Campul 'task' este obligatoriu."}), 400

            try:
                result = orchestrator_self.execute(task, context=context)
                return jsonify({
                    "success":      result.success,
                    "task":         result.task,
                    "summary":      result.summary,
                    "steps_done":   result.steps_done,
                    "steps_total":  result.steps_total,
                    "duration_sec": round(result.duration_sec, 2),
                    "visual_proof": result.visual_proof,
                    "learned":      result.learned,
                    "errors":       result.errors,
                    "hyper_summary": {
                        "file_analysis_used": result.hyper_summary.file_analysis_used,
                        "anomalies_detected": result.hyper_summary.anomalies_detected,
                        "memory_entries_written": result.hyper_summary.memory_entries_written,
                        "context_updates": result.hyper_summary.context_updates,
                        "self_healing_attempts": result.hyper_summary.self_healing_attempts,
                    },
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @mcp_app.route("/tools/ana_orchestrate_batch", methods=["POST"])
        def mcp_orchestrate_batch():
            """MCP endpoint: executa mai multe taskuri in batch."""
            data  = request.get_json(force=True) or {}
            tasks = data.get("tasks", [])
            stop_on_failure = data.get("stop_on_failure", False)

            if not tasks or not isinstance(tasks, list):
                return jsonify({"error": "Campul 'tasks' trebuie sa fie o lista non-goala."}), 400

            try:
                results = orchestrator_self.execute_batch(tasks, stop_on_failure=stop_on_failure)
                return jsonify({
                    "total":    len(results),
                    "success":  sum(1 for r in results if r.success),
                    "failed":   sum(1 for r in results if not r.success),
                    "results":  [
                        {
                            "task":         r.task,
                            "success":      r.success,
                            "steps_done":   r.steps_done,
                            "steps_total":  r.steps_total,
                            "duration_sec": round(r.duration_sec, 2),
                            "errors":       r.errors,
                        }
                        for r in results
                    ],
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @mcp_app.route("/tools/ana_orchestrator_status", methods=["GET"])
        def mcp_orchestrator_status():
            """MCP endpoint: health-check si status al orchestratorului."""
            return jsonify(orchestrator_self.get_status())

        logger.info("   Orchestrator inregistrat ca MCP tools:")
        logger.info("     POST /tools/ana_orchestrate")
        logger.info("     POST /tools/ana_orchestrate_batch")
        logger.info("     GET  /tools/ana_orchestrator_status")


# -----------------------------------------------------------------------------
# Exemplu de utilizare
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Exemplu de utilizare directa
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    orchestrator = AnaOrchestrator(
        db_path="ana_memory.db",
        llm_url="http://localhost:11434/api/generate",
        llm_model="mistral",
        voice_feedback=True,
        auto_verify=True,
        dry_run=False,        # True = simulare fara executie reala
    )

    # -- Status ----------------------------------------------------------------
    print("\n=== STATUS ORCHESTRATOR ===")
    status = orchestrator.get_status()
    print(f"Tooluri disponibile ({len(status['tools_available'])}): {', '.join(status['tools_available'])}")
    if status['tools_unavailable']:
        print(f"Tooluri lipsa: {', '.join(status['tools_unavailable'])}")
    print(f"Memory Cortex: {'' if status['memory_cortex'] else '[WARN] indisponibil'}")
    print(f"Self-Evolving: {'' if status['self_evolving'] else '[WARN] indisponibil'}")

    # -- Task simplu -----------------------------------------------------------
    print("\n=== TEST 1: Task simplu ===")
    result = orchestrator.execute(
        "Fa screenshot la ecran si extrage tot textul vizibil"
    )

    # -- Task complex UI -------------------------------------------------------
    # print("\n=== TEST 2: Task complex UI ===")
    # result = orchestrator.execute(
    #     "Deschide Notepad, scrie data si ora curenta, salveaza ca ana_log.txt pe Desktop"
    # )

    # -- Batch -----------------------------------------------------------------
    # print("\n=== TEST 3: Batch ===")
    # results = orchestrator.execute_batch([
    #     "Fa screenshot la ecran",
    #     "Extrage textul din fereastra activa",
    #     "Verifica daca exista erori vizibile pe ecran",
    # ], stop_on_failure=False)

    # -- Monitorizare ----------------------------------------------------------
    # print("\n=== TEST 4: Monitorizare compilare ===")
    # orchestrator.monitor("compilarea proiectului", interval_sec=10, max_checks=12)

    # -- MCP registration (demo, necesita Flask app) ---------------------------
    # from flask import Flask
    # app = Flask(__name__)
    # orchestrator.register_as_mcp_tool(app)
    # app.run(port=8766)  # disponibil la http://127.0.0.1:8766/tools/ana_orchestrate
