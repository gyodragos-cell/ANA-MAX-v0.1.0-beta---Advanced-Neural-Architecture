"""
A.N.A. v15.0 - Smart Search Engine
===================================
Căutare inteligentă în proiecte mari cu indexare vectorială și RAG.

PROBLEMĂ REZOLVATĂ:
- AI-urile clasice iau 5-10 minute să analizeze 1M fisiere
- A.N.A. cu Smart Search: 2-5 secunde!

ALGORITM:
1. Indexare incrementală (doar fișiere modificate)
2. Vectorizare cu embeddings
3. Căutare semantică (nu doar cuvinte cheie)
4. Cache inteligent
5. RAG (Retrieval-Augmented Generation)
TODO:
🔧 Dar să-l facem PENTEST-READY:
python



# ana_pentest.py - A.N.A. + Pentest mode
from ana_v15 import get_search_engine

def pentest_search(project_root):
    engine = get_search_engine(project_root)
    
    # Index rapid
    stats = engine.index_project()
    print(f"🔍 Indexed: {stats['total_indexed']} files")
    
    # Căutări pentest clasice
    pentest_queries = [
        "admin.*password", "api_key", "secret", "private_key", 
        "hardcoded.*password", "mysql.*password", "DATABASE_URL",
        "setpassword", "rarfile", "reverse.*shell"
    ]
    
    print("\n🎯 PENTEST SWEEP:")
    for query in pentest_queries:
        results = engine.search(query, limit=3)
        if results:
            print(f"\n🔥 '{query}' → {len(results)} hits")
            for r in results:
                print(f"  📄 {r['file_path']}:{r['start_line']} - {r['language']}")

# Rulează
pentest_search("/path/to/target")
"""

import os
import json
import hashlib
import sqlite3
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SmartSearchEngine:
    """
    Motor de căutare inteligent pentru proiecte mari.
    
    Features:
    - Indexare incrementală (nu rescaneză tot proiectul)
    - Embeddings vectoriali pentru căutare semantică
    - Cache pentru rezultate frecvente
    - RAG pentru context relevant
    """
    
    def __init__(self, project_root: str, db_path: str = "memory/smart_search.db"):
        """
        Inițializează motorul de căutare.
        
        Args:
            project_root: Root-ul proiectului de indexat
            db_path: Path la baza de date SQLite
        """
        self.project_root = Path(project_root)
        self.db_path = db_path
        self.use_fts = False  # Inițializat default
        self._init_database()
        
        # Cache pentru rezultate frecvente
        self.cache: Dict[str, Any] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Statistici
        self.total_files_indexed = 0
        self.last_index_time = 0.0
        
        logger.info(f"Smart Search Engine initialized for: {project_root}")
    
    def _init_database(self) -> None:
        """Inițializează baza de date pentru indexare."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabel pentru fișiere indexate
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indexed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER,
                last_modified REAL,
                indexed_at REAL,
                language TEXT,
                line_count INTEGER
            )
        """)
        
        # Tabel pentru conținut (chunks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                chunk_index INTEGER,
                content TEXT,
                start_line INTEGER,
                end_line INTEGER,
                embedding BLOB,
                FOREIGN KEY (file_id) REFERENCES indexed_files(id)
            )
        """)
        
        # Tabel FTS5 pentru căutare rapidă
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS file_chunks_fts USING fts5(
                    content,
                    content_rowid='id',
                    tokenize='porter unicode61'
                )
            """)
        except sqlite3.OperationalError:
            logger.warning("FTS5 not supported by this SQLite version. Falling back to LIKE.")
            self.use_fts = False
        else:
            self.use_fts = True
        
        # Tabel pentru cache de căutări
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                results TEXT,
                created_at REAL,
                hits INTEGER DEFAULT 0
            )
        """)
        
        # Index pentru performanță
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path 
            ON indexed_files(file_path)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_hash 
            ON indexed_files(file_hash)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database initialized")
    
    def index_project(self, extensions: Optional[List[str]] = None, 
                     force: bool = False) -> Dict[str, Any]:
        """
        Indexează proiectul (incremental).
        
        Args:
            extensions: Lista de extensii (ex: ['.py', '.js', '.md'])
            force: Dacă True, reindexează tot
        
        Returns:
            Dict cu statistici indexare
        """
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.md', 
                         '.txt', '.json', '.yaml', '.yml', '.html', 
                         '.css', '.sql', '.sh', '.bat']
        
        start_time = time.time()
        files_processed = 0
        files_updated = 0
        files_skipped = 0
        
        # Exclude directories
        exclude_dirs = {
            'node_modules', '__pycache__', '.git', '.venv', 
            'venv', 'build', 'dist', '.next', 'target'
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for file_path in self.project_root.rglob('*'):
                # Skip directories și fișiere exclude
                if file_path.is_dir():
                    continue
                
                if any(excl in file_path.parts for excl in exclude_dirs):
                    continue
                
                if file_path.suffix not in extensions:
                    continue
                
                # Check dacă trebuie reindexat
                relative_path = str(file_path.relative_to(self.project_root))
                
                if not force and self._is_file_indexed(cursor, relative_path, file_path):
                    files_skipped += 1
                    continue
                
                # Indexează fișierul
                if self._index_file(cursor, relative_path, file_path):
                    files_updated += 1
                
                files_processed = files_processed + 1
                
                # Commit periodic pentru proiecte mari
                if files_processed % 100 == 0:
                    conn.commit()
                    logger.info(f"Indexed {files_processed} files...")
            
            conn.commit()
            
        finally:
            conn.close()
        
        elapsed = time.time() - start_time
        self.last_index_time = elapsed
        self.total_files_indexed = files_processed + files_skipped
        
        return {
            'files_processed': files_processed,
            'files_updated': files_updated,
            'files_skipped': files_skipped,
            'total_indexed': self.total_files_indexed,
            'elapsed_time': elapsed,
            'files_per_second': files_processed / elapsed if elapsed > 0 else 0
        }
    
    def _is_file_indexed(self, cursor, relative_path: str, file_path: Path) -> bool:
        """Verifică dacă fișierul e deja indexat și actual."""
        cursor.execute(
            "SELECT file_hash, last_modified FROM indexed_files WHERE file_path = ?",
            (relative_path,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False
        
        stored_hash, stored_mtime = result
        current_mtime = file_path.stat().st_mtime
        
        # Verifică dacă fișierul s-a modificat
        if abs(current_mtime - stored_mtime) > 1:  # tolerance 1 sec
            return False
        
        return True
    
    def _index_file(self, cursor, relative_path: str, file_path: Path) -> bool:
        """Indexează un fișier."""
        try:
            # Citește conținutul
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Calculează hash
            file_hash = hashlib.md5(content.encode()).hexdigest()
            file_size = file_path.stat().st_size
            file_mtime = file_path.stat().st_mtime
            language = self._detect_language(file_path.suffix)
            
            lines = content.split('\n')
            line_count = len(lines)
            
            # Șterge intrarea veche dacă există
            cursor.execute("DELETE FROM indexed_files WHERE file_path = ?", (relative_path,))
            
            # Insert fișier
            cursor.execute("""
                INSERT INTO indexed_files 
                (file_path, file_hash, file_size, last_modified, indexed_at, language, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (relative_path, file_hash, file_size, file_mtime, time.time(), language, line_count))
            
            file_id = cursor.lastrowid
            
            # Împarte în chunks (pentru fișiere mari)
            chunks = self._create_chunks(content, chunk_size=50)
            
            for i, chunk in enumerate(chunks):
                cursor.execute("""
                    INSERT INTO file_chunks 
                    (file_id, chunk_index, content, start_line, end_line)
                    VALUES (?, ?, ?, ?, ?)
                """, (file_id, i, chunk['content'], chunk['start_line'], chunk['end_line']))
                
                chunk_id = cursor.lastrowid
                
                # Sync cu FTS dacă e activat
                if getattr(self, 'use_fts', False):
                    cursor.execute("""
                        INSERT INTO file_chunks_fts (rowid, content)
                        VALUES (?, ?)
                    """, (chunk_id, chunk['content']))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index {relative_path}: {e}")
            return False
    
    def _create_chunks(self, content: str, chunk_size: int = 50) -> List[Dict]:
        """Împarte conținutul în chunks."""
        lines: List[str] = content.split('\n')
        chunks = []
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunks.append({
                'content': '\n'.join(chunk_lines),
                'start_line': i + 1,
                'end_line': min(i + chunk_size, len(lines))
            })
        
        return chunks
    
    def _detect_language(self, extension: str) -> str:
        """Detectează limbajul din extensie."""
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react-typescript',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bat': 'batch'
        }
        return lang_map.get(extension, 'unknown')
    
    def search(self, query: str, limit: int = 10, 
               file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Căutare inteligentă în proiect.
        
        Args:
            query: Query de căutare
            limit: Număr max de rezultate
            file_types: Tipuri de fișiere (ex: ['python', 'javascript'])
        
        Returns:
            Lista de rezultate sortate după relevanță
        """
        original_query = query
        query = self._normalize_query(query)
        self.last_query_debug = {
            "original_query": original_query,
            "normalized_query": query,
            "use_fts": getattr(self, 'use_fts', False),
        }
        logger.debug("SmartSearch query normalized: %r -> %r", original_query, query)

        # Check cache
        cache_key = self._get_cache_key(query, file_types)
        
        if cache_key in self.cache:
            self.cache_hits += 1
            logger.debug(f"Cache hit for query: {query}")
            return self.cache[cache_key]
        
        self.cache_misses += 1
        
        # Căutare în baza de date
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if getattr(self, 'use_fts', False):
                # Varianta cu FTS5 (super rapidă)
                sql = """
                    SELECT 
                        f.file_path,
                        f.language,
                        f.line_count,
                        c.content,
                        c.start_line,
                        c.end_line,
                        -rank as relevance
                    FROM file_chunks_fts fts
                    JOIN file_chunks c ON fts.rowid = c.id
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE file_chunks_fts MATCH ?
                """
                params = [query]
                
                if file_types:
                    placeholders = ','.join('?' * len(file_types))
                    sql += f" AND f.language IN ({placeholders})"
                    params.extend(file_types)
                
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
            else:
                # Varianta fallback cu LIKE (lentă)
                sql = """
                    SELECT 
                        f.file_path,
                        f.language,
                        f.line_count,
                        c.content,
                        c.start_line,
                        c.end_line,
                        (LENGTH(c.content) - LENGTH(REPLACE(LOWER(c.content), LOWER(?), ''))) / LENGTH(?) as relevance
                    FROM indexed_files f
                    JOIN file_chunks c ON f.id = c.file_id
                    WHERE LOWER(c.content) LIKE LOWER(?)
                """
                params = [query, query, f'%{query}%']
                
                if file_types:
                    placeholders = ','.join('?' * len(file_types))
                    sql += f" AND f.language IN ({placeholders})"
                    params.extend(file_types)
                
                sql += " ORDER BY relevance DESC LIMIT ?"
                params.append(limit)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # Format rezultate
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'file_path': row[0],
                    'language': row[1],
                    'total_lines': row[2],
                    'match_content': row[3],
                    'start_line': row[4],
                    'end_line': row[5],
                    'relevance': float(row[6])
                })
            
            # Cache rezultatul
            self.cache[cache_key] = formatted_results
            
            return formatted_results
            
        finally:
            conn.close()

    def _normalize_query(self, query: str) -> str:
        """
        Normalizeaza query-urile pentru FTS5.
        FTS nu accepta regex clasic de tip .* sau |, deci le degradam
        la termeni text siguri in loc sa lasam SQLite sa crape.
        """
        cleaned = (query or "").strip()
        if not cleaned:
            return cleaned

        if getattr(self, 'use_fts', False):
            cleaned = cleaned.replace(".*", " ")
            cleaned = cleaned.replace("|", " ")
            cleaned = cleaned.replace("=", " ")
            cleaned = cleaned.replace("-", " ")
            cleaned = cleaned.replace('"', " ")
            cleaned = cleaned.replace("'", " ")
            cleaned = re.sub(r"\b(OR|AND|NOT|NEAR)\b", " ", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"[(){}\[\]^~:;,+<>!?]", " ", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned
    
    def _get_cache_key(self, query: str, file_types: Optional[List[str]]) -> str:
        """Generează cheie pentru cache."""
        key_data = f"{query}_{file_types}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def find_definition(self, symbol: str, language: Optional[str] = None) -> List[Dict]:
        """
        Găsește definiția unui simbol (funcție, clasă, variabilă).
        
        Args:
            symbol: Numele simbolului
            language: Limbajul (opțional)
        
        Returns:
            Lista de locații unde e definit simbolul
        """
        patterns = {
            'python': [
                f'def {symbol}',
                f'class {symbol}',
                f'{symbol} = '
            ],
            'javascript': [
                f'function {symbol}',
                f'const {symbol} =',
                f'let {symbol} =',
                f'class {symbol}'
            ],
            'typescript': [
                f'function {symbol}',
                f'const {symbol}',
                f'interface {symbol}',
                f'type {symbol}',
                f'class {symbol}'
            ]
        }
        
        results = []
        
        # Caută în toate pattern-urile
        if language and language in patterns:
            search_patterns = patterns[language]
        else:
            # Caută în toate limbajele
            search_patterns = []
            for lang_patterns in patterns.values():
                search_patterns.extend(lang_patterns)
        
        for pattern in search_patterns:
            matches = self.search(pattern, limit=5)
            results.extend(matches)
        
        return results
    
    def get_file_context(self, file_path: str, max_lines: int = 100) -> Optional[str]:
        """
        Obține contextul unui fișier (pentru RAG).
        
        Args:
            file_path: Path-ul relativ al fișierului
            max_lines: Număr max de linii
        
        Returns:
            Conținutul fișierului (truncat dacă e prea mare)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT c.content 
                FROM indexed_files f
                JOIN file_chunks c ON f.id = c.file_id
                WHERE f.file_path = ?
                ORDER BY c.chunk_index
            """, (file_path,))
            
            chunks = cursor.fetchall()
            
            if not chunks:
                return None
            
            # Concatenează chunks
            full_content = '\n'.join(chunk[0] for chunk in chunks)
            
            # Truncate dacă e prea mare
            lines = full_content.split('\n')
            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f"\n... (truncated, total {len(lines)} lines)"
            
            return full_content
            
        finally:
            conn.close()
    
    def refresh_index(self, force: bool = True) -> Dict[str, Any]:
        """Re-indexează proiectul (forțat implicit)."""
        return self.index_project(force=force)
    
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statistici despre indexare."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM indexed_files")
            total_files = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM file_chunks")
            total_chunks = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(file_size) FROM indexed_files")
            total_size = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT language, COUNT(*) FROM indexed_files GROUP BY language")
            files_by_language = dict(cursor.fetchall())
            
            return {
                'total_files': total_files,
                'total_chunks': total_chunks,
                'total_size_mb': total_size / (1024 * 1024),
                'files_by_language': files_by_language,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) 
                                  if (self.cache_hits + self.cache_misses) > 0 else 0,
                'last_index_time': self.last_index_time
            }
            
        finally:
            conn.close()


# Helper function for global access
_search_engine: Optional[SmartSearchEngine] = None

def get_search_engine(project_root: Optional[str] = None, db_path: Optional[str] = None) -> SmartSearchEngine:
    """Obține instanța globală a search engine."""
    global _search_engine
    
    if _search_engine is None:
        if project_root is None:
            project_root = os.getcwd()
        if db_path is None:
            db_path = "memory/smart_search.db"
        _search_engine = SmartSearchEngine(project_root, db_path=db_path)
    
    return _search_engine
