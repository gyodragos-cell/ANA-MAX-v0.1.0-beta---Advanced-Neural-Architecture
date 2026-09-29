import json
from pathlib import Path

class SelfHealingEngine:
    def __init__(self, ana_max_root: Path):
        self.ana_max_root = ana_max_root
        self.knowledge_base = self._load_knowledge()

    def _load_knowledge(self):
        # Load from CHANGELOG, ARCHITECTURE, etc.
        # This is a simplified version
        knowledge = {
            "NameError": "Check if all local imports are present at the function level to avoid circular imports.",
            "ModuleNotFoundError": "Verify if the module is in sys.path or if it needs to be installed via pip.",
            "PermissionError": "Try running the command with administrative privileges or check if the file is locked by another process.",
            "JSONDecodeError": "Check if the file is empty or corrupted. Validate JSON structure."
        }
        return knowledge

    def analyze_error(self, error_msg: str):
        print(f"[Self-Healing] Analyzing error: {error_msg}")
        for error_type, suggestion in self.knowledge_base.items():
            if error_type in error_msg:
                return {
                    "error_type": error_type,
                    "suggestion": suggestion,
                    "action": "re-run with fix"
                }
        return {"error_type": "Unknown", "suggestion": "Consult docs/TECHNICAL_NOTES.md or ask user.", "action": "none"}

if __name__ == "__main__":
    engine = SelfHealingEngine(Path(os.getcwd()).parent)
    print(engine.analyze_error("NameError: name '_get_tool_registry' is not defined"))
    print(engine.analyze_error("PermissionError: [WinError 5] Access is denied"))
