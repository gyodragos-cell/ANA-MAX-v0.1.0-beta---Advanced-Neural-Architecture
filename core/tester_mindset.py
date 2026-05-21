"""
A.N.A. v15.1 - Tester Mindset Algorithm
=======================================
Algoritm dedicat pentru gandire critica de tip QA/Tester.
Include auto-documentare prin web search pentru cele mai noi strategii.
"""

import logging
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TesterMindset:
    def __init__(self, agent):
        self.agent = agent
        self.test_strategies = [
            "Boundary Value Analysis",
            "Equivalence Partitioning",
            "Error Guessing",
            "Exploratory Testing",
            "Regression Testing"
        ]

    def think_like_a_tester(self, code_context: str, task_description: str) -> str:
        """
        Executa loop-ul de gandire tip Tester:
        1. Auto-documentare (Cautare strategii noi pe net).
        2. Analiza codului din perspectiva distrugerii/bug-urilor.
        3. Generare plan de testare.
        """
        logger.info("🧠 Activare 'Tester Mindset' Algorithm...")
        
        # 1. Auto-documentare (Internet Research)
        research_query = f"best testing strategies for {task_description} 2025 2026"
        research_results = self.agent.send_message(f"/web_search operation=search query='{research_query}'")
        
        # 2. Construire Prompt de Tester (Brainstorming Bug-uri)
        tester_prompt = f"""
        Esti acum in modul 'PROFESSIONAL QA TESTER'. 
        
        CONTEXT COD:
        {code_context}
        
        TASK DE TESTAT:
        {task_description}
        
        RECENT RESEARCH (Web):
        {research_results}
        
        ALGORITM DE GANDIRE:
        1. Identifica 'Happy Path' (ce ar trebui sa mearga).
        2. Identifica 'Negative Scenarios' (cum putem strica asta?).
        3. Aplica 'Boundary Value Analysis' (valori limita).
        4. Verifica securitatea datelor (SQL injection, XSS, etc.).
        5. Sugereaza tool-uri specifice (Pytest, Playwright, etc.).
        
        Te rog sa oferi un raport de testare critic si sugestii de cod pentru teste.
        """
        
        return self.agent.send_message(tester_prompt)

    def generate_test_cases(self, feature_desc: str) -> List[str]:
        """Genereaza cazuri de testare bazate pe experienta si research."""
        prompt = f"Generati 5 cazuri de testare critice pentru functionalitatea: {feature_desc}. Gandeste ca un tester care vrea sa gaseasca bug-uri ascunse."
        response = self.agent.send_message(prompt)
        return [response]
