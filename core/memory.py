"""
ANA MAX - Memory System (SQLite-based)
===========================================
Sistem de memorie persistenta folosind SQLite.
Inlocuieste JSON pentru performanta si fiabilitate mai buna.
"""

import sqlite3
import json
import time
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)


class Memory:
    """
    Sistem de memorie persistenta pentru A.N.A.
    Foloseste SQLite pentru stocare fiabila.
    """
    
    def __init__(self, db_path: str = "memory/ana_brain.db"):
        self.db_path = db_path
        self._conn = None
        self._lock = threading.Lock()
        self._ensure_directory()
        self._init_database()
    
    def _ensure_directory(self) -> None:
        """Creeaza directorul pentru baza de date daca nu exista."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Context manager pentru conexiuni la baza de date."""
        with self._lock:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
                self._conn.row_factory = sqlite3.Row
            try:
                yield self._conn
                self._conn.commit()
            except Exception as e:
                self._conn.rollback()
                logger.error(f"Eroare baza de date: {e}")
                raise
    
    def _init_database(self) -> None:
        """Initializeaza schema bazei de date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabel pentru conversatii
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Tabel pentru cunostinte (brain)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL UNIQUE,
                    category TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            # Tabel pentru erori si solutii
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_pattern TEXT NOT NULL,
                    solution TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    last_used REAL
                )
            """)
            
            # Tabel pentru evolutie/modificari
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evolution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    timestamp REAL NOT NULL,
                    success INTEGER DEFAULT 1
                )
            """)
            
            # Tabel pentru plugin-uri
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plugins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    version TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    config TEXT DEFAULT '{}',
                    installed_at REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engineer_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE,
                    profile TEXT NOT NULL,
                    task TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    result TEXT DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engineer_run_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    created_at REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repair_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature TEXT NOT NULL UNIQUE,
                    strategy TEXT NOT NULL,
                    patch_hint TEXT DEFAULT '',
                    example_error TEXT DEFAULT '',
                    occurrence_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    project_path TEXT NOT NULL UNIQUE,
                    project_type TEXT NOT NULL,
                    spec TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    created_at REAL NOT NULL
                )
            """)
            
            # Indecsi pentru performanta
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic)")
            self._migrate_schema(cursor)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_pattern ON error_solutions(error_pattern)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_engineer_runs_profile ON engineer_runs(profile)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_engineer_steps_run_id ON engineer_run_steps(run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_repair_signature ON repair_patterns(signature)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_generated_projects_path ON generated_projects(project_path)")
            
            logger.info("Baza de date initializata cu succes")

    def _migrate_schema(self, cursor) -> None:
        """Aplica migratii compatibile pentru bazele de date deja existente."""
        cursor.execute("PRAGMA table_info(knowledge)")
        columns = {row[1] for row in cursor.fetchall()}
        if "category" not in columns:
            cursor.execute("ALTER TABLE knowledge ADD COLUMN category TEXT DEFAULT ''")
        if "created_at" not in columns:
            cursor.execute("ALTER TABLE knowledge ADD COLUMN created_at REAL DEFAULT 0")
            cursor.execute("UPDATE knowledge SET created_at = COALESCE(timestamp, strftime('%s','now')) WHERE created_at = 0")
        if "updated_at" not in columns:
            cursor.execute("ALTER TABLE knowledge ADD COLUMN updated_at REAL DEFAULT 0")
            cursor.execute("UPDATE knowledge SET updated_at = COALESCE(timestamp, strftime('%s','now')) WHERE updated_at = 0")
        if "access_count" not in columns:
            cursor.execute("ALTER TABLE knowledge ADD COLUMN access_count INTEGER DEFAULT 0")
        cursor.execute("PRAGMA index_list(knowledge)")
        indexes = {row[1]: row for row in cursor.fetchall()}
        if "idx_knowledge_topic_unique" not in indexes:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_topic_unique ON knowledge(topic)")
    
    # ==================== CONVERSATII ====================
    
    def save_message(self, session_id: str, role: str, content: str, 
                     metadata: Optional[Dict] = None) -> int:
        """Salveaza un mesaj in conversatie."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, role, content, time.time(), json.dumps(metadata or {})))
            return cursor.lastrowid
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Obtine istoricul conversatiei."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, timestamp, metadata
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            rows = cursor.fetchall()
            return [
                {
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'metadata': json.loads(row['metadata'])
                }
                for row in reversed(rows)
            ]
    
    def clear_old_conversations(self, days: int = 30) -> int:
        """Sterge conversatiile mai vechi de X zile."""
        cutoff = time.time() - (days * 24 * 60 * 60)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff,))
            return cursor.rowcount
    
    # ==================== CUNOSTINTE ====================
    
    def save_knowledge(self, topic: str = "", content: str = "",
                       *, category: str = "", key: str = "",
                       value: str = "", metadata: Optional[Dict] = None) -> bool:
        """Salveaza sau actualizeaza cunostinte."""
        if not topic and (category or key):
            topic = f"{category}::{key}" if category and key else (category or key)
        if not content and value:
            content = value
        if metadata and content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    parsed.setdefault("_metadata", metadata)
                    content = json.dumps(parsed)
            except (json.JSONDecodeError, TypeError):
                pass

        if not topic:
            logger.warning("save_knowledge: topic/key lipsa - ignorat")
            return False

        now = time.time()
        resolved_category = category or (topic.split("::", 1)[0] if "::" in topic else "")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge (topic, category, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(topic) DO UPDATE SET
                    category = excluded.category,
                    content = excluded.content,
                    updated_at = excluded.updated_at
            """, (topic, resolved_category, content, now, now))
            return True
    
    def get_knowledge(self, topic: str) -> Optional[str]:
        """Obtine cunostinte despre un subiect."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE knowledge SET access_count = access_count + 1
                WHERE topic = ?
            """, (topic,))
            cursor.execute("""
                SELECT content FROM knowledge WHERE topic = ?
            """, (topic,))
            row = cursor.fetchone()
            return row['content'] if row else None
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """Cauta in cunostinte (full-text search simplu)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT topic, category, content, access_count
                FROM knowledge
                WHERE topic LIKE ? OR content LIKE ?
                ORDER BY access_count DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            
            return [
                {
                    'topic': row['topic'],
                    'category': row['category'],
                    'content': row['content'],
                    'access_count': row['access_count']
                }
                for row in cursor.fetchall()
            ]
    
    def list_all_knowledge(self) -> List[str]:
        """Listeaza toate subiectele din baza de cunostinte."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic FROM knowledge ORDER BY topic")
            return [row['topic'] for row in cursor.fetchall()]
    
    # ==================== ERORI SI SOLUTII ====================
    
    def save_error_solution(self, error_pattern: str, solution: str) -> bool:
        """Salveaza o solutie pentru un tip de eroare."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM error_solutions WHERE error_pattern = ?
            """, (error_pattern,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE error_solutions 
                    SET solution = ?, last_used = ?
                    WHERE error_pattern = ?
                """, (solution, now, error_pattern))
            else:
                cursor.execute("""
                    INSERT INTO error_solutions (error_pattern, solution, created_at)
                    VALUES (?, ?, ?)
                """, (error_pattern, solution, now))
            return True
    
    def find_error_solution(self, error_text: str) -> Optional[Dict]:
        """Cauta solutie pentru o eroare."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT error_pattern, solution, success_count
                FROM error_solutions
                WHERE ? LIKE '%' || error_pattern || '%'
                   OR error_pattern LIKE '%' || ? || '%'
                ORDER BY success_count DESC
                LIMIT 1
            """, (error_text, error_text))
            
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE error_solutions 
                    SET success_count = success_count + 1, last_used = ?
                    WHERE error_pattern = ?
                """, (time.time(), row['error_pattern']))
                
                return {
                    'error_pattern': row['error_pattern'],
                    'solution': row['solution'],
                    'success_count': row['success_count']
                }
            return None
    
    # ==================== EVOLUTIE LOG ====================
    
    def log_evolution(self, action_type: str, description: str, 
                      details: Optional[Dict] = None, success: bool = True) -> int:
        """Inregistreaza o actiune de evolutie."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evolution_log (action_type, description, details, timestamp, success)
                VALUES (?, ?, ?, ?, ?)
            """, (action_type, description, json.dumps(details or {}), time.time(), int(success)))
            return cursor.lastrowid
    
    def get_evolution_history(self, limit: int = 50) -> List[Dict]:
        """Obtine istoricul evolutiei."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT action_type, description, details, timestamp, success
                FROM evolution_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    'action_type': row['action_type'],
                    'description': row['description'],
                    'details': json.loads(row['details']),
                    'timestamp': row['timestamp'],
                    'success': bool(row['success'])
                }
                for row in cursor.fetchall()
            ]
    
    # ==================== ENGINEER / LAB ====================
    
    def create_engineer_run(self, profile: str, task: str, workspace: str,
                            metadata: Optional[Dict] = None,
                            run_id: Optional[str] = None) -> str:
        """Creeaza un run operational pentru Engineer, Repair sau Lab."""
        run_identifier = run_id or f"run_{int(time.time() * 1000)}"
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO engineer_runs (
                    run_id, profile, task, workspace, status, summary,
                    metadata, result, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_identifier,
                profile,
                task,
                workspace,
                "running",
                "",
                json.dumps(metadata or {}),
                json.dumps({}),
                now,
                now,
            ))
        return run_identifier

    def log_engineer_step(self, run_id: str, stage: str, title: str, status: str,
                          details: Optional[Dict] = None,
                          step_order: Optional[int] = None) -> int:
        """Inregistreaza un pas intr-un run operational."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if step_order is None:
                cursor.execute("""
                    SELECT COALESCE(MAX(step_order), 0) + 1 AS next_order
                    FROM engineer_run_steps
                    WHERE run_id = ?
                """, (run_id,))
                step_order = cursor.fetchone()["next_order"]

            cursor.execute("""
                INSERT INTO engineer_run_steps (run_id, step_order, stage, title, status, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                step_order,
                stage,
                title,
                status,
                json.dumps(details or {}),
                time.time(),
            ))
            cursor.execute(
                "UPDATE engineer_runs SET updated_at = ? WHERE run_id = ?",
                (time.time(), run_id),
            )
            return cursor.lastrowid

    def finalize_engineer_run(self, run_id: str, status: str,
                               summary: str = "",
                               result: Optional[Dict] = None) -> bool:
        """Finalizeaza un run operational."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE engineer_runs
                SET status = ?, summary = ?, result = ?, updated_at = ?
                WHERE run_id = ?
            """, (
                status,
                summary,
                json.dumps(result or {}),
                time.time(),
                run_id,
            ))
            return cursor.rowcount > 0

    def get_engineer_run(self, run_id: str) -> Optional[Dict]:
        """Returneaza un run operational si pasii sai."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT run_id, profile, task, workspace, status, summary,
                       metadata, result, created_at, updated_at
                FROM engineer_runs
                WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute("""
                SELECT step_order, stage, title, status, details, created_at
                FROM engineer_run_steps
                WHERE run_id = ?
                ORDER BY step_order ASC, id ASC
            """, (run_id,))
            steps = [
                {
                    'step_order': step['step_order'],
                    'stage': step['stage'],
                    'title': step['title'],
                    'status': step['status'],
                    'details': json.loads(step['details']),
                    'created_at': step['created_at'],
                }
                for step in cursor.fetchall()
            ]

            return {
                'run_id': row['run_id'],
                'profile': row['profile'],
                'task': row['task'],
                'workspace': row['workspace'],
                'status': row['status'],
                'summary': row['summary'],
                'metadata': json.loads(row['metadata']),
                'result': json.loads(row['result']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'steps': steps,
            }

    def list_engineer_runs(self, limit: int = 20, profile: Optional[str] = None) -> List[Dict]:
        """Listeaza run-urile operationale recente."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if profile:
                cursor.execute("""
                    SELECT run_id, profile, task, workspace, status, summary, created_at, updated_at
                    FROM engineer_runs
                    WHERE profile = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (profile, limit))
            else:
                cursor.execute("""
                    SELECT run_id, profile, task, workspace, status, summary, created_at, updated_at
                    FROM engineer_runs
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def record_repair_pattern(self, signature: str, strategy: str,
                               successful: bool,
                               patch_hint: str = "",
                               example_error: str = "",
                               metadata: Optional[Dict] = None) -> bool:
        """Salveaza sau actualizeaza un pattern de reparare."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM repair_patterns WHERE signature = ?
            """, (signature,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE repair_patterns
                    SET strategy = ?,
                        patch_hint = ?,
                        example_error = ?,
                        occurrence_count = occurrence_count + 1,
                        success_count = success_count + ?,
                        metadata = ?,
                        updated_at = ?
                    WHERE signature = ?
                """, (
                    strategy,
                    patch_hint,
                    example_error,
                    int(bool(successful)),
                    json.dumps(metadata or {}),
                    now,
                    signature,
                ))
            else:
                cursor.execute("""
                    INSERT INTO repair_patterns (
                        signature, strategy, patch_hint, example_error,
                        occurrence_count, success_count, metadata,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signature,
                    strategy,
                    patch_hint,
                    example_error,
                    1,
                    int(bool(successful)),
                    json.dumps(metadata or {}),
                    now,
                    now,
                ))
            return True

    def get_repair_pattern(self, signature: str) -> Optional[Dict]:
        """Returneaza pattern-ul asociat unei semnaturi de eroare."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT signature, strategy, patch_hint, example_error,
                       occurrence_count, success_count, metadata, created_at, updated_at
                FROM repair_patterns
                WHERE signature = ?
            """, (signature,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'signature': row['signature'],
                'strategy': row['strategy'],
                'patch_hint': row['patch_hint'],
                'example_error': row['example_error'],
                'occurrence_count': row['occurrence_count'],
                'success_count': row['success_count'],
                'metadata': json.loads(row['metadata']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }

    def record_generated_project(self, project_name: str, project_path: str,
                                  project_type: str = "cli_bot",
                                  spec: Optional[Dict] = None,
                                  metadata: Optional[Dict] = None) -> bool:
        """Inregistreaza un proiect generat de Bot Factory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generated_projects (
                    project_name, project_path, project_type, spec, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_path) DO UPDATE SET
                    project_name = excluded.project_name,
                    project_type = excluded.project_type,
                    spec = excluded.spec,
                    metadata = excluded.metadata
            """, (
                project_name,
                project_path,
                project_type,
                json.dumps(spec or {}),
                json.dumps(metadata or {}),
                time.time(),
            ))
            return True

    def list_generated_projects(self, limit: int = 20) -> List[Dict]:
        """Listeaza proiectele generate recent."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT project_name, project_path, project_type, spec, metadata, created_at
                FROM generated_projects
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [
                {
                    'project_name': row['project_name'],
                    'project_path': row['project_path'],
                    'project_type': row['project_type'],
                    'spec': json.loads(row['spec']),
                    'metadata': json.loads(row['metadata']),
                    'created_at': row['created_at'],
                }
                for row in cursor.fetchall()
            ]

    # ==================== STATISTICI ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtine statistici despre memorie."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Conversatii
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            stats['total_messages'] = cursor.fetchone()['count']
            
            # Cunostinte
            cursor.execute("SELECT COUNT(*) as count FROM knowledge")
            stats['total_knowledge'] = cursor.fetchone()['count']
            
            # Erori
            cursor.execute("SELECT COUNT(*) as count FROM error_solutions")
            stats['total_error_solutions'] = cursor.fetchone()['count']
            
            # Evolutie
            cursor.execute("SELECT COUNT(*) as count FROM evolution_log")
            stats['total_evolutions'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM engineer_runs")
            stats['total_engineer_runs'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM repair_patterns")
            stats['total_repair_patterns'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM generated_projects")
            stats['total_generated_projects'] = cursor.fetchone()['count']
            
            # Dimensiune fisier
            stats['database_size_mb'] = round(
                os.path.getsize(self.db_path) / (1024 * 1024), 2
            ) if os.path.exists(self.db_path) else 0
            
            return stats
    
    def export_to_json(self, output_path: str) -> bool:
        """Exporta toata memoria in format JSON (pentru backup)."""
        try:
            data = {
                'exported_at': datetime.now().isoformat(),
                'knowledge': [],
                'error_solutions': [],
                'evolution_log': [],
                'engineer_runs': [],
                'engineer_run_steps': [],
                'repair_patterns': [],
                'generated_projects': [],
            }
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Export knowledge
                cursor.execute("SELECT topic, category, content FROM knowledge")
                data['knowledge'] = [dict(row) for row in cursor.fetchall()]
                
                # Export error solutions
                cursor.execute("SELECT error_pattern, solution FROM error_solutions")
                data['error_solutions'] = [dict(row) for row in cursor.fetchall()]
                
                # Export evolution log
                cursor.execute("SELECT action_type, description, details, timestamp FROM evolution_log")
                data['evolution_log'] = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT * FROM engineer_runs")
                data['engineer_runs'] = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT * FROM engineer_run_steps")
                data['engineer_run_steps'] = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT * FROM repair_patterns")
                data['repair_patterns'] = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT * FROM generated_projects")
                data['generated_projects'] = [dict(row) for row in cursor.fetchall()]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Eroare la export: {e}")
            return False


# Singleton pentru acces global
_memory_instance: Optional[Memory] = None


def get_memory(db_path: Optional[str] = None) -> Memory:
    """Obtine instanta globala de memorie."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = Memory(db_path or "memory/ana_brain.db")
    return _memory_instance
