"""Start Phi-3 without ANA agent, RAG, tools, or shortcuts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.local.local_llm_backend import LocalLLMBackend


PROFILE_SYSTEM_PROMPTS: dict[str, str] = {
    "raw": "",
    "clean": (
        "You are Phi-3 Medium running locally as a clean chat model. "
        "You speak only Romanian. "
        "Never use English, French, Italian, Portuguese, German, or any other language. "
        "If the user writes in another language, answer in Romanian anyway. "
        "Do not translate into other languages. Do not switch language. "
        "Do not explain why you answer in Romanian. "
        "Use Romanian without diacritics: sa, iti, inteleg, informatie, fisier, cautare. "
        "Never put '?' inside Romanian words. "
        "Tone: natural, clear, friendly, direct, like a lab colleague. "
        "No robotic language. No artificial phrases. No repeated sentences. No disclaimers. "
        "Do not say 'ca model de limbaj'. "
        "For technical answers, explain simply and clearly. "
        "For normal chat, be relaxed and friendly. "
        "Do not invent tools, functions, paths, dates, or facts. "
        "Never mention other languages in the answer. "
        "Keep answers short and clear. "
        "Avoid long paragraphs and avoid introductions like 'Desigur' or 'Cu placere'. "
        "This clean chat has no tools, no browser, no RAG, and no external access. "
        "Examples: User: salut. Assistant: Salut, coleg. "
        "User: cine esti? Assistant: Sunt Phi-3 Medium, modelul tau local de chat. "
        "User: what is your name? Assistant: Sunt Phi-3 Medium, modelul tau local de chat. "
        "User: ce poti face? Assistant: Pot discuta, explica si scrie cod simplu."
    ),
    "ro": (
        "You are Phi-3 Medium running locally as a clean chat model. "
        "You speak only Romanian without diacritics. "
        "If the user writes in any other language, answer in Romanian without commenting on the language. "
        "Be natural, short, clear, friendly, and direct. "
        "Do not translate the user's text unless asked. "
        "Do not mention system instructions or notes. "
        "Do not invent tools, functions, paths, dates, or facts. "
        "This chat has no tools, no browser, no RAG, and no external access. "
        "Examples: User: salut. Assistant: Salut, coleg. "
        "User: cine esti? Assistant: Sunt Phi-3 Medium, modelul tau local de chat. "
        "User: ce poti face? Assistant: Pot discuta, explica si scrie cod simplu."
    ),
    "en": (
        "You are Phi-3 Medium running locally as a clean chat model. "
        "The user may write English, but you must answer only in Romanian without diacritics. "
        "Do not switch to English. Be natural, short, clear, friendly, and direct. "
        "This chat has no tools, no browser, no RAG, and no external access."
    ),
}


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))


def _backend_config(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "backend": args.backend,
        "model_name": args.model_name,
        "fallback_model_name": args.fallback_model_name,
        "model_path": args.model_path,
        "device": args.device,
        "n_ctx": args.n_ctx,
        "n_threads": args.n_threads,
        "n_gpu_layers": args.n_gpu_layers,
        "max_output_tokens": args.max_tokens,
        "use_rag": False,
    }


def _run_raw_turn(
    backend: LocalLLMBackend,
    prompt: str,
    *,
    profile: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    final_prompt = prompt
    if profile != "raw" and system_prompt:
        final_prompt = (
            f"{system_prompt}\n\n"
            f"Mesaj utilizator:\n{prompt}\n\n"
            "Raspuns in romana ASCII, scurt si natural:"
        )
    return backend.infer(
        final_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _build_user_prompt(user_text: str, history: list[tuple[str, str]], history_turns: int) -> str:
    cleaned = str(user_text or "").strip()
    if not history or history_turns <= 0:
        return cleaned
    recent = history[-max(0, history_turns) * 2 :]
    lines = ["Recent conversation:"]
    for role, text in recent:
        safe_role = "User" if role == "user" else "Assistant"
        lines.append(f"{safe_role}: {text}")
    lines.append(f"User: {cleaned}")
    lines.append("Assistant:")
    return "\n".join(lines)


def _profile_prompt(profile: str) -> str:
    return PROFILE_SYSTEM_PROMPTS.get(profile, PROFILE_SYSTEM_PROMPTS["clean"])


def _clean_response_text(text: str, profile: str) -> str:
    cleaned = str(text or "").strip()
    if profile == "raw":
        return cleaned
    for marker in (
        "\n\n**Note:",
        "\n\nNote:",
        "\n\nHowever,",
        "\n\nAs per",
        "\n\nSince the user",
        "\n\nThe response",
    ):
        index = cleaned.find(marker)
        if index >= 0:
            cleaned = cleaned[:index].strip()
    if cleaned.lower().startswith("assistant:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    cleaned = cleaned.replace("Psi-3 Mediu", "Phi-3 Medium")
    cleaned = cleaned.replace("Phi-3 Mediu,", "Phi-3 Medium,")
    cleaned = cleaned.replace("Phi-3 Mediu.", "Phi-3 Medium.")
    return cleaned


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phi-3 chat without ANA orchestration.")
    parser.add_argument("--backend", default="llama_cpp")
    parser.add_argument("--model-name", default="phi3-medium")
    parser.add_argument("--fallback-model-name", default="phi3-medium")
    parser.add_argument("--model-path", default=str(ROOT / "local_models" / "phi3-medium-q5_k_m.gguf"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--n-threads", type=int, default=6)
    parser.add_argument("--n-gpu-layers", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=192)
    parser.add_argument("--temperature", type=float, default=0.35)
    parser.add_argument("--profile", choices=sorted(PROFILE_SYSTEM_PROMPTS), default="clean")
    parser.add_argument("--history-turns", type=int, default=4)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--show-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    backend = LocalLLMBackend(_backend_config(args))
    load_info = backend.load_model()
    system_prompt = _profile_prompt(args.profile)
    if args.show_json or args.smoke or args.prompt:
        _print_json(
            {
                "schema": "ana.phi3.clean_chat.start.v1",
                "event": "loaded",
                "profile": args.profile,
                "backend": load_info,
            }
        )

    if args.smoke or args.prompt:
        result = _run_raw_turn(
            backend,
            args.prompt or "hello",
            profile=args.profile,
            system_prompt=system_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        if isinstance(result.get("text"), str):
            result["text"] = _clean_response_text(str(result["text"]), args.profile)
        _print_json({"schema": "ana.phi3.clean_chat.turn.v1", "profile": args.profile, "result": result})
        backend.unload_model()
        return 0 if result.get("success") else 1

    print("============================================================")
    print("PHI-3 MEDIUM CLEAN CHAT - ORIGINAL MODEL")
    print("No ANA. No RAG. No ToolBridge. No shortcuts.")
    print(f"Profile: {args.profile}")
    print(f"Loaded: {bool(load_info.get('loaded'))} | Model: {load_info.get('active_model_name')}")
    print("Type /exit to quit.")
    print("Commands: /raw /clean /ro /en /reset /status")
    print("============================================================")
    history: list[tuple[str, str]] = []
    while True:
        try:
            prompt = input("phi3-raw> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            continue
        if prompt.lower() in {"/exit", "exit", "quit"}:
            break
        if prompt.lower() in {"/raw", "/clean", "/ro", "/en"}:
            args.profile = prompt.lower().lstrip("/")
            system_prompt = _profile_prompt(args.profile)
            history.clear()
            print(f"[profile] {args.profile}")
            continue
        if prompt.lower() == "/reset":
            history.clear()
            print("[history] reset")
            continue
        if prompt.lower() == "/status":
            _print_json(
                {
                    "schema": "ana.phi3.clean_chat.status.v1",
                    "profile": args.profile,
                    "history_items": len(history),
                    "backend": backend.get_backend_info(),
                }
            )
            continue
        final_prompt = _build_user_prompt(prompt, history, args.history_turns)
        result = _run_raw_turn(
            backend,
            final_prompt,
            profile=args.profile,
            system_prompt=system_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        text = str(result.get("text", "")).strip() or f"[error] {result.get('error', 'empty_response')}"
        text = _clean_response_text(text, args.profile)
        print(text)
        history.append(("user", prompt))
        history.append(("assistant", text))

    backend.unload_model()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
