import sys
import os

# Adauga folderul curent la path pentru importuri
sys.path.append(os.path.abspath('.'))

from tools.network_tool import NetworkTool
from tools.qa_tool import QATool
from tools.security_tool import SecurityTool

def test_tools():
    print("--- Verificare Tool-uri Profesionale ---")
    
    # 1. Network Tool
    net = NetworkTool()
    print("\n[Network] Ping Localhost:")
    res_ping = net.execute("ping", "127.0.0.1")
    print(res_ping.data[:100] + "...")
    
    # 2. QA Tool
    qa = QATool()
    print("\n[QA] Genereaza Test Boilerplate:")
    res_qa = qa.execute("generate_tests", "def calculate_sum(a, b): return a + b")
    print(res_qa.data)
    
    # 3. Security Tool
    sec = SecurityTool()
    print("\n[Security] Scanare Secrete:")
    res_sec = sec.execute("scan_secrets", "api_key = 'sk-1234567890'")
    print(res_sec.data)
    
    print("\n--- Verificare Finalizata ---")

if __name__ == "__main__":
    test_tools()
