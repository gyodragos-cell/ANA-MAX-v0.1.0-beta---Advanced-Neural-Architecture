"""
ANA_MAX Autonomous Brain
========================
Nucleul de decizie proactiva. Permite agentului sa monitorizeze sistemul 
si sa ia masuri de optimizare fara interventia directa a utilizatorului.
"""

import logging
import time
from tools.windows_insight_tool import WindowsInsightTool
from tools.desktop_control_tool import DesktopControlTool

logger = logging.getLogger(__name__)

class AutonomousBrain:
    def __init__(self):
        self.insight = WindowsInsightTool()
        self.desktop = DesktopControlTool()
        self.is_running = False

    def start_patrol(self):
        """Incepe monitorizarea proactiva."""
        logger.info("[BRAIN] Patrulare autonoma ACTIVATA.")
        self.is_running = True
        self.insight.execute(operation="start_monitor")
        
        # Bucla de decizie
        while self.is_running:
            events = self.insight.execute(operation="get_events").data.get("events", [])
            for event in events:
                self._analyze_event(event)
            time.sleep(5)

    def _analyze_event(self, event):
        """Analizeaza evenimentele si decide actiuni."""
        if event['category'] == 'PROC' and 'error' in event['details'].lower():
            logger.warning(f"[BRAIN] Detectata eroare proces: {event['details']}. Initiere diagnostic...")
            # Aici am putea adauga logica de fixare automata
            
        if event['category'] == 'CLIP':
            # Putem retine contextul pentru a ajuta utilizatorul mai tarziu
            pass

if __name__ == "__main__":
    # Test scurt
    brain = AutonomousBrain()
    print("🧠 Creierul ANA_MAX este acum LIBER.")
