import logging
import base64
import json
import requests
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("ANA.VLMEngine")

class VLMDaemon:
    """
    Vision Language Model Daemon for ANA OS-27.
    Attempts to use Local Swarm if available, otherwise falls back to local CPU VLM.
    """
    def __init__(self, swarm_router_url: str = "http://localhost:8888"):
        self.swarm_router_url = swarm_router_url
        self.local_model_loaded = False
        self.model = None
        self.tokenizer = None
        
    def _load_local_model(self):
        if self.local_model_loaded:
            return
            
        logger.info("Loading local Moondream2 model on CPU (Fallback Mode)...")
        try:
            # We defer import so it doesn't crash if transformers isn't installed
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from PIL import Image
            
            # Using trust_remote_code=True for Moondream2
            # NOTE: For real deployment, this would be downloaded beforehand.
            self.model_id = "vikhyatk/moondream2"
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, trust_remote_code=True
            ).to("cpu")  # Force CPU to save GTX 1650 for Qwen
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.local_model_loaded = True
            logger.info("Local VLM loaded successfully.")
        except ImportError:
            logger.error("transformers library not found. Local VLM disabled.")
        except Exception as e:
            logger.error(f"Error loading local VLM: {e}")

    def analyze_image(self, image_path: str, prompt: str = "Describe what the user is doing and if there is an error on the screen.") -> Dict[str, Any]:
        """
        Analyze an image. Prefers Swarm.
        """
        # Try Swarm first
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
            payload = {
                "image_b64": img_b64,
                "prompt": prompt
            }
            
            res = requests.post(f"{self.swarm_router_url}/task", json={"task_type": "vlm", "payload": payload}, timeout=3)
            if res.status_code == 200:
                task_id = res.json()["task_id"]
                logger.info(f"Delegated VLM task to Swarm (Task: {task_id})")
                
                # Poll for result (timeout 30s)
                for _ in range(15):
                    status_res = requests.get(f"{self.swarm_router_url}/task/status/{task_id}", timeout=2)
                    if status_res.status_code == 200:
                        status_data = status_res.json()
                        if status_data["status"] == "completed":
                            return status_data["result"]
                        elif status_data["status"] == "failed":
                            logger.warning(f"Swarm VLM task failed: {status_data['result']}")
                            break
                    time.sleep(2)
        except Exception as e:
            logger.info(f"Swarm router not available or failed: {e}. Falling back to local.")
            
        # Fallback to local CPU
        return self._analyze_local(image_path, prompt)
        
    def _analyze_local(self, image_path: str, prompt: str) -> Dict[str, Any]:
        self._load_local_model()
        if not self.local_model_loaded:
            return {"intent": "unknown", "error_visible": False, "details": "VLM not available (no swarm, no local)"}
            
        from PIL import Image
        
        try:
            image = Image.open(image_path)
            enc_image = self.model.encode_image(image)
            answer = self.model.answer_question(enc_image, prompt, self.tokenizer)
            
            # Simple heuristic parsing of the answer
            error_visible = "error" in answer.lower() or "exception" in answer.lower()
            return {
                "intent": "user_activity",
                "error_visible": error_visible,
                "details": answer
            }
        except Exception as e:
            logger.error(f"Local VLM inference failed: {e}")
            return {"intent": "error", "error_visible": False, "details": str(e)}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    vlm = VLMDaemon()
    # vlm.analyze_image("test.png")
