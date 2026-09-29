"""
ANA MAX - digital_immune_system.py
====================================
Digital Immune System (Antivirus pentru Agenti LLM)

Actioneaza ca un "Semantic Firewall" intre agenti si OS-ul gazda.
Monitorizeaza argumentele pasate tool-urilor si blocheaza executiile
daca recunoaste semnaturi ofensive sau prompt injections.

Protectie impotriva:
1. Citire de secrete (ex: cat .env, id_rsa)
2. Stergeri in masa (ex: rm -rf /)
3. Exfiltrare date (ex: curl spre domenii externe necunoscute)
4. Modificare credentiale
"""
from __future__ import annotations

import logging
import re
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.DigitalImmuneSystem")

# Reguli de tip YARA (semnaturi de atac)
SIGNATURES = [
    {"id": "R01", "desc": "Accesare secrete (.env, ssh, pem)", "regex": r"(\.env|id_rsa|id_dsa|\.pem|\.aws/credentials|shadow|passwd)"},
    {"id": "R02", "desc": "Stergere masiva/fortata", "regex": r"(rm\s+-r|Remove-Item\s+-Recurse|del\s+/s)"},
    {"id": "R03", "desc": "Exfiltrare externa", "regex": r"(curl|wget|Invoke-WebRequest).*?(http://|https://)(?!(localhost|127\.0\.0\.1|api\.openai\.com|api\.anthropic\.com))"},
    {"id": "R04", "desc": "Modificare credentiale sistem", "regex": r"(net\s+user|chmod|chown|Set-LocalUser)"},
    {"id": "R05", "desc": "Reverse shell", "regex": r"(nc\s+-e|bash\s+-i|/dev/tcp/)"},
]

# Stare globala a sistemului imunitar
_quarantine: list[dict] = []
_active = True


def _scan_payload(tool_name: str, args: dict) -> list[dict]:
    """Scaneaza argumentele tool-ului impotriva semnaturilor malitioase."""
    if not _active:
        return []
        
    payload_str = str(args)
    threats = []
    
    for sig in SIGNATURES:
        if re.search(sig["regex"], payload_str, re.IGNORECASE):
            threats.append(sig)
            
    return threats


def guard_execution(tool_name: str, args: dict) -> tuple[bool, str]:
    """
    Se apela inainte de executia oricarui tool periculos (ex: run_command).
    Daca returneaza (False, "motiv"), executia este BLOCATA.
    """
    threats = _scan_payload(tool_name, args)
    
    if threats:
        reasons = [t["desc"] for t in threats]
        alert_msg = f"Imunitate Digitala declansata! Executia blocata. Motive: {', '.join(reasons)}"
        
        # Pune incidentul in carantina
        _quarantine.append({
            "tool": tool_name,
            "args": args,
            "threats": threats,
            "timestamp": __import__("time").time()
        })
        logger.warning(f"[IMMUNE SYSTEM] Blocked {tool_name}. Threats: {reasons}")
        
        return False, alert_msg
        
    return True, "Safe"


class DigitalImmuneSystemTool(Tool):
    """Interfata de control pentru Sistemul Imunitar."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="immune_system",
            description="Antivirus semantic pentru agenti. Intercepteaza comenzile malitioase si protejeaza host-ul. Actiuni: 'status', 'toggle', 'quarantine'.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="'status', 'toggle' (porneste/opreste scutul), 'quarantine' (vezi incidentele blocate)",
                    type="string",
                    required=True,
                    choices=["status", "toggle", "quarantine"],
                ),
                ToolParameter(
                    name="state",
                    description="Pentru toggle: 'on' sau 'off'",
                    type="string",
                    required=False,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        global _active
        action = kwargs.get("action")
        
        if action == "status":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "active": _active,
                    "signatures_loaded": len(SIGNATURES),
                    "incidents_blocked": len(_quarantine)
                },
                message=f"Sistem Imunitar: {'ACTIV' if _active else 'OPRIT'}."
            )
            
        elif action == "toggle":
            req_state = kwargs.get("state", "").lower()
            if req_state == "on":
                _active = True
            elif req_state == "off":
                _active = False
            else:
                _active = not _active
                
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"active": _active},
                message=f"Sistem Imunitar a fost {'pornit' if _active else 'oprit'}."
            )
            
        elif action == "quarantine":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"quarantine": _quarantine[-50:]},  # ultimele 50
                message=f"Incidentele din carantina ({len(_quarantine)} total)."
            )
            
        return ToolResult(status=ToolStatus.ERROR, error="Actiune invalida.")
