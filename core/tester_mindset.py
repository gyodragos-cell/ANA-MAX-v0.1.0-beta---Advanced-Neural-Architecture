"""
A.N.A. v15.1 - Tester Mindset Algorithm
=======================================
Algoritm dedicat pentru gândire critică de tip QA/Tester.
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
        Execută loop-ul de gândire tip Tester:
        1. Auto-documentare (Căutare strategii noi pe net).
        2. Analiza codului din perspectiva distrugerii/bug-urilor.
        3. Generare plan de testare.
        """
        logger.info("🧠 Activare 'Tester Mindset' Algorithm...")
        
        # 1. Auto-documentare (Internet Research)
        research_query = f"best testing strategies for {task_description} 2025 2026"
        research_results = self.agent.send_message(f"/web_search operation=search query='{research_query}'")
        
        # 2. Construire Prompt de Tester (Brainstorming Bug-uri)
        tester_prompt = f"""
        Ești acum în modul 'PROFESSIONAL QA TESTER'. 
        
        CONTEXT COD:
        {code_context}
        
        TASK DE TESTAT:
        {task_description}
        
        RECENT RESEARCH (Web):
        {research_results}
        
        ALGORITM DE GÂNDIRE:
        1. Identifică 'Happy Path' (ce ar trebui să meargă).
        2. Identifică 'Negative Scenarios' (cum putem strica asta?).
        3. Aplică 'Boundary Value Analysis' (valori limită).
        4. Verifică securitatea datelor (SQL injection, XSS, etc.).
        5. Sugerează tool-uri specifice (Pytest, Playwright, etc.).
        
        Te rog să oferi un raport de testare critic și sugestii de cod pentru teste.
        """
        
        return self.agent.send_message(tester_prompt)

    def generate_test_cases(self, feature_desc: str) -> List[str]:
        """Generează cazuri de testare bazate pe experiență și research."""
        prompt = f"Generați 5 cazuri de testare critice pentru funcționalitatea: {feature_desc}. Gândește ca un tester care vrea să găsească bug-uri ascunse."
        response = self.agent.send_message(prompt)
        return [response]
