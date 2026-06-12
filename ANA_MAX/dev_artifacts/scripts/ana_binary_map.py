"""Minimal static binary/text metadata parser for ANA binary_map tool."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BinaryMapResult:
    format: str
    architecture: str
    size: int
    sha256: str
    strings: list[str]


def _detect_format(data: bytes) -> tuple[str, str]:
    if data.startswith(b"MZ"):
        return "PE", "unknown"
    if data.startswith(b"\x7fELF"):
        arch = "64-bit" if len(data) > 5 and data[4] == 2 else "32-bit"
        return "ELF", arch
    if data.startswith(b"#!"):
        return "script", "text"
    return "text/unknown", "n/a"


def parse_binary(path: str | Path, max_bytes: int = 26_214_400, strings_limit: int = 80) -> BinaryMapResult:
    path = Path(path)
    data = path.read_bytes()[:max(1, int(max_bytes))]
    file_format, architecture = _detect_format(data)
    strings = [
        match.decode("utf-8", errors="ignore")
        for match in re.findall(rb"[\x20-\x7e]{4,}", data)
    ][: max(0, int(strings_limit))]
    return BinaryMapResult(
        format=file_format,
        architecture=architecture,
        size=path.stat().st_size,
        sha256=hashlib.sha256(data).hexdigest(),
        strings=strings,
    )
