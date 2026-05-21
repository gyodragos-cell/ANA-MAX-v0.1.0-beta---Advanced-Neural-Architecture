"""
A.N.A. v15.1 - Safety & Ethics Protocol
======================================
Defineste limitele etice si de siguranta ale prototipului.
Prevenirea utilizarii malitioase si asigurarea caracterului educational.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SafetyProtocol:
    def __init__(self):
        from core.config import config
        self.restricted_topics = [
            "bioweapons", "explosives", "illegal_drugs", 
            "hacking_infrastructure", "malware_distribution",
            "personal_data_theft"
        ]
        self.is_prototype = True
        self.educational_focus = True
        # Citeste sandbox_mode din config, default True pentru teste
        self.sandbox_mode = config.get('safety.sandbox_mode', True)

    def validate_request(self, message: str) -> Dict[str, Any]:
        """Verifica daca cererea incalca protocolul de siguranta."""
        if self.sandbox_mode:
            return {"safe": True, "reason": None}
            
        msg_lower = message.lower()
        
        for topic in self.restricted_topics:
            if topic.replace("_", " ") in msg_lower:
                logger.warning(f"⚠️ Protocol Siguranta: Topic restrictionat detectat: {topic}")
                return {
                    "safe": False,
                    "reason": f"Acest task implica un subiect restrictionat ({topic}) conform protocolului de siguranta ANA Prototip."
                }
        
        return {"safe": True, "reason": None}

    def get_safety_disclaimer(self) -> str:
        # Disclaimer-ul a fost scos la cererea utilizatorului pentru focus mai bun
        return ""
