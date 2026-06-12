"""Test the optional ANA MAX local LLM backend from local_llm_env."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.local.local_llm_backend import LocalLLMBackend
from ANA_MAX.local.prompt_profiles import available_prompt_profiles, get_system_prompt, normalize_profile_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test optional ANA local brain backend.")
    parser.add_argument("--infer", action="store_true", help="Run a tiny inference if backend is available")
    parser.add_argument(
        "--profile",
        default="",
        choices=available_prompt_profiles(),
        help="Prompt profile to use for inference.",
    )
    args = parser.parse_args(argv)

    profile = normalize_profile_name(args.profile)
    backend = LocalLLMBackend()
    info = backend.get_backend_info()
    result = {
        "schema": "ana.local_llm.brain_test.v1",
        "profile": profile,
        "backend_info": info,
        "inference": {
            "attempted": False,
            "result": None,
        },
        "success": True,
    }
    if args.infer and backend.is_available():
        result["inference"] = {
            "attempted": True,
            "result": backend.infer(
                "Return the word ready.",
                system_prompt=get_system_prompt(profile),
                max_tokens=16,
                temperature=0.0,
            ),
        }
    elif args.infer:
        result["inference"] = {
            "attempted": False,
            "result": {
                "used_llm": False,
                "error": "backend_unavailable",
            },
        }
    print(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
