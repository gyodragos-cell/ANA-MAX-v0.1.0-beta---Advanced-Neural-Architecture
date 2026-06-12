#!/usr/bin/env python3
"""
Normalize ANA DEV text files for PowerShell-safe, AI-readable output.

Default scope is active workspace text files, including docs, scripts, Python,
JSON, HTML, and env files. The script removes UTF-8 BOMs, maps common
punctuation and Romanian diacritics to ASCII, and can optionally force
remaining non-ASCII characters to ASCII.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".css",
    ".htm",
    ".html",
    ".json",
    ".js",
    ".md",
    ".ps1",
    ".py",
    ".txt",
}
DEFAULT_FILENAMES = {".env"}
DEFAULT_EXCLUDED_NAMES = {
    ".claude_brain",
    ".opencode",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".qoder",
    ".venv",
    "__pycache__",
    "browser_snapshots",
    "dist",
    "logs",
    "memory",
    "node_modules",
    "rem_sleep",
    "sandbox",
    "venv",
    "voice_temp",
}
DEFAULT_EXCLUDED_FRAGMENTS = {
    "ANA_MAX/sandbox/research/agent-zero",
    "ANA_MAX/archives",
    "ANA_MAX/logs",
    "ANA_MAX/memory",
}
DEFAULT_EXCLUDED_PREFIXES = {
    "SESSION_CHECKPOINT_",
    "voice_queue",
}

DIRECT_REPLACEMENTS = {
    "\ufeff": "",
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u2026": "...",
    "\u2713": "[OK]",
    "\u2714": "[OK]",
    "\u274c": "[FAIL]",
    "\u26a0": "[WARN]",
    "\ufe0f": "",
    "\u2500": "-",
    "\u2502": "|",
    "\u250c": "+",
    "\u2510": "+",
    "\u2514": "+",
    "\u2518": "+",
    "\u251c": "+",
    "\u2524": "+",
    "\u252c": "+",
    "\u2534": "+",
    "\u253c": "+",
    "\u0103": "a",
    "\u00e2": "a",
    "\u00ee": "i",
    "\u0219": "s",
    "\u021b": "t",
    "\u0102": "A",
    "\u00c2": "A",
    "\u00ce": "I",
    "\u0218": "S",
    "\u021a": "T",
}

MOJIBAKE_REPLACEMENTS: dict[str, str] = {}


def normalize_text(text: str, ascii_only: bool) -> str:
    for source, target in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(source, target)
    for source, target in DIRECT_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if ascii_only:
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text


def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:4096]


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if any(fragment in rel for fragment in DEFAULT_EXCLUDED_FRAGMENTS):
        return True
    if any(path.name.startswith(prefix) for prefix in DEFAULT_EXCLUDED_PREFIXES):
        return True
    return any(part in DEFAULT_EXCLUDED_NAMES for part in path.relative_to(root).parts)


def iter_targets(root: Path, extensions: set[str], extra_files: list[Path]) -> list[Path]:
    targets: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and (
            path.suffix.lower() in extensions or path.name.lower() in DEFAULT_FILENAMES
        ) and not should_skip(path, root):
            targets.append(path)
    for path in extra_files:
        resolved = path if path.is_absolute() else root / path
        if resolved.exists() and resolved.is_file() and resolved not in targets:
            targets.append(resolved)
    return sorted(targets)


def process_file(path: Path, apply: bool, ascii_only: bool) -> dict[str, object] | None:
    data = path.read_bytes()
    if is_binary(data):
        return None
    original = data.decode("utf-8-sig", errors="replace")
    normalized = normalize_text(original, ascii_only=ascii_only)
    changed = normalized != original or data.startswith(b"\xef\xbb\xbf")
    remaining_non_ascii = sorted({char for char in normalized if ord(char) > 127})
    if apply and changed:
        path.write_text(normalized, encoding="utf-8", newline="\n")
    if changed or remaining_non_ascii:
        return {
            "path": str(path),
            "changed": changed,
            "remaining_non_ascii_count": len(remaining_non_ascii),
            "remaining_non_ascii_sample": "".join(remaining_non_ascii[:20]),
        }
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize ANA DEV docs/scripts for ASCII-safe tooling.")
    parser.add_argument("--root", default=".", help="Workspace root")
    parser.add_argument("--apply", action="store_true", help="Write normalized files")
    parser.add_argument("--ascii-only", action="store_true", default=True, help="Force ASCII-only output")
    parser.add_argument("--keep-unicode", dest="ascii_only", action="store_false", help="Repair BOM/mojibake only")
    parser.add_argument("--extensions", nargs="*", default=sorted(DEFAULT_EXTENSIONS), help="Extensions to scan")
    parser.add_argument("--extra-file", action="append", default=[], help="Additional file to normalize")
    parser.add_argument("--report", default="ANA_MAX/memory/encoding_normalization_report.json", help="JSON report path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    extensions = {ext if ext.startswith(".") else f".{ext}" for ext in args.extensions}
    extra_files = [Path(item) for item in args.extra_file]
    targets = iter_targets(root, extensions, extra_files)
    findings = [item for path in targets if (item := process_file(path, args.apply, args.ascii_only))]
    report = {
        "schema": "ana.encoding_normalization.v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "apply": bool(args.apply),
        "ascii_only": bool(args.ascii_only),
        "extensions": sorted(extensions),
        "target_count": len(targets),
        "finding_count": len(findings),
        "changed_count": sum(1 for item in findings if item.get("changed")),
        "findings": findings,
    }
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("schema", "apply", "target_count", "finding_count", "changed_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
