from typing import Any, List

class ToolRouter:
    """
    Simplified Tool Router for models with limited VRAM (e.g. 7B on 4GB).
    Instead of passing complex JSON schemas to the model, this router
    gives the model 1, 2, or 3 clear options. The model only needs to
    reply with a number. The router maps it back to the complex action.
    """
    def __init__(self, llm_service):
        self.llm_service = llm_service

    def route_with_options(self, context: str, options: List[dict[str, Any]]) -> dict[str, Any]:
        """
        options: list of dicts with 'description' and 'payload'
        """
        if not options:
            raise ValueError("Must provide at least one option")

        prompt = f"Context:\n{context}\n\nOptions:\n"
        for idx, opt in enumerate(options, 1):
            prompt += f"{idx}. {opt['description']}\n"
        
        prompt += "\nOutput only the number (e.g., 1, 2, or 3) corresponding to the best option. NO TALKING."
        
        response = self.llm_service.complete({"prompt": prompt})
        text_resp = response.get("text", "").strip()
        
        # Parse the number
        try:
            import re
            match = re.search(r'\d+', text_resp)
            if not match:
                raise ValueError("No number found in response")
                
            choice_idx = int(match.group()) - 1
            if 0 <= choice_idx < len(options):
                return options[choice_idx]["payload"]
            else:
                return options[0]["payload"]
        except Exception:
            # Fallback to first option if parsing fails completely
            return options[0]["payload"]
