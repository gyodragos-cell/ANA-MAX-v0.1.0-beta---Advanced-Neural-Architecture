"""
A.N.A. v15.1 - Multi-Model Consensus Engine
==========================================
Sistem de votare între modele (Gemini, Ollama, Grok) pentru decizii critice.
Asigură o acuratețe maximă și reduce halucinațiile.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConsensusEngine:
    def __init__(self, agent):
        self.agent = agent
        self.enabled = True

    def get_consensus(self, task: str, primary_response: str) -> str:
        """
        Solicită o a doua opinie de la un alt backend disponibil 
        pentru a valida decizia/codul generat.
        """
        if not self.enabled:
            return primary_response

        # Identificăm backends disponibile (altele decât cel curent)
        available_backends = []
        if self.agent.backend != "gemini" and self.agent.ai_client: available_backends.append("gemini")
        if self.agent.backend != "ollama" and hasattr(self.agent, 'ollama_client'): available_backends.append("ollama")
        if self.agent.backend != "grok" and hasattr(self.agent, 'grok_api_keys'): available_backends.append("grok")

        if not available_backends:
            return primary_response

        # Alegem un backend secundar pentru validare
        secondary_backend = available_backends[0]
        logger.info(f"⚖️ Consensus: Validare decizie cu {secondary_backend}...")

        validation_prompt = f"""
        Suntem într-un proces de consens. Un alt model AI a propus următoarea soluție pentru task-ul: "{task}"
        
        Soluția propusă:
        {primary_response}
        
        Te rog să analizezi critic această soluție. 
        Dacă este corectă, răspunde cu "VALID". 
        Dacă are erori, explică-le pe scurt și oferă o variantă corectată.
        """

        try:
            # Apelăm temporar backend-ul secundar
            original_backend = self.agent.backend
            self.agent.backend = secondary_backend
            
            # Notă: Folosim o metodă privată de trimitere pentru a nu polua istoricul principal
            if secondary_backend == "gemini":
                validation_resp = self.agent._send_gemini(validation_prompt)
            elif secondary_backend == "ollama":
                validation_resp = self.agent._send_ollama(validation_prompt)
            elif secondary_backend == "grok":
                validation_resp = self.agent._send_grok(validation_prompt)
            else:
                validation_resp = "VALID"

            self.agent.backend = original_backend

            if "VALID" in validation_resp.upper() and len(validation_resp) < 20:
                logger.info("✅ Consensus atins: Soluția este validată.")
                return primary_response
            else:
                logger.warning("⚠️ Consensus: Modelul secundar a propus corecții.")
                return f"{primary_response}\n\n--- ⚖️ NOTĂ CONSENS ({secondary_backend}) ---\n{validation_resp}"

        except Exception as e:
            logger.error(f"Eroare în motorul de consens: {e}")
            self.agent.backend = original_backend
            return primary_response
