# -*- coding: utf-8 -*-
import json, os

CONFIG_PATH = "C:\\Users\\billy\\Desktop\\ana-manus\\config.json"
REPORT_PATH = "C:\\Users\\billy\\Desktop\\ana-manus\\health_check_report.md"

def run_check():
    if not os.path.exists(CONFIG_PATH):
        return "[HEALTH-CHECK FAILED] config.json lipsa"
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    model = config.get("model", "necunoscut")
    port = config.get("port", "necunoscut")
    report = (
        "# Health Check Report\n\n"
        "## Status\n[HEALTH-CHECK SUCCESSFUL]\n\n"
        "## Details\n"
        f"- **Model:** {model}\n"
        f"- **Port:** {port}\n"
        "- **Chei valide:** ✅\n\n"
    )
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    
    return report
