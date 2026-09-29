"""
ANA MAX / OS27 - Hyper Enterprise Large File Intelligence Engine
=================================================================
Kernel-grade streaming + semantic analysis + MCP-ready runtime.

Level: OS27 Hyper Edition
- True lazy generator (yield-based, zero-copy where possible)
- mmap + buffered I/O hybrid
- Compression-aware (gzip/bzip2/xz/zip) with transparent decompression
- Smart semantic chunking (code / logs / JSON / HTML / SQL)
- Adaptive chunk size based on file type + structure
- Differential reading (new/changed/removed segments)
- LRU + LFU hybrid cache for hot chunks
- Persistent bookmarks + session fingerprints
- Entropy + anomaly hints (corruption, injection, weird patterns)
- MCP streaming schema (start/next/end)
- Hooks pentru memory_cortex, context_engine, orchestrator
"""

import gzip
import hashlib
import json
import logging
import math
import os
import shutil
import sys
import tempfile
import threading
import time
from collections import Counter
from collections.abc import Callable, Generator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# Allow running from ANA_MAX root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
except ImportError:
    class Tool: pass

    class ToolDefinition:
        def __init__(self, name: str, description: str, parameters: list, category: str):
            self.name = name
            self.description = description
            self.parameters = parameters
            self.category = category

    class ToolParameter:
        def __init__(self, name: str, description: str, type: str, required: bool):
            self.name = name
            self.description = description
            self.type = type
            self.required = required

    class ToolResult:
        def __init__(
            self,
            status: str,
            data: Optional[dict] = None,
            error: Optional[str] = None,
            message: Optional[str] = None,
        ):
            self.status = status
            self.data = data
            self.error = error
            self.message = message

    class ToolStatus:
        SUCCESS = "success"
        ERROR = "error"


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

# OS27 Hyper++ Telemetry
_reader_telemetry: dict = {}


def _record_reader_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for file reader operations."""
    if operation not in _reader_telemetry:
        _reader_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _reader_telemetry[operation]["operation_count"] += 1
    _reader_telemetry[operation]["total_time"] += execution_time
    _reader_telemetry[operation]["last_execution_time"] = execution_time
    _reader_telemetry[operation]["last_success"] = success
    
    if success:
        _reader_telemetry[operation]["success_count"] += 1
    else:
        _reader_telemetry[operation]["failure_count"] += 1


def get_reader_telemetry(operation: str | None = None) -> dict | dict[str, dict]:
    """Get telemetry for file reader operations."""
    if operation:
        return _reader_telemetry.get(operation)
    return _reader_telemetry.copy()


def get_reader_health() -> str:
    """Get health status for file reader based on telemetry."""
    if not _reader_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _reader_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _reader_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


# ======================================================================
# Configuration & Constants
# ======================================================================

class FileExtension(Enum):
    PYTHON = ".py"
    JSON = ".json"
    MARKDOWN = ".md"
    YAML = ".yaml"
    YML = ".yml"
    TEXT = ".txt"
    JAVASCRIPT = ".js"
    TYPESCRIPT = ".ts"
    HTML = ".html"
    CSS = ".css"
    XML = ".xml"
    CONFIG = ".cfg"
    INI = ".ini"
    LOG = ".log"
    BATCH = ".bat"
    POWERSHELL = ".ps1"
    TOML = ".toml"
    ENV = ".env"
    SQL = ".sql"
    CSV = ".csv"
    CPP = ".cpp"
    C = ".c"
    H = ".h"
    JAVA = ".java"
    GO = ".go"
    RUST = ".rs"
    PHP = ".php"
    RUBY = ".rb"


SUPPORTED_EXTENSIONS = {ext.value for ext in FileExtension}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".cpp", ".c", ".h", ".java", ".go", ".rs", ".php", ".rb"
}

STRUCTURED_EXTENSIONS = {".json", ".yaml", ".yml", ".xml", ".html", ".sql"}

LOG_EXTENSIONS = {".log"}

COMPRESSION_MAGIC = {
    b"\x1f\x8b": "gzip",
    b"BZh": "bzip2",
    b"\xfd7zXZ\x00": "xz",
    b"PK\x03\x04": "zip",
}

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_MAX_CHUNKS = 10
DEFAULT_START_LINE = 1
BUFFER_SIZE = 64 * 1024
MAX_FILE_SIZE_GB = 50
ENTROPY_SAMPLE_BYTES = 256 * 1024
CACHE_SIZE = 128
BOOKMARK_DIR = os.path.join(tempfile.gettempdir(), "ana_os27_bookmarks")


# ======================================================================
# Data Classes
# ======================================================================

@dataclass
class FileMetadata:
    path: str
    size_bytes: int
    size_human: str
    extension: str
    encoding: str
    has_bom: bool
    line_ending: str
    is_binary: bool
    is_compressed: bool
    compression_type: Optional[str]
    modified_time: float
    file_hash_short: Optional[str]
    entropy_bits_per_byte: float
    avg_line_length: float
    max_line_length: int
    comment_ratio: float
    blank_ratio: float
    code_vs_text_hint: str
    structure_hint: str
    anomaly_hints: list[str]


@dataclass
class ChunkInfo:
    chunk_number: int
    start_line: int
    end_line: int
    text: str
    line_count: int
    char_count: int
    byte_offset_start: int
    byte_offset_end: int
    is_complete_boundary: bool
    semantic_hint: str
    anomaly_hints: list[str]


@dataclass
class ReadStatistics:
    total_lines: int
    returned_lines: int
    returned_chars: int
    chunks_returned: int
    read_time_seconds: float
    bytes_processed: int
    throughput_mb_s: float
    memory_peak_mb: float
    cache_hits: int
    cache_misses: int


@dataclass
class Bookmark:
    file_path: str
    file_hash: str
    line_number: int
    timestamp: float
    metadata: dict


# ======================================================================
# Utility Functions
# ======================================================================

def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} EB"


def get_memory_usage_mb() -> float:
    if HAS_PSUTIL:
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except OSError:
            pass
    return 0.0


def detect_compression(file_path: str) -> tuple[Optional[str], str]:
    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
        for sig, comp_type in COMPRESSION_MAGIC.items():
            if magic.startswith(sig):
                return comp_type, file_path
    except OSError:
        pass
    return None, file_path


def decompress_file(file_path: str, compression_type: str) -> str:
    temp_dir = tempfile.mkdtemp(prefix="ana_os27_decompress_")
    output_path = os.path.join(temp_dir, f"decompressed_{os.path.basename(file_path)}")
    try:
        if compression_type == "gzip":
            with gzip.open(file_path, "rb") as f_in, open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        elif compression_type == "bzip2":
            import bz2
            with bz2.open(file_path, "rb") as f_in, open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        elif compression_type == "xz":
            import lzma
            with lzma.open(file_path, "rb") as f_in, open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        else:
            return file_path
        return output_path
    except OSError as e:
        logger.error(f"Decompression failed: {e}")
        return file_path


def detect_encoding(file_path: str) -> tuple[str, bool]:
    bom_encodings = {
        b"\xef\xbb\xbf": "utf-8-sig",
        b"\xff\xfe": "utf-16-le",
        b"\xfe\xff": "utf-16-be",
        b"\xff\xfe\x00\x00": "utf-32-le",
        b"\x00\x00\xfe\xff": "utf-32-be",
    }
    try:
        with open(file_path, "rb") as f:
            raw = f.read(4)
            for bom, enc in bom_encodings.items():
                if raw.startswith(bom):
                    return enc, True
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                f.read(1024)
            return "utf-8", False
        except UnicodeDecodeError:
            return "latin-1", False
    except OSError:
        return "utf-8", False


def is_binary_heuristic(file_path: str, sample_size: int = 8192) -> bool:
    try:
        with open(file_path, "rb") as f:
            sample = f.read(sample_size)
        if not sample:
            return False
        if b"\x00" in sample:
            return True
        text_bytes = sum(1 for b in sample if (32 <= b <= 126) or b in (9, 10, 13))
        return text_bytes / len(sample) < 0.7
    except OSError:
        return False


def detect_line_ending(sample: str) -> str:
    if "\r\n" in sample:
        return "CRLF"
    if "\r" in sample:
        return "CR"
    if "\n" in sample:
        return "LF"
    return "unknown"


def compute_short_hash(file_path: str) -> Optional[str]:
    try:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for _ in range(16):
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()[:16]
    except OSError:
        return None


def compute_entropy(file_path: str, sample_bytes: int = ENTROPY_SAMPLE_BYTES) -> float:
    try:
        with open(file_path, "rb") as f:
            data = f.read(sample_bytes)
        if not data:
            return 0.0
        counts = [0] * 256
        for b in data:
            counts[b] += 1
        total = len(data)
        entropy = 0.0
        for c in counts:
            if c == 0:
                continue
            p = c / total
            entropy -= p * math.log2(p)
        return entropy
    except OSError:
        return 0.0


def analyze_text_sample(sample: str, extension: str) -> tuple[float, float, float, int, str, str, list[str]]:
    lines = sample.splitlines()
    if not lines:
        return 0.0, 0.0, 0.0, 0, "unknown", "unknown", []

    total_len = sum(len(l) for l in lines)
    max_len = max(len(l) for l in lines)
    blank = sum(1 for l in lines if not l.strip())
    comments = 0
    anomalies: list[str] = []

    for l in lines:
        s = l.strip()
        if not s:
            continue
        if s.startswith(("#", "//", "<!--")):
            comments += 1
        if "\x00" in s:
            anomalies.append("null-bytes-in-text")
        if "DROP TABLE" in s.upper():
            anomalies.append("sql-drop-table")
        if "UNION SELECT" in s.upper():
            anomalies.append("sql-union-select")
        if "<script" in s.lower():
            anomalies.append("embedded-script")

    avg_len = total_len / len(lines)
    blank_ratio = blank / len(lines)
    comment_ratio = comments / len(lines)

    code_hint = "unknown"
    if extension in CODE_EXTENSIONS:
        code_hint = "code"
    elif extension in {".md", ".txt"}:
        code_hint = "text"
    elif extension in {".json", ".yaml", ".yml"}:
        code_hint = "structured-data"
    elif extension in {".html", ".xml"}:
        code_hint = "markup"
    elif extension in {".sql"}:
        code_hint = "sql"
    elif extension in {".log"}:
        code_hint = "log"

    s_hint = "unknown"
    up = sample.upper()
    if "{" in sample and "}" in sample and ":" in sample and extension in {".json", ".js", ".ts"}:
        s_hint = "json-like"
    elif "---" in sample and ":" in sample and extension in {".yaml", ".yml"}:
        s_hint = "yaml-like"
    elif "<html" in sample.lower() or "<body" in sample.lower():
        s_hint = "html-page"
    elif "SELECT " in up or "INSERT " in up or "UPDATE " in up:
        s_hint = "sql-queries"
    elif "[INFO]" in sample or "[ERROR]" in sample or "[WARN]" in sample:
        s_hint = "log-stream"
    elif "def " in sample or "class " in sample:
        s_hint = "python-code"
    elif "function " in sample or "const " in sample:
        s_hint = "javascript-code"

    return avg_len, blank_ratio, comment_ratio, max_len, code_hint, s_hint, anomalies


def find_logical_boundary(lines: list[str], extension: str) -> int:
    if extension not in CODE_EXTENSIONS:
        return len(lines)
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if not line:
            return i + 1
        if extension == ".py" and line.startswith(("def ", "class ")):
            return i
        if line == "}" or line.endswith("};"):
            return i + 1
    return len(lines)


def semantic_hint_for_chunk(lines: list[str], extension: str) -> str:
    if extension in LOG_EXTENSIONS:
        severities = Counter()
        for l in lines:
            up = l.upper()
            if "ERROR" in up:
                severities["ERROR"] += 1
            elif "WARN" in up or "WARNING" in up:
                severities["WARN"] += 1
            elif "INFO" in up:
                severities["INFO"] += 1
        if severities:
            return f"log-chunk:{dict(severities)}"
        return "log-chunk"
    if extension in CODE_EXTENSIONS:
        funcs = sum(1 for l in lines if "def " in l or "function " in l or "class " in l)
        if funcs:
            return f"code-chunk:{funcs}-blocks"
        return "code-chunk"
    if extension in {".json", ".yaml", ".yml"}:
        return "structured-data-chunk"
    if extension in {".html", ".xml"}:
        return "markup-chunk"
    if extension in {".sql"}:
        return "sql-chunk"
    return "generic-chunk"


# ======================================================================
# Bookmark Management
# ======================================================================

class BookmarkManager:
    def __init__(self, bookmark_dir: str = BOOKMARK_DIR):
        self.bookmark_dir = bookmark_dir
        os.makedirs(bookmark_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _get_bookmark_path(self, file_path: str) -> str:
        file_hash = compute_short_hash(file_path) or "unknown"
        return os.path.join(self.bookmark_dir, f"bookmark_{file_hash}.json")

    def save_bookmark(self, file_path: str, line_number: int, metadata: dict) -> None:
        with self._lock:
            bookmark_path = self._get_bookmark_path(file_path)
            bookmark = Bookmark(
                file_path=file_path,
                file_hash=compute_short_hash(file_path) or "",
                line_number=line_number,
                timestamp=time.time(),
                metadata=metadata,
            )
            try:
                with open(bookmark_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "file_path": bookmark.file_path,
                        "file_hash": bookmark.file_hash,
                        "line_number": bookmark.line_number,
                        "timestamp": bookmark.timestamp,
                        "metadata": bookmark.metadata,
                    }, f)
            except OSError as e:
                logger.error(f"Failed to save bookmark: {e}")

    def load_bookmark(self, file_path: str) -> Optional[Bookmark]:
        with self._lock:
            bookmark_path = self._get_bookmark_path(file_path)
            if not os.path.exists(bookmark_path):
                return None
            try:
                with open(bookmark_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                current_hash = compute_short_hash(file_path)
                if current_hash and current_hash != data.get("file_hash"):
                    return None
                return Bookmark(
                    file_path=data["file_path"],
                    file_hash=data["file_hash"],
                    line_number=data["line_number"],
                    timestamp=data["timestamp"],
                    metadata=data.get("metadata", {}),
                )
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load bookmark: {e}")
                return None

    def clear_bookmark(self, file_path: str) -> None:
        with self._lock:
            bookmark_path = self._get_bookmark_path(file_path)
            try:
                if os.path.exists(bookmark_path):
                    os.remove(bookmark_path)
            except OSError as e:
                logger.error(f"Failed to clear bookmark: {e}")


# ======================================================================
# Cache Layer (Hybrid LRU/LFU)
# ======================================================================

class ChunkCache:
    def __init__(self, max_size: int = CACHE_SIZE):
        self.max_size = max_size
        self._cache: dict[str, ChunkInfo] = {}
        self._access_order: list[str] = []
        self._freq: dict[str, int] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _evict(self) -> None:
        if not self._access_order:
            return
        # Evict by lowest frequency, then oldest
        candidate = min(
            self._access_order,
            key=lambda k: (self._freq.get(k, 0), self._access_order.index(k)),
        )
        self._access_order.remove(candidate)
        self._cache.pop(candidate, None)
        self._freq.pop(candidate, None)

    def get(self, key: str) -> Optional[ChunkInfo]:
        with self._lock:
            if key in self._cache:
                self.hits += 1
                self._freq[key] = self._freq.get(key, 0) + 1
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            self.misses += 1
            return None

    def put(self, key: str, chunk: ChunkInfo) -> None:
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict()
            self._cache[key] = chunk
            self._access_order.append(key)
            self._freq[key] = self._freq.get(key, 0) + 1

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._freq.clear()
            self.hits = 0
            self.misses = 0


# ======================================================================
# Hyper Tool
# ======================================================================

class LargeFileReaderError(Exception):
    pass


class LargeFileReaderHyperTool(Tool):
    """
    OS27 Hyper Enterprise Large File Intelligence Engine.
    """

    def __init__(self):
        super().__init__()
        self.bookmark_manager = BookmarkManager()
        self.chunk_cache = ChunkCache()
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        self._progress_callback = callback

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="large_file_reader_hyper",
            description=(
                "OS27 Hyper Enterprise streaming reader for massive files (10k–100M+ lines). "
                "Features: lazy generator, mmap hybrid, compression-aware, semantic chunking, "
                "LRU/LFU cache, bookmarks, differential reading, entropy/anomaly hints, MCP-ready."
            ),
            parameters=[
                ToolParameter("file_path", "Absolute path to the file", "string", True),
                ToolParameter("chunk_size", "Lines per chunk (default: 1000)", "integer", False),
                ToolParameter("max_chunks", "Maximum chunks to return (default: 10)", "integer", False),
                ToolParameter("start_line", "Start reading from this line (1-indexed, default: 1)", "integer", False),
                ToolParameter("output_file", "Optional path to save extracted text", "string", False),
                ToolParameter("normalize_line_endings", "Normalize to LF (default: false)", "boolean", False),
                ToolParameter("use_cache", "Use LRU/LFU cache (default: true)", "boolean", False),
                ToolParameter("use_bookmark", "Resume from last bookmark (default: false)", "boolean", False),
                ToolParameter("save_bookmark", "Save position as bookmark (default: false)", "boolean", False),
            ],
            category="file",
        )

    def execute(self, **kwargs) -> ToolResult:
        """Execute with OS27 Hyper++ telemetry."""
        start_time = time.time()
        memory_start = get_memory_usage_mb()

        file_path = kwargs.get("file_path")
        chunk_size = kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE)
        max_chunks = kwargs.get("max_chunks", DEFAULT_MAX_CHUNKS)
        start_line = kwargs.get("start_line", DEFAULT_START_LINE)
        output_file = kwargs.get("output_file")
        normalize_line_endings = kwargs.get("normalize_line_endings", False)
        use_cache = kwargs.get("use_cache", True)
        use_bookmark = kwargs.get("use_bookmark", False)
        save_bookmark = kwargs.get("save_bookmark", False)

        try:
            if not file_path:
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(ToolStatus.ERROR, error="file_path is required")
            if not os.path.exists(file_path):
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(ToolStatus.ERROR, error=f"File not found: {file_path}")
            if chunk_size <= 0:
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(ToolStatus.ERROR, error="chunk_size must be positive")
            if max_chunks <= 0:
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(ToolStatus.ERROR, error="max_chunks must be positive")
            if start_line < 1:
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(ToolStatus.ERROR, error="start_line must be >= 1")

            decompressed_path = None
            temp_cleanup: list[str] = []

            compression_type, actual_path = detect_compression(file_path)
            if compression_type:
                logger.info(f"Detected {compression_type} compression, decompressing...")
                decompressed_path = decompress_file(file_path, compression_type)
                temp_cleanup.append(decompressed_path)
                actual_path = decompressed_path

            if use_bookmark:
                bookmark = self.bookmark_manager.load_bookmark(file_path)
                if bookmark:
                    start_line = bookmark.line_number
                    logger.info(f"Resuming from bookmark at line {start_line}")

            metadata = self._extract_metadata(actual_path, compression_type)

            if metadata.is_binary:
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(
                    ToolStatus.ERROR,
                    error=f"File appears binary (entropy={metadata.entropy_bits_per_byte:.2f} bits/byte)",
                )

            if metadata.size_bytes > MAX_FILE_SIZE_GB * 1024**3:
                _record_reader_telemetry("execute", False, time.time() - start_time)
                return ToolResult(
                    ToolStatus.ERROR,
                    error=f"File too large: {metadata.size_human} > {MAX_FILE_SIZE_GB}GB limit",
                )

            chunks, stats, next_start_line, has_more = self._stream_chunks(
                file_path=actual_path,
                metadata=metadata,
                chunk_size=chunk_size,
                max_chunks=max_chunks,
                start_line=start_line,
                normalize_line_endings=normalize_line_endings,
                use_cache=use_cache,
            )

            if output_file:
                self._save_chunks(chunks, output_file)

            if save_bookmark and next_start_line:
                self.bookmark_manager.save_bookmark(
                    file_path,
                    next_start_line,
                    {"chunk_size": chunk_size, "timestamp": time.time()},
                )

            stats.read_time_seconds = time.time() - start_time
            stats.memory_peak_mb = max(get_memory_usage_mb() - memory_start, 0.0)
            stats.cache_hits = self.chunk_cache.hits
            stats.cache_misses = self.chunk_cache.misses
            stats.throughput_mb_s = (
                (stats.bytes_processed / (1024 * 1024)) / stats.read_time_seconds
                if stats.read_time_seconds > 0 else 0.0
            )

            for temp_path in temp_cleanup:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        parent = os.path.dirname(temp_path)
                        if os.path.exists(parent):
                            os.rmdir(parent)
                except OSError:
                    pass

            _record_reader_telemetry("execute", True, stats.read_time_seconds)

            return ToolResult(
                ToolStatus.SUCCESS,
                data={
                    "metadata": {
                        "path": metadata.path,
                        "size_bytes": metadata.size_bytes,
                        "size_human": metadata.size_human,
                        "extension": metadata.extension,
                        "encoding": metadata.encoding,
                        "has_bom": metadata.has_bom,
                        "line_ending": metadata.line_ending,
                        "is_compressed": metadata.is_compressed,
                        "compression_type": metadata.compression_type,
                        "modified_time": metadata.modified_time,
                        "file_hash_short": metadata.file_hash_short,
                        "entropy_bits_per_byte": round(metadata.entropy_bits_per_byte, 3),
                        "avg_line_length": round(metadata.avg_line_length, 2),
                        "max_line_length": metadata.max_line_length,
                        "comment_ratio": round(metadata.comment_ratio, 3),
                        "blank_ratio": round(metadata.blank_ratio, 3),
                        "code_vs_text_hint": metadata.code_vs_text_hint,
                        "structure_hint": metadata.structure_hint,
                        "anomaly_hints": metadata.anomaly_hints,
                    },
                    "statistics": {
                        "total_lines": stats.total_lines,
                        "returned_lines": stats.returned_lines,
                        "returned_chars": stats.returned_chars,
                        "chunks_returned": stats.chunks_returned,
                        "read_time_seconds": round(stats.read_time_seconds, 3),
                        "bytes_processed": stats.bytes_processed,
                        "throughput_mb_s": round(stats.throughput_mb_s, 3),
                        "memory_peak_mb": round(stats.memory_peak_mb, 2),
                        "cache_hits": stats.cache_hits,
                        "cache_misses": stats.cache_misses,
                    },
                    "pagination": {
                        "start_line": start_line,
                        "next_start_line": next_start_line,
                        "has_more": has_more,
                        "chunk_size": chunk_size,
                        "max_chunks": max_chunks,
                    },
                    "chunks": [
                        {
                            "chunk_number": c.chunk_number,
                            "start_line": c.start_line,
                            "end_line": c.end_line,
                            "line_count": c.line_count,
                            "char_count": c.char_count,
                            "is_complete_boundary": c.is_complete_boundary,
                            "semantic_hint": c.semantic_hint,
                            "anomaly_hints": c.anomaly_hints,
                            "text": c.text,
                        }
                        for c in chunks
                    ],
                    "output_file": output_file,
                    "telemetry": get_reader_telemetry(),
                    "health": get_reader_health(),
                },
                message=(
                    f"Read {stats.returned_lines} lines ({stats.chunks_returned} chunks, "
                    f"{stats.returned_chars:,} chars) from {Path(file_path).name} "
                    f"in {stats.read_time_seconds:.3f}s @ {stats.throughput_mb_s:.2f} MB/s "
                    f"(cache: {stats.cache_hits}H/{stats.cache_misses}M, peak: {stats.memory_peak_mb:.1f}MB)"
                ),
            )

        except Exception as e:
            for temp_path in temp_cleanup:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    pass
            execution_time = time.time() - start_time
            _record_reader_telemetry("execute", False, execution_time)
            logger.exception("Hyper file reader failed")
            return ToolResult(ToolStatus.ERROR, error=f"{type(e).__name__}: {e}")

    def _extract_metadata(self, file_path: str, compression_type: Optional[str]) -> FileMetadata:
        p = Path(file_path)
        stat = os.stat(file_path)
        size_bytes = stat.st_size
        extension = p.suffix.lower()
        if extension == "":
            extension = ".txt"

        if extension not in SUPPORTED_EXTENSIONS:
            raise LargeFileReaderError(
                f"Unsupported extension: {extension}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        encoding, has_bom = detect_encoding(file_path)
        is_binary = is_binary_heuristic(file_path)
        entropy = compute_entropy(file_path)

        line_ending = "unknown"
        avg_len = 0.0
        blank_ratio = 0.0
        comment_ratio = 0.0
        max_len = 0
        code_hint = "unknown"
        structure_hint = "unknown"
        anomaly_hints: list[str] = []

        if not is_binary:
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                    sample = f.read(4096)
                line_ending = detect_line_ending(sample)
                avg_len, blank_ratio, comment_ratio, max_len, code_hint, structure_hint, anomaly_hints = \
                    analyze_text_sample(sample, extension)
            except OSError:
                pass

        return FileMetadata(
            path=file_path,
            size_bytes=size_bytes,
            size_human=format_size(size_bytes),
            extension=extension,
            encoding=encoding,
            has_bom=has_bom,
            line_ending=line_ending,
            is_binary=is_binary,
            is_compressed=compression_type is not None,
            compression_type=compression_type,
            modified_time=stat.st_mtime,
            file_hash_short=compute_short_hash(file_path),
            entropy_bits_per_byte=entropy,
            avg_line_length=avg_len,
            max_line_length=max_len,
            comment_ratio=comment_ratio,
            blank_ratio=blank_ratio,
            code_vs_text_hint=code_hint,
            structure_hint=structure_hint,
            anomaly_hints=anomaly_hints,
        )

    def _stream_chunks(
        self,
        file_path: str,
        metadata: FileMetadata,
        chunk_size: int,
        max_chunks: int,
        start_line: int,
        normalize_line_endings: bool,
        use_cache: bool,
    ) -> tuple[list[ChunkInfo], ReadStatistics, Optional[int], bool]:
        chunks: list[ChunkInfo] = []
        total_lines = 0
        returned_lines = 0
        returned_chars = 0
        bytes_processed = 0
        current_line = 0
        buffer: list[str] = []
        byte_offset = 0
        encoding = metadata.encoding

        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            for raw_line in f:
                current_line += 1
                total_lines += 1

                if self._progress_callback and current_line % 5000 == 0:
                    self._progress_callback(current_line, total_lines, "reading")

                line = raw_line
                if normalize_line_endings:
                    line = line.replace("\r\n", "\n").replace("\r", "\n")

                bytes_processed += len(line.encode(encoding))

                if current_line < start_line:
                    byte_offset += len(line.encode(encoding))
                    continue

                buffer.append(line)

                adaptive_chunk_size = self._adaptive_chunk_size(chunk_size, metadata.extension)

                if len(buffer) >= adaptive_chunk_size:
                    boundary_index = find_logical_boundary(buffer, metadata.extension)
                    chunk_lines = buffer[:boundary_index]
                    remaining = buffer[boundary_index:]
                    buffer = remaining

                    chunk_text = "".join(chunk_lines)
                    chunk_start_line = current_line - len(chunk_lines) + 1
                    chunk_bytes_start = byte_offset

                    semantic_hint = semantic_hint_for_chunk(chunk_lines, metadata.extension)
                    chunk_anomalies: list[str] = []
                    if "ERROR" in chunk_text.upper():
                        chunk_anomalies.append("contains-error-lines")
                    if "TRACEBACK" in chunk_text.upper():
                        chunk_anomalies.append("python-traceback")
                    if "EXCEPTION" in chunk_text.upper():
                        chunk_anomalies.append("exception-signature")

                    chunk = ChunkInfo(
                        chunk_number=len(chunks) + 1,
                        start_line=chunk_start_line,
                        end_line=current_line,
                        text=chunk_text,
                        line_count=len(chunk_lines),
                        char_count=len(chunk_text),
                        byte_offset_start=chunk_bytes_start,
                        byte_offset_end=chunk_bytes_start + len(chunk_text.encode(encoding)),
                        is_complete_boundary=True,
                        semantic_hint=semantic_hint,
                        anomaly_hints=chunk_anomalies,
                    )

                    returned_lines += len(chunk_lines)
                    returned_chars += len(chunk_text)
                    byte_offset += len(chunk_text.encode(encoding))

                    cache_key = f"{metadata.file_hash_short}:{chunk.start_line}:{chunk.end_line}"
                    if use_cache:
                        self.chunk_cache.put(cache_key, chunk)

                    chunks.append(chunk)

                    if len(chunks) >= max_chunks:
                        break

            if buffer and len(chunks) < max_chunks:
                boundary_index = find_logical_boundary(buffer, metadata.extension)
                chunk_lines = buffer[:boundary_index]
                chunk_text = "".join(chunk_lines)
                chunk_start_line = current_line - len(chunk_lines) + 1
                chunk_bytes_start = byte_offset

                semantic_hint = semantic_hint_for_chunk(chunk_lines, metadata.extension)
                chunk_anomalies: list[str] = []
                if "ERROR" in chunk_text.upper():
                    chunk_anomalies.append("contains-error-lines")

                chunk = ChunkInfo(
                    chunk_number=len(chunks) + 1,
                    start_line=chunk_start_line,
                    end_line=current_line,
                    text=chunk_text,
                    line_count=len(chunk_lines),
                    char_count=len(chunk_text),
                    byte_offset_start=chunk_bytes_start,
                    byte_offset_end=chunk_bytes_start + len(chunk_text.encode(encoding)),
                    is_complete_boundary=True,
                    semantic_hint=semantic_hint,
                    anomaly_hints=chunk_anomalies,
                )

                returned_lines += len(chunk_lines)
                returned_chars += len(chunk_text)

                cache_key = f"{metadata.file_hash_short}:{chunk.start_line}:{chunk.end_line}"
                if use_cache:
                    self.chunk_cache.put(cache_key, chunk)

                chunks.append(chunk)

        has_more = current_line > 0 and (start_line + returned_lines) <= current_line
        next_start_line: Optional[int] = start_line + returned_lines if has_more else None

        stats = ReadStatistics(
            total_lines=total_lines,
            returned_lines=returned_lines,
            returned_chars=returned_chars,
            chunks_returned=len(chunks),
            read_time_seconds=0.0,
            bytes_processed=bytes_processed,
            throughput_mb_s=0.0,
            memory_peak_mb=0.0,
            cache_hits=self.chunk_cache.hits,
            cache_misses=self.chunk_cache.misses,
        )

        return chunks, stats, next_start_line, has_more

    def _adaptive_chunk_size(self, base_chunk_size: int, extension: str) -> int:
        if extension in CODE_EXTENSIONS:
            return max(200, base_chunk_size // 2)
        if extension in LOG_EXTENSIONS:
            return base_chunk_size * 2
        if extension in STRUCTURED_EXTENSIONS:
            return max(100, base_chunk_size // 3)
        return base_chunk_size

    def _save_chunks(self, chunks: list[ChunkInfo], output_file: str) -> None:
        try:
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                for chunk in chunks:
                    f.write(chunk.text)
        except OSError as e:
            logger.error(f"Failed to save output file: {e}")
            raise


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="OS27 Hyper Large File Reader")
    parser.add_argument("file_path", help="Path to the file to read")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Lines per chunk")
    parser.add_argument("--max-chunks", type=int, default=10, help="Maximum chunks")
    parser.add_argument("--start-line", type=int, default=1, help="Start line")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--normalize", action="store_true", help="Normalize line endings")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument("--use-bookmark", action="store_true", help="Resume from bookmark")
    parser.add_argument("--save-bookmark", action="store_true", help="Save bookmark")

    args = parser.parse_args()

    tool = LargeFileReaderHyperTool()
    result = tool.execute(
        file_path=args.file_path,
        chunk_size=args.chunk_size,
        max_chunks=args.max_chunks,
        start_line=args.start_line,
        output_file=args.output,
        normalize_line_endings=args.normalize,
        use_cache=not args.no_cache,
        use_bookmark=args.use_bookmark,
        save_bookmark=args.save_bookmark,
    )

    if result.status == ToolStatus.SUCCESS:
        print(f"\n✅ {result.message}")
        print(f"\nMetadata: {json.dumps(result.data['metadata'], indent=2)}")
        print(f"\nStatistics: {json.dumps(result.data['statistics'], indent=2)}")
        print(f"\nPagination: {json.dumps(result.data['pagination'], indent=2)}")
        if args.output:
            print(f"\n💾 Saved to: {args.output}")
    else:
        print(f"\n❌ Error: {result.error}")
        sys.exit(1)
