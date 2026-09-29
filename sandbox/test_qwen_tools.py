"""
Script simplu pentru a testa Qwen Tool Calling prin qwen_executor.
Acest script instaniaza executorul si ii da un prompt de test.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from bridge.qwen_executor import QwenExecutor

def main():
    print("=" * 60)
    print(" OS-27 Qwen Tool Calling Test (Phase 4)")
    print("=" * 60)
    
    # Init executor
    # Daca Ollama ruleaza pe alt port, modificati host-ul
    executor = QwenExecutor(model="qwen2.5-coder:7b")
    
    prompt = (
        "Foloseste system_control cu operation='vitals' pentru a citi RAM, CPU si disk. "
        "Dupa, scrie rezultatul in fisierul 'vitale_test_qwen.txt' folosind file_operations cu operation='write' si path='vitale_test_qwen.txt'."
    )
    
    executor.run(prompt=prompt, max_steps=5)

if __name__ == "__main__":
    main()
