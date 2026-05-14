"""
A.N.A. v15.1 - Critical Thinking Engine (White Hat & Pentest)
==========================================================
Algoritm universal de gândire critică pentru QA, Pentest și Security Research.
Include auto-documentare prin web search pentru cele mai noi amenințări și strategii.
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
        Execută analiza critică bazată pe mindset-ul selectat:
        1. Research Web (Latest Trends/Threats).
        2. Analiză adversă (cum poate fi exploatat/stricat).
        3. Raport strategic de tip White Hat.
        """
        logger.info(f"🧠 Activare Critical Thinking Engine în modul: {mode}")
        
        # 1. Auto-documentare dinamică pe net
        research_query = f"latest {mode} strategies and vulnerabilities for {task} 2025 2026"
        research_results = self.agent.send_message(f"/web_search operation=search query='{research_query}'")
        
        # 2. Construire Prompt Adversarial (White Hat Approach)
        critical_prompt = f"""
        Ești în modul 'CRITICAL THINKING - {mode.upper()}'. Abordarea ta este de tip WHITE HAT RESEARCHER.
        
        CONTEXT:
        {context}
        
        TASK:
        {task}
        
        LATEST RESEARCH DATA:
        {research_results}
        
        ALGORITM DE GÂNDIRE ADVERSARIALĂ:
        1. ANALIZĂ SUPRAFAȚĂ: Unde sunt punctele de intrare cele mai expuse?
        2. ADVERSARIAL MINDSET: Dacă ai fi un atacator, ce ai încerca prima dată?
        3. MITM/SECURITY CHECK: Există riscuri de interceptare sau manipulare a datelor?
        4. EROARE LOGICĂ: Există scenarii în care sistemul se comportă imprevizibil?
        5. REMEDIERE: Oferă recomandări clare de securitate și stabilitate.
        
        Te rog să oferi un raport tehnic detaliat și proactiv.
        """
        
        return self.agent.send_message(critical_prompt)

    def threat_model(self, target: str) -> str:
        """Generează un model de amenințare rapid."""
        prompt = f"Realizează un Threat Model rapid pentru: {target}. Identifică vectori de atac și contramăsuri."
        return self.agent.send_message(prompt)
