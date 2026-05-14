"""
ANA MAX – ana_orchestrator.py
==============================
Creierul care coordonează toate toolurile ANA MAX între ele.

Problema pe care o rezolvă:
  Ai tooluri excelente dar fiecare lucrează singur.
  window_manager nu știe ce face ocr_tool.
  memory_cortex nu știe ce vede desktop_capture.
  Rezultat: agent care lucrează orb, task de 2h rămâne 2h.

Soluția:
  Orchestratorul primește un task în limbaj natural și:
    1. VEDE      — face screenshot, rulează OCR, înțelege contextul vizual
    2. GÂNDEȘTE  — consultă memory_cortex pentru erori anterioare și preferințe
    3. PLANIFICĂ — împarte taskul în pași mici cu toolurile corecte
    4. EXECUTĂ   — rulează pașii în ordine, cu retry automat
    5. VERIFICĂ  — face screenshot după fiecare pas, confirmă vizual că a mers
    6. RAPORTEAZĂ — ce a făcut, cât a durat, ce a învățat
    7. ÎNVAȚĂ    — salvează patternuri de succes și erori în memory_cortex

Rezultat practic:
  Task de 2 ore → 30 minute
  Agent orb → agent care vede și verifică
  Erori repetate → eliminate prin memory_cortex

Integrare în main.py:
    from tools.ana_orchestrator import AnaOrchestrator

    orchestrator = AnaOrchestrator(
        db_path="ana_memory.db",
        llm_url="http://localhost:11434/api/generate",
        llm_model="mistral",
    )

    # Task simplu în limbaj natural:
    result = orchestrator.execute("Deschide Excel, verifică coloana B pentru erori și raportează")
    result = orchestrator.execute("Fă screenshot, extrage toate emailurile din pagina curentă")
    result = orchestrator.execute("Monitorizează progresul compilării și anunță când termină")

    # Taskuri multiple în batch:
    results = orchestrator.execute_batch([
        "Fă screenshot la ecran",
        "Extrage textul din fereastra activă",
        "Salvează raportul în clipboard",
    ])

    # Expunere ca tool MCP (pentru Claude / Cursor / Windsurf):
    #   Adaugă în mcp_server.py:
    #   from tools.ana_orchestrator import AnaOrchestrator
    #   orchestrator = AnaOrchestrator(...)
    #   @app.route("/mcp", methods=["POST"])
    #   def mcp_handler(): ...  # vezi secțiunea MCP la finalul fișierului

Note tehnice:
  - Toolurile se încarcă lazy (la prima folosire), nu la init
  - Referențierea rezultatelor anterioare: args={"image": "$step_1"}
  - dry_run=True simulează tot fără să execute nimic real
  - voice_feedback=True folosește pyttsx3 pentru feedback vocal
"""

import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ANA.Orchestrator")


# ── Structuri de date ─────────────────────────────────────────────────────────
@dataclass
class Step:
    """Un pas dintr-un plan de execuție."""
    id: int
    description: str
    tool: str                    # ex: "desktop_capture", "ocr_tool", "window_manager"
    action: str                  # ex: "capture_and_read", "get_active_window"
    args: Dict = field(default_factory=dict)
    depends_on: List[int] = field(default_factory=list)  # ID-uri pași anteriori
    visual_verify: bool = False  # face screenshot după execuție pentru verificare
    retry_count: int = 2
    status: str = "pending"      # pending | running | done | failed | skipped
    result: Any = None
    error: str = ""
    duration_sec: float = 0.0


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
    learned: List[str] = field(default_factory=list)  # ce a învățat ANA
    errors: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
class AnaOrchestrator:
    """
    Orchestratorul principal ANA MAX.

    Coordonează toate toolurile între ele pentru a executa
    taskuri complexe în limbaj natural.
    """

    def __init__(
        self,
        db_path: str = "ana_memory.db",
        llm_url: str = "http://localhost:11434/api/generate",
        llm_model: str = "mistral",
        project_root: str = ".",
        voice_feedback: bool = True,
        auto_verify: bool = True,       # screenshot după fiecare pas important
        dry_run: bool = False,          # simulează fără a executa (pentru test)
    ):
        self.db_path      = db_path
        self.llm_url      = llm_url
        self.llm_model    = llm_model
        self.project_root = Path(project_root).resolve()
        self.voice_feedback = voice_feedback
        self.auto_verify  = auto_verify
        self.dry_run      = dry_run

        # Inițializăm sub-sistemele ANA MAX
        self._cortex   = None   # MemoryCortex
        self._evolver  = None   # SelfEvolvingTool
        self._pi       = None   # ProactiveInterrupt
        self._tts      = None   # voce

        self._load_subsystems()
        self._register_tools()

        logger.info("✅ AnaOrchestrator inițializat.")

    # ── Încărcare sub-sisteme ─────────────────────────────────────────────────
    def _load_subsystems(self):
        """Încarcă toate sub-sistemele ANA MAX disponibile."""

        # Memory Cortex
        try:
            from tools.memory_cortex import MemoryCortex
            self._cortex = MemoryCortex(db_path=self.db_path, verbose=False)
            logger.info("  ✅ MemoryCortex încărcat")
        except ImportError:
            logger.warning("  ⚠️ MemoryCortex indisponibil")

        # Self Evolving Tool
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            self._evolver = SelfEvolvingTool(
                project_root=str(self.project_root),
                db_path=self.db_path,
                llm_url=self.llm_url,
                llm_model=self.llm_model,
                auto_improve=False,  # manual în orchestrator
            )
            logger.info("  ✅ SelfEvolvingTool încărcat")
        except ImportError:
            logger.warning("  ⚠️ SelfEvolvingTool indisponibil")

        # TTS
        if self.voice_feedback:
            try:
                import pyttsx3
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 165)
                logger.info("  ✅ TTS încărcat")
            except Exception:
                logger.warning("  ⚠️ TTS indisponibil")

    # ── Registry tooluri ─────────────────────────────────────────────────────
    def _register_tools(self):
        """
        Registrul tuturor toolurilor ANA MAX disponibile.
        Orchestratorul știe ce poate face fiecare tool.
        """
        self._tool_registry: Dict[str, dict] = {

            "desktop_capture": {
                "description": "Face screenshot la ecranul curent. Returnează calea imaginii.",
                "capabilities": ["vede ecranul", "captură vizuală", "screenshot"],
                "loader": self._load_tool("tools.desktop_capture", "DesktopCapture"),
            },

            "ocr_tool": {
                "description": "Extrage textul vizibil de pe ecran prin OCR (PaddleOCR).",
                "capabilities": ["citește text", "extrage date", "recunoaște text pe ecran"],
                "loader": self._load_tool("tools.ocr_tool", "OCRTool"),
            },

            "window_manager": {
                "description": "Controlează ferestrele Windows: focus, resize, listare.",
                "capabilities": ["gestionează ferestre", "focus app", "lista ferestre deschise"],
                "loader": self._load_tool("tools.window_manager", "WindowManager"),
            },

            "clipboard_manager": {
                "description": "Citește și scrie în clipboard.",
                "capabilities": ["clipboard", "copiere", "lipire text"],
                "loader": self._load_tool("tools.clipboard_manager", "ClipboardManager"),
            },

            "windows_uia_bridge": {
                "description": "Click, type, read prin UIAutomation. Controlul complet al UI-ului Windows.",
                "capabilities": ["click", "tastează", "automatizare UI", "buton", "input"],
                "loader": self._load_tool("tools.windows_uia_bridge", "WindowsUIABridge"),
            },

            "terminal_tool": {
                "description": "Execută comenzi PowerShell/CMD.",
                "capabilities": ["rulează comandă", "terminal", "powershell", "script"],
                "loader": self._load_tool("tools.terminal_tool", "TerminalTool"),
            },

            "security_tool": {
                "description": "Scanează fișiere pentru secrete și vulnerabilități.",
                "capabilities": ["securitate", "scan", "vulnerabilități", "secrete"],
                "loader": self._load_tool("tools.security_tool", "SecurityTool"),
            },

            "network_tool": {
                "description": "Ping, port-scan, DNS lookup.",
                "capabilities": ["rețea", "ping", "port", "dns", "conexiune"],
                "loader": self._load_tool("tools.network_tool", "NetworkTool"),
            },
        }

    def _load_tool(self, module_path: str, class_name: str):
        """Returnează un factory lazy pentru un tool."""
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

    # ── API PRINCIPAL: execute ────────────────────────────────────────────────
    def execute(
        self,
        task: str,
        context: Optional[str] = None,
        max_steps: int = 15,
    ) -> TaskResult:
        """
        Execută un task complex în limbaj natural.

        Parametri:
            task     : descrierea taskului în română sau engleză
            context  : context suplimentar opțional
            max_steps: numărul maxim de pași pentru siguranță

        Exemplu:
            result = orchestrator.execute(
                "Deschide Notepad, scrie 'Hello ANA', salvează ca test.txt"
            )
            result = orchestrator.execute(
                "Verifică dacă există erori în fereastra activă și raportează"
            )
        """
        start_time = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 TASK: {task}")
        logger.info(f"{'='*60}")

        self._speak(f"Am primit taskul: {task[:80]}")

        # 1. VEDE — snapshot vizual al stării curente
        visual_context = self._see_current_state()

        # 2. GÂNDEȘTE — consultă memoria
        memory_context = self._think(task)

        # 3. PLANIFICĂ — creează planul de execuție
        plan = self._plan(task, visual_context, memory_context, context, max_steps)

        if not plan:
            return TaskResult(
                task=task, success=False,
                steps_total=0, steps_done=0, steps_failed=0,
                duration_sec=time.time() - start_time,
                summary="Nu am putut crea un plan de execuție.",
                errors=["Planning failed"]
            )

        logger.info(f"📋 Plan creat: {len(plan)} pași")
        for step in plan:
            logger.info(f"  [{step.id}] {step.description} → {step.tool}")

        # 4. EXECUTĂ — rulează pașii
        results = self._execute_plan(plan)

        # 5. VERIFICĂ — screenshot final
        final_screenshot = self._verify_final_state(task)

        # 6. RAPORTEAZĂ — sintetizează ce s-a întâmplat
        duration = time.time() - start_time
        task_result = self._build_result(
            task, plan, results, final_screenshot, duration
        )

        # 7. ÎNVAȚĂ — salvează în memory_cortex
        self._learn_from_execution(task, plan, task_result)

        self._speak(
            f"Task finalizat în {duration:.0f} secunde. "
            f"{task_result.steps_done} pași reușiți."
        )

        self._print_result(task_result)
        return task_result

    # ── 1. VEDE ───────────────────────────────────────────────────────────────
    def _see_current_state(self) -> dict:
        """
        Face un snapshot complet al stării vizuale curente.
        Ăsta e avantajul față de orice agent cloud — ANA vede ecranul.
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
                logger.info(f"  📸 Screenshot: {path}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")

        # Fereastră activă
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
                    logger.info(f"  👁️ OCR: {len(state['screen_text'])} caractere citite")
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

    # ── 2. GÂNDEȘTE ───────────────────────────────────────────────────────────
    def _think(self, task: str) -> dict:
        """Consultă memoria pentru context relevant."""
        memory = {
            "similar_tasks": [],
            "known_errors": [],
            "preferences": [],
        }

        if not self._cortex:
            return memory

        try:
            stats = self._cortex.get_memory_stats()
            memory["total_memories"] = stats.get("episodic_memories", 0)
            memory["known_errors"] = stats.get("top_repeated_errors", [])
            logger.info(
                f"  🧠 Memorie: {stats.get('episodic_memories', 0)} episoade, "
                f"{stats.get('llm_errors_caught', 0)} erori cunoscute"
            )
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")

        return memory

    # ── 3. PLANIFICĂ ──────────────────────────────────────────────────────────
    def _plan(
        self,
        task: str,
        visual_context: dict,
        memory_context: dict,
        extra_context: Optional[str],
        max_steps: int,
    ) -> List[Step]:
        """
        Folosește LLM-ul pentru a crea un plan de execuție structurat.
        Injectează contextul vizual și memoria în prompt.
        """

        # Construim descrierea toolurilor disponibile
        tools_desc = "\n".join(
            f"  - {name}: {info['description']}"
            for name, info in self._tool_registry.items()
        )

        # Context vizual
        visual_summary = ""
        if visual_context.get("active_window"):
            visual_summary += f"Fereastra activă: {visual_context['active_window']}\n"
        if visual_context.get("screen_text"):
            visual_summary += f"Text vizibil pe ecran: {visual_context['screen_text'][:500]}\n"
        if visual_context.get("open_windows"):
            visual_summary += f"Ferestre deschise: {', '.join(str(w) for w in visual_context['open_windows'][:5])}\n"

        # Erori cunoscute
        errors_warning = ""
        if memory_context.get("known_errors"):
            errors_warning = "ATENȚIE — erori anterioare de evitat:\n" + "\n".join(
                f"  - {e['type']}: repetat de {e['times']} ori"
                for e in memory_context["known_errors"]
            )

        prompt = f"""Ești orchestratorul ANA MAX, un agent AI pentru Windows.

TOOLURI DISPONIBILE:
{tools_desc}

STAREA CURENTĂ A ECRANULUI:
{visual_summary if visual_summary else "Indisponibilă"}

{errors_warning}

TASK DE EXECUTAT:
{task}

{f"CONTEXT SUPLIMENTAR: {extra_context}" if extra_context else ""}

Creează un plan de execuție cu MAXIM {max_steps} pași.
Fiecare pas trebuie să folosească un tool disponibil.
Pașii critici (care modifică ceva) trebuie să aibă visual_verify: true.

Răspunde STRICT în JSON, fără text suplimentar:
{{
  "plan_summary": "descriere scurtă a ce vei face",
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

            # Curățăm markdown dacă există
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            steps_data = data.get("steps", [])

            logger.info(f"  📋 Plan LLM: {data.get('plan_summary', '')}")
            logger.info(f"  ⏱️  Estimat: {data.get('estimated_minutes', '?')} minute")

            return [
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

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # Fallback: plan minimal — vede + raportează
            return self._fallback_plan(task)

    def _fallback_plan(self, task: str) -> List[Step]:
        """Plan minimal când LLM-ul nu poate planifica."""
        return [
            Step(
                id=1,
                description="Captură ecran curent",
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

    # ── 4. EXECUTĂ ────────────────────────────────────────────────────────────
    def _execute_plan(self, plan: List[Step]) -> Dict[int, Any]:
        """
        Execută planul pas cu pas.
        Fiecare pas: verifică dependențe → rulează → verifică vizual → retry dacă fail.
        """
        results: Dict[int, Any] = {}
        completed_ids = set()

        for step in plan:
            # Verifică dependențe
            if step.depends_on:
                missing = [d for d in step.depends_on if d not in completed_ids]
                if missing:
                    logger.warning(
                        f"  ⏭️ Pas {step.id} sărit — dependențe neîndeplinite: {missing}"
                    )
                    step.status = "skipped"
                    continue

            logger.info(f"\n  ▶️  Pas {step.id}: {step.description}")
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
                        f"  ✅ Pas {step.id} gata în {step.duration_sec:.1f}s"
                    )

                    # Verificare vizuală după pas important
                    if step.visual_verify and self.auto_verify:
                        self._visual_verify_step(step)

                    break  # succes — ieșim din retry

                except Exception as e:
                    step.error = str(e)
                    if attempt < step.retry_count:
                        logger.warning(
                            f"  🔄 Retry {attempt+1}/{step.retry_count} "
                            f"pentru pasul {step.id}: {e}"
                        )
                        time.sleep(1)
                    else:
                        step.status = "failed"
                        step.duration_sec = time.time() - start
                        logger.error(f"  ❌ Pas {step.id} eșuat: {e}")

                        # Self-healing: încearcă să repare toolul
                        if self._evolver:
                            try:
                                # Construim calea modulului manual (robust, fără _module_to_path)
                                tool_file = self.project_root / "tools" / f"{step.tool}.py"
                                if tool_file.exists():
                                    repair_fn = getattr(self._evolver, "_repair_file", None)
                                    if repair_fn:
                                        repair_fn(str(tool_file), traceback.format_exc())
                                        logger.info(f"  🔧 Self-healing aplicat pe {step.tool}")
                            except Exception as heal_err:
                                logger.debug(f"Self-healing failed (non-critical): {heal_err}")

        return results

    def _run_step(self, step: Step, previous_results: Dict[int, Any]) -> Any:
        """
        Rulează un singur pas din plan.
        Injectează rezultatele pașilor anteriori ca context.
        """
        if self.dry_run:
            logger.info(f"  [DRY RUN] {step.tool}.{step.action}({step.args})")
            return f"DRY_RUN_RESULT_{step.id}"

        # Obținem instanța toolului
        tool_info = self._tool_registry.get(step.tool)
        if not tool_info:
            raise ValueError(f"Tool necunoscut: {step.tool}")

        tool_instance = tool_info["loader"]()
        if not tool_instance:
            raise RuntimeError(f"Tool {step.tool} nu a putut fi inițializat")

        # Injectăm rezultatele anterioare în args dacă sunt referențiate
        args = dict(step.args)
        for key, val in args.items():
            if isinstance(val, str) and val.startswith("$step_"):
                step_ref = int(val.replace("$step_", ""))
                if step_ref in previous_results:
                    args[key] = previous_results[step_ref]

        # Apelăm metoda
        method = getattr(tool_instance, step.action, None)
        if not method:
            raise AttributeError(
                f"Metoda '{step.action}' nu există în {step.tool}"
            )

        if args:
            return method(**args)
        else:
            return method()

    # ── 5. VERIFICĂ VIZUAL ────────────────────────────────────────────────────
    def _visual_verify_step(self, step: Step):
        """
        Face screenshot după un pas important și verifică vizual că a funcționat.
        Ăsta e avantajul cheie față de agenții orbi.
        """
        try:
            capture = self._tool_registry["desktop_capture"]["loader"]()
            ocr     = self._tool_registry["ocr_tool"]["loader"]()

            if capture:
                screenshot_path = capture.capture()
                logger.info(f"  🔍 Verificare vizuală: {screenshot_path}")

            if ocr:
                screen_text = ocr.capture_and_read() or ""
                # Verificare simplă: dacă există text de eroare pe ecran
                error_keywords = ["error", "eroare", "failed", "eșuat", "exception", "crash"]
                found_errors = [kw for kw in error_keywords if kw.lower() in screen_text.lower()]
                if found_errors:
                    logger.warning(
                        f"  ⚠️ Verificare vizuală: găsit text suspect: {found_errors}"
                    )
                else:
                    logger.info(f"  ✅ Verificare vizuală: ecran pare OK")

        except Exception as e:
            logger.debug(f"Visual verify failed: {e}")

    def _verify_final_state(self, task: str) -> Optional[str]:
        """Screenshot final al stării după execuția completă."""
        try:
            capture = self._tool_registry["desktop_capture"]["loader"]()
            if capture:
                path = capture.capture()
                logger.info(f"  📸 Screenshot final: {path}")
                return path
        except Exception:
            pass
        return None

    # ── 6. RAPORTEAZĂ ─────────────────────────────────────────────────────────
    def _build_result(
        self,
        task: str,
        plan: List[Step],
        results: Dict,
        final_screenshot: Optional[str],
        duration: float,
    ) -> TaskResult:
        done    = [s for s in plan if s.status == "done"]
        failed  = [s for s in plan if s.status == "failed"]
        skipped = [s for s in plan if s.status == "skipped"]

        success = len(failed) == 0 and len(done) > 0

        summary_parts = [
            f"Task: {task}",
            f"Durată: {duration:.1f}s",
            f"Pași: {len(done)} reușiți, {len(failed)} eșuați, {len(skipped)} săriti",
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
        )

    # ── 7. ÎNVAȚĂ ─────────────────────────────────────────────────────────────
    def _learn_from_execution(self, task: str, plan: List[Step], result: TaskResult):
        """
        Salvează ce a funcționat și ce nu în memory_cortex.
        Folosește metode defensive — funcționează indiferent de versiunea cortex-ului.
        """
        if not self._cortex:
            return

        try:
            tools_used = list(dict.fromkeys(s.tool for s in plan if s.status == "done"))
            pattern = f"Tooluri în ordine: {' → '.join(tools_used)}"

            if result.success:
                # Încearcă metodele posibile ale MemoryCortex în ordine de preferință
                if hasattr(self._cortex, "learned_success"):
                    self._cortex.learned_success(
                        task_type=self._classify_task(task),
                        pattern=pattern,
                        notes=f"Task: {task[:100]} | Durată: {result.duration_sec:.0f}s",
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
                logger.info(f"  🧠 Salvat în memorie: {pattern}")

            # Salvăm erorile pentru evitare viitoare
            for step in plan:
                if step.status == "failed" and step.error:
                    error_entry = {
                        "tool": step.tool,
                        "action": step.action,
                        "error": step.error[:200],
                        "task_context": task[:100],
                    }

                    if hasattr(self._cortex, "correct"):
                        self._cortex.correct(
                            original_prompt=task,
                            bad_response=f"Tool {step.tool}.{step.action} a eșuat",
                            correct_response=f"Evită {step.tool}.{step.action} fără verificare prealabilă",
                            error_type=f"tool_failure_{step.tool}",
                            tags=[step.tool],
                        )
                    elif hasattr(self._cortex, "store"):
                        self._cortex.store(
                            category="orchestrator_error",
                            key=f"error_{step.tool}_{int(time.time())}",
                            value=json.dumps(error_entry),
                        )
                    elif hasattr(self._cortex, "remember"):
                        self._cortex.remember(
                            context=f"error|{step.tool}",
                            content=json.dumps(error_entry),
                        )

        except Exception as e:
            logger.debug(f"Learning failed (non-critical): {e}")

    def _classify_task(self, task: str) -> str:
        """Clasifică taskul în categorii pentru pattern learning."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["screenshot", "captură", "ecran", "vede"]):
            return "visual_task"
        if any(w in task_lower for w in ["scrie", "tastează", "deschide", "click"]):
            return "ui_automation"
        if any(w in task_lower for w in ["verifică", "eroare", "debug", "analizează"]):
            return "debug_task"
        if any(w in task_lower for w in ["fișier", "folder", "salvează", "citește"]):
            return "file_task"
        return "general_task"

    # ── Print result ──────────────────────────────────────────────────────────
    def _print_result(self, result: TaskResult):
        icon = "✅" if result.success else "❌"
        print(f"\n{'='*60}")
        print(f"{icon} TASK {'FINALIZAT' if result.success else 'EȘUAT'}")
        print(f"{'='*60}")
        print(f"Durată:  {result.duration_sec:.1f}s  "
              f"({'~' + str(int(result.duration_sec/60)) + ' min' if result.duration_sec > 60 else 'sub 1 min'})")
        print(f"Pași:    {result.steps_done}/{result.steps_total} reușiți")
        if result.visual_proof:
            print(f"Dovadă:  {result.visual_proof}")
        if result.learned:
            print(f"Învățat: {'; '.join(result.learned)}")
        if result.errors:
            print(f"Erori:   {'; '.join(result.errors[:3])}")
        print("="*60 + "\n")

    # ── TTS helper ────────────────────────────────────────────────────────────
    def _speak(self, text: str):
        if self._tts and self.voice_feedback:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception:
                pass

    # ── Monitor continuu ──────────────────────────────────────────────────────
    def monitor(self, task: str, interval_sec: int = 30, max_checks: int = 20):
        """
        Monitorizează un proces în curs (compilare, download, etc.)
        și anunță când se termină sau apare o eroare.

        Exemplu:
            orchestrator.monitor("compilarea proiectului", interval_sec=15)
        """
        logger.info(f"👁️ Monitorizez: {task}")
        self._speak(f"Încep monitorizarea: {task}")

        prev_text = ""
        for check in range(max_checks):
            state = self._see_current_state()
            current_text = state.get("screen_text", "")

            # Detectăm schimbări semnificative
            if current_text != prev_text:
                changed_lines = len(set(current_text.split()) - set(prev_text.split()))
                logger.info(f"  [{check+1}/{max_checks}] Schimbare detectată: {changed_lines} cuvinte noi")

                # Detectăm finalizare sau eroare
                finish_signals = ["done", "complete", "finished", "success", "gata", "finalizat"]
                error_signals  = ["error", "failed", "crash", "exception", "eroare", "eșuat"]

                text_lower = current_text.lower()

                if any(s in text_lower for s in finish_signals):
                    msg = f"Procesul '{task}' pare finalizat!"
                    logger.info(f"  ✅ {msg}")
                    self._speak(msg)
                    return True

                if any(s in text_lower for s in error_signals):
                    msg = f"Detectat posibil eroare în '{task}'!"
                    logger.warning(f"  ⚠️ {msg}")
                    self._speak(msg)
                    return False

                prev_text = current_text

            time.sleep(interval_sec)

        self._speak(f"Monitorizare terminată pentru: {task}")
        return None

    # ── Batch execution ───────────────────────────────────────────────────────
    def execute_batch(
        self,
        tasks: List[str],
        stop_on_failure: bool = False,
    ) -> List[TaskResult]:
        """
        Execută o listă de taskuri în ordine.

        Exemplu:
            results = orchestrator.execute_batch([
                "Fă screenshot la ecran",
                "Extrage textul din fereastra activă",
                "Salvează log-ul în Desktop/ana_log.txt",
            ])
            for r in results:
                print(r.summary)

        Parametri:
            tasks           : lista de taskuri în limbaj natural
            stop_on_failure : dacă True, se oprește la primul task eșuat
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 BATCH: {len(tasks)} taskuri")
        logger.info(f"{'='*60}")

        self._speak(f"Pornesc {len(tasks)} taskuri în batch.")
        results = []

        for i, task in enumerate(tasks, 1):
            logger.info(f"\n🔢 Batch [{i}/{len(tasks)}]: {task[:60]}")
            result = self.execute(task)
            results.append(result)

            if stop_on_failure and not result.success:
                logger.warning(f"⛔ Batch oprit la taskul {i} (eșec): {task[:60]}")
                self._speak("Batch oprit din cauza unei erori.")
                break

        done_count  = sum(1 for r in results if r.success)
        fail_count  = sum(1 for r in results if not r.success)
        total_time  = sum(r.duration_sec for r in results)

        logger.info(f"\n{'='*60}")
        logger.info(f"📦 BATCH FINALIZAT: {done_count} reușite, {fail_count} eșuate, {total_time:.1f}s total")
        logger.info(f"{'='*60}")
        self._speak(f"Batch finalizat. {done_count} din {len(tasks)} taskuri reușite.")

        return results

    # ── Status / introspection ────────────────────────────────────────────────
    def get_status(self) -> dict:
        """
        Returnează statusul curent al orchestratorului:
        ce tooluri sunt disponibile, câte memories are, etc.

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
            "orchestrator": "ANA MAX Orchestrator v0.1.0",
            "dry_run": self.dry_run,
            "auto_verify": self.auto_verify,
            "voice_feedback": self.voice_feedback,
            "tools_available": available_tools,
            "tools_unavailable": unavailable_tools,
            "tools_total": len(self._tool_registry),
            "memory_cortex": bool(self._cortex),
            "self_evolving": bool(self._evolver),
            "memory_stats": memory_stats,
            "llm_url": self.llm_url,
            "llm_model": self.llm_model,
        }

    # ── MCP Server integration ────────────────────────────────────────────────
    def register_as_mcp_tool(self, mcp_app) -> None:
        """
        Înregistrează orchestratorul ca tool MCP în serverul ANA MAX.
        Apelează asta din mcp_server.py după ce inițializezi AnaOrchestrator.

        Exemplu în mcp_server.py:
            from tools.ana_orchestrator import AnaOrchestrator
            orchestrator = AnaOrchestrator(...)

            # Înregistrare ca tool MCP:
            orchestrator.register_as_mcp_tool(app)

        Dup asta, orice client MCP (Claude, Cursor, Windsurf) poate apela:
            {
              "method": "call_tool",
              "params": {
                "tool": "ana_orchestrate",
                "args": {"task": "Deschide Notepad și scrie Hello ANA"}
              }
            }

            {
              "method": "call_tool",
              "params": {
                "tool": "ana_orchestrate_batch",
                "args": {
                  "tasks": ["Fă screenshot", "Extrage text", "Salvează log"],
                  "stop_on_failure": false
                }
              }
            }
        """
        try:
            from flask import request, jsonify
        except ImportError:
            logger.error("Flask indisponibil — nu pot înregistra toolurile MCP.")
            return

        orchestrator_self = self  # referință pentru closure

        @mcp_app.route("/tools/ana_orchestrate", methods=["POST"])
        def mcp_orchestrate():
            """MCP endpoint: execută un task complex în limbaj natural."""
            data = request.get_json(force=True) or {}
            task    = data.get("task", "")
            context = data.get("context", None)

            if not task:
                return jsonify({"error": "Câmpul 'task' este obligatoriu."}), 400

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
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @mcp_app.route("/tools/ana_orchestrate_batch", methods=["POST"])
        def mcp_orchestrate_batch():
            """MCP endpoint: execută mai multe taskuri în batch."""
            data  = request.get_json(force=True) or {}
            tasks = data.get("tasks", [])
            stop_on_failure = data.get("stop_on_failure", False)

            if not tasks or not isinstance(tasks, list):
                return jsonify({"error": "Câmpul 'tasks' trebuie să fie o listă non-goală."}), 400

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
            """MCP endpoint: health-check și status al orchestratorului."""
            return jsonify(orchestrator_self.get_status())

        logger.info("  ✅ Orchestrator înregistrat ca MCP tools:")
        logger.info("     POST /tools/ana_orchestrate")
        logger.info("     POST /tools/ana_orchestrate_batch")
        logger.info("     GET  /tools/ana_orchestrator_status")


# ─────────────────────────────────────────────────────────────────────────────
# Exemplu de utilizare
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Exemplu de utilizare directă
# ─────────────────────────────────────────────────────────────────────────────
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
        dry_run=False,        # True = simulare fără execuție reală
    )

    # ── Status ────────────────────────────────────────────────────────────────
    print("\n=== STATUS ORCHESTRATOR ===")
    status = orchestrator.get_status()
    print(f"Tooluri disponibile ({len(status['tools_available'])}): {', '.join(status['tools_available'])}")
    if status['tools_unavailable']:
        print(f"Tooluri lipsă: {', '.join(status['tools_unavailable'])}")
    print(f"Memory Cortex: {'✅' if status['memory_cortex'] else '⚠️ indisponibil'}")
    print(f"Self-Evolving: {'✅' if status['self_evolving'] else '⚠️ indisponibil'}")

    # ── Task simplu ───────────────────────────────────────────────────────────
    print("\n=== TEST 1: Task simplu ===")
    result = orchestrator.execute(
        "Fă screenshot la ecran și extrage tot textul vizibil"
    )

    # ── Task complex UI ───────────────────────────────────────────────────────
    # print("\n=== TEST 2: Task complex UI ===")
    # result = orchestrator.execute(
    #     "Deschide Notepad, scrie data și ora curentă, salvează ca ana_log.txt pe Desktop"
    # )

    # ── Batch ─────────────────────────────────────────────────────────────────
    # print("\n=== TEST 3: Batch ===")
    # results = orchestrator.execute_batch([
    #     "Fă screenshot la ecran",
    #     "Extrage textul din fereastra activă",
    #     "Verifică dacă există erori vizibile pe ecran",
    # ], stop_on_failure=False)

    # ── Monitorizare ──────────────────────────────────────────────────────────
    # print("\n=== TEST 4: Monitorizare compilare ===")
    # orchestrator.monitor("compilarea proiectului", interval_sec=10, max_checks=12)

    # ── MCP registration (demo, necesită Flask app) ───────────────────────────
    # from flask import Flask
    # app = Flask(__name__)
    # orchestrator.register_as_mcp_tool(app)
    # app.run(port=8766)  # disponibil la http://127.0.0.1:8766/tools/ana_orchestrate
