"""Metadata-only OS-22 self-healing diagnostics."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from ANA_MAX.tools.tool_manifest_loader import get_tool_manifest


ROOT = Path(__file__).resolve().parents[2]
SELF_HEALING_SCHEMA = "ana.os22.agent_self_healing.v2"
SELF_HEALING_TELEMETRY_PATH = ROOT / "ANA_MAX" / "logs" / "self_healing_telemetry.jsonl"


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _log_healing_event(event: Mapping[str, Any]) -> None:
    """Best-effort JSONL telemetry for self-healing events."""
    try:
        SELF_HEALING_TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SELF_HEALING_SCHEMA,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **dict(event),
        }
        with SELF_HEALING_TELEMETRY_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    except Exception:
        pass


def _with_telemetry(result: dict[str, Any]) -> dict[str, Any]:
    _log_healing_event(
        {
            "kind": result.get("kind", "unknown"),
            "success": result.get("success", False),
            "issue_class": result.get("issue_class", "unknown"),
            "severity": result.get("severity", "info"),
            "repair_action": result.get("repair_action", "none"),
        }
    )
    return result


def _tool_contracts() -> dict[str, dict[str, Any]]:
    manifest = get_tool_manifest()
    tools = manifest.get("tools", [])
    if not isinstance(tools, list):
        return {}
    contracts: dict[str, dict[str, Any]] = {}
    for tool in tools:
        if isinstance(tool, dict) and tool.get("name"):
            contracts[str(tool["name"])] = dict(tool)
    return contracts


def _resolve_workspace_path(path_value: Any) -> tuple[bool, str]:
    try:
        candidate = Path(str(path_value or ""))
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        resolved = candidate.resolve()
        workspace = ROOT.resolve()
        return bool(resolved == workspace or workspace in resolved.parents), str(resolved)
    except Exception as exc:
        return False, _ascii_text(exc)


def diagnose_tool_request(tool_name: str, args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Diagnose a proposed tool call without executing it."""
    tool = str(tool_name or "").strip()
    payload = dict(args or {})
    contracts = _tool_contracts()
    available_tools = sorted(contracts)
    issues: list[str] = []

    if tool not in contracts:
        return _with_telemetry({
            "schema": SELF_HEALING_SCHEMA,
            "kind": "tool_diagnostic",
            "success": False,
            "issue_class": "tool_missing",
            "severity": "error",
            "tool": tool,
            "args": payload,
            "available_tools": available_tools,
            "repair_action": "choose_manifest_tool",
            "safe_to_retry": False,
            "next_step": "Run /tools and choose an available tool.",
            "issues": ["tool_not_in_manifest"],
        })

    contract = contracts[tool]
    args_schema = contract.get("args_schema", {})
    explicit_required = contract.get("required_args")
    if isinstance(explicit_required, list):
        required_keys = sorted(str(key) for key in explicit_required)
    else:
        required_keys = sorted(args_schema) if isinstance(args_schema, dict) else []
    missing = [key for key in required_keys if key not in payload or payload.get(key) in {"", None}]
    if missing:
        issues.extend(f"missing:{key}" for key in missing)

    path_keys = [key for key in ("path", "file_path") if key in payload]
    for key in path_keys:
        safe, resolved = _resolve_workspace_path(payload.get(key))
        if not safe:
            issues.append(f"path_outside_workspace:{key}:{resolved}")

    if issues:
        issue_class = "path_outside_workspace" if any(item.startswith("path_outside_workspace") for item in issues) else "tool_args_missing"
        return _with_telemetry({
            "schema": SELF_HEALING_SCHEMA,
            "kind": "tool_diagnostic",
            "success": False,
            "issue_class": issue_class,
            "severity": "error",
            "tool": tool,
            "args": payload,
            "required_args": required_keys,
            "repair_action": "provide_valid_arguments",
            "safe_to_retry": False,
            "next_step": f"Provide required args: {', '.join(missing) if missing else 'workspace-safe path'}.",
            "issues": issues,
        })

    return _with_telemetry({
        "schema": SELF_HEALING_SCHEMA,
        "kind": "tool_diagnostic",
        "success": True,
        "issue_class": "none",
        "severity": "info",
        "tool": tool,
        "args": payload,
        "required_args": required_keys,
        "repair_action": "none",
        "safe_to_retry": True,
        "next_step": "Tool request is structurally valid.",
        "issues": [],
    })


def _score_memory_item(item: Mapping[str, Any]) -> tuple[float, float, float, str]:
    importance = _as_float(item.get("importance"), 0.0)
    score = _as_float(item.get("score"), 0.0)
    updated = _as_float(item.get("updated_at"), _as_float(item.get("created_at"), 0.0))
    content = _ascii_text(item.get("content", ""))
    return (importance, score, updated, content)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def resolve_rag_conflicts(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Rank retrieved RAG items and report possible conflicts deterministically."""
    normalized = [dict(item) for item in items if isinstance(item, Mapping)]
    ranked = sorted(normalized, key=_score_memory_item, reverse=True)
    unique_contents = []
    seen = set()
    for item in ranked:
        content = _ascii_text(item.get("content", "")).strip()
        if content and content not in seen:
            seen.add(content)
            unique_contents.append(content)

    conflict_detected = len(unique_contents) > 1
    selected = ranked[0] if ranked else {}
    return _with_telemetry({
        "schema": SELF_HEALING_SCHEMA,
        "kind": "rag_conflict_resolution",
        "success": True,
        "issue_class": "rag_conflict" if conflict_detected else ("rag_empty" if not ranked else "none"),
        "severity": "warn" if conflict_detected else ("info" if ranked else "warn"),
        "input_count": len(normalized),
        "conflict_detected": conflict_detected,
        "selected": selected,
        "selected_content": _ascii_text(selected.get("content", "")) if selected else "",
        "ranked_memory_ids": [_ascii_text(item.get("memory_id", "")) for item in ranked],
        "repair_action": "use_selected_or_report_uncertainty" if conflict_detected else "none",
        "safe_to_retry": True,
        "next_step": "Use selected local evidence; report uncertainty if the conflict matters." if conflict_detected else "Use available local context.",
    })


def _query_terms(query: str) -> set[str]:
    return {
        token.strip(".,:;!?()[]{}\"'").lower()
        for token in _ascii_text(query).split()
        if len(token.strip(".,:;!?()[]{}\"'")) >= 3
    }


def diagnose_rag_context(
    query: str,
    items: Iterable[Mapping[str, Any]],
    max_context_chars: int = 2000,
) -> dict[str, Any]:
    """Diagnose retrieved RAG context quality without mutating memory."""
    normalized = [dict(item) for item in items if isinstance(item, Mapping)]
    resolution = resolve_rag_conflicts(normalized)
    contents = [_ascii_text(item.get("content", "")).strip() for item in normalized]
    non_empty_contents = [content for content in contents if content]
    total_context = "\n".join(non_empty_contents)
    redundant_count = len(non_empty_contents) - len(set(non_empty_contents))
    terms = _query_terms(query)
    matching_terms = {term for term in terms if term in total_context.lower()}

    issue_class = "none"
    severity = "info"
    repair_action = "none"
    next_step = "Use available local context."
    success = True

    if not non_empty_contents:
        issue_class = "rag_empty"
        severity = "warn"
        repair_action = "fallback_minimal_answer"
        next_step = "Answer minimally or refine the query."
        success = False
    elif len(total_context) > max_context_chars:
        issue_class = "rag_context_too_long"
        severity = "warn"
        repair_action = "compress_context"
        next_step = "Use selected evidence and discard redundant detail."
        success = False
    elif resolution.get("conflict_detected"):
        issue_class = "rag_conflict"
        severity = "warn"
        repair_action = "use_selected_or_report_uncertainty"
        next_step = "Use highest-ranked local evidence and report uncertainty."
        success = False
    elif terms and not matching_terms:
        issue_class = "rag_irrelevant"
        severity = "warn"
        repair_action = "fallback_minimal_answer"
        next_step = "Do not force unrelated RAG context into the answer."
        success = False
    elif redundant_count:
        issue_class = "rag_redundant"
        severity = "warn"
        repair_action = "deduplicate_context"
        next_step = "Use one copy of duplicate evidence."
        success = False

    return _with_telemetry({
        "schema": SELF_HEALING_SCHEMA,
        "kind": "rag_quality_diagnostic",
        "success": success,
        "issue_class": issue_class,
        "severity": severity,
        "query": _ascii_text(query),
        "input_count": len(normalized),
        "context_chars": len(total_context),
        "redundant_count": redundant_count,
        "matching_terms": sorted(matching_terms),
        "selected_content": resolution.get("selected_content", ""),
        "repair_action": repair_action,
        "safe_to_retry": True,
        "next_step": next_step,
        "resolution": resolution,
    })


def classify_text_issue(text: str) -> dict[str, Any]:
    """Classify common agent output issues."""
    payload = str(text or "")
    issue_class = "none"
    severity = "info"
    repair_action = "none"
    next_step = "Output is within simple OS-22 limits."

    if len(payload.split()) > 120:
        issue_class = "reasoning_too_long"
        severity = "warn"
        repair_action = "compress_answer"
        next_step = "Compress answer to the essential result."
    if "TOOL_CALL:" in payload and payload.count("TOOL_CALL:") > 1:
        issue_class = "tool_call_multiple"
        severity = "error"
        repair_action = "emit_one_tool_call"
        next_step = "Emit only one TOOL_CALL per turn."

    return _with_telemetry({
        "schema": SELF_HEALING_SCHEMA,
        "kind": "text_issue_classification",
        "success": issue_class == "none",
        "issue_class": issue_class,
        "severity": severity,
        "repair_action": repair_action,
        "safe_to_retry": issue_class != "tool_call_multiple",
        "next_step": next_step,
        "word_count": len(payload.split()),
    })


def stabilize_reasoning_text(text: str, max_sentences: int = 3, max_words: int = 80) -> dict[str, Any]:
    """Compress unstable reasoning text into a compact OS-22-safe form."""
    payload = _ascii_text(text)
    classification = classify_text_issue(payload)
    words = payload.split()
    sentences = []
    for part in payload.replace("?", ".").replace("!", ".").split("."):
        cleaned = " ".join(part.split())
        if cleaned:
            sentences.append(cleaned)
    clipped_sentences = sentences[: max(1, max_sentences)]
    stabilized = ". ".join(clipped_sentences).strip()
    if not stabilized:
        stabilized = "Insufficient context. Providing a minimal direct answer."
    stabilized_words = stabilized.split()[: max(1, max_words)]
    stabilized = " ".join(stabilized_words)
    if stabilized and not stabilized.endswith("."):
        stabilized += "."

    too_long = len(words) > max_words or len(sentences) > max_sentences
    issue_class = classification.get("issue_class", "none")
    if issue_class == "none" and too_long:
        issue_class = "reasoning_too_long"

    success = issue_class == "none"
    return _with_telemetry({
        "schema": SELF_HEALING_SCHEMA,
        "kind": "reasoning_stabilization",
        "success": success,
        "issue_class": issue_class,
        "severity": "info" if success else "warn",
        "original_word_count": len(words),
        "stabilized_word_count": len(stabilized.split()),
        "stabilized_text": stabilized,
        "repair_action": "none" if success else "compress_answer",
        "safe_to_retry": True,
        "next_step": "Use stabilized text as the final concise answer.",
        "classification": classification,
    })


def preflight_diagnostics(
    tool_name: str | None = None,
    args: Mapping[str, Any] | None = None,
    rag_items: Iterable[Mapping[str, Any]] | None = None,
    text: str = "",
    query: str = "",
) -> dict[str, Any]:
    """Run preventive metadata diagnostics before a tool or reasoning turn."""
    diagnostics: list[dict[str, Any]] = []
    if tool_name:
        diagnostics.append(diagnose_tool_request(tool_name, args or {}))
    if rag_items is not None:
        diagnostics.append(diagnose_rag_context(query or text or tool_name or "", rag_items))
    if text:
        diagnostics.append(classify_text_issue(text))

    issue_count = sum(1 for item in diagnostics if item.get("issue_class") not in {"none", ""})
    success = issue_count == 0
    return _with_telemetry({
        "schema": SELF_HEALING_SCHEMA,
        "kind": "preflight_diagnostics",
        "success": success,
        "issue_class": "none" if success else "preflight_issues",
        "severity": "info" if success else "warn",
        "diagnostics": diagnostics,
        "issue_count": issue_count,
        "repair_action": "none" if success else "apply_individual_repairs",
        "safe_to_retry": all(item.get("safe_to_retry", False) for item in diagnostics) if diagnostics else True,
        "next_step": "Proceed." if success else "Resolve or follow each diagnostic next_step before execution.",
    })


def get_self_healing_status() -> dict[str, Any]:
    return {
        "schema": SELF_HEALING_SCHEMA,
        "ready": True,
        "metadata_only": True,
        "local_only": True,
        "capabilities": [
            "diagnose_tool_request",
            "resolve_rag_conflicts",
            "classify_text_issue",
            "diagnose_rag_context",
            "stabilize_reasoning_text",
            "preflight_diagnostics",
        ],
        "telemetry_path": str(SELF_HEALING_TELEMETRY_PATH),
        "blocked_actions": [
            "create_tools",
            "edit_manifest",
            "edit_architecture",
            "external_paths",
            "internet_access",
        ],
    }


def parse_json_args(raw_args: str) -> dict[str, Any]:
    text = str(raw_args or "").strip()
    if not text:
        return {}
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("diagnostic arguments must be a JSON object")
    return payload
