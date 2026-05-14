"""
A.N.A. v15.0 - Codebase Understanding Engine
=============================================
RAG (Retrieval-Augmented Generation) cu embeddings vectoriali.
"""

import os
import json
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import ast
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")


class CodebaseUnderstanding:
    """
    Motor de înțelegere a codebase-ului cu suport pentru persistență.
    """
    
    def __init__(self, project_root: str, db_path: str = "memory/smart_search.db"):
        self.project_root = Path(project_root)
        self.db_path = db_path
        self._init_db()
        
        # Embeddings model
        self.model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2') 
                logger.info("Embeddings model 'all-MiniLM-L6-v2' loaded")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
        
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)
        self.class_definitions: Dict[str, Dict] = {}
        self.function_definitions: Dict[str, Dict] = {}
        self.imports: Dict[str, List[str]] = defaultdict(list)
        
        logger.info(f"Codebase Understanding initialized for: {project_root}")

    def _init_db(self):
        """Asigură-te că tabelul de embeddings există în baza de date Smart Search."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verificăm dacă coloana embedding există deja în file_chunks (ar trebui să fie din smart_search.py)
        # Dar ne asigurăm că avem și un tabel pentru metadate de codebase
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS codebase_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        conn.commit()
        conn.close()

    def analyze_project(self, extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analizează proiectul și generează embeddings."""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.md']
            
        stats = {
            'files_analyzed': 0,
            'embeddings_generated': 0,
            'total_lines': 0
        }
        
        exclude_dirs = {'node_modules', '__pycache__', '.git', '.venv', 'venv'}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for file_path in self.project_root.rglob('*'):
                if file_path.is_dir() or any(excl in file_path.parts for excl in exclude_dirs):
                    continue
                if file_path.suffix not in extensions:
                    continue
                
                relative_path = str(file_path.relative_to(self.project_root))
                
                # Citim conținutul
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check if we need to update embeddings (based on file_chunks missing embeddings)
                cursor.execute("""
                    SELECT c.id, c.content 
                    FROM file_chunks c
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.file_path = ? AND c.embedding IS NULL
                """, (relative_path,))
                
                chunks_to_embed = cursor.fetchall()
                
                if chunks_to_embed and self.model is not None:
                    for chunk_id, chunk_content in chunks_to_embed:
                        # Generăm embedding
                        embedding = self.model.encode(chunk_content)
                        # Salvăm în DB ca blob
                        embedding_blob = embedding.tobytes()
                        
                        cursor.execute(
                            "UPDATE file_chunks SET embedding = ? WHERE id = ?",
                            (embedding_blob, chunk_id)
                        )
                        stats['embeddings_generated'] += 1
                
                stats['files_analyzed'] += 1
                
                # AST logic for Python to find classes/funcs (simplified)
                if file_path.suffix == '.py':
                    self._parse_python_ast(content, relative_path)
            
            conn.commit()
        finally:
            conn.close()
            
        return stats

    def _parse_python_ast(self, content: str, relative_path: str):
        """Extrage clase și funcții folosind AST."""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.class_definitions[node.name] = {
                        'file': relative_path,
                        'line': node.lineno
                    }
                elif isinstance(node, ast.FunctionDef):
                    self.function_definitions[f"{relative_path}::{node.name}"] = {
                        'name': node.name,
                        'file': relative_path,
                        'line': node.lineno
                    }
        except:
            pass

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Căutare semantică folosind embeddings din baza de date."""
        if self.model is None or not HAS_NUMPY:
            return []
            
        query_embedding = self.model.encode(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = []
        try:
            # Luăm toate chunkurile care au embedding
            cursor.execute("""
                SELECT f.file_path, c.content, c.start_line, c.end_line, c.embedding
                FROM file_chunks c
                JOIN indexed_files f ON c.file_id = f.id
                WHERE c.embedding IS NOT NULL
            """)
            
            rows = cursor.fetchall()
            for file_path, content, start, end, emb_blob in rows:
                chunk_emb = np.frombuffer(emb_blob, dtype=np.float32)
                
                # Cosine similarity
                similarity = np.dot(query_embedding, chunk_emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_emb)
                )
                
                results.append({
                    'file': file_path,
                    'content': content,
                    'line': start,
                    'similarity': float(similarity)
                })
            
            # Sortăm
            results.sort(key=lambda x: x['similarity'], reverse=True)
        finally:
            conn.close()
            
        return results[:limit]

    def ask_codebase(self, question: str) -> str:
        """Răspunde semantic la o întrebare."""
        results = self.semantic_search(question)
        if not results:
            return "Nu am găsit informații semantice. Te rog să indexezi proiectul mai întâi."
            
        resp = f"Pe baza analizei semantice, am găsit următoarele fragmente relevante:\n\n"
        for i, r in enumerate(results, 1):
            resp += f"{i}. **{r['file']}** (Linia {r['line']}) - Scorul similiaritate: {r['similarity']:.2f}\n"
            resp += f"```\n{r['content'][:300]}...\n```\n"
            
        return resp


_instance = None

def get_codebase_understanding(project_root: Optional[str] = None) -> CodebaseUnderstanding:
    global _instance
    if _instance is None:
        if project_root is None:
            project_root = os.getcwd()
        _instance = CodebaseUnderstanding(project_root)
    return _instance
