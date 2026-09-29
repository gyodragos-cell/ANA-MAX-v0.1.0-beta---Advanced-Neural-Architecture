"""OS-21.5 local brain agent metadata helper.

This agent can optionally use LocalLLMBackend, but defaults to deterministic
metadata-only output so OS-21.5 behavior stays stable without a local model.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.local.local_llm_backend import LocalLLMBackend
from ANA_MAX.local.prompt_engine import compose_system_prompt, get_tool_specs
from ANA_MAX.local.prompt_profiles import get_system_prompt, normalize_profile_name
from ANA_MAX.local.rag_prompt_policy import should_use_rag_for_prompt
from ANA_MAX.local.chat_response_coach import coach_chat_response
from ANA_MAX.local.tool_dispatcher import execute_tool, parse_tool_call
from ANA_MAX.local.tool_prompt_policy import get_tool_specs_for_prompt


LOCAL_BRAIN_SCHEMA = "ana.os21.local_brain_agent.v1"
AGENT_NAME = "local_brain_agent_v1"


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _stable_keys(value: Mapping[str, Any]) -> list[str]:
    return sorted(str(key) for key in value.keys())


def _ascii_text(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def _is_identity_prompt(prompt: str) -> bool:
    lowered = _ascii_text(prompt).lower()
    identity_terms = (
        "cine esti",
        "cum te cheama",
        "cum te numesti",
        "te numesti",
        "te cheama",
        "who are you",
        "your name",
        "what are you",
    )
    return any(term in lowered for term in identity_terms)


def _identity_answer(profile: str) -> str:
    if profile == "codex":
        return "Sunt ANA_MAX CODEX, inginerul local pentru stack-ul ANA_MAX OS-22."
    if profile == "ana_chat":
        return "Sunt ANA_MAX CHAT, agentul tau local OS-22 cu RAG, ToolBridge si tooluri de laborator."
    return "Sunt ANA_MAX OS-22 CORE, agentul local Phi-3 pentru RAG, ToolBridge si executie determinista."


def _looks_like_pseudo_tool_output(text: str) -> bool:
    candidate = _ascii_text(text).strip()
    return (
        candidate.startswith("ANA_MAX:") and "(" in candidate and ")" in candidate
    ) or (
        candidate.startswith("ANA_MAX.") and "(" in candidate and ")" in candidate
    )


def _strip_output_artifacts(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines:
        marker = lines[-1].strip()
        if marker and set(marker) <= {"-", "_", "="}:
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


def _repair_ascii_question_artifacts(text: str) -> str:
    candidate = str(text or "")
    replacements = {
        "informa?ii": "informatii",
        "func?ii": "functii",
        "ac?i": "acti",
        "conversa?": "conversat",
        "execu?": "execut",
        "semnifica?": "semnificat",
        "utilizeaz?": "utilizeaza",
        "folose?": "foloses",
        "arat?": "arata",
        "aceast?": "aceasta",
        "rom?n?": "romana",
        "rom?n": "roman",
        " ?i ": " si ",
        "?n": "in",
        "s? ": "sa ",
        "s?-": "sa ",
        "a-?i": "a-ti",
        "?i ": "si ",
    }
    for broken, fixed in replacements.items():
        candidate = candidate.replace(broken, fixed)
    words: list[str] = []
    for word in candidate.split(" "):
        if word.endswith("?"):
            word = word[:-1] + "a"
        word = word.replace("?", "")
        words.append(word)
    return " ".join(words)


class LocalBrainAgent:
    """Build optional local-brain reasoning metadata."""

    def __init__(
        self,
        backend: LocalLLMBackend | None = None,
        *,
        enable_inference: bool = False,
        prompt_profile: str | None = None,
        rag_bridge: Any | None = None,
        use_rag: bool = True,
        tool_aware: bool = True,
        max_response_tokens: int = 256,
        generation_temperature: float = 0.0,
    ) -> None:
        self.backend = backend or LocalLLMBackend()
        self.enable_inference = bool(enable_inference)
        self.prompt_profile = normalize_profile_name(prompt_profile)
        self.rag_bridge = rag_bridge
        self.use_rag = bool(use_rag)
        self.tool_aware = bool(tool_aware)
        self.max_response_tokens = max(16, int(max_response_tokens or 256))
        self.generation_temperature = float(generation_temperature or 0.0)
        self._last_capsule: dict[str, Any] | None = None

    def _input_summary(self, input_metadata: Mapping[str, Any]) -> dict[str, Any]:
        keys = _stable_keys(input_metadata)
        return {
            "key_count": len(keys),
            "keys": keys,
            "has_pipeline": "pipeline" in input_metadata or "phases" in input_metadata,
            "has_capsules": "capsules" in input_metadata or "capsule" in input_metadata,
            "has_graph": "graph" in input_metadata or "reasoning_graph" in input_metadata,
        }

    def _fallback_reasoning(self, input_metadata: Mapping[str, Any]) -> dict[str, Any]:
        summary = self._input_summary(input_metadata)
        focus = "general"
        if summary["has_pipeline"]:
            focus = "pipeline"
        elif summary["has_capsules"]:
            focus = "capsules"
        elif summary["has_graph"]:
            focus = "reasoning_graph"
        return {
            "used_llm": False,
            "focus": focus,
            "hypotheses": [
                "Keep the local brain optional and capability-checked.",
                "Prefer deterministic metadata when no local model is loaded.",
            ],
            "plan_candidates": [
                "Collect compact context metadata.",
                "Build review-only reasoning hints.",
                "Defer execution to explicit future runtime gates.",
            ],
            "reflection": "Fallback metadata generated without model inference.",
        }

    def _tool_prompt_block(self, user_prompt: str = "") -> str:
        if not self.tool_aware:
            return ""
        if user_prompt:
            return get_tool_specs_for_prompt(user_prompt)
        return get_tool_specs()

    def _resolve_rag_bridge(self) -> Any | None:
        if not self.use_rag:
            return None
        if self.rag_bridge is not None:
            return self.rag_bridge
        try:
            from ANA_MAX.local.rag_bridge import get_rag_bridge

            self.rag_bridge = get_rag_bridge()
        except Exception:
            self.rag_bridge = None
        return self.rag_bridge

    def _rag_query(self, input_metadata: Mapping[str, Any], user_prompt: str | None = None) -> str:
        candidates = [
            user_prompt,
            input_metadata.get("user_prompt"),
            input_metadata.get("prompt"),
            input_metadata.get("query"),
            input_metadata.get("text"),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        summary = self._input_summary(input_metadata)
        keys = summary.get("keys", [])
        if isinstance(keys, list) and keys:
            return " ".join(str(key) for key in keys[:8])
        return "local brain reasoning"

    def build_reasoning_capsule(
        self,
        input_metadata: Mapping[str, Any] | None = None,
        user_prompt: str | None = None,
    ) -> dict[str, Any]:
        metadata = _mapping(input_metadata)
        backend_info = self.backend.get_backend_info()
        summary = self._input_summary(metadata)
        rag_bridge = self._resolve_rag_bridge()
        rag_query = self._rag_query(metadata, user_prompt)
        rag_context = ""
        rag_results_count = 0
        if self.use_rag and rag_bridge is not None and rag_query:
            try:
                retrieval = None
                if hasattr(rag_bridge, "retrieve"):
                    retrieval = rag_bridge.retrieve(
                        rag_query,
                        top_k=5,
                        memory_type=None,
                        tags=None,
                        min_importance=0.0,
                    )
                if hasattr(rag_bridge, "build_context"):
                    rag_context = _ascii_text(
                        rag_bridge.build_context(
                            rag_query,
                            top_k=5,
                            memory_type=None,
                            tags=None,
                            min_importance=0.0,
                        )
                    )
                elif isinstance(retrieval, Mapping):
                    results = retrieval.get("results")
                    if isinstance(results, list):
                        lines: list[str] = []
                        for index, item in enumerate(results, start=1):
                            if isinstance(item, Mapping):
                                lines.append(f"[{index}] {_ascii_text(item.get('content', ''))}")
                        rag_context = "\n".join(lines)
                        rag_results_count = len(lines)
                if isinstance(retrieval, Mapping):
                    maybe_count = retrieval.get("count")
                    if isinstance(maybe_count, int):
                        rag_results_count = maybe_count
            except Exception as exc:
                rag_context = ""
                rag_results_count = 0
                metadata.setdefault("rag_error", _ascii_text(exc))

        prompt_preview = compose_system_prompt(
            get_system_prompt(self.prompt_profile),
            tool_specs=self._tool_prompt_block(),
            rag_context=rag_context if self.use_rag else "",
        )
        llm_result: dict[str, Any] = {
            "success": False,
            "used_llm": False,
            "text": "",
            "error": "inference_disabled",
            "model_name": backend_info.get("model_name", ""),
        }
        if self.enable_inference and self.backend.is_available():
            prompt = json.dumps(
                {
                    "task": "produce_compact_reasoning_capsule",
                    "input_summary": summary,
                    "user_prompt": _ascii_text(user_prompt or ""),
                    "rag_query": rag_query,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
            llm_result = self.backend.infer_with_rag(
                prompt,
                system_prompt=get_system_prompt(self.prompt_profile),
                rag_query=rag_query,
                rag_context=rag_context if self.use_rag else "",
                rag_bridge=rag_bridge,
                tools_spec=self._tool_prompt_block(),
                max_tokens=self.max_response_tokens,
                temperature=self.generation_temperature,
            )

        fallback = self._fallback_reasoning(metadata)
        capsule = {
            "schema": LOCAL_BRAIN_SCHEMA,
            "agent_name": AGENT_NAME,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "no_tool_execution": True,
            "enable_inference": self.enable_inference,
            "input_summary": summary,
            "backend": backend_info,
            "rag": {
                "enabled": self.use_rag,
                "available": rag_bridge is not None,
                "query": rag_query,
                "results_count": rag_results_count,
                "context": rag_context,
            },
            "tool_awareness": {
                "enabled": self.tool_aware,
                "tools_spec": self._tool_prompt_block(),
                "prompt_preview": prompt_preview,
            },
            "reasoning_capsule": {
                "schema": "ana.os21.local_reasoning_capsule.v1",
                "capsule_type": "local_brain_reasoning",
                "used_llm": bool(llm_result.get("used_llm")),
                "model_name": str(llm_result.get("model_name", "")),
                "text": str(llm_result.get("text", "")),
                "fallback": fallback,
                "error": str(llm_result.get("error", "")),
            },
            "reasoning_graph_hints": {
                "nodes": [
                    f"agent:{AGENT_NAME}",
                    "tool:local_llm_backend",
                    "capsule_hint:local_brain_reasoning",
                ],
                "edges": [
                    {
                        "source": f"agent:{AGENT_NAME}",
                        "target": "tool:local_llm_backend",
                        "relation": "optionally_uses",
                    },
                    {
                        "source": f"agent:{AGENT_NAME}",
                        "target": "capsule_hint:local_brain_reasoning",
                        "relation": "emits",
                    },
                ],
            },
        }
        self._last_capsule = capsule
        return capsule

    def propose_plan(self, input_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        capsule = self.build_reasoning_capsule(input_metadata)
        fallback = capsule["reasoning_capsule"]["fallback"]
        return {
            "schema": "ana.os21.local_brain_plan.v1",
            "agent_name": AGENT_NAME,
            "metadata_only": True,
            "local_only": True,
            "used_llm": capsule["reasoning_capsule"]["used_llm"],
            "steps": list(fallback["plan_candidates"]),
            "source_capsule_schema": capsule["reasoning_capsule"]["schema"],
        }

    def reflect_on_outputs(self, output_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        metadata = _mapping(output_metadata)
        summary = self._input_summary(metadata)
        return {
            "schema": "ana.os21.local_brain_reflection.v1",
            "agent_name": AGENT_NAME,
            "metadata_only": True,
            "local_only": True,
            "used_llm": False,
            "confidence": 0.75 if summary["key_count"] else 0.5,
            "notes": [
                "Reflection is deterministic unless inference is explicitly enabled.",
                "No tool execution or pipeline mutation was performed.",
            ],
            "input_summary": summary,
        }

    def summarize_agent(self) -> dict[str, Any]:
        backend_info = self.backend.get_backend_info()
        return {
            "schema": LOCAL_BRAIN_SCHEMA,
            "agent_name": AGENT_NAME,
            "metadata_only": True,
            "local_only": True,
            "enable_inference": self.enable_inference,
            "prompt_profile": self.prompt_profile,
            "rag_enabled": self.use_rag,
            "tool_aware": self.tool_aware,
            "max_response_tokens": self.max_response_tokens,
            "generation_temperature": self.generation_temperature,
            "backend_available": bool(backend_info.get("available")),
            "backend_loaded": bool(backend_info.get("loaded")),
            "last_capsule_present": self._last_capsule is not None,
        }

    def _extract_llm_text(self, result: Any) -> str:
        if isinstance(result, Mapping):
            text = result.get("text")
            if isinstance(text, str):
                return self._normalize_final_text(text)
            return self._normalize_final_text(_ascii_text(text))
        return self._normalize_final_text(_ascii_text(result))

    def _normalize_final_text(self, text: str) -> str:
        candidate = _strip_output_artifacts(str(text or ""))
        candidate = _repair_ascii_question_artifacts(candidate)
        if not candidate:
            return ""
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
            except Exception:
                return candidate
            if isinstance(parsed, Mapping):
                for key in ("answer", "text", "response", "output", "content"):
                    value = parsed.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            elif isinstance(parsed, str) and parsed.strip():
                return parsed.strip()
        return candidate

    def _build_turn_prompt(self, user_prompt: str, conversation_context: str = "") -> str:
        clean_prompt = _ascii_text(user_prompt)
        clean_context = _ascii_text(conversation_context).strip()
        language_guard = ""
        if self.prompt_profile == "ana_chat":
            language_guard = (
                "Reguli pentru acest raspuns:\n"
                "- Raspunde doar in romana ASCII.\n"
                "- Nu folosi engleza sau alta limba, chiar daca utilizatorul cere asta.\n"
                "- Nu explica regula de limba.\n"
                "- Raspunde scurt, natural si clar.\n\n"
            )
        if not clean_context:
            return f"{language_guard}Mesaj utilizator:\n{clean_prompt}\n\nRaspuns:"
        return (
            language_guard
            +
            f"{clean_context}\n\n"
            "Mesaj utilizator curent:\n"
            f"{clean_prompt}\n\n"
            "Raspunde la mesajul curent natural. Pastreaza continuitatea conversatiei. "
            "Foloseste un tool doar cand mesajul curent cere o actiune locala concreta sau date locale precise."
        )

    def _coach_final_chat_response(self, user_prompt: str, response: str) -> str:
        if self.prompt_profile != "ana_chat":
            return response
        coached = coach_chat_response(user_prompt, response)
        return str(coached.get("text", response))

    def _extract_tool_call_text(self, text: str) -> str | None:
        for line in str(text or "").splitlines():
            if "TOOL_CALL:" not in line:
                continue
            return line[line.index("TOOL_CALL:") :].strip()
        return None

    def _build_followup_prompt(
        self,
        original_prompt: str,
        tool_name: str,
        tool_args: Mapping[str, Any],
        tool_result: str,
    ) -> str:
        tool_call_text = json.dumps(
            {
                "tool_name": _ascii_text(tool_name),
                "args": dict(tool_args or {}),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        return (
            "Original user prompt:\n"
            f"{_ascii_text(original_prompt)}\n\n"
            "Executed tool call:\n"
            f"{tool_call_text}\n\n"
            "Tool result:\n"
            f"{tool_result}\n\n"
            "Instructions:\n"
            "- Use the tool result and any available RAG context to answer the original user prompt.\n"
            "- Return a final answer only.\n"
            "- Do not emit TOOL_CALL unless another distinct tool is still required.\n"
            "- Keep the answer concise, factual, and deterministic.\n"
            "- Do not include labels like Question, Emission, or tool planning text."
        )

    def _build_pseudo_output_repair_prompt(self, original_prompt: str, invalid_output: str) -> str:
        return (
            "Original user prompt:\n"
            f"{_ascii_text(original_prompt)}\n\n"
            "Invalid previous output:\n"
            f"{_ascii_text(invalid_output)}\n\n"
            "Repair instructions:\n"
            "- The previous output was a pseudo-call, not a valid answer.\n"
            "- Do not use ANA_MAX: function(...) syntax.\n"
            "- If no exact TOOL_CALL from the manifest is required, answer in normal language.\n"
            "- Return a final answer only, concise and factual."
        )

    def _build_invalid_tool_call_repair_prompt(
        self,
        original_prompt: str,
        invalid_output: str,
        error_text: str,
    ) -> str:
        return (
            "Original user prompt:\n"
            f"{_ascii_text(original_prompt)}\n\n"
            "Invalid TOOL_CALL output:\n"
            f"{_ascii_text(invalid_output)}\n\n"
            "Parser error:\n"
            f"{_ascii_text(error_text)}\n\n"
            "Repair instructions:\n"
            "- If no exact tool is required, answer the original prompt in normal language.\n"
            "- If a tool is required, emit exactly: TOOL_CALL: <tool_name> <json_arguments>\n"
            "- Do not output pseudo-calls, labels, or planning text.\n"
            "- Return one final response only."
        )

    def _handle_llm_output(
        self,
        text: str,
        *,
        original_prompt: str = "",
        max_rounds: int = 3,
        use_rag_for_turn: bool = True,
    ) -> str:
        current_text = _ascii_text(text)
        rag_bridge = self._resolve_rag_bridge() if use_rag_for_turn else None
        last_invalid_tool_error = ""
        for _ in range(max_rounds):
            if _looks_like_pseudo_tool_output(current_text):
                repair_prompt = self._build_pseudo_output_repair_prompt(original_prompt, current_text)
                repair_result = self.backend.infer_with_rag(
                    repair_prompt,
                    system_prompt=get_system_prompt(self.prompt_profile),
                    rag_query=self._rag_query({}, original_prompt or repair_prompt),
                    rag_context="",
                    rag_bridge=rag_bridge,
                    tools_spec=self._tool_prompt_block(original_prompt),
                    max_tokens=160,
                    temperature=0.0,
                )
                current_text = self._extract_llm_text(repair_result)
                continue
            tool_call_text = self._extract_tool_call_text(current_text)
            if not tool_call_text:
                return current_text
            try:
                tool_name, args = parse_tool_call(tool_call_text)
            except Exception as exc:
                if _is_identity_prompt(original_prompt):
                    return _identity_answer(self.prompt_profile)
                last_invalid_tool_error = _ascii_text(exc)
                repair_prompt = self._build_invalid_tool_call_repair_prompt(
                    original_prompt,
                    current_text,
                    str(exc),
                )
                repair_result = self.backend.infer_with_rag(
                    repair_prompt,
                    system_prompt=get_system_prompt(self.prompt_profile),
                    rag_query=self._rag_query({}, original_prompt or repair_prompt),
                    rag_context="",
                    rag_bridge=rag_bridge,
                    tools_spec=self._tool_prompt_block(original_prompt),
                    max_tokens=160,
                    temperature=0.0,
                )
                current_text = self._extract_llm_text(repair_result)
                continue
            tool_result = execute_tool(tool_name, args)
            if "[tool_dispatcher] unknown tool:" in tool_result:
                if _is_identity_prompt(original_prompt):
                    return _identity_answer(self.prompt_profile)
                return tool_result
            followup = self._build_followup_prompt(original_prompt, tool_name, args, tool_result)
            followup_result = self.backend.infer_with_rag(
                followup,
                system_prompt=get_system_prompt(self.prompt_profile),
                rag_query=self._rag_query({}, original_prompt or followup),
                rag_context="",
                rag_bridge=rag_bridge,
                tools_spec=self._tool_prompt_block(original_prompt),
                max_tokens=128,
                temperature=0.0,
            )
            current_text = self._extract_llm_text(followup_result)
        if _looks_like_pseudo_tool_output(current_text):
            return (
                "Nu am raspuns corect: am generat o pseudo-comanda in loc de raspuns. "
                "Reincercati natural sau folositi un tool explicit."
            )
        if self._extract_tool_call_text(current_text):
            error = last_invalid_tool_error or "Could not repair invalid tool call."
            return f"Invalid tool call. {error}"
        return current_text

    def run_turn(self, user_prompt: str, *, conversation_context: str = "") -> str:
        if _is_identity_prompt(user_prompt):
            return _identity_answer(self.prompt_profile)
        use_rag_for_turn = should_use_rag_for_prompt(user_prompt)
        rag_bridge = self._resolve_rag_bridge() if use_rag_for_turn else None
        turn_prompt = self._build_turn_prompt(user_prompt, conversation_context)
        initial_result = self.backend.infer_with_rag(
            turn_prompt,
            system_prompt=get_system_prompt(self.prompt_profile),
            rag_query=self._rag_query({}, user_prompt) if use_rag_for_turn else "",
            rag_context="",
            rag_bridge=rag_bridge,
            tools_spec=self._tool_prompt_block(user_prompt),
            max_tokens=self.max_response_tokens,
            temperature=self.generation_temperature,
        )
        final_text = self._handle_llm_output(
            self._extract_llm_text(initial_result),
            original_prompt=user_prompt,
            use_rag_for_turn=use_rag_for_turn,
        )
        return self._coach_final_chat_response(user_prompt, final_text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local brain agent metadata.")
    parser.add_argument("--summary", action="store_true", help="Print compact agent summary")
    args = parser.parse_args(argv)
    agent = LocalBrainAgent()
    payload = agent.summarize_agent() if args.summary else agent.build_reasoning_capsule({})
    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
