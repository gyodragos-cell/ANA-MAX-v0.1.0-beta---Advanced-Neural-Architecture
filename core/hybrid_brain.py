"""
ANA MAX - HYBRID AUTONOMOUS BRAIN
Acesta este "Creierul" care uneste Viziunea (OpenCV/OCR) cu Telemetria de Sistem (Frida).
"""

import sys
import os
import time
import threading

# Adaugam path-ul ca sa putem importa tool-urile
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.desktop_control_tool import DesktopControlTool
from tools.frida_automation import FridaTool

class HybridBrain:
    def __init__(self):
        self.desktop = DesktopControlTool()
        self.frida = FridaTool()

    def execute_hybrid_task(self, target_process: str, window_title: str, visual_target: str, is_image: bool = False):
        print(f"\n==================================================")
        print(f"🧠 INITIERE MISIUNE HIBRIDA (GOD MODE)")
        print(f"Tinta Proces: {target_process}")
        print(f"Tinta Vizuala: {visual_target}")
        print(f"==================================================\n")

        # PASUL 1: Sistemul Nervos (Hook cu Frida sub capota)
        print("[1] Pregatesc senzorii Frida sub capota...")
        hook_script = """
        // Hook pe Kernel32 CreateFileW ca sa vedem exact ce fisiere acceseaza Windows-ul
        var CreateFileW = Module.findExportByName("kernel32.dll", "CreateFileW");
        if (CreateFileW) {
            Interceptor.attach(CreateFileW, {
                onEnter: function(args) {
                    var filename = Memory.readUtf16String(args[0]);
                    if (filename && filename.indexOf("AppData") !== -1) {
                        console.log("🔔 [FRIDA ALERTA] Procesul a accesat fisier: " + filename);
                    }
                }
            });
            console.log("[*] Frida Hook Inserat pe CreateFileW!");
        } else {
            console.log("[!] Nu am gasit Kernel32.dll (probabil e proces pe alta arhitectura)");
        }
        """

        # Lansam Frida intr-un thread separat ca sa asculte in background
        print(f"[2] Atasez Frida pe procesul {target_process}...")
        frida_thread = threading.Thread(
            target=self.frida.execute,
            kwargs={
                "operation": "inject",
                "target": target_process,
                "script": hook_script,
                "timeout": 15
            }
        )
        frida_thread.start()

        # Dam timp Fridei sa se ataseze
        time.sleep(3)

        # PASUL 2: Vederea si Mainile (Actiune vizuala deasupra capotei)
        print("\n[3] Trec la Vedere si Maini (OpenCV / OCR) -> actionez in interfata!")
        
        op = 'click_image' if is_image else 'click_text'
        
        result = self.desktop.execute(operation=op, target=visual_target, window_title=window_title)
        
        if result.status.name == "SUCCESS":
            print(f"✅ [SUCCES VIZUAL] {result.message}")
        else:
            print(f"❌ [ESEC VIZUAL] {result.error}")

        # Asteptam ca actiunea sa declanseze call-urile in Windows
        print("\n[4] Astept ca Windows sa proceseze click-ul si culeg telemetria...")
        time.sleep(3)

        print("\n==================================================")
        print("Misiune completa! Daca procesul a accesat fisiere ascunse, ")
        print("Frida le-a printat mai sus, direct sub click-ul nostru!")
        print("==================================================\n")

if __name__ == "__main__":
    brain = HybridBrain()
    
    # EXEMPLU DE RULARE:
    # Aici ar trebui sa punem un proces care ruleaza acum (de ex. 'notepad.exe' sau altceva)
    # Si un target vizual. 
    # Pentru a nu bloca sistemul acum, vom testa scriptul cu Notepad (trebuie sa fie deschis)
    
    print("Modulul hibrid este functional si gata sa primeasca comenzi!")
