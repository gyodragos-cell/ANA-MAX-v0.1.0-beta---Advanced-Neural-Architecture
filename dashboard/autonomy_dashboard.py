# PATCH_START v20_phase5
"""Read-only HTML dashboard for ANA MAX v20 autonomy outputs."""

from __future__ import annotations

import html
import json
from typing import Any


V20_SECTIONS = [
    ("ana_health_check", "ANA Health Check"),
    ("baseline_update_suggester", "Baseline Update Suggester"),
    ("docs_generator", "Docs Generator"),
    ("ana_patch_suggester", "ANA Patch Suggester"),
    ("runtime_guard", "Runtime Guard"),
]


def _safe_json(value: Any) -> str:
    return html.escape(json.dumps(value, indent=2, sort_keys=True, default=str))


def _default_outputs() -> dict[str, Any]:
    from tools.v20 import ana_health_check
    from tools.v20 import ana_patch_suggester
    from tools.v20 import baseline_update_suggester
    from tools.v20 import docs_generator
    from tools.v20 import runtime_guard

    return {
        "ana_health_check": ana_health_check.run({"include_contracts": False}),
        "baseline_update_suggester": baseline_update_suggester.run(
            {"current": {"tool_count": 80}}
        ),
        "docs_generator": docs_generator.run({"document": "SUMMARY.md"}),
        "ana_patch_suggester": ana_patch_suggester.run({"issues": []}),
        "runtime_guard": runtime_guard.run({}),
    }


def _render_sections(outputs: dict[str, Any]) -> str:
    sections = []
    for key, title in V20_SECTIONS:
        payload = outputs.get(key, {"success": False, "error": "missing output"})
        status = "OK" if isinstance(payload, dict) and payload.get("success") else "WARN"
        sections.append(
            "<section class=\"panel\">"
            f"<h2>{html.escape(title)}</h2>"
            f"<p class=\"status\">Status: {html.escape(status)}</p>"
            f"<pre>{_safe_json(payload)}</pre>"
            "</section>"
        )
    return "\n".join(sections)


def render_dashboard(outputs: dict[str, Any] | None = None) -> str:
    """Return a complete HTML dashboard string without writing files."""
    outputs = outputs if outputs is not None else _default_outputs()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ANA MAX v20 Autonomy Dashboard</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #101419; color: #edf2f7; }}
    main {{ max-width: 1160px; margin: 0 auto; padding: 28px; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; }}
    .intro {{ color: #a8b3c2; margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .panel {{ border: 1px solid #2f3a48; border-radius: 8px; padding: 16px; background: #171d24; }}
    .panel h2 {{ font-size: 17px; margin: 0 0 8px; }}
    .status {{ color: #8bd3ff; margin: 0 0 10px; }}
    pre {{ overflow: auto; white-space: pre-wrap; word-break: break-word; background: #0b0f14; padding: 12px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main>
    <h1>ANA MAX v20 Autonomy Dashboard</h1>
    <p class="intro">Manual, read-only view of v20 autonomy tool outputs. No writes. No auto-run.</p>
    <div class="grid">
      {_render_sections(outputs)}
    </div>
  </main>
</body>
</html>
"""


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    outputs = args.get("outputs")
    if outputs is not None and not isinstance(outputs, dict):
        return {"success": False, "error": "outputs must be a dict when provided"}
    html_text = render_dashboard(outputs)
    return {
        "success": True,
        "format": "html",
        "html": html_text,
        "sections": [key for key, _ in V20_SECTIONS],
        "written": False,
    }


# PATCH_END v20_phase5
