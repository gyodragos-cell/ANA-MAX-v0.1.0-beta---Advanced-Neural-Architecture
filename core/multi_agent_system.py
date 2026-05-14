import json
import logging
from core.autonomous_agent import AutonomousAgent

logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """
    Coordonează colaborarea între doi agenți:
    1. DevAgent: Scrie codul și rezolvă task-ul.
    2. AuditorAgent: Verifică securitatea, bug-urile și calitatea codului.
    """
    
    def __init__(self, main_agent):
        self.dev_agent = AutonomousAgent(main_agent)
        self.auditor_agent = AutonomousAgent(main_agent)
        self.main_agent = main_agent

    def execute_with_audit(self, task):
        print(f"🚀 [MULTI-AGENT] Starting task with Audit: {task}")
        
        # 1. DevAgent propune o soluție
        print("👨‍💻 [DEV AGENT] Generating solution...")
        dev_result = self.dev_agent.execute_task(task)
        
        # 2. AuditorAgent verifică ce a făcut DevAgent
        print("🛡️ [AUDITOR AGENT] Auditing changes...")
        audit_task = f"Analizează modificările făcute pentru task-ul: '{task}'. Verifică securitatea, posibilele bug-uri și conformitatea cu standardele."
        audit_result = self.auditor_agent.execute_task(audit_task)
        
        # 3. Dacă Auditor găsește probleme, DevAgent repară
        if not audit_result.get('success', False):
            print("⚠️ [AUDITOR] Issues found! Requesting fix from Dev Agent...")
            fix_task = f"Repară următoarele probleme identificate de Auditor: {audit_result.get('output')}"
            final_result = self.dev_agent.execute_task(fix_task)
            return final_result
            
        return dev_result

def get_multi_agent_system(main_agent):
    return MultiAgentSystem(main_agent)
