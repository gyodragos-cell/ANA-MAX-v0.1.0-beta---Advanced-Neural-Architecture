import json
import logging
from core.autonomous_agent import AutonomousAgent

logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """
    Coordoneaza colaborarea intre doi agenti:
    1. DevAgent: Scrie codul si rezolva task-ul.
    2. AuditorAgent: Verifica securitatea, bug-urile si calitatea codului.
    """
    
    def __init__(self, main_agent):
        self.dev_agent = AutonomousAgent(main_agent)
        self.auditor_agent = AutonomousAgent(main_agent)
        self.main_agent = main_agent

    def execute_with_audit(self, task):
        print(f"🚀 [MULTI-AGENT] Starting task with Audit: {task}")
        
        # 1. DevAgent propune o solutie
        print("👨‍💻 [DEV AGENT] Generating solution...")
        dev_result = self.dev_agent.execute_task(task)
        
        # 2. AuditorAgent verifica ce a facut DevAgent
        print("🛡️ [AUDITOR AGENT] Auditing changes...")
        audit_task = f"Analizeaza modificarile facute pentru task-ul: '{task}'. Verifica securitatea, posibilele bug-uri si conformitatea cu standardele."
        audit_result = self.auditor_agent.execute_task(audit_task)
        
        # 3. Daca Auditor gaseste probleme, DevAgent repara
        if not audit_result.get('success', False):
            print("⚠️ [AUDITOR] Issues found! Requesting fix from Dev Agent...")
            fix_task = f"Repara urmatoarele probleme identificate de Auditor: {audit_result.get('output')}"
            final_result = self.dev_agent.execute_task(fix_task)
            return final_result
            
        return dev_result

def get_multi_agent_system(main_agent):
    return MultiAgentSystem(main_agent)
