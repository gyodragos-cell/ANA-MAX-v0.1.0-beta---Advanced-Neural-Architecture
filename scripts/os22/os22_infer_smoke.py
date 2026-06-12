from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents import LocalBrainAgent
from ANA_MAX.local import LocalLLMBackend
from ANA_MAX.local.os22_boot import OS22BootSequence
from ANA_MAX.local.prompt_profiles import normalize_profile_name


DEFAULT_LOG_PATH = ROOT / "ANA_MAX" / "logs" / "os22_infer_smoke.log"


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _log_lines(lines: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class _ToolCallSmokeBackend:
    def __init__(self, backend: LocalLLMBackend) -> None:
        self.backend = backend
        self.calls = 0

    def get_backend_info(self) -> dict[str, Any]:
        return self.backend.get_backend_info()

    def is_available(self) -> bool:
        return self.backend.is_available()

    def infer_with_rag(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            info = self.backend.get_backend_info()
            return {
                "schema": info.get("schema", "ana.os21.local_llm_backend.v1"),
                "success": True,
                "used_llm": True,
                "text": 'TOOL_CALL: system_info {}',
                "model_name": info.get("model_name", ""),
                "error": "",
            }
        if self.backend.is_available():
            return self.backend.infer_with_rag(*args, **kwargs)
        prompt = str(args[0] if args else kwargs.get("prompt", ""))
        return {
            "schema": "ana.os21.local_llm_backend.v1",
            "success": True,
            "used_llm": False,
            "text": f"ok:smoke-fallback:{prompt[:120]}",
            "model_name": self.backend.get_backend_info().get("model_name", ""),
            "error": "",
        }


def _build_backend(
    *,
    backend_name: str,
    model_name: str,
    fallback_model_name: str,
    model_path: str,
    n_ctx: int,
    n_threads: int,
    n_gpu_layers: int,
    max_output_tokens: int,
    use_rag: bool,
) -> LocalLLMBackend:
    return LocalLLMBackend(
        {
            "backend": backend_name,
            "model_name": model_name,
            "fallback_model_name": fallback_model_name,
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_threads": n_threads,
            "n_gpu_layers": n_gpu_layers,
            "max_output_tokens": max_output_tokens,
            "use_rag": use_rag,
        }
    )


def run_smoke(
    *,
    prompt: str,
    boot: OS22BootSequence | None = None,
    backend: LocalLLMBackend | None = None,
    agent: LocalBrainAgent | None = None,
    output_dir: str | Path | None = None,
    log_path: str | Path | None = None,
    profile: str = "os22_core",
    backend_name: str = "llama_cpp",
    model_name: str = "phi3-medium",
    fallback_model_name: str = "phi3-medium",
    model_path: str = "",
    n_ctx: int = 4096,
    n_threads: int = 6,
    n_gpu_layers: int = 0,
    max_output_tokens: int = 256,
    use_rag: bool = True,
    force_tool_call: bool = True,
) -> dict[str, Any]:
    output_path = Path(output_dir) if output_dir is not None else DEFAULT_LOG_PATH.parent
    final_log_path = Path(log_path) if log_path is not None else output_path / "os22_infer_smoke.log"
    lines: list[str] = []

    boot = boot or OS22BootSequence(boot_profile=profile)
    lines.append("[OS22] Running boot sequence...")
    boot_report = boot.run()
    lines.append(json.dumps(boot_report, indent=2, ensure_ascii=True, sort_keys=True))

    if not boot_report.get("overall_success", False):
        lines.append("[OS22] Boot not healthy enough, aborting smoke run.")
        _log_lines(lines, final_log_path)
        return {
            "boot": boot_report,
            "aborted": True,
            "final_output": "",
            "log_path": str(final_log_path),
        }

    backend = backend or _build_backend(
        backend_name=backend_name,
        model_name=model_name,
        fallback_model_name=fallback_model_name,
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        max_output_tokens=max_output_tokens,
        use_rag=use_rag,
    )
    if force_tool_call:
        backend_for_agent: Any = _ToolCallSmokeBackend(backend)
    else:
        backend_for_agent = backend

    lines.append("\n[OS22] Initializing LocalLLMBackend...")
    lines.append(json.dumps(backend.get_backend_info(), indent=2, ensure_ascii=True, sort_keys=True))

    agent = agent or LocalBrainAgent(
        backend=backend_for_agent,
        enable_inference=True,
        prompt_profile=normalize_profile_name(profile),
        use_rag=use_rag,
        tool_aware=True,
    )

    lines.append(f"\n[OS22] Running smoke turn with profile={profile!r}...")
    lines.append(f"[OS22] Prompt: {_ascii_text(prompt)!r}")
    result_text = agent.run_turn(prompt)
    lines.append("\n[OS22] Final agent output:")
    lines.append(_ascii_text(result_text))

    _log_lines(lines, final_log_path)
    return {
        "boot": boot_report,
        "backend": backend.get_backend_info(),
        "final_output": result_text,
        "aborted": False,
        "profile": normalize_profile_name(profile),
        "tool_call_forced": force_tool_call,
        "tool_bridge_rounds": getattr(backend_for_agent, "calls", 0),
        "log_path": str(final_log_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a small OS-22 local brain smoke test.")
    parser.add_argument(
        "--prompt",
        default="Plan a minimal OS-22 RAG + ToolBridge validation step and call system_info if useful.",
        help="Smoke prompt to send to the local brain.",
    )
    parser.add_argument("--profile", default="os22_core", help="Prompt profile to use.")
    parser.add_argument("--backend", default="llama_cpp", help="Local backend name.")
    parser.add_argument("--model-name", default="phi3-medium", help="Primary model name.")
    parser.add_argument("--fallback-model-name", default="phi3-medium", help="Fallback model name.")
    parser.add_argument("--model-path", default="", help="Optional model path or directory.")
    parser.add_argument("--n-ctx", type=int, default=4096, help="Context window size.")
    parser.add_argument("--n-threads", type=int, default=6, help="CPU threads.")
    parser.add_argument("--n-gpu-layers", type=int, default=0, help="GPU layers.")
    parser.add_argument("--max-output-tokens", type=int, default=256, help="Output token cap.")
    parser.add_argument("--no-rag", action="store_true", help="Disable RAG for the smoke run.")
    parser.add_argument(
        "--no-forced-tool-call",
        action="store_true",
        help="Do not inject a deterministic TOOL_CALL on the first pass.",
    )
    parser.add_argument("--log-path", default="", help="Optional explicit log path.")
    args = parser.parse_args(argv)

    result = run_smoke(
        prompt=args.prompt,
        profile=args.profile,
        backend_name=args.backend,
        model_name=args.model_name,
        fallback_model_name=args.fallback_model_name,
        model_path=args.model_path,
        n_ctx=args.n_ctx,
        n_threads=args.n_threads,
        n_gpu_layers=args.n_gpu_layers,
        max_output_tokens=args.max_output_tokens,
        use_rag=not args.no_rag,
        force_tool_call=not args.no_forced_tool_call,
        log_path=args.log_path or None,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if not result.get("aborted", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
