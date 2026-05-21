"""
A.N.A. v15.1 - Critical Thinking Engine (White Hat & Pentest)
==========================================================
Algoritm universal de gandire critica pentru QA, Pentest si Security Research.
Include auto-documentare prin web search pentru cele mai noi amenintari si strategii.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CriticalThinkingEngine:
    def __init__(self, agent):
        self.agent = agent
        self.mindsets = {
            "QA": ["Boundary Value Analysis", "Equivalence Partitioning", "Error Guessing"],
            "Pentest": ["Reconnaissance", "Vulnerability Scanning", "Exploitation Analysis", "Privilege Escalation"],
            "Security": ["Threat Modeling", "Risk Assessment", "Zero Trust Analysis"],
            "Network": ["MITM Analysis", "Protocol Fingerprinting", "Packet Inspection Strategies"],
            "Science": ["Data Integrity", "Hypothesis Testing", "Statistical Significance", "Literature Review"],
            "Data_Analyst": ["Pattern Recognition", "Outlier Detection", "Trend Analysis", "Visualization Strategy"],
            "Game_Dev": ["Physics Simulation", "Game Loop Optimization", "Asset Management", "User Experience (UX)"]
        }

    def critical_analyze(self, context: str, task: str, mode: str = "Generalist") -> str:
        """
        Executa analiza critica bazata pe mindset-ul selectat:
        1. Research Web (Latest Trends/Threats).
        2. Analiza adversa (cum poate fi exploatat/stricat).
        3. Raport strategic de tip White Hat.
        """
        logger.info(f"🧠 Activare Critical Thinking Engine in modul: {mode}")
        
        # 1. Auto-documentare dinamica pe net
        research_query = f"latest {mode} strategies and vulnerabilities for {task} 2025 2026"
        research_results = self.agent.send_message(f"/web_search operation=search query='{research_query}'")
        
        # 2. Construire Prompt Adversarial (White Hat Approach)
        critical_prompt = f"""
        Esti in modul 'CRITICAL THINKING - {mode.upper()}'. Abordarea ta este de tip WHITE HAT RESEARCHER.
        
        CONTEXT:
        {context}
        
        TASK:
        {task}
        
        LATEST RESEARCH DATA:
        {research_results}
        
        ALGORITM DE GANDIRE ADVERSARIALA:
        1. ANALIZA SUPRAFATA: Unde sunt punctele de intrare cele mai expuse?
        2. ADVERSARIAL MINDSET: Daca ai fi un atacator, ce ai incerca prima data?
        3. MITM/SECURITY CHECK: Exista riscuri de interceptare sau manipulare a datelor?
        4. EROARE LOGICA: Exista scenarii in care sistemul se comporta imprevizibil?
        5. REMEDIERE: Ofera recomandari clare de securitate si stabilitate.
        
        Te rog sa oferi un raport tehnic detaliat si proactiv.
        """
        
        return self.agent.send_message(critical_prompt)

    def threat_model(self, target: str) -> str:
        """Genereaza un model de amenintare rapid."""
        prompt = f"Realizeaza un Threat Model rapid pentru: {target}. Identifica vectori de atac si contramasuri."
        return self.agent.send_message(prompt)
