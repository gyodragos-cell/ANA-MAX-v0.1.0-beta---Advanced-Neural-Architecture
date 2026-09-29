"""OS-22 agent foundation document status helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_SCHEMA = "ana.os22.agent_foundation.v1"
FOUNDATION_PATH = ROOT / "docs" / "OS22_AGENT_FOUNDATION.md"
FOUNDATION_DOCS = (
    "OS22_AGENT_SELF_INIT.md",
    "OS22_AGENT_BOOT_BANNER.md",
    "OS22_AGENT_CONTRACT.md",
    "OS22_AGENT_TRAINING_LESSONS.md",
    "OS22_AGENT_ADVANCED_TRAINING.md",
    "OS22_AGENT_SANDBOX_SCENARIOS.md",
    "OS22_AGENT_MASTER_CLASS.md",
    "OS22_AGENT_AUTONOMY_V1.md",
    "OS22_AGENT_AUTONOMY_V2.md",
    "OS22_AGENT_AUTONOMY_V3.md",
    "OS22_AGENT_SELF_HEALING_V1.md",
    "OS22_AGENT_SELF_HEALING_V2.md",
    "OS22_AGENT_MEMORY_PRIMER.md",
    "OS22_TOOL_AWARENESS_PACK.md",
    "OS22_REASONING_GRAPH_PRIMER.md",
    "OS22_WORKFLOW_PLAYBOOK.md",
    "OS22_AGENT_OPERATING_PACK.md",
    "OS22_AGENT_FOUNDATION.md",
)


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def load_agent_foundation(path: str | Path | None = None) -> str:
    target = Path(path) if path is not None else FOUNDATION_PATH
    if not target.is_absolute():
        target = ROOT / target
    return target.read_text(encoding="utf-8")


def summarize_agent_foundation(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else FOUNDATION_PATH
    if not target.is_absolute():
        target = ROOT / target
    exists = target.exists()
    content = target.read_text(encoding="utf-8") if exists else ""
    headings = [
        line.strip("# ").strip()
        for line in content.splitlines()
        if line.startswith("## ")
    ]
    return {
        "schema": FOUNDATION_SCHEMA,
        "path": str(target),
        "exists": exists,
        "ascii_safe": _is_ascii_safe(content),
        "line_count": len(content.splitlines()) if exists else 0,
        "heading_count": len(headings),
        "headings": [_ascii_text(item) for item in headings[:16]],
        "preview": _ascii_text(content[:500]),
    }


def get_agent_foundation_status() -> dict[str, Any]:
    docs_dir = ROOT / "docs"
    present = []
    missing = []
    for name in FOUNDATION_DOCS:
        if (docs_dir / name).exists():
            present.append(name)
        else:
            missing.append(name)
    summary = summarize_agent_foundation()
    return {
        "schema": FOUNDATION_SCHEMA,
        "ready": summary["exists"] and summary["ascii_safe"] and not missing,
        "foundation": summary,
        "doc_count": len(FOUNDATION_DOCS),
        "present": present,
        "missing": missing,
        "local_only": True,
        "metadata_only": True,
    }


def _is_ascii_safe(text: str) -> bool:
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True
