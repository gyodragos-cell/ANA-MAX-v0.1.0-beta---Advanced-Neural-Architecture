"""
ANA MAX - Large File Reader Tool
================================
Tool pentru citirea fisierelor mari (10k+ linii) fara OCR.
Pentru fisiere text/cod, citim direct si impartim in chunks.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class LargeFileReaderTool(Tool):
    """
    Tool pentru citirea fisierelor mari fara OCR.
    Pentru fisiere text/cod, citim direct si impartim in chunks.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="large_file_reader",
            description="Read large text/code files (10k+ lines) by splitting into chunks. Supports .py, .json, .md, .yaml, .txt, .js, .ts, .html, .css, .xml, .cfg, .ini, .log, .csv. Much faster than OCR for text files.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    description="Path to the large text/code file to read",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="start_line",
                    description="1-based line where reading starts (default: 1)",
                    type="integer",
                    required=False,
                    default=1
                ),
                ToolParameter(
                    name="chunk_size",
                    description="Number of lines per chunk (default: 1000)",
                    type="integer",
                    required=False,
                    default=1000
                ),
                ToolParameter(
                    name="max_chunks",
                    description="Maximum number of chunks to return (default: 10)",
                    type="integer",
                    required=False,
                    default=10
                ),
                ToolParameter(
                    name="output_file",
                    description="Optional path to save extracted text",
                    type="string",
                    required=False
                )
            ],
            category="file"
        )

    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        output_file = kwargs.get("output_file")

        if not file_path:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="file_path is required"
            )

        try:
            start_line = max(1, int(kwargs.get("start_line", 1)))
            chunk_size = max(1, int(kwargs.get("chunk_size", 1000)))
            max_chunks = max(1, int(kwargs.get("max_chunks", 10)))
        except (TypeError, ValueError):
            return ToolResult(
                status=ToolStatus.ERROR,
                error="start_line, chunk_size and max_chunks must be integers"
            )

        # Verificam daca fisierul exista
        if not os.path.exists(file_path):
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"File not found: {file_path}"
            )

        try:
            # Determinam tipul fisierului
            file_ext = Path(file_path).suffix.lower()
            
            # Formate text/cod suportate
            text_extensions = {".py", ".json", ".md", ".tt", ".yaml", ".yml", ".txt", ".js", ".ts", ".html", ".css", ".xml", ".cfg", ".ini", ".log", ".csv"}
            
            if file_ext not in text_extensions:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unsupported file extension: {file_ext}. Supported: {', '.join(text_extensions)}"
                )
            
            # Citim fisierul
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            num_lines = len(lines)
            logger.info(f"Reading {num_lines} lines from {file_path}")
            
            # Impartim in chunks incepand de la linia ceruta. Acest lucru
            # permite citirea tintita a unui fisier mare fara a trimite tot
            # continutul catre agent si fara risipa de tokeni.
            start_index = min(start_line - 1, num_lines)
            stop_index = min(num_lines, start_index + chunk_size * max_chunks)
            chunks = []
            for i in range(start_index, stop_index, chunk_size):
                chunk_lines = lines[i:min(i + chunk_size, stop_index)]
                chunk_text = ''.join(chunk_lines)
                chunks.append({
                    "chunk_number": len(chunks) + 1,
                    "start_line": i + 1,
                    "end_line": min(i + len(chunk_lines), num_lines),
                    "text": chunk_text,
                    "line_count": len(chunk_lines)
                })
            
            # Calculam statistici si cursorul pentru apelul urmator.
            total_chars = sum(len(chunk["text"]) for chunk in chunks)
            total_lines = sum(chunk["line_count"] for chunk in chunks)
            next_start_line = stop_index + 1 if stop_index < num_lines else None
            
            # Salvam in fisier daca e specificat
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for chunk in chunks:
                        f.write(chunk["text"])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "file_path": file_path,
                    "total_lines": num_lines,
                    "start_line_requested": start_line,
                    "lines_returned": total_lines,
                    "chunks_returned": len(chunks),
                    "total_chars_returned": total_chars,
                    "chunk_size": chunk_size,
                    "max_chunks": max_chunks,
                    "next_start_line": next_start_line,
                    "has_more": next_start_line is not None,
                    "chunks": chunks,
                    "output_file": output_file
                },
                message=(
                    f"Read {total_lines}/{num_lines} lines from line {start_line} "
                    f"({len(chunks)} chunks, {total_chars} chars)"
                )
            )

        except Exception as e:
            logger.exception("Large file reading failed")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to read file: {e}"
            )
