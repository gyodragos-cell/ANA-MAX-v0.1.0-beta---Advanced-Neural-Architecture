"""Optional local LLM backend for ANA MAX OS-21.5.

The backend is intentionally optional. Importing this module never imports or
loads OLLM. Model loading happens only through ``load_model`` or ``infer``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .prompt_engine import compose_system_prompt


BACKEND_SCHEMA = "ana.os21.local_llm_backend.v1"
DEFAULT_BACKEND = "ollm"
LLAMA_CPP_BACKEND = "llama_cpp"
DEFAULT_MODEL = "phi3-medium"
DEFAULT_FALLBACK_MODEL = "phi3-medium"
ENV_FILE = ROOT / ".env.local_llm"


def _ascii_error(exc: BaseException | str | None) -> str:
    if exc is None:
        return ""
    return _ascii_text(exc)


def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _safe_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    candidate = str(value).strip().lower()
    if candidate in {"1", "true", "yes", "on"}:
        return True
    if candidate in {"0", "false", "no", "off"}:
        return False
    return default


def _ascii_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return normalized.encode("ascii", errors="ignore").decode("ascii")


def _load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _env_value(values: Mapping[str, str], key: str, default: str = "") -> str:
    return str(os.environ.get(key) or values.get(key) or default).strip()


class _TransformersGGUFSession:
    """Small local inference wrapper for direct GGUF loading."""

    def __init__(self, model_dir: Path, gguf_file: Path, model_name: str, device: str) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.model_dir = model_dir
        self.gguf_file = gguf_file
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, gguf_file=gguf_file.name)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, gguf_file=gguf_file.name, device_map=device)
        self.model.eval()

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        import torch

        prompt_text = str(prompt or "").strip()
        system_text = str(system_prompt or "").strip()
        if system_text:
            prompt_text = f"{system_text}\n\n{prompt_text}"
        inputs = self.tokenizer(prompt_text, return_tensors="pt")
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": max_tokens,
            "do_sample": temperature > 0.0,
        }
        if temperature > 0.0:
            generation_kwargs["temperature"] = temperature
        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **generation_kwargs)
        decoded = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return {
            "schema": BACKEND_SCHEMA,
            "backend": "transformers_gguf",
            "model_name": self.model_name,
            "text": decoded,
            "success": True,
            "used_llm": True,
            "local_only": True,
            "error": "",
        }

    def unload(self) -> None:
        self.model = None


class _LlamaCppSession:
    """Small local inference wrapper for llama.cpp GGUF loading."""

    def __init__(
        self,
        model_path: Path,
        model_name: str,
        n_ctx: int,
        n_threads: int,
        n_gpu_layers: int,
    ) -> None:
        from llama_cpp import Llama

        self.model_name = model_name
        self.model_path = model_path
        self.model = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        prompt_text = str(prompt or "").strip()
        system_text = str(system_prompt or "").strip()

        chat_messages = []
        if system_text:
            chat_messages.append({"role": "system", "content": system_text})
        chat_messages.append({"role": "user", "content": prompt_text})

        if hasattr(self.model, "create_chat_completion"):
            try:
                return self.model.create_chat_completion(
                    messages=chat_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["<|user|>", "<|assistant|>"],
                )
            except Exception:
                pass

        if system_text:
            prompt_text = f"{system_text}\n\n{prompt_text}"
        return self.model(
            prompt_text,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False,
            stop=["<|user|>", "<|assistant|>"],
        )

    def unload(self) -> None:
        self.model = None


@dataclass(frozen=True)
class LocalLLMConfig:
    """Configuration for the optional local LLM backend."""

    backend: str = DEFAULT_BACKEND
    model_name: str = DEFAULT_MODEL
    fallback_model_name: str = DEFAULT_FALLBACK_MODEL
    device: str = "cpu"
    model_path: str = ""
    use_rag: bool = True
    max_context_tokens: int = 4096
    max_output_tokens: int = 512
    n_ctx: int = 2048
    n_threads: int = 6
    n_gpu_layers: int = 0

    @classmethod
    def from_value(cls, value: Mapping[str, Any] | "LocalLLMConfig" | None = None) -> "LocalLLMConfig":
        if isinstance(value, LocalLLMConfig):
            return value
        data = dict(value or {})
        env_values = _load_env_file()
        return cls(
            backend=str(data.get("backend") or _env_value(env_values, "ANA_LOCAL_LLM_BACKEND", DEFAULT_BACKEND)).strip().lower(),
            model_name=str(data.get("model_name") or _env_value(env_values, "ANA_LOCAL_LLM_MODEL_NAME", DEFAULT_MODEL)).strip(),
            fallback_model_name=str(
                data.get("fallback_model_name")
                or _env_value(env_values, "ANA_LOCAL_LLM_FALLBACK_MODEL_NAME", DEFAULT_FALLBACK_MODEL)
            ).strip(),
            device=str(data.get("device") or _env_value(env_values, "ANA_LOCAL_LLM_DEVICE", "cpu")).strip().lower(),
            model_path=str(data.get("model_path") or _env_value(env_values, "ANA_LOCAL_LLM_MODEL_PATH", "")).strip(),
            use_rag=_safe_bool(
                data["use_rag"] if "use_rag" in data else _env_value(env_values, "ANA_LOCAL_LLM_USE_RAG", "1"),
                True,
            ),
            max_context_tokens=_safe_int(data.get("max_context_tokens"), 4096, 512, 131072),
            max_output_tokens=_safe_int(data.get("max_output_tokens"), 512, 1, 8192),
            n_ctx=_safe_int(data.get("n_ctx") or _env_value(env_values, "ANA_LOCAL_LLM_N_CTX", "2048"), 2048, 512, 32768),
            n_threads=_safe_int(
                data.get("n_threads") or _env_value(env_values, "ANA_LOCAL_LLM_N_THREADS", "6"),
                6,
                1,
                64,
            ),
            n_gpu_layers=_safe_int(
                data.get("n_gpu_layers") or _env_value(env_values, "ANA_LOCAL_LLM_N_GPU_LAYERS", "0"),
                0,
                0,
                512,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "model_name": self.model_name,
            "fallback_model_name": self.fallback_model_name,
            "device": self.device,
            "model_path": self.model_path,
            "use_rag": self.use_rag,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "n_ctx": self.n_ctx,
            "n_threads": self.n_threads,
            "n_gpu_layers": self.n_gpu_layers,
        }


class LocalLLMBackend:
    """Optional local LLM adapter with graceful failure behavior."""

    def __init__(self, config: Mapping[str, Any] | LocalLLMConfig | None = None) -> None:
        self.config = LocalLLMConfig.from_value(config)
        self._module: Any | None = None
        self._model: Any | None = None
        self._active_model_name = ""
        self._runtime_backend = ""
        self._last_error = ""
        self._load_attempted = False

    def _import_backend_module(self) -> Any | None:
        if self.config.backend not in {DEFAULT_BACKEND, LLAMA_CPP_BACKEND}:
            self._last_error = f"unsupported_backend:{self.config.backend}"
            return None
        if self._module is not None:
            return self._module
        try:
            self._module = importlib.import_module(self.config.backend)
        except Exception as exc:  # optional dependency boundary
            self._last_error = f"backend_missing:{_ascii_error(exc)}"
            self._module = None
        return self._module

    def is_available(self) -> bool:
        """Return True only when the optional backend module imports cleanly."""

        return self._import_backend_module() is not None

    def _call_loader(self, loader: Any, model_name: str) -> Any:
        attempts = [
            lambda: loader(
                model_name=model_name,
                device=self.config.device,
                max_context_tokens=self.config.max_context_tokens,
            ),
            lambda: loader(model_name=model_name, device=self.config.device),
            lambda: loader(model_name=model_name),
            lambda: loader(model_name, device=self.config.device),
            lambda: loader(model_name),
        ]
        last_error: BaseException | None = None
        for attempt in attempts:
            try:
                return attempt()
            except TypeError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("loader_call_failed")

    def _load_transformers_gguf(self, model_name: str) -> Any:
        model_path = Path(self.config.model_path) if self.config.model_path else Path()
        if self.config.model_path and not model_path.is_absolute():
            model_path = ROOT / model_path
        if not self.config.model_path:
            raise RuntimeError("model_path_required_for_transformers_gguf")
        if not model_path.exists():
            raise FileNotFoundError(f"model_path_missing:{model_path}")
        if model_path.is_dir():
            gguf_files = sorted(model_path.glob("*.gguf"))
            if not gguf_files:
                raise FileNotFoundError(f"gguf_file_missing_in_directory:{model_path}")
            gguf_path = gguf_files[0]
            model_dir = model_path
        else:
            gguf_path = model_path
            model_dir = model_path.parent
        self._runtime_backend = "transformers_gguf"
        return _TransformersGGUFSession(model_dir=model_dir, gguf_file=gguf_path, model_name=model_name, device=self.config.device)

    def _load_llama_cpp(self, model_name: str) -> Any:
        model_path = Path(self.config.model_path) if self.config.model_path else Path()
        if self.config.model_path and not model_path.is_absolute():
            model_path = ROOT / model_path
        if not self.config.model_path:
            raise RuntimeError("model_path_required_for_llama_cpp")
        if not model_path.exists():
            raise FileNotFoundError(f"model_path_missing:{model_path}")
        if model_path.is_dir():
            gguf_files = sorted(model_path.glob("*.gguf"))
            if not gguf_files:
                raise FileNotFoundError(f"gguf_file_missing_in_directory:{model_path}")
            model_path = gguf_files[0]
        self._runtime_backend = LLAMA_CPP_BACKEND
        return _LlamaCppSession(
            model_path=model_path,
            model_name=model_name,
            n_ctx=self.config.n_ctx,
            n_threads=self.config.n_threads,
            n_gpu_layers=self.config.n_gpu_layers,
        )

    def _load_candidate(self, module: Any, model_name: str) -> Any:
        if self.config.backend == LLAMA_CPP_BACKEND:
            return self._load_llama_cpp(model_name)
        for attr in ("load_model", "load", "Model", "LLM"):
            loader = getattr(module, attr, None)
            if loader is None:
                continue
            self._runtime_backend = DEFAULT_BACKEND
            return self._call_loader(loader, model_name)
        auto_inference = getattr(module, "AutoInference", None)
        if auto_inference is not None:
            model_path = Path(self.config.model_path) if self.config.model_path else Path()
            if self.config.model_path and not model_path.is_absolute():
                model_path = ROOT / model_path
            if not self.config.model_path:
                raise RuntimeError("model_path_required_for_ollm_auto_inference")
            if not model_path.exists():
                raise FileNotFoundError(f"model_path_missing:{model_path}")
            inference_root = model_path.parent if model_path.is_file() else model_path
            self._runtime_backend = DEFAULT_BACKEND
            return auto_inference(str(inference_root), device=self.config.device, logging=False)
        if model_name.lower().startswith("phi3"):
            return self._load_transformers_gguf(model_name)
        raise RuntimeError("ollm_loader_not_found")

    def load_model(self, config: Mapping[str, Any] | LocalLLMConfig | None = None) -> dict[str, Any]:
        """Load the primary model, then fallback model if needed."""

        if config is not None:
            self.config = LocalLLMConfig.from_value(config)
        self._load_attempted = True
        module = self._import_backend_module()
        if module is None:
            return self.get_backend_info()

        errors: list[dict[str, str]] = []
        candidates = [self.config.model_name]
        if self.config.fallback_model_name and self.config.fallback_model_name not in candidates:
            candidates.append(self.config.fallback_model_name)

        for candidate in candidates:
            try:
                self._model = self._load_candidate(module, candidate)
                self._active_model_name = candidate
                self._last_error = ""
                return self.get_backend_info()
            except Exception as exc:  # model loader is optional and backend-specific
                errors.append({"model_name": candidate, "error": _ascii_error(exc)})

        self._model = None
        self._active_model_name = ""
        self._last_error = json.dumps(errors, ensure_ascii=True, sort_keys=True)
        return self.get_backend_info()

    def unload_model(self) -> dict[str, Any]:
        """Unload model if the backend exposes a no-arg close/unload hook."""

        model = self._model
        if model is not None:
            for attr in ("unload", "close", "shutdown"):
                hook = getattr(model, attr, None)
                if hook is None:
                    continue
                try:
                    hook()
                    break
                except Exception as exc:  # unload should not crash callers
                    self._last_error = f"unload_failed:{_ascii_error(exc)}"
                    break
        self._model = None
        self._active_model_name = ""
        return self.get_backend_info()

    def _call_infer_method(
        self,
        method: Any,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
    ) -> Any:
        attempts = [
            lambda: method(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            ),
            lambda: method(prompt=prompt, max_tokens=max_tokens, temperature=temperature),
            lambda: method(prompt=prompt),
            lambda: method(prompt, system_prompt=system_prompt, max_tokens=max_tokens, temperature=temperature),
            lambda: method(prompt, max_tokens=max_tokens, temperature=temperature),
            lambda: method(prompt),
        ]
        last_error: BaseException | None = None
        for attempt in attempts:
            try:
                return attempt()
            except TypeError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("infer_call_failed")

    def _raw_infer(self, prompt: str, system_prompt: str | None, max_tokens: int, temperature: float) -> Any:
        if self._model is None:
            raise RuntimeError("model_not_loaded")
        for attr in ("infer", "generate", "complete", "chat"):
            method = getattr(self._model, attr, None)
            if method is None:
                continue
            return self._call_infer_method(method, prompt, system_prompt, max_tokens, temperature)
        if callable(self._model):
            return self._call_infer_method(self._model, prompt, system_prompt, max_tokens, temperature)
        raise RuntimeError("model_infer_method_not_found")

    def _extract_text(self, raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, Mapping):
            for key in ("text", "response", "output", "content", "message"):
                value = raw.get(key)
                if isinstance(value, str):
                    return value
                if isinstance(value, Mapping) and isinstance(value.get("content"), str):
                    return str(value.get("content"))
            choices = raw.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, Mapping):
                    message = first.get("message")
                    if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                        return str(message["content"])
                    if isinstance(first.get("text"), str):
                        return str(first["text"])
            return json.dumps(raw, ensure_ascii=True, sort_keys=True)
        return str(raw)

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Run optional local inference or return a structured error."""

        normalized_prompt = str(prompt or "").strip()
        if not normalized_prompt:
            return self._infer_error("empty_prompt")
        if self._model is None:
            load_info = self.load_model()
            if not load_info.get("loaded"):
                return self._infer_error(load_info.get("error") or "backend_unavailable")

        bounded_tokens = _safe_int(max_tokens, self.config.max_output_tokens, 1, self.config.max_output_tokens)
        bounded_temperature = _safe_float(temperature, 0.2, 0.0, 2.0)
        try:
            raw = self._raw_infer(normalized_prompt, system_prompt, bounded_tokens, bounded_temperature)
            text = _ascii_text(self._extract_text(raw))
            self._last_error = ""
            return {
                "schema": BACKEND_SCHEMA,
                "success": True,
                "used_llm": True,
                "local_only": True,
                "backend": self._runtime_backend or self.config.backend,
                "model_name": self._active_model_name,
                "text": text,
                "error": "",
            }
        except Exception as exc:  # inference is optional and must not crash ANA
            return self._infer_error(f"infer_failed:{_ascii_error(exc)}")

    def infer_with_rag(
        self,
        prompt: str,
        system_prompt: str | None = None,
        *,
        rag_query: str | None = None,
        rag_context: str | None = None,
        rag_bridge: Any | None = None,
        tools_spec: str = "",
        top_k: int = 5,
        memory_type: str | None = None,
        tags: Any | None = None,
        min_importance: float = 0.0,
        max_tokens: int | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Run inference with optional RAG and tool-awareness prompt injection."""

        normalized_prompt = str(prompt or "").strip()
        if not normalized_prompt:
            return self._infer_error("empty_prompt")

        effective_query = str(rag_query or normalized_prompt).strip()
        effective_context = _ascii_text(rag_context)
        rag_source = "provided" if effective_context else ""

        if self.config.use_rag and not effective_context:
            bridge = rag_bridge
            if bridge is None:
                try:
                    from .rag_bridge import get_rag_bridge

                    bridge = get_rag_bridge()
                    rag_source = "resolved"
                except Exception as exc:
                    bridge = None
                    rag_source = f"unavailable:{_ascii_error(exc)}"
            if bridge is not None and effective_query:
                try:
                    if hasattr(bridge, "build_context"):
                        effective_context = _ascii_text(
                            bridge.build_context(
                                effective_query,
                                top_k=top_k,
                                memory_type=memory_type,
                                tags=tags,
                                min_importance=min_importance,
                            )
                        )
                    elif hasattr(bridge, "retrieve"):
                        retrieval = bridge.retrieve(
                            effective_query,
                            top_k=top_k,
                            memory_type=memory_type,
                            tags=tags,
                            min_importance=min_importance,
                        )
                        lines: list[str] = []
                        results = retrieval.get("results") if isinstance(retrieval, Mapping) else []
                        if isinstance(results, list):
                            for index, item in enumerate(results, start=1):
                                if isinstance(item, Mapping):
                                    lines.append(f"[{index}] {item.get('content', '')}")
                        effective_context = _ascii_text("\n".join(lines))
                    rag_source = "bridge"
                except Exception as exc:
                    effective_context = ""
                    rag_source = f"bridge_error:{_ascii_error(exc)}"

        tool_specs = _ascii_text(tools_spec).strip() or None
        composed_system_prompt = compose_system_prompt(
            system_prompt or "",
            tool_specs=tool_specs,
            rag_context=effective_context,
        )
        result = self.infer(
            normalized_prompt,
            system_prompt=composed_system_prompt,
            max_tokens=max_tokens if max_tokens is not None else self.config.max_output_tokens,
            temperature=temperature,
        )
        result["rag_used"] = bool(effective_context)
        result["rag_query"] = effective_query
        result["rag_context"] = effective_context
        result["rag_source"] = rag_source
        result["tools_spec_used"] = bool(str(tools_spec or "").strip())
        result["use_rag"] = self.config.use_rag
        return result

    def _infer_error(self, error: str) -> dict[str, Any]:
        self._last_error = str(error)
        return {
            "schema": BACKEND_SCHEMA,
            "success": False,
            "used_llm": False,
            "local_only": True,
            "backend": self.config.backend,
            "model_name": self._active_model_name or self.config.model_name,
            "text": "",
            "error": _ascii_error(error),
        }

    def get_backend_info(self) -> dict[str, Any]:
        module_available = self._import_backend_module() is not None
        loaded = self._model is not None
        model_path = Path(self.config.model_path) if self.config.model_path else Path()
        if self.config.model_path and not model_path.is_absolute():
            model_path = ROOT / model_path
        return {
            "schema": BACKEND_SCHEMA,
            "backend": self.config.backend,
            "model_name": self.config.model_name,
            "fallback_model_name": self.config.fallback_model_name,
            "active_model_name": self._active_model_name,
            "device": self.config.device,
            "model_path": str(model_path) if self.config.model_path else "",
            "model_path_exists": model_path.exists() if self.config.model_path else False,
            "use_rag": self.config.use_rag,
            "max_context_tokens": self.config.max_context_tokens,
            "max_output_tokens": self.config.max_output_tokens,
            "n_ctx": self.config.n_ctx,
            "n_threads": self.config.n_threads,
            "n_gpu_layers": self.config.n_gpu_layers,
            "available": module_available,
            "backend_module_available": module_available,
            "inference_backend": self._runtime_backend or self.config.backend,
            "loaded": loaded,
            "load_attempted": self._load_attempted,
            "local_only": True,
            "optional": True,
            "hard_dependency": False,
            "error": _ascii_error(self._last_error),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect optional ANA MAX local LLM backend metadata.")
    parser.add_argument("--info", action="store_true", help="Print backend info")
    args = parser.parse_args(argv)
    backend = LocalLLMBackend()
    payload = backend.get_backend_info()
    if args.info:
        print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
