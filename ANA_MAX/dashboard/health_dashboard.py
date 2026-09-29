"""ANA MAX health dashboard generator."""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.resource_loader import detect_theme, is_dev_mode, load_theme, t  # noqa: E402
from test_all_tools import DEFAULT_BRIDGE_URL, call_tool, fetch_tools  # noqa: E402

REPORT_ROOT = Path(os.environ.get("TEMP", ".")) / "ana-max-test-suite"


def get_json(url: str, timeout: int) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {"value": data}


def output_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_ROOT / stamp / "dashboard"
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="ANA MAX health dashboard generator.")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    bridge_url = args.bridge_url.rstrip("/")
    if not bridge_url.startswith("http://127.0.0.1:"):
        raise SystemExit("Refusing non-localhost bridge URL.")

    health = get_json(f"{bridge_url}/health", args.timeout)
    tools = fetch_tools(bridge_url, args.timeout)
    listed_names = {str(tool.get("name")) for tool in tools}
    if "tool_healthcheck" in listed_names:
        healthcheck = call_tool(
            bridge_url,
            "tool_healthcheck",
            {"scope": "safe"},
            args.timeout,
        )
    else:
        healthcheck = {
            "classification": "WARN",
            "detail": t("message_tool_healthcheck_not_listed"),
        }
    logs = get_json(f"{bridge_url}/logs", args.timeout)
    recent_logs = logs.get("logs", []) if isinstance(logs, dict) else []
    warnings = [item for item in recent_logs if str(item).lower().find("warn") >= 0]
    failures = [
        item
        for item in recent_logs
        if str(item).lower().find("error") >= 0
        or str(item).lower().find("fail") >= 0
    ]
    success = (
        healthcheck.get("classification") != "FAIL"
        and health.get("status") in {"ok", "healthy", True}
    )
    status = "PASS" if success else "WARN"
    status_text = t("status_pass") if success else t("status_warn")
    payload = {
        "suite": "dashboard",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "health": health,
        "tool_count": len(tools),
        "tool_healthcheck": healthcheck,
        "warnings": warnings[-20:],
        "failures": failures[-20:],
    }
    out = output_dir()
    (out / "health_dashboard.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    md = [
        f"# {t('dashboard_title')}",
        "",
        f"{t('status_label')}: {status_text}",
        f"{t('label_tool_count')}: {len(tools)}",
        f"{t('label_warnings')}: {len(warnings)}",
        f"{t('label_failures')}: {len(failures)}",
        "",
        f"## {t('label_tool_healthcheck')}",
        "",
        str(healthcheck.get("detail", t("status_ready"))),
    ]
    (out / "health_dashboard.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    theme_name = detect_theme("light")
    theme = load_theme(theme_name)
    title = t("dashboard_title")
    theme_label = t(f"theme_name_{theme_name}")
    dev_status = t("dev_mode_enabled") if is_dev_mode() else t("dev_mode_disabled")
    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>{html.escape(title)}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:{theme['background']};color:{theme['text']}}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}
.card{{background:{theme['panel_background']};border:1px solid {theme['panel_border']};border-radius:8px;padding:16px}}
pre{{white-space:pre-wrap;background:{theme['pre_background']};color:{theme['text']};padding:12px;border-radius:6px;overflow:auto}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>{html.escape(t('label_theme'))}: {html.escape(theme_label)} | {html.escape(t('dev_mode_label'))}: {html.escape(dev_status)}</p>
<div class='grid'>
<div class='card'><b>{html.escape(t('status_label'))}</b><p>{html.escape(status_text)}</p></div>
<div class='card'><b>{html.escape(t('label_tool_count'))}</b><p>{len(tools)}</p></div>
<div class='card'><b>{html.escape(t('label_warnings'))}</b><p>{len(warnings)}</p></div>
<div class='card'><b>{html.escape(t('label_failures'))}</b><p>{len(failures)}</p></div>
</div>
<h2>{html.escape(t('label_health'))}</h2><pre>{html.escape(json.dumps(health, indent=2, default=str))}</pre>
<h2>{html.escape(t('label_tool_healthcheck'))}</h2><pre>{html.escape(json.dumps(healthcheck, indent=2, default=str))}</pre>
<h2>{html.escape(t('label_recent_failures'))}</h2><pre>{html.escape(json.dumps(failures[-20:], indent=2, default=str))}</pre>
<h1>{html.escape(t('section_v21_foundations'))}</h1>
<p>{html.escape(t('dev_mode_safe_message'))}</p>
<div class='grid'>
<div class='card'><b>{html.escape(t('section_resource_inspector'))}</b><p>{html.escape(t('placeholder_resource_inspector'))}</p></div>
<div class='card'><b>{html.escape(t('section_dashboard_v2'))}</b><p>{html.escape(t('placeholder_dashboard_v2'))}</p></div>
<div class='card'><b>{html.escape(t('section_tool_health_visualizer'))}</b><p>{html.escape(t('placeholder_tool_health_visualizer'))}</p></div>
</div>
</body>
</html>"""
    (out / "health_dashboard.html").write_text(html_doc, encoding="utf-8")
    print(f"{t('status_label')}: {status_text}")
    print(f"{t('label_tool_count')}: {len(tools)}")
    print(f"Report folder: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
