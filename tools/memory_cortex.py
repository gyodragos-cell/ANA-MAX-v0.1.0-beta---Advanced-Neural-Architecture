"""
ANA MAX – memory_cortex.py
===========================
Stratul de memorie care sta INTRE tine si orice LLM.

Problema pe care o rezolva:
  Toate AI-urile (Claude, GPT, Gemini, Ollama) uita dupa fiecare sesiune.
  Repeta aceleasi greseli. Nu stiu cine esti, ce preferi, ce ai corectat.

Solutia:
  memory_cortex.py intercepteaza ORICE prompt inainte sa ajunga la LLM si
  injecteaza automat:
    • Greselile pe care LLM-ul le-a mai facut (si fix-urile tale)
    • Preferintele tale de lucru (detectate automat din feedback)
    • Contextul proiectului curent
    • Fapte despre tine pe care le-ai spus explicit
    • Patterns de succes — ce a functionat bine in trecut

  Rezultat: LLM-ul "pare ca isi aminteste" — chiar daca el uita de fiecare data.

Categorii de memorie:
  1. EPISODIC   — ce s-a intamplat (erori, corectii, conversatii importante)
  2. SEMANTIC   — fapte stabile (cine esti, ce proiecte ai, preferinte)
  3. PROCEDURAL — cum faci lucrurile (fluxuri de lucru, comenzi preferate)
  4. ERROR_LOG  — greseli LLM + fix-urile tale (cel mai important)

Integrare in main.py:
    from tools.memory_cortex import MemoryCortex

    cortex = MemoryCortex(db_path="ana_memory.db")

    # In loc sa trimiti direct la LLM:
    # response = llm.generate(prompt)

    # Folosesti cortex ca intermediar:
    response = cortex.ask(prompt, llm_fn=your_llm_function)

    # Daca raspunsul e gresit, corectezi:
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
MAX_CONTEXT_MEMORIES   = 10    # cate memorii injectam per prompt
MAX_ERRORS_INJECTED    = 5     # cate greseli anterioare injectam
SIMILARITY_THRESHOLD   = 0.3   # prag pentru "prompt similar"
MEMORY_DECAY_DAYS      = 90    # memoriile foarte vechi si nefolosite se arhiveaza


# ─────────────────────────────────────────────────────────────────────────────
class MemoryCortex:
    """
    Stratul de memorie universal. Functioneaza cu orice LLM.

    Parametri:
        db_path     : SQLite-ul ANA MAX existent
        user_name   : cum sa te numeasca ANA (optional)
        project     : proiectul curent (optional, detectat automat)
        verbose     : afiseaza ce memorii injecteaza (util la debug)
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
        self._session_context: List[dict] = []  # conversatia curenta

        self._ensure_tables()
        logger.info("✅ MemoryCortex initializat.")

    # ── DB Setup ──────────────────────────────────────────────────────────────
    def _ensure_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Memoria episodica: ce s-a intamplat
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

                -- Memoria semantica: fapte stabile despre user si proiect
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

                -- Memoria procedurala: fluxuri si comenzi care functioneaza
                CREATE TABLE IF NOT EXISTS cortex_procedural (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type   TEXT NOT NULL,
                    pattern     TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    fail_count    INTEGER DEFAULT 0,
                    last_used   TEXT,
                    notes       TEXT
                );

                -- Error log: greselile LLM + fix-urile tale (CORE)
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

                -- Index pentru cautare rapida
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
        Trimite un prompt la LLM cu memoria injectata automat.

        Parametri:
            prompt      : intrebarea / comanda ta originala
            llm_fn      : functia care apeleaza LLM-ul tau
                          trebuie sa accepte un string si sa returneze un string
                          Exemplu: lambda p: ollama_generate(p)
            context_tags: taguri optionale pentru filtrarea memoriei
                          Exemplu: ["python", "window_manager"]

        Returneaza:
            Raspunsul LLM (string)

        Exemplu:
            def my_llm(prompt):
                import requests
                r = requests.post("http://localhost:11434/api/generate",
                    json={"model": "mistral", "prompt": prompt, "stream": False})
                return r.json()["response"]

            response = cortex.ask("Cum repari o eroare de timeout?", my_llm)
        """
        # 1. Construim prompt-ul imbogatit cu memorie
        enriched_prompt = self._enrich_prompt(prompt, context_tags)

        if self.verbose:
            injected_lines = enriched_prompt.count("\n") - prompt.count("\n")
            logger.info(f"Prompt imbogatit cu {injected_lines} linii de memorie.")

        # 2. Trimitem la LLM
        start = time.time()
        try:
            response = llm_fn(enriched_prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

        elapsed = time.time() - start

        # 3. Salvam in memorie episodica
        self._save_episode(prompt, response, elapsed)

        # 4. Adaugam in contextul sesiunii curente
        self._session_context.append({
            "role": "user", "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        self._session_context.append({
            "role": "assistant", "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    # ── Corectare greseli ─────────────────────────────────────────────────────
    def correct(
        self,
        original_prompt: str,
        bad_response: str,
        correct_response: str,
        error_type: str = "general",
        tags: Optional[List[str]] = None,
    ):
        """
        Inregistreaza o greseala a LLM-ului si raspunsul corect.
        Data viitoare cand apare un prompt similar, ANA va sti sa evite greseala.

        Parametri:
            original_prompt  : ce ai cerut
            bad_response     : ce a raspuns gresit LLM-ul
            correct_response : raspunsul corect (dat de tine)
            error_type       : categoria greselii (ex: "cod_python", "factual", "ton")
            tags             : taguri pentru grupare

        Exemplu:
            cortex.correct(
                original_prompt="Scrie o functie de screenshot",
                bad_response="import PIL...",  # a folosit PIL desi tu folosesti mss
                correct_response="import mss...",
                error_type="library_preference",
                tags=["python", "screenshot"]
            )
        """
        tags_str = json.dumps(tags or [])

        with sqlite3.connect(self.db_path) as conn:
            # Verificam daca aceasta greseala exista deja
            existing = conn.execute(
                """SELECT id, times_repeated FROM cortex_errors
                   WHERE error_type = ? AND bad_response = ?
                   LIMIT 1""",
                (error_type, bad_response[:500])
            ).fetchone()

            if existing:
                # Incrementam contorul — LLM a repetat greseala!
                conn.execute(
                    """UPDATE cortex_errors
                       SET times_repeated = times_repeated + 1,
                           last_seen = ?
                       WHERE id = ?""",
                    (datetime.now().isoformat(), existing[0])
                )
                times = existing[1] + 1
                logger.warning(
                    f"⚠️ LLM a repetat aceeasi greseala de {times} ori! "
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

            # Marcam episodul original ca corectat
            prompt_hash = self._hash(original_prompt)
            conn.execute(
                """UPDATE cortex_episodic
                   SET corrected = 1, correction = ?
                   WHERE prompt_hash = ?""",
                (correct_response[:500], prompt_hash)
            )

        logger.info(f"✅ Corectie inregistrata: {error_type}")

    # ── Invata fapte despre user ──────────────────────────────────────────────
    def remember(
        self,
        key: str,
        value: str,
        category: str = "user_preference",
        confidence: float = 1.0,
    ):
        """
        Salveaza un fapt permanent despre tine sau proiectul tau.

        Exemplu:
            cortex.remember("limbaj_preferat", "Python")
            cortex.remember("editor", "VS Code")
            cortex.remember("stil_cod", "fara comentarii in exces")
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

    # ── Invata pattern de succes ──────────────────────────────────────────────
    def learned_success(self, task_type: str, pattern: str, notes: str = ""):
        """
        Marcheaza un pattern ca functionand bine.

        Exemplu:
            cortex.learned_success(
                task_type="debug_python",
                pattern="intotdeauna verifica mai intai ImportError inainte de RuntimeError",
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
        Construieste prompt-ul imbogatit cu toate memoriile relevante.
        Acesta e nucleul — ce face memory_cortex unic.
        """
        sections = []

        # ── 1. Identitate si preferinte ───────────────────────────────────────
        user_facts = self._get_semantic("user_preference")
        project_facts = self._get_semantic("project")
        tech_facts = self._get_semantic("tech_preference")

        all_facts = user_facts + project_facts + tech_facts
        if all_facts:
            facts_text = "\n".join(f"  • {f['key']}: {f['value']}" for f in all_facts[:8])
            sections.append(
                f"[CONTEXT UTILIZATOR]\n{facts_text}"
            )

        # ── 2. Greseli anterioare ale LLM-ului ────────────────────────────────
        errors = self._get_relevant_errors(prompt)
        if errors:
            err_lines = []
            for e in errors[:MAX_ERRORS_INJECTED]:
                times_str = f" (repetata de {e['times_repeated']} ori!)" if e['times_repeated'] > 1 else ""
                err_lines.append(
                    f"  ❌ GRESEALA ANTERIOARA{times_str}: {e['error_type']}\n"
                    f"     Context: {e['prompt_context'][:100]}\n"
                    f"     Raspuns GRESIT: {e['bad_response'][:150]}\n"
                    f"     Raspuns CORECT: {e['correct_response'][:150]}"
                )
            sections.append(
                "[GRESELI ANTERIOARE — EVITA-LE]\n" + "\n".join(err_lines)
            )

        # ── 3. Pattern-uri de succes relevante ────────────────────────────────
        patterns = self._get_relevant_patterns(prompt)
        if patterns:
            pat_lines = [
                f"  ✅ {p['task_type']}: {p['pattern']}"
                for p in patterns[:3]
            ]
            sections.append(
                "[ABORDARI CARE AU FUNCTIONAT]\n" + "\n".join(pat_lines)
            )

        # ── 4. Contextul sesiunii curente (ultimele 3 schimburi) ──────────────
        if len(self._session_context) >= 2:
            recent = self._session_context[-6:]  # ultimele 3 perechi
            ctx_lines = []
            for msg in recent:
                role = "Tu" if msg["role"] == "user" else "ANA"
                ctx_lines.append(f"  {role}: {msg['content'][:200]}")
            sections.append(
                "[CONTEXTUL CONVERSATIEI CURENTE]\n" + "\n".join(ctx_lines)
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
                    f"\n     Raspuns dat: {ep['response'][:120]}{correction_note}"
                )
            sections.append(
                "[SITUATII SIMILARE DIN TRECUT]\n" + "\n".join(sim_lines)
            )

        # ── Asamblam prompt-ul final ──────────────────────────────────────────
        if not sections:
            return prompt  # nu avem memorie inca — prompt simplu

        memory_block = "\n\n".join(sections)

        enriched = f"""[MEMORIA ANA MAX — FOLOSESTE ACESTE INFORMATII]
{memory_block}
[SFARSITUL MEMORIEI]

Tinand cont de tot ce stii despre utilizator si de greselile anterioare, raspunde la:

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
        """Returneaza greselile anterioare relevante pentru prompt-ul curent."""
        with sqlite3.connect(self.db_path) as conn:
            # Luam toate erorile si le filtram pe cuvinte cheie
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
            if overlap > 0 or row[4] > 1:  # relevant sau greseala repetata
                scored.append({
                    "error_type": row[0],
                    "prompt_context": row[1] or "",
                    "bad_response": row[2] or "",
                    "correct_response": row[3] or "",
                    "times_repeated": row[4],
                    "score": overlap + (row[4] * 2),  # greselile repetate au prioritate
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:MAX_ERRORS_INJECTED]

    def _get_relevant_patterns(self, prompt: str) -> List[dict]:
        """Returneaza pattern-urile de succes relevante."""
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
        """Gaseste episoade similare din trecut pe baza cuvintelor cheie."""
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
        print(f"Greseli LLM inregistrate:   {stats['llm_errors_caught']}")
        print(f"De cate ori LLM a repetat:  {stats['times_llm_repeated_error']}")
        print(f"Corectii aplicate:          {stats['corrections_applied']}")
        if stats["top_repeated_errors"]:
            print("\nTop greseli repetate:")
            for e in stats["top_repeated_errors"]:
                print(f"  ⚠️  {e['type']}: repetat de {e['times']} ori")
        print("="*60 + "\n")

    def forget(self, category: str = None, older_than_days: int = None):
        """
        Sterge memorii selectiv.

        Exemplu:
            cortex.forget(category="user_preference")  # sterge preferintele
            cortex.forget(older_than_days=30)           # sterge ce e mai vechi de 30 zile
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
        logger.info(f"Memorie stearsa: category={category}, older_than={older_than_days}d")


# ─────────────────────────────────────────────────────────────────────────────
# Exemplu complet de utilizare
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initializare
    cortex = MemoryCortex(
        db_path="ana_memory.db",
        user_name="<YOUR_NAME>",
        project="ANA MAX",
        verbose=True,
    )

    # Spune-i ce stii deja despre tine
    cortex.remember("limbaj_preferat", "Python 3.11")
    cortex.remember("editor", "VS Code + Cursor")
    cortex.remember("proiect_activ", "ANA MAX — Windows AI Agent")
    cortex.remember("librarie_screenshot", "mss (nu PIL sau pyautogui)")
    cortex.remember("stil_cod", "comentarii clare, fara over-engineering")
    cortex.remember("os", "Windows 11")

    # Functie LLM — inlocuieste cu Ollama, Claude API, etc.
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

    # Exemplu de intrebare normala
    print("\n--- Test 1: intrebare simpla ---")
    response = cortex.ask(
        "Scrie o functie Python care face screenshot la ecran",
        llm_fn=my_llm,
    )
    print(f"Raspuns: {response[:300]}")

    # Simulare greseala: LLM a folosit PIL in loc de mss
    print("\n--- Test 2: inregistrare greseala ---")
    cortex.correct(
        original_prompt="Scrie o functie Python care face screenshot la ecran",
        bad_response="import PIL\nfrom PIL import ImageGrab\nimg = ImageGrab.grab()",
        correct_response="import mss\nwith mss.mss() as sct:\n    sct.shot()",
        error_type="library_preference",
        tags=["screenshot", "python"]
    )

    # Data viitoare, cand ceri din nou screenshot, LLM va sti sa evite PIL
    print("\n--- Test 3: acelasi topic — greseala e injectata in memorie ---")
    response2 = cortex.ask(
        "Am nevoie de cod pentru a captura ecranul in Python",
        llm_fn=my_llm,
    )
    print(f"Raspuns: {response2[:300]}")

    # Pattern de succes
    cortex.learned_success(
        task_type="debug_python",
        pattern="verifica intotdeauna ImportError inainte de a rula codul",
    )

    # Raport final
    cortex.print_memory_report()
