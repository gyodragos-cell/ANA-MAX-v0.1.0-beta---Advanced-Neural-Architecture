import math
import re
import os
import json
import logging
import hashlib
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

class BM25:
    """Pure CPU BM25 Implementation for Zero-VRAM Semantic Search."""
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0
        self.corpus_size = 0

    def tokenize(self, text):
        return [w.lower() for w in re.findall(r'\w+', text)]

    def fit(self, corpus):
        """corpus is a list of strings (chunks)"""
        self.corpus_size = len(corpus)
        nd = {}  # word -> number of documents containing the word
        num_doc = 0
        total_len = 0

        for document in corpus:
            doc_len = 0
            frequencies = {}
            for word in self.tokenize(document):
                doc_len += 1
                frequencies[word] = frequencies.get(word, 0) + 1
            
            self.doc_len.append(doc_len)
            total_len += doc_len
            self.doc_freqs.append(frequencies)

            for word, freq in frequencies.items():
                nd[word] = nd.get(word, 0) + 1
            num_doc += 1

        self.avgdl = total_len / num_doc if num_doc > 0 else 0

        # Calculate IDF
        for word, freq in nd.items():
            # Standard BM25 IDF formula
            idf = math.log(((self.corpus_size - freq + 0.5) / (freq + 0.5)) + 1)
            self.idf[word] = idf

    def get_scores(self, query):
        """Score all chunks against the query."""
        scores = [0.0] * self.corpus_size
        query_words = self.tokenize(query)
        
        for i in range(self.corpus_size):
            score = 0.0
            doc_len = self.doc_len[i]
            frequencies = self.doc_freqs[i]
            
            for word in query_words:
                if word not in frequencies:
                    continue
                freq = frequencies[word]
                numerator = self.idf.get(word, 0) * freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += numerator / denominator
            scores[i] = score
        return scores


class CPURagEngine:
    def __init__(self, cache_dir=".cache/rag"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _chunk_text(self, text, chunk_size=500):
        """Simple chunker. Splits text into chunks of `chunk_size` words with overlap."""
        words = text.split()
        chunks = []
        overlap = 50
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks
        
    def _get_cache_path(self, filepath):
        """Generate a deterministic cache path based on filepath + modification time."""
        if not os.path.exists(filepath):
            return None
        mtime = os.path.getmtime(filepath)
        fingerprint = f"{filepath}_{mtime}"
        file_hash = hashlib.md5(fingerprint.encode()).hexdigest()
        return self.cache_dir / f"{file_hash}.json"

    def index_file(self, filepath):
        """Indexes a file using BM25 and saves chunks."""
        import hashlib # Lazy import
        if not os.path.exists(filepath):
            return f"Error: File {filepath} not found."
            
        cache_path = self._get_cache_path(filepath)
        if cache_path and cache_path.exists():
            return "ALREADY_INDEXED"
            
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return f"Error reading file: {e}"
            
        chunks = self._chunk_text(content)
        if not chunks:
            return "File is empty."
            
        bm25 = BM25()
        bm25.fit(chunks)
        
        # Save to cache
        cache_data = {
            "chunks": chunks,
            "idf": bm25.idf,
            "doc_len": bm25.doc_len,
            "doc_freqs": bm25.doc_freqs,
            "corpus_size": bm25.corpus_size,
            "avgdl": bm25.avgdl
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
            
        return "INDEXED"

    def search_file(self, filepath, query, top_k=3):
        """Searches an indexed file."""
        import hashlib
        cache_path = self._get_cache_path(filepath)
        
        if not cache_path or not cache_path.exists():
            status = self.index_file(filepath)
            if "Error" in status:
                return status
                
        # Load from cache
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception as e:
            return f"Error loading RAG cache: {e}"
            
        bm25 = BM25()
        bm25.idf = cache_data["idf"]
        bm25.doc_len = cache_data["doc_len"]
        bm25.doc_freqs = cache_data["doc_freqs"]
        bm25.corpus_size = cache_data["corpus_size"]
        bm25.avgdl = cache_data["avgdl"]
        chunks = cache_data["chunks"]
        
        scores = bm25.get_scores(query)
        
        # Get top K indices
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        
        results = []
        for i in ranked_indices[:top_k]:
            if scores[i] > 0:  # Only return if it actually matched something
                results.append(f"--- MATCH SCORE: {scores[i]:.2f} ---\n{chunks[i]}")
                
        if not results:
            return f"No matches found for query: '{query}' in file."
            
        return "\n\n".join(results)

    def index_jsonl(self, filepath):
        """Indexes a JSONL file, treating each line as a distinct document."""
        import hashlib
        if not os.path.exists(filepath):
            return {"status": "error", "message": f"File {filepath} not found."}
            
        cache_path = self._get_cache_path(filepath)
        if cache_path and cache_path.exists():
            return {"status": "success", "message": "ALREADY_INDEXED"}
            
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.read().splitlines()
        except Exception as e:
            return {"status": "error", "message": f"Error reading file: {e}"}
            
        chunks = [line for line in lines if line.strip()]
        if not chunks:
            return {"status": "error", "message": "File is empty."}
            
        bm25 = BM25()
        bm25.fit(chunks)
        
        # Save to cache
        cache_data = {
            "chunks": chunks,
            "idf": bm25.idf,
            "doc_len": bm25.doc_len,
            "doc_freqs": bm25.doc_freqs,
            "corpus_size": bm25.corpus_size,
            "avgdl": bm25.avgdl
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
            
        return {"status": "success", "message": "INDEXED"}

    def search_jsonl(self, filepath, query, top_k=10, filter_type=None):
        """Searches an indexed JSONL file and returns parsed JSON objects."""
        import hashlib
        cache_path = self._get_cache_path(filepath)
        
        if not cache_path or not cache_path.exists():
            res = self.index_jsonl(filepath)
            if res["status"] == "error":
                return []
                
        # Load from cache
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading RAG cache: {e}")
            return []
            
        bm25 = BM25()
        bm25.idf = cache_data["idf"]
        bm25.doc_len = cache_data["doc_len"]
        bm25.doc_freqs = cache_data["doc_freqs"]
        bm25.corpus_size = cache_data["corpus_size"]
        bm25.avgdl = cache_data["avgdl"]
        chunks = cache_data["chunks"]
        
        scores = bm25.get_scores(query)
        
        # Get top K indices
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        
        results = []
        for i in ranked_indices:
            if scores[i] > 0:
                try:
                    obj = json.loads(chunks[i])
                    if filter_type and obj.get("type") != filter_type:
                        continue
                    obj["_score"] = scores[i]
                    results.append(obj)
                    if len(results) >= top_k:
                        break
                except Exception:
                    continue
                    
        return results

# Global engine instance
_engine = None
def get_rag_engine():
    global _engine
    if _engine is None:
        _engine = CPURagEngine()
    return _engine
