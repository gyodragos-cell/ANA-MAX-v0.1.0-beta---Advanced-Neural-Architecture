"""
Bot Factory for local CLI bots.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class BotFactory:
    """Generate local Ollama-first CLI bot projects."""

    def __init__(self, output_root: str, default_model: str = "mistral:7b"):
        self.output_root = Path(output_root).resolve()
        self.default_model = default_model
        self.output_root.mkdir(parents=True, exist_ok=True)

    def create_bot(self, spec: str, name: str = "", output_dir: str = "") -> Dict[str, Any]:
        bot_name = name or self._derive_name(spec)
        slug = self._slugify(bot_name)
        project_dir = Path(output_dir).resolve() if output_dir else self.output_root / slug
        project_dir.mkdir(parents=True, exist_ok=True)

        directories = [
            project_dir / "config",
            project_dir / "memory",
            project_dir / "logs",
            project_dir / "tests",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        config_path = project_dir / "config" / "settings.json"
        main_path = project_dir / "main.py"
        test_path = project_dir / "tests" / "test_smoke.py"
        readme_path = project_dir / "README.md"
        bat_path = project_dir / f"START_{slug.upper()}.bat"
        requirements_path = project_dir / "requirements.txt"

        config_data = {
            "name": bot_name,
            "model": self.default_model,
            "api_url": "http://127.0.0.1:11434/api/generate",
            "memory_file": "memory/conversation.jsonl",
        }
        config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        main_path.write_text(self._render_main(bot_name), encoding="utf-8")
        test_path.write_text(self._render_test(slug), encoding="utf-8")
        readme_path.write_text(self._render_readme(bot_name, slug, spec), encoding="utf-8")
        bat_path.write_text(self._render_bat(main_path.name), encoding="utf-8")
        requirements_path.write_text("requests>=2.31.0\n", encoding="utf-8")

        files = [str(path) for path in [config_path, main_path, test_path, readme_path, bat_path, requirements_path]]
        return {
            "name": bot_name,
            "slug": slug,
            "project_dir": str(project_dir),
            "files": files,
            "spec": spec,
        }

    def _derive_name(self, spec: str) -> str:
        quoted = re.findall(r"[\"']([^\"']+)[\"']", spec)
        if quoted:
            return quoted[0][:40]
        words = [word for word in re.split(r"[^A-Za-z0-9]+", spec) if word]
        if not words:
            return "ana_cli_bot"
        return "_".join(words[:4])

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
        return slug or "ana_cli_bot"

    def _render_main(self, bot_name: str) -> str:
        return f'''#!/usr/bin/env python3
import argparse
import json
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def generate(prompt: str, config: dict) -> str:
    payload = json.dumps({{
        "model": config["model"],
        "prompt": prompt,
        "stream": False,
    }}).encode("utf-8")
    request = urllib.request.Request(
        config["api_url"],
        data=payload,
        headers={{"Content-Type": "application/json"}},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("response", "")


def main() -> int:
    parser = argparse.ArgumentParser(description="{bot_name} - local CLI bot")
    parser.add_argument("--prompt", help="Single prompt mode")
    args = parser.parse_args()
    config = load_config()

    if args.prompt:
        print(generate(args.prompt, config))
        return 0

    print("{bot_name} ready. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("{bot_name}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\\nBye.")
            return 0

        if not user_input:
            continue
        if user_input.lower() in {{"exit", "quit"}}:
            print("Bye.")
            return 0
        print(generate(user_input, config))


if __name__ == "__main__":
    raise SystemExit(main())
'''

    @staticmethod
    def _render_test(slug: str) -> str:
        return f'''import subprocess
import sys
from pathlib import Path


def test_help():
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(project_root / "main.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
'''

    @staticmethod
    def _render_readme(bot_name: str, slug: str, spec: str) -> str:
        return f"""# {bot_name}

Local CLI bot generated by ANA Engineer.

## Spec
{spec}

## Files
- `main.py`
- `config/settings.json`
- `tests/test_smoke.py`
- `START_{slug.upper()}.bat`

## Run
- `python main.py`
- `START_{slug.upper()}.bat`
"""

    @staticmethod
    def _render_bat(main_filename: str) -> str:
        return f"""@echo off
setlocal
cd /d "%~dp0"
python "{main_filename}" %*
pause
"""
