"""Register optional local model files for ANA MAX local LLM.

Default mode is dry-run. Use --apply with --source to copy a local file or
download from a user-provided URL into local_models.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
DEFAULT_MODEL_DIR = ROOT / "local_models"

MODEL_FILENAMES = {
    "phi3-medium": "phi3-medium-q5_k_m.gguf",
    "phi3-mini": "phi3-mini-q5_k_m.gguf",
}


def _is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def _copy_or_download(
    source: str,
    destination: Path,
    timeout: int,
    token: str = "",
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _is_url(source):
        request = urllib.request.Request(source)
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with destination.open("wb") as output:
                shutil.copyfileobj(response, output)
        return {"mode": "download", "source": source, "destination": str(destination)}
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(str(source_path))
    shutil.copy2(source_path, destination)
    return {"mode": "copy", "source": str(source_path), "destination": str(destination)}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    model_name = str(args.model or "").strip().lower()
    model_dir = Path(args.model_dir).resolve() if args.model_dir else DEFAULT_MODEL_DIR
    filename = MODEL_FILENAMES.get(model_name, "")
    destination = model_dir / filename if filename else model_dir / "unknown-model.gguf"
    token = str(args.token or os.environ.get("HUGGINGFACE_HUB_TOKEN") or os.environ.get("HF_TOKEN") or "").strip()
    report: dict[str, Any] = {
        "schema": "ana.local_llm.model_install.v1",
        "root": str(ROOT),
        "apply": bool(args.apply),
        "model": model_name,
        "known_models": sorted(MODEL_FILENAMES),
        "source": str(args.source or ""),
        "token_provided": bool(token),
        "model_dir": str(model_dir),
        "destination": str(destination),
        "destination_exists": destination.exists(),
        "success": False,
        "error": "",
    }

    if model_name not in MODEL_FILENAMES:
        report["error"] = "unknown_model"
        return report
    if not args.apply:
        report["success"] = True
        report["error"] = "dry_run_no_changes"
        return report
    if not args.source:
        report["error"] = "source_required"
        return report

    try:
        result = _copy_or_download(str(args.source), destination, max(10, int(args.timeout)), token=token)
        report["operation"] = result
        report["destination_exists"] = destination.exists()
        report["bytes"] = destination.stat().st_size if destination.exists() else 0
        report["success"] = destination.exists() and report["bytes"] > 0
        if not report["success"]:
            report["error"] = "model_file_missing_after_operation"
    except urllib.error.HTTPError as exc:
        report["error"] = f"http_error_{exc.code}"
        if exc.code == 401 and not token:
            report["error"] = "unauthorized_download_source; provide --token or set HUGGINGFACE_HUB_TOKEN/HF_TOKEN"
    except Exception as exc:
        report["error"] = str(exc).encode("ascii", errors="replace").decode("ascii")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy or download optional local LLM model files.")
    parser.add_argument("--apply", action="store_true", help="Copy or download the model file")
    parser.add_argument("--model", choices=sorted(MODEL_FILENAMES), required=True)
    parser.add_argument("--source", default="", help="User-provided URL or local file path")
    parser.add_argument("--token", default="", help="Optional Hugging Face token for gated downloads")
    parser.add_argument("--model-dir", default="", help="Optional local model directory")
    parser.add_argument("--timeout", type=int, default=1800, help="Download timeout seconds")
    args = parser.parse_args(argv)
    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
