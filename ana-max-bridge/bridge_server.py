"""Local ANA MAX bridge service for Copilot-style HTTP tool clients."""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import requests
import yaml
from flask import Flask, jsonify, request, send_from_directory

from tool_mapper import ToolMapper
from watchdog import BridgeWatchdog


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


class BridgeState:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.started_at = time.time()
        self.running = bool(config.get("bridge", {}).get("auto_start", True))
        self.tools: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []

    def add_log(self, level: str, message: str, **data: Any) -> None:
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level,
            "message": message,
            "data": data,
        }
        self.logs.append(entry)
        max_entries = int(self.config.get("bridge", {}).get("max_logs", 250))
        if len(self.logs) > max_entries:
            self.logs = self.logs[-max_entries:]


def _ana_headers(config: Dict[str, Any]) -> Dict[str, str]:
    if config.get("local_dev", False):
        return {}
    env_names = config.get("ana_max", {}).get("api_key_env", ["ANA_MCP_KEY", "MCP_API_KEY"])
    for env_name in env_names:
        token = os.environ.get(env_name)
        if token:
            return {"Authorization": f"Bearer {token}"}
    return {}


def _ana_url(config: Dict[str, Any], path: str) -> str:
    base_url = config.get("ana_max", {}).get("base_url", "http://127.0.0.1:8765").rstrip("/")
    return f"{base_url}{path}"


def create_app(config: Dict[str, Any] | None = None) -> Flask:
    config = config or load_config()
    app = Flask(__name__, static_folder=None)
    state = BridgeState(config)
    mapper = ToolMapper(config)
    watchdog = BridgeWatchdog(config)

    def request_is_localhost() -> bool:
        return request.remote_addr == "127.0.0.1"

    @app.before_request
    def enforce_local_dev_boundary():
        if config.get("local_dev", False) and not request_is_localhost():
            return jsonify({"success": False, "error": "Local dev mode only accepts localhost"}), 403

    def ana_request(method: str, path: str, **kwargs: Any) -> Tuple[dict[str, Any], int]:
        timeout = float(config.get("ana_max", {}).get("timeout_seconds", 20))
        headers = kwargs.pop("headers", {})
        headers.update(_ana_headers(config))
        try:
            response = requests.request(
                method,
                _ana_url(config, path),
                timeout=timeout,
                headers=headers,
                **kwargs,
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {"text": response.text}
            return payload, response.status_code
        except requests.RequestException as exc:
            return {"success": False, "error": str(exc)}, 502

    def reload_tools() -> Tuple[dict[str, Any], int]:
        payload, status = ana_request("GET", "/tools")
        if status >= 400:
            if status in {401, 403, 503} and not watchdog.should_report_auth_warning():
                state.add_log("info", "ANA MAX auth warning suppressed in local dev", status=status)
            else:
                state.add_log("error", "Failed to load ANA MAX tools", status=status, payload=payload)
            return payload, status
        tools = payload.get("tools", [])
        state.tools = mapper.map_tools(tools)
        state.add_log("info", "Reloaded tools", count=len(state.tools))
        return {"tools": state.tools, "count": len(state.tools)}, 200

    @app.get("/")
    def index():
        return send_from_directory(BASE_DIR / "ui", "index.html")

    @app.get("/ui/<path:filename>")
    def ui_file(filename: str):
        return send_from_directory(BASE_DIR / "ui", filename)

    @app.get("/health")
    def health():
        ana_health, ana_status = ana_request("GET", "/health")
        return jsonify(
            {
                "status": "online" if state.running else "offline",
                "bridge_running": state.running,
                "uptime_seconds": round(time.time() - state.started_at, 2),
                "tools_count": len(state.tools),
                "ana_status_code": ana_status,
                "ana": ana_health,
                "watchdog": watchdog.snapshot(),
            }
        )

    @app.post("/start")
    def start():
        state.running = True
        result, status = reload_tools()
        state.add_log("info", "Bridge started")
        return jsonify({"success": status < 400, "state": "online", **result}), status

    @app.post("/stop")
    def stop():
        state.running = False
        state.add_log("info", "Bridge stopped")
        return jsonify({"success": True, "state": "offline"})

    @app.get("/tools/list")
    def tools_list():
        if not state.tools:
            result, status = reload_tools()
            if status >= 400:
                return jsonify(result), status
        return jsonify({"tools": state.tools, "count": len(state.tools)})

    @app.post("/tools/reload")
    def tools_reload():
        result, status = reload_tools()
        return jsonify(result), status

    @app.get("/logs")
    def logs():
        return jsonify({"logs": state.logs, "count": len(state.logs)})

    @app.post("/tools/call")
    @app.post("/execute")
    def call_tool():
        if not state.running:
            return jsonify({"success": False, "error": "Bridge is stopped"}), 409

        body = request.get_json(silent=True) or {}
        tool_name = body.get("tool") or body.get("name")
        params = body.get("params") or body.get("arguments") or {}
        verdict = watchdog.validate_call(tool_name, params)
        if not verdict.allowed:
            state.add_log("warning", "Blocked unsafe tool call", tool=tool_name, reason=verdict.reason)
            return jsonify({"success": False, "error": verdict.reason}), 400

        payload, status = ana_request("POST", "/execute", json={"tool": tool_name, "params": params})
        out_verdict = watchdog.validate_response(tool_name, payload)
        if not out_verdict.allowed:
            state.add_log("warning", "Blocked unsafe tool response", tool=tool_name, reason=out_verdict.reason)
            return jsonify({"success": False, "error": out_verdict.reason}), 502

        state.add_log("info", "Forwarded tool call", tool=tool_name, status=status)
        return jsonify(payload), status

    @app.post("/mcp")
    def mcp_passthrough():
        if not state.running:
            return jsonify({"jsonrpc": "2.0", "error": {"code": -32000, "message": "Bridge is stopped"}}), 409
        body = request.get_json(silent=True) or {}
        payload, status = ana_request("POST", "/mcp", json=body)
        return jsonify(payload), status

    reload_tools()
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ANA MAX local bridge service.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    host = args.host or config.get("bridge", {}).get("host", "127.0.0.1")
    port = args.port or int(config.get("bridge", {}).get("port", 8790))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    create_app(config).run(host=host, port=port)


if __name__ == "__main__":
    main()
