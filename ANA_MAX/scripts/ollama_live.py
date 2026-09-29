import os
import time
import sys

# colorama for ANSI cross-platform support
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_AVAILABLE = True
except ImportError:
    COLOR_AVAILABLE = False

def tail_file(filepath):
    """Citeste si randeaza in timp real noile linii/caractere adaugate in fisier."""
    if not os.path.exists(filepath):
        print(f"Astept sa apara fisierul: {filepath}")
        while not os.path.exists(filepath):
            time.sleep(1)
            
    print(f"Ollama Live Reasoning asculta {filepath}...")
    
    in_thought = False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        # Sari la sfarsitul fisierului initial
        f.seek(0, 2)
        
        # Buffer pentru a detecta tagurile de thought
        buffer = ""
        
        while True:
            char = f.read(1)
            if not char:
                time.sleep(0.1)
                continue
                
            buffer += char
            if len(buffer) > 15:
                buffer = buffer[-15:]
                
            if "<thought>" in buffer:
                in_thought = True
                buffer = buffer.replace("<thought>", "")
                if COLOR_AVAILABLE:
                    sys.stdout.write(Fore.CYAN)
            elif "</thought>" in buffer:
                in_thought = False
                buffer = buffer.replace("</thought>", "")
                if COLOR_AVAILABLE:
                    sys.stdout.write(Style.RESET_ALL)
            
            # Printam fara newline pentru a simula un stream
            sys.stdout.write(char)
            sys.stdout.flush()

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file = os.path.join(base_dir, "logs", "ollama_reasoning.log")
    
    try:
        tail_file(log_file)
    except KeyboardInterrupt:
        print("\n\nOllama Live Reasoning oprit.")
        sys.exit(0)
