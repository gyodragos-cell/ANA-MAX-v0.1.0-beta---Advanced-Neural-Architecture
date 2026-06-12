"""Start ANA MAX local LLM in smoke or interactive mode."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents import LocalBrainAgent
from ANA_MAX.local.agent_boot_banner import build_agent_boot_banner
from ANA_MAX.local.agent_foundation import get_agent_foundation_status
from ANA_MAX.local.agent_self_healing import (
    diagnose_rag_context,
    diagnose_tool_request,
    get_self_healing_status,
    stabilize_reasoning_text,
)
from ANA_MAX.local.local_llm_backend import LocalLLMBackend
from ANA_MAX.local.os22_doctor import run_os22_doctor
from ANA_MAX.local.os22_boot import OS22BootSequence
from ANA_MAX.local.conversation_context import ConversationMemory
from ANA_MAX.local.operator_intent_router import route_operator_intent
from ANA_MAX.local.prompt_profiles import available_prompt_profiles, get_system_prompt, normalize_profile_name
from ANA_MAX.local.rag_bridge import get_rag_bridge
from ANA_MAX.local.tool_dispatcher import execute_tool
from ANA_MAX.tools.tool_manifest_loader import load_tool_manifest


CHAT_LOG_PATH = Path(__file__).resolve().parents[2] / "ANA_MAX" / "logs" / "os22_chat.log"


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))


def _ascii_text(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def _log_chat_event(event: str, payload: dict[str, Any]) -> None:
    try:
        CHAT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": _ascii_text(event),
            "payload": payload,
        }
        with CHAT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    except Exception:
        pass


def _system_prompt_text(profile: str, system_prompt_file: str) -> str:
    if system_prompt_file:
        path = Path(system_prompt_file).expanduser()
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return get_system_prompt(profile)


def _run_prompt(
    backend: LocalLLMBackend,
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> dict:
    return backend.infer(prompt, system_prompt=system_prompt, max_tokens=max_tokens, temperature=temperature)


def _backend_config(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {
        "backend": args.backend,
        "model_name": args.model_name,
        "fallback_model_name": args.fallback_model_name,
        "model_path": args.model_path,
        "n_ctx": args.n_ctx,
        "n_threads": args.n_threads,
        "n_gpu_layers": args.n_gpu_layers,
        "max_output_tokens": args.max_tokens,
        "use_rag": not args.no_rag,
    }
    return {key: value for key, value in config.items() if value not in {"", None}}


def _print_interactive_help() -> None:
    print("Commands: /help, /status, /boot, /doctor, /foundation, /heal, /ragheal, /stabilize, /tools, /time, /log, /tool, /open, /rag, /exit")
    print("  /time")
    print("  /log")
    print("  /tool <tool_name> [json_args]")
    print("  /open <url>")
    print("  /rag <query>")
    print("  /heal <tool_name> [json_args]")
    print("  /ragheal <query>")
    print("  /stabilize <text>")
    print("  /doctor")
    print("  /foundation")
    print("Any other input is sent to ANA OS-22 Agent through RAG + ToolBridge.")


def _print_tool_manifest() -> None:
    manifest = load_tool_manifest()
    tools = manifest.get("tools", [])
    print(f"Tool manifest: {manifest.get('schema', '')} ({len(tools)} tools)")
    for item in tools:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        category = item.get("category", "")
        description = item.get("description", "")
        print(f"- {name} [{category}] - {description}")


def _run_agent_prompt(agent: LocalBrainAgent, prompt: str, conversation_context: str = "") -> dict[str, Any]:
    try:
        _log_chat_event("prompt", {"text": _ascii_text(prompt)})
        try:
            text = agent.run_turn(prompt, conversation_context=conversation_context)
        except TypeError:
            text = agent.run_turn(prompt)
        if not str(text or "").strip():
            text = "No response generated. Try /doctor or ask a more specific question."
        _log_chat_event("response", {"success": True, "text": _ascii_text(text)})
        return {
            "schema": "ana.local_llm.agent_turn.v1",
            "success": True,
            "text": text,
            "error": "",
        }
    except Exception as exc:
        return {
            "schema": "ana.local_llm.agent_turn.v1",
            "success": False,
            "text": f"Agent error: {_ascii_text(exc)}",
            "error": _ascii_text(exc),
        }


def _looks_like_time_question(prompt: str) -> bool:
    text = _ascii_text(prompt).lower()
    has_time_word = any(
        token in text
        for token in (
            "ce zi",
            "ce data",
            "data este",
            "zi este",
            "ora",
            "date today",
            "what date",
            "what day",
            "current_time",
        )
    )
    return has_time_word and not any(token in text for token in ("fisier", "file", "read_file", "write_file"))


def _format_current_time_answer() -> str:
    raw = _run_tool_command("current_time")
    try:
        payload = json.loads(str(raw.get("result") or "{}"))
    except json.JSONDecodeError:
        payload = {}
    date = payload.get("date", "")
    weekday = payload.get("weekday", "")
    time_text = payload.get("time", "")
    if date:
        return f"Azi este {date}. Ziua este {weekday}. Ora locala este {time_text}."
    return str(raw.get("result") or "")


def _looks_like_romania_president_question(prompt: str) -> bool:
    text = _ascii_text(prompt).lower()
    asks_president = "presedinte" in text or "presedintele" in text or "president" in text
    asks_romania = "romaniei" in text or "romania" in text or "romanian" in text
    return asks_president and asks_romania


def _format_romania_president_answer() -> str:
    return "Presedintele Romaniei este Nicusor Dan."


def _looks_like_tool_inventory_question(prompt: str) -> bool:
    text = _ascii_text(prompt).lower()
    patterns = (
        "cate tooluri",
        "cate tools",
        "ce tooluri",
        "ce tools",
        "lista tooluri",
        "lista tools",
        "list tools",
        "available tools",
        "tooluri disponibile",
        "tools disponibile",
    )
    return any(pattern in text for pattern in patterns)


def _format_tool_inventory_answer() -> str:
    manifest = load_tool_manifest()
    tools = [tool for tool in manifest.get("tools", []) if isinstance(tool, dict)]
    names = sorted(str(tool.get("name", "")).strip() for tool in tools if str(tool.get("name", "")).strip())
    categories: dict[str, int] = {}
    for tool in tools:
        category = str(tool.get("category", "other") or "other").strip()
        categories[category] = categories.get(category, 0) + 1
    category_text = ", ".join(f"{name}:{count}" for name, count in sorted(categories.items()))
    names_text = ", ".join(names)
    return (
        f"In chat am {len(names)} tooluri OS-22 prin ToolBridge: {names_text}. "
        f"Categorii: {category_text}. "
        "Phi-3 Medium este creierul local; ANA orchestreaza RAG, ToolBridge, logs si shortcuts. "
        "Pentru lista detaliata scrie /tools."
    )


def _looks_like_capability_question(prompt: str) -> bool:
    text = _ascii_text(prompt).lower()
    patterns = (
        "ce poti face",
        "ce stii sa faci",
        "cu ce ma ajuti",
        "ce faci pentru mine",
        "cum ma poti ajuta",
        "what can you do",
        "capabilitati",
        "capabilities",
    )
    return any(pattern in text for pattern in patterns)


def _format_capability_answer() -> str:
    return (
        "Pot sa vorbesc natural cu tine, sa folosesc RAG pentru memorie locala si sa apelez ToolBridge cand e nevoie. "
        "Am tooluri pentru timp, system_info, citire/scriere fisiere in workspace, browser local, web_fetch/web_scrape si memorie vectoriala. "
        "Phi-3 Medium este creierul local; ANA orchestreaza toolurile, RAG-ul, logurile si verificarea. "
        "Pentru lista exacta scrie /tools."
    )


def _looks_like_language_switch_prompt(prompt: str) -> bool:
    text = _ascii_text(prompt).lower()
    patterns = (
        "continue in english",
        "speak in english",
        "english mode",
        "write in english",
        "answer in english",
        "vorbeste in engleza",
        "scrie in engleza",
        "mod engleza",
    )
    return any(pattern in text for pattern in patterns)


def _format_language_lock_answer() -> str:
    return "Raman in romana. Spune-mi ce vrei sa facem mai departe."


def _looks_like_simple_explanation_prompt(prompt: str) -> bool:
    text = _ascii_text(prompt).lower()
    if not (("explica-mi" in text or "explica" in text) and "simplu" in text):
        return False
    concrete_tokens = ("python", "ana", "os-22", "rag", "tool", "fisier", "browser", "cod", "model")
    return not any(token in text for token in concrete_tokens)


def _format_simple_explanation_answer() -> str:
    return "Sigur. Spune-mi subiectul si il explic simplu, pe intelesul tau."


def _looks_like_greeting_prompt(prompt: str) -> bool:
    text = _ascii_text(prompt).strip().lower()
    return text in {
        "salut",
        "buna",
        "hello",
        "hi",
        "hey",
        "noroc",
    }


def _format_greeting_answer(prompt: str) -> str:
    return "Salut, Gyo. Sunt aici si sunt gata."


def _parse_json_args(raw_args: str) -> dict[str, Any]:
    text = str(raw_args or "").strip()
    if not text:
        return {}
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("tool arguments must be a JSON object")
    return payload


def _run_tool_command(tool_name: str, raw_args: str = "") -> dict[str, Any]:
    try:
        args = _parse_json_args(raw_args)
        result = execute_tool(tool_name, args)
        return {
            "schema": "ana.local_llm.tool_command.v1",
            "success": True,
            "tool": tool_name,
            "args": args,
            "result": result,
            "error": "",
        }
    except Exception as exc:
        return {
            "schema": "ana.local_llm.tool_command.v1",
            "success": False,
            "tool": tool_name,
            "args": {},
            "result": "",
            "error": str(exc).encode("ascii", errors="replace").decode("ascii"),
        }


def _run_rag_command(query: str) -> dict[str, Any]:
    try:
        bridge = get_rag_bridge()
        retrieval = bridge.retrieve(query, top_k=5)
        context = bridge.build_context(query, top_k=5)
        return {
            "schema": "ana.local_llm.rag_command.v1",
            "success": True,
            "query": query,
            "retrieval": retrieval,
            "context": context,
            "status": bridge.get_status(),
            "error": "",
        }
    except Exception as exc:
        return {
            "schema": "ana.local_llm.rag_command.v1",
            "success": False,
            "query": query,
            "retrieval": {},
            "context": "",
            "status": {},
            "error": str(exc).encode("ascii", errors="replace").decode("ascii"),
        }


def _run_heal_command(tool_name: str, raw_args: str = "") -> dict[str, Any]:
    try:
        args = _parse_json_args(raw_args)
        return diagnose_tool_request(tool_name, args)
    except Exception as exc:
        return {
            "schema": "ana.os22.agent_self_healing.v2",
            "kind": "tool_diagnostic",
            "success": False,
            "issue_class": "tool_args_invalid",
            "severity": "error",
            "tool": tool_name,
            "args": {},
            "repair_action": "provide_valid_json_arguments",
            "safe_to_retry": False,
            "next_step": "Use JSON object arguments.",
            "issues": [str(exc).encode("ascii", errors="replace").decode("ascii")],
        }


def _run_rag_heal_command(query: str) -> dict[str, Any]:
    try:
        bridge = get_rag_bridge()
        retrieval = bridge.retrieve(query, top_k=5)
        results = retrieval.get("results", []) if isinstance(retrieval, dict) else []
        return diagnose_rag_context(query, results)
    except Exception as exc:
        return {
            "schema": "ana.os22.agent_self_healing.v2",
            "kind": "rag_conflict_resolution",
            "success": False,
            "issue_class": "rag_error",
            "severity": "error",
            "input_count": 0,
            "conflict_detected": False,
            "selected": {},
            "selected_content": "",
            "ranked_memory_ids": [],
            "repair_action": "fallback_minimal_answer",
            "safe_to_retry": False,
            "next_step": "Use a minimal answer or refine the query.",
            "error": str(exc).encode("ascii", errors="replace").decode("ascii"),
        }


def _run_stabilize_command(text: str) -> dict[str, Any]:
    try:
        return stabilize_reasoning_text(text)
    except Exception as exc:
        return {
            "schema": "ana.os22.agent_self_healing.v2",
            "kind": "reasoning_stabilization",
            "success": False,
            "issue_class": "stabilizer_error",
            "severity": "error",
            "repair_action": "fallback_minimal_answer",
            "safe_to_retry": False,
            "next_step": "Use a shorter direct answer.",
            "error": str(exc).encode("ascii", errors="replace").decode("ascii"),
        }


def _run_doctor_command(profile: str) -> dict[str, Any]:
    try:
        return run_os22_doctor(profile=profile)
    except Exception as exc:
        return {
            "schema": "ana.os22.doctor.v1",
            "success": False,
            "status": "ERROR",
            "profile": profile,
            "failed_checks": ["doctor_exception"],
            "error": str(exc).encode("ascii", errors="replace").decode("ascii"),
        }


def _build_interactive_banner(profile: str, backend_info: dict[str, Any]) -> str:
    try:
        boot_report = OS22BootSequence(boot_profile=profile).build_boot_report()
    except Exception:
        boot_report = {}
    return build_agent_boot_banner(
        profile=profile,
        backend_info=backend_info,
        boot_report=boot_report,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start ANA MAX local LLM.")
    parser.add_argument("--prompt", default="Return the word ready.", help="Prompt for single-shot mode")
    parser.add_argument("--max-tokens", type=int, default=64, help="Maximum generated tokens")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--backend", default="llama_cpp", help="Local backend name")
    parser.add_argument("--model-name", default="phi3-medium", help="Primary model name")
    parser.add_argument("--fallback-model-name", default="phi3-medium", help="Fallback model name")
    parser.add_argument("--model-path", default="local_models/phi3-medium-q5_k_m.gguf", help="GGUF model path")
    parser.add_argument("--n-ctx", type=int, default=4096, help="Context window size")
    parser.add_argument("--n-threads", type=int, default=6, help="CPU threads")
    parser.add_argument("--n-gpu-layers", type=int, default=0, help="GPU layers for llama.cpp")
    parser.add_argument("--no-rag", action="store_true", help="Disable RAG context injection")
    parser.add_argument("--raw-backend", action="store_true", help="Bypass LocalBrainAgent and call backend.infer directly")
    parser.add_argument(
        "--profile",
        default="os22_core",
        choices=available_prompt_profiles(),
        help="Prompt profile to use.",
    )
    parser.add_argument(
        "--system-prompt-file",
        default="",
        help="Optional UTF-8 file that overrides the built-in profile prompt.",
    )
    parser.add_argument("--interactive", action="store_true", help="Open a local terminal chat loop")
    parser.add_argument("--no-banner", action="store_true", help="Hide the OS-22 boot banner in interactive mode")
    parser.add_argument("--smoke", action="store_true", help="Run one short prompt and exit")
    args = parser.parse_args(argv)

    profile = normalize_profile_name(args.profile)
    system_prompt = _system_prompt_text(profile, args.system_prompt_file)
    backend = LocalLLMBackend(_backend_config(args))
    load_info = backend.load_model()
    _print_json(
        {
            "schema": "ana.local_llm.start.v1",
            "event": "loaded",
            "profile": profile,
            "backend": load_info,
        }
    )
    if not load_info.get("loaded"):
        return 1

    agent = LocalBrainAgent(
        backend=backend,
        enable_inference=True,
        prompt_profile=profile,
        use_rag=not args.no_rag,
        tool_aware=True,
        max_response_tokens=args.max_tokens,
        generation_temperature=args.temperature,
    )

    if args.interactive:
        if not args.no_banner:
            print(_build_interactive_banner(profile, load_info))
        print(f"ANA OS-22 Agent ready. Profile: {profile}. Type /help for commands.")
        conversation = ConversationMemory(max_turns=6)
        while True:
            try:
                prompt = input("ana> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not prompt:
                continue
            if prompt.lower() in {"/exit", "exit", "quit", "/quit"}:
                break
            if prompt.lower() == "/help":
                _print_interactive_help()
                continue
            if prompt.lower() == "/status":
                _print_json({"schema": "ana.local_llm.status.v1", "backend": backend.get_backend_info(), "agent": agent.summarize_agent()})
                continue
            if prompt.lower() == "/boot":
                _print_json(OS22BootSequence(boot_profile=profile).run())
                continue
            if prompt.lower() == "/doctor":
                _print_json(_run_doctor_command(profile))
                continue
            if prompt.lower() == "/foundation":
                _print_json(get_agent_foundation_status())
                continue
            if prompt.lower() == "/heal":
                _print_json(get_self_healing_status())
                continue
            if prompt.lower().startswith("/heal "):
                payload = prompt.split(" ", 1)[1].strip()
                tool_name, _, raw_args = payload.partition(" ")
                _print_json(_run_heal_command(tool_name, raw_args))
                continue
            if prompt.lower().startswith("/ragheal "):
                query = prompt.split(" ", 1)[1].strip()
                _print_json(_run_rag_heal_command(query))
                continue
            if prompt.lower().startswith("/stabilize "):
                text = prompt.split(" ", 1)[1].strip()
                _print_json(_run_stabilize_command(text))
                continue
            if prompt.lower() == "/tools":
                _print_tool_manifest()
                continue
            if prompt.lower() == "/time":
                _print_json(_run_tool_command("current_time"))
                continue
            if prompt.lower() == "/log":
                print(str(CHAT_LOG_PATH))
                continue
            if prompt.lower().startswith("/open "):
                url = prompt.split(" ", 1)[1].strip()
                _print_json(_run_tool_command("open_browser", json.dumps({"url": url}, ensure_ascii=True)))
                continue
            if prompt.lower().startswith("/tool "):
                payload = prompt.split(" ", 1)[1].strip()
                tool_name, _, raw_args = payload.partition(" ")
                _print_json(_run_tool_command(tool_name, raw_args))
                continue
            if prompt.lower().startswith("/rag "):
                query = prompt.split(" ", 1)[1].strip()
                _print_json(_run_rag_command(query))
                continue
            routed_intent = route_operator_intent(prompt)
            if routed_intent.get("handled"):
                answer = str(routed_intent.get("text", ""))
                _log_chat_event(
                    "intent_response",
                    {"kind": _ascii_text(routed_intent.get("kind", "")), "text": _ascii_text(answer)},
                )
                result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
            elif _looks_like_time_question(prompt):
                answer = _format_current_time_answer()
                _log_chat_event("shortcut_response", {"kind": "current_time", "text": _ascii_text(answer)})
                result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
            elif _looks_like_romania_president_question(prompt):
                answer = _format_romania_president_answer()
                _log_chat_event("shortcut_response", {"kind": "romania_president", "text": _ascii_text(answer)})
                result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
            elif _looks_like_tool_inventory_question(prompt):
                answer = _format_tool_inventory_answer()
                _log_chat_event("shortcut_response", {"kind": "tool_inventory", "text": _ascii_text(answer)})
                result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
            elif _looks_like_language_switch_prompt(prompt):
                answer = _format_language_lock_answer()
                _log_chat_event("shortcut_response", {"kind": "language_lock", "text": _ascii_text(answer)})
                result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
            else:
                result = (
                    _run_prompt(backend, prompt, args.max_tokens, args.temperature, system_prompt)
                    if args.raw_backend
                    else _run_agent_prompt(agent, prompt, conversation.render())
                )
            answer_text = str(result.get("text", "")).strip()
            conversation.add_turn(prompt, answer_text)
            print(answer_text)
        backend.unload_model()
        return 0

    routed_intent = route_operator_intent(args.prompt)
    if routed_intent.get("handled"):
        answer = str(routed_intent.get("text", ""))
        _log_chat_event(
            "intent_response",
            {"kind": _ascii_text(routed_intent.get("kind", "")), "text": _ascii_text(answer)},
        )
        result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
    elif _looks_like_time_question(args.prompt):
        answer = _format_current_time_answer()
        _log_chat_event("shortcut_response", {"kind": "current_time", "text": _ascii_text(answer)})
        result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
    elif _looks_like_romania_president_question(args.prompt):
        answer = _format_romania_president_answer()
        _log_chat_event("shortcut_response", {"kind": "romania_president", "text": _ascii_text(answer)})
        result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
    elif _looks_like_tool_inventory_question(args.prompt):
        answer = _format_tool_inventory_answer()
        _log_chat_event("shortcut_response", {"kind": "tool_inventory", "text": _ascii_text(answer)})
        result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
    elif _looks_like_language_switch_prompt(args.prompt):
        answer = _format_language_lock_answer()
        _log_chat_event("shortcut_response", {"kind": "language_lock", "text": _ascii_text(answer)})
        result = {"schema": "ana.local_llm.agent_turn.v1", "success": True, "text": answer, "error": ""}
    else:
        result = (
            _run_prompt(backend, args.prompt, args.max_tokens, args.temperature, system_prompt)
            if args.raw_backend
            else _run_agent_prompt(agent, args.prompt)
        )
    _print_json({"schema": "ana.local_llm.infer.v1", "profile": profile, "result": result})
    backend.unload_model()
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
