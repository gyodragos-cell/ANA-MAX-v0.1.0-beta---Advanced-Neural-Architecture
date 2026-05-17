"""
ANA MAX – memory_cortex.py
===========================
Stratul de memorie care stă ÎNTRE tine și orice LLM.

Problema pe care o rezolvă:
  Toate AI-urile (Claude, GPT, Gemini, Ollama) uită după fiecare sesiune.
  Repetă aceleași greșeli. Nu știu cine ești, ce preferi, ce ai corectat.

Soluția:
  memory_cortex.py interceptează ORICE prompt înainte să ajungă la LLM și
  injectează automat:
    • Greșelile pe care LLM-ul le-a mai făcut (și fix-urile tale)
    • Preferințele tale de lucru (detectate automat din feedback)
    • Contextul proiectului curent
    • Fapte despre tine pe care le-ai spus explicit
    • Patterns de succes — ce a funcționat bine în trecut

  Rezultat: LLM-ul "pare că își amintește" — chiar dacă el uită de fiecare dată.

Categorii de memorie:
  1. EPISODIC   — ce s-a întâmplat (erori, corecții, conversații importante)
  2. SEMANTIC   — fapte stabile (cine ești, ce proiecte ai, preferințe)
  3. PROCEDURAL — cum faci lucrurile (fluxuri de lucru, comenzi preferate)
  4. ERROR_LOG  — greșeli LLM + fix-urile tale (cel mai important)

Integrare în main.py:
    from tools.memory_cortex import MemoryCortex

    cortex = MemoryCortex(db_path="ana_memory.db")

    # În loc să trimiți direct la LLM:
    # response = llm.generate(prompt)

    # Folosești cortex ca intermediar:
    response = cortex.ask(prompt, llm_fn=your_llm_function)

    # Dacă răspunsul e greșit, corectezi:
    cortex.correct(original_prompt, bad_response, correct_response)
"""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ANA.MemoryCortex")

# ── Constante ─────────────────────────────────────────────────────────────────
MAX_CONTEXT_MEMORIES   = 10    # câte memorii injectăm per prompt
MAX_ERRORS_INJECTED    = 5     # câte greșeli anterioare injectăm
SIMILARITY_THRESHOLD   = 0.3   # prag pentru "prompt similar"
MEMORY_DECAY_DAYS      = 90    # memoriile foarte vechi și nefolosite se arhivează


# ─────────────────────────────────────────────────────────────────────────────
class MemoryCortex:
    """
    Stratul de memorie universal. Funcționează cu orice LLM.

    Parametri:
        db_path     : SQLite-ul ANA MAX existent
        user_name   : cum să te numească ANA (opțional)
        project     : proiectul curent (opțional, detectat automat)
        verbose     : afișează ce memorii injectează (util la debug)
    """

    def __init__(
        self,
        db_path: str = "ana_memory.db",
        user_name: str = "utilizator",
        project: str = "",
        verbose: bool = False,
    ):
        self.db_path   = db_path
        self.user_name = user_name
        self.project   = project
        self.verbose   = verbose

        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_context: List[dict] = []  # conversația curentă

        self._ensure_tables()
        logger.info("✅ MemoryCortex inițializat.")

    # ── DB Setup ──────────────────────────────────────────────────────────────
    def _ensure_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Memoria episodică: ce s-a întâmplat
                CREATE TABLE IF NOT EXISTS cortex_episodic (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    session_id  TEXT,
                    prompt_hash TEXT,
                    prompt      TEXT,
                    response    TEXT,
                    corrected   INTEGER DEFAULT 0,
                    correction  TEXT,
                    relevance   REAL DEFAULT 1.0,
                    last_used   TEXT
                );

                -- Memoria semantică: fapte stabile despre user și proiect
                CREATE TABLE IF NOT EXISTS cortex_semantic (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    category    TEXT NOT NULL,
                    key         TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    confidence  REAL DEFAULT 1.0,
                    source      TEXT,
                    timestamp   TEXT,
                    UNIQUE(category, key)
                );

                -- Memoria procedurală: fluxuri și comenzi care funcționează
                CREATE TABLE IF NOT EXISTS cortex_procedural (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type   TEXT NOT NULL,
                    pattern     TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    fail_count    INTEGER DEFAULT 0,
                    last_used   TEXT,
                    notes       TEXT
                );

                -- Error log: greșelile LLM + fix-urile tale (CORE)
                CREATE TABLE IF NOT EXISTS cortex_errors (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    error_type      TEXT,
                    prompt_context  TEXT,
                    bad_response    TEXT,
                    correct_response TEXT,
                    times_repeated  INTEGER DEFAULT 1,
                    last_seen       TEXT,
                    tags            TEXT
                );

                -- Index pentru căutare rapidă
                CREATE INDEX IF NOT EXISTS idx_episodic_hash 
                    ON cortex_episodic(prompt_hash);
                CREATE INDEX IF NOT EXISTS idx_errors_type 
                    ON cortex_errors(error_type);
            """)

    # ── API PRINCIPAL: ask ────────────────────────────────────────────────────
    def ask(
        self,
        prompt: str,
        llm_fn: Callable[[str], str],
        context_tags: Optional[List[str]] = None,
    ) -> str:
        """
        Trimite un prompt la LLM cu memoria injectată automat.

        Parametri:
            prompt      : întrebarea / comanda ta originală
            llm_fn      : funcția care apelează LLM-ul tău
                          trebuie să accepte un string și să returneze un string
                          Exemplu: lambda p: ollama_generate(p)
            context_tags: taguri opționale pentru filtrarea memoriei
                          Exemplu: ["python", "window_manager"]

        Returnează:
            Răspunsul LLM (string)

        Exemplu:
            def my_llm(prompt):
                import requests
                r = requests.post("http://localhost:11434/api/generate",
                    json={"model": "mistral", "prompt": prompt, "stream": False})
                return r.json()["response"]

            response = cortex.ask("Cum repari o eroare de timeout?", my_llm)
        """
        # 1. Construim prompt-ul îmbogățit cu memorie
        enriched_prompt = self._enrich_prompt(prompt, context_tags)

        if self.verbose:
            injected_lines = enriched_prompt.count("\n") - prompt.count("\n")
            logger.info(f"Prompt îmbogățit cu {injected_lines} linii de memorie.")

        # 2. Trimitem la LLM
        start = time.time()
        try:
            response = llm_fn(enriched_prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

        elapsed = time.time() - start

        # 3. Salvăm în memorie episodică
        self._save_episode(prompt, response, elapsed)

        # 4. Adăugăm în contextul sesiunii curente
        self._session_context.append({
            "role": "user", "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        self._session_context.append({
            "role": "assistant", "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    # ── Corectare greșeli ─────────────────────────────────────────────────────
    def correct(
        self,
        original_prompt: str,
        bad_response: str,
        correct_response: str,
        error_type: str = "general",
        tags: Optional[List[str]] = None,
    ):
        """
        Înregistrează o greșeală a LLM-ului și răspunsul corect.
        Data viitoare când apare un prompt similar, ANA va ști să evite greșeala.

        Parametri:
            original_prompt  : ce ai cerut
            bad_response     : ce a răspuns greșit LLM-ul
            correct_response : răspunsul corect (dat de tine)
            error_type       : categoria greșelii (ex: "cod_python", "factual", "ton")
            tags             : taguri pentru grupare

        Exemplu:
            cortex.correct(
                original_prompt="Scrie o funcție de screenshot",
                bad_response="import PIL...",  # a folosit PIL deși tu folosești mss
                correct_response="import mss...",
                error_type="library_preference",
                tags=["python", "screenshot"]
            )
        """
        tags_str = json.dumps(tags or [])

        with sqlite3.connect(self.db_path) as conn:
            # Verificăm dacă această greșeală există deja
            existing = conn.execute(
                """SELECT id, times_repeated FROM cortex_errors
                   WHERE error_type = ? AND bad_response = ?
                   LIMIT 1""",
                (error_type, bad_response[:500])
            ).fetchone()

            if existing:
                # Incrementăm contorul — LLM a repetat greșeala!
                conn.execute(
                    """UPDATE cortex_errors
                       SET times_repeated = times_repeated + 1,
                           last_seen = ?
                       WHERE id = ?""",
                    (datetime.now().isoformat(), existing[0])
                )
                times = existing[1] + 1
                logger.warning(
                    f"⚠️ LLM a repetat aceeași greșeală de {times} ori! "
                    f"Tip: {error_type}"
                )
            else:
                conn.execute(
                    """INSERT INTO cortex_errors
                       (timestamp, error_type, prompt_context, bad_response,
                        correct_response, last_seen, tags)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.now().isoformat(),
                        error_type,
                        original_prompt[:500],
                        bad_response[:1000],
                        correct_response[:1000],
                        datetime.now().isoformat(),
                        tags_str,
                    )
                )

            # Marcăm episodul original ca corectat
            prompt_hash = self._hash(original_prompt)
            conn.execute(
                """UPDATE cortex_episodic
                   SET corrected = 1, correction = ?
                   WHERE prompt_hash = ?""",
                (correct_response[:500], prompt_hash)
            )

        logger.info(f"✅ Corecție înregistrată: {error_type}")

    # ── Învață fapte despre user ──────────────────────────────────────────────
    def remember(
        self,
        key: str,
        value: str,
        category: str = "user_preference",
        confidence: float = 1.0,
    ):
        """
        Salvează un fapt permanent despre tine sau proiectul tău.

        Exemplu:
            cortex.remember("limbaj_preferat", "Python")
            cortex.remember("editor", "VS Code")
            cortex.remember("stil_cod", "fără comentarii în exces")
            cortex.remember("proiect_activ", "ANA MAX")
            cortex.remember("librarie_screenshot", "mss, nu PIL")
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO cortex_semantic (category, key, value, confidence, timestamp)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(category, key) DO UPDATE SET
                       value = excluded.value,
                       confidence = excluded.confidence,
                       timestamp = excluded.timestamp""",
                (category, key, value, confidence, datetime.now().isoformat())
            )
        logger.info(f"💾 Memorat: [{category}] {key} = {value}")

    # ── Învață pattern de succes ──────────────────────────────────────────────
    def learned_success(self, task_type: str, pattern: str, notes: str = ""):
        """
        Marchează un pattern ca funcționând bine.

        Exemplu:
            cortex.learned_success(
                task_type="debug_python",
                pattern="întotdeauna verifică mai întâi ImportError înainte de RuntimeError",
                notes="salvat din sesiunea de debug din 15 mai"
            )
        """
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM cortex_procedural WHERE task_type = ? AND pattern = ?",
                (task_type, pattern)
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE cortex_procedural
                       SET success_count = success_count + 1, last_used = ?
                       WHERE id = ?""",
                    (datetime.now().isoformat(), existing[0])
                )
            else:
                conn.execute(
                    """INSERT INTO cortex_procedural
                       (task_type, pattern, last_used, notes)
                       VALUES (?, ?, ?, ?)""",
                    (task_type, pattern, datetime.now().isoformat(), notes)
                )

    # ── Enrich prompt ─────────────────────────────────────────────────────────
    def _enrich_prompt(self, prompt: str, tags: Optional[List[str]] = None) -> str:
        """
        Construiește prompt-ul îmbogățit cu toate memoriile relevante.
        Acesta e nucleul — ce face memory_cortex unic.
        """
        sections = []

        # ── 1. Identitate și preferințe ───────────────────────────────────────
        user_facts = self._get_semantic("user_preference")
        project_facts = self._get_semantic("project")
        tech_facts = self._get_semantic("tech_preference")

        all_facts = user_facts + project_facts + tech_facts
        if all_facts:
            facts_text = "\n".join(f"  • {f['key']}: {f['value']}" for f in all_facts[:8])
            sections.append(
                f"[CONTEXT UTILIZATOR]\n{facts_text}"
            )

        # ── 2. Greșeli anterioare ale LLM-ului ────────────────────────────────
        errors = self._get_relevant_errors(prompt)
        if errors:
            err_lines = []
            for e in errors[:MAX_ERRORS_INJECTED]:
                times_str = f" (repetată de {e['times_repeated']} ori!)" if e['times_repeated'] > 1 else ""
                err_lines.append(
                    f"  ❌ GREȘEALĂ ANTERIOARĂ{times_str}: {e['error_type']}\n"
                    f"     Context: {e['prompt_context'][:100]}\n"
                    f"     Răspuns GREȘIT: {e['bad_response'][:150]}\n"
                    f"     Răspuns CORECT: {e['correct_response'][:150]}"
                )
            sections.append(
                "[GREȘELI ANTERIOARE — EVITĂ-LE]\n" + "\n".join(err_lines)
            )

        # ── 3. Pattern-uri de succes relevante ────────────────────────────────
        patterns = self._get_relevant_patterns(prompt)
        if patterns:
            pat_lines = [
                f"  ✅ {p['task_type']}: {p['pattern']}"
                for p in patterns[:3]
            ]
            sections.append(
                "[ABORDĂRI CARE AU FUNCȚIONAT]\n" + "\n".join(pat_lines)
            )

        # ── 4. Contextul sesiunii curente (ultimele 3 schimburi) ──────────────
        if len(self._session_context) >= 2:
            recent = self._session_context[-6:]  # ultimele 3 perechi
            ctx_lines = []
            for msg in recent:
                role = "Tu" if msg["role"] == "user" else "ANA"
                ctx_lines.append(f"  {role}: {msg['content'][:200]}")
            sections.append(
                "[CONTEXTUL CONVERSAȚIEI CURENTE]\n" + "\n".join(ctx_lines)
            )

        # ── 5. Episoade similare din trecut ───────────────────────────────────
        similar = self._get_similar_episodes(prompt)
        if similar:
            sim_lines = []
            for ep in similar[:2]:
                correction_note = ""
                if ep["corrected"] and ep["correction"]:
                    correction_note = f"\n     → Corectat la: {ep['correction'][:100]}"
                sim_lines.append(
                    f"  [{ep['timestamp'][:10]}] Prompt similar: {ep['prompt'][:120]}"
                    f"\n     Răspuns dat: {ep['response'][:120]}{correction_note}"
                )
            sections.append(
                "[SITUAȚII SIMILARE DIN TRECUT]\n" + "\n".join(sim_lines)
            )

        # ── Asamblăm prompt-ul final ──────────────────────────────────────────
        if not sections:
            return prompt  # nu avem memorie încă — prompt simplu

        memory_block = "\n\n".join(sections)

        enriched = f"""[MEMORIA ANA MAX — FOLOSEȘTE ACESTE INFORMAȚII]
{memory_block}
[SFÂRȘITUL MEMORIEI]

Ținând cont de tot ce știi despre utilizator și de greșelile anterioare, răspunde la:

{prompt}"""

        return enriched

    # ── Retrieval helpers ─────────────────────────────────────────────────────
    def _get_semantic(self, category: str) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT key, value, confidence FROM cortex_semantic
                   WHERE category = ?
                   ORDER BY confidence DESC, timestamp DESC
                   LIMIT 10""",
                (category,)
            ).fetchall()
        return [{"key": r[0], "value": r[1], "confidence": r[2]} for r in rows]

    def _get_relevant_errors(self, prompt: str) -> List[dict]:
        """Returnează greșelile anterioare relevante pentru prompt-ul curent."""
        with sqlite3.connect(self.db_path) as conn:
            # Luăm toate erorile și le filtrăm pe cuvinte cheie
            rows = conn.execute(
                """SELECT error_type, prompt_context, bad_response,
                          correct_response, times_repeated
                   FROM cortex_errors
                   ORDER BY times_repeated DESC, timestamp DESC
                   LIMIT 20"""
            ).fetchall()

        prompt_words = set(prompt.lower().split())
        scored = []
        for row in rows:
            context_words = set((row[1] or "").lower().split())
            overlap = len(prompt_words & context_words)
            if overlap > 0 or row[4] > 1:  # relevant sau greșeală repetată
                scored.append({
                    "error_type": row[0],
                    "prompt_context": row[1] or "",
                    "bad_response": row[2] or "",
                    "correct_response": row[3] or "",
                    "times_repeated": row[4],
                    "score": overlap + (row[4] * 2),  # greșelile repetate au prioritate
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:MAX_ERRORS_INJECTED]

    def _get_relevant_patterns(self, prompt: str) -> List[dict]:
        """Returnează pattern-urile de succes relevante."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT task_type, pattern, success_count, notes
                   FROM cortex_procedural
                   WHERE success_count > fail_count
                   ORDER BY success_count DESC
                   LIMIT 10"""
            ).fetchall()

        prompt_lower = prompt.lower()
        relevant = []
        for row in rows:
            if any(word in prompt_lower for word in row[0].lower().split("_")):
                relevant.append({
                    "task_type": row[0],
                    "pattern": row[1],
                    "success_count": row[2],
                    "notes": row[3],
                })

        return relevant[:3]

    def _get_similar_episodes(self, prompt: str) -> List[dict]:
        """Găsește episoade similare din trecut pe baza cuvintelor cheie."""
        prompt_words = [w for w in prompt.lower().split() if len(w) > 4]
        if not prompt_words:
            return []

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT timestamp, prompt, response, corrected, correction
                   FROM cortex_episodic
                   WHERE session_id != ?
                   ORDER BY timestamp DESC
                   LIMIT 100""",
                (self._session_id,)
            ).fetchall()

        scored = []
        for row in rows:
            stored_prompt = (row[1] or "").lower()
            overlap = sum(1 for w in prompt_words if w in stored_prompt)
            if overlap >= 2:
                scored.append({
                    "timestamp": row[0],
                    "prompt": row[1],
                    "response": row[2],
                    "corrected": row[3],
                    "correction": row[4],
                    "score": overlap,
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:2]

    # ── Save episode ──────────────────────────────────────────────────────────
    def _save_episode(self, prompt: str, response: str, elapsed: float):
        prompt_hash = self._hash(prompt)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO cortex_episodic
                   (timestamp, session_id, prompt_hash, prompt, response, last_used)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    self._session_id,
                    prompt_hash,
                    prompt[:1000],
                    response[:2000],
                    datetime.now().isoformat(),
                )
            )

    # ── Utils ─────────────────────────────────────────────────────────────────
    def _hash(self, text: str) -> str:
        return hashlib.md5(text[:200].encode()).hexdigest()

    # ── Stats & Report ────────────────────────────────────────────────────────
    def get_memory_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            episodes   = conn.execute("SELECT COUNT(*) FROM cortex_episodic").fetchone()[0]
            facts      = conn.execute("SELECT COUNT(*) FROM cortex_semantic").fetchone()[0]
            patterns   = conn.execute("SELECT COUNT(*) FROM cortex_procedural").fetchone()[0]
            errors     = conn.execute("SELECT COUNT(*) FROM cortex_errors").fetchone()[0]
            repeated   = conn.execute(
                "SELECT SUM(times_repeated) FROM cortex_errors WHERE times_repeated > 1"
            ).fetchone()[0] or 0
            top_errors = conn.execute(
                """SELECT error_type, times_repeated FROM cortex_errors
                   ORDER BY times_repeated DESC LIMIT 3"""
            ).fetchall()
            corrections = conn.execute(
                "SELECT COUNT(*) FROM cortex_episodic WHERE corrected = 1"
            ).fetchone()[0]

        return {
            "episodic_memories":   episodes,
            "known_facts":         facts,
            "success_patterns":    patterns,
            "llm_errors_caught":   errors,
            "times_llm_repeated_error": repeated,
            "corrections_applied": corrections,
            "top_repeated_errors": [
                {"type": r[0], "times": r[1]} for r in top_errors
            ],
        }

    def print_memory_report(self):
        stats = self.get_memory_stats()
        print("\n" + "="*60)
        print("🧠 ANA MAX — MEMORY CORTEX REPORT")
        print("="*60)
        print(f"Memorii episodice:          {stats['episodic_memories']}")
        print(f"Fapte cunoscute:            {stats['known_facts']}")
        print(f"Pattern-uri de succes:      {stats['success_patterns']}")
        print(f"Greșeli LLM înregistrate:   {stats['llm_errors_caught']}")
        print(f"De câte ori LLM a repetat:  {stats['times_llm_repeated_error']}")
        print(f"Corecții aplicate:          {stats['corrections_applied']}")
        if stats["top_repeated_errors"]:
            print("\nTop greșeli repetate:")
            for e in stats["top_repeated_errors"]:
                print(f"  ⚠️  {e['type']}: repetat de {e['times']} ori")
        print("="*60 + "\n")

    def forget(self, category: str = None, older_than_days: int = None):
        """
        Șterge memorii selectiv.

        Exemplu:
            cortex.forget(category="user_preference")  # șterge preferințele
            cortex.forget(older_than_days=30)           # șterge ce e mai vechi de 30 zile
        """
        with sqlite3.connect(self.db_path) as conn:
            if category:
                conn.execute(
                    "DELETE FROM cortex_semantic WHERE category = ?", (category,)
                )
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                conn.execute(
                    "DELETE FROM cortex_episodic WHERE timestamp < ? AND corrected = 0",
                    (cutoff,)
                )
        logger.info(f"Memorie ștearsă: category={category}, older_than={older_than_days}d")


# ─────────────────────────────────────────────────────────────────────────────
# Exemplu complet de utilizare
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Inițializare
    cortex = MemoryCortex(
        db_path="ana_memory.db",
        user_name="<YOUR_NAME>",
        project="ANA MAX",
        verbose=True,
    )

    # Spune-i ce știi deja despre tine
    cortex.remember("limbaj_preferat", "Python 3.11")
    cortex.remember("editor", "VS Code + Cursor")
    cortex.remember("proiect_activ", "ANA MAX — Windows AI Agent")
    cortex.remember("librarie_screenshot", "mss (nu PIL sau pyautogui)")
    cortex.remember("stil_cod", "comentarii clare, fără over-engineering")
    cortex.remember("os", "Windows 11")

    # Funcție LLM — înlocuiește cu Ollama, Claude API, etc.
    def my_llm(prompt: str) -> str:
        try:
            import requests
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral", "prompt": prompt, "stream": False},
                timeout=60,
            )
            return r.json().get("response", "")
        except Exception as e:
            return f"[LLM indisponibil: {e}]"

    # Exemplu de întrebare normală
    print("\n--- Test 1: întrebare simplă ---")
    response = cortex.ask(
        "Scrie o funcție Python care face screenshot la ecran",
        llm_fn=my_llm,
    )
    print(f"Răspuns: {response[:300]}")

    # Simulare greșeală: LLM a folosit PIL în loc de mss
    print("\n--- Test 2: înregistrare greșeală ---")
    cortex.correct(
        original_prompt="Scrie o funcție Python care face screenshot la ecran",
        bad_response="import PIL\nfrom PIL import ImageGrab\nimg = ImageGrab.grab()",
        correct_response="import mss\nwith mss.mss() as sct:\n    sct.shot()",
        error_type="library_preference",
        tags=["screenshot", "python"]
    )

    # Data viitoare, când ceri din nou screenshot, LLM va ști să evite PIL
    print("\n--- Test 3: același topic — greșeala e injectată în memorie ---")
    response2 = cortex.ask(
        "Am nevoie de cod pentru a captura ecranul în Python",
        llm_fn=my_llm,
    )
    print(f"Răspuns: {response2[:300]}")

    # Pattern de succes
    cortex.learned_success(
        task_type="debug_python",
        pattern="verifică întotdeauna ImportError înainte de a rula codul",
    )

    # Raport final
    cortex.print_memory_report()
