#!/usr/bin/env python3
"""Analiza profesionala OS27 - Large File Reader pentru analiza completa"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from tools.large_file_reader import LargeFileReaderTool

def analyze_os27_dashboard():
    """Analizeaza OS27 dashboard"""
    dashboard_path = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\dashboard\os27_dashboard.html"
    
    tool = LargeFileReaderTool()
    result = tool.execute(
        file_path=dashboard_path,
        chunk_size=100,
        max_chunks=4
    )
    
    if result.status.value == "success":
        print("[INFO] OS27 Dashboard Analysis")
        print(f"Total lines: {result.data['total_lines']}")
        print(f"Chunks: {result.data['chunks_returned']}")
        
        # Cautam componentele principale
        components = []
        for chunk in result.data['chunks']:
            text = chunk['text'].lower()
            if 'frida' in text:
                components.append("Frida integration")
            if 'memory' in text:
                components.append("Memory cortex")
            if 'reflex' in text:
                components.append("Reflex dispatcher")
            if 'vision' in text:
                components.append("Vision system")
            if 'ollama' in text:
                components.append("Ollama integration")
        
        print(f"\n[FOUND] Components: {set(components)}")
        return components
    return []

def analyze_os27_startup_scripts():
    """Analizeaza script-urile OS27"""
    scripts = [
        r"C:\Users\billy\Desktop\ana-manus\START_ATOMIC_ANA_OS27.bat",
        r"C:\Users\billy\Desktop\ana-manus\START_PHI4_OS27.bat"
    ]
    
    tool = LargeFileReaderTool()
    
    for script in scripts:
        if os.path.exists(script):
            result = tool.execute(
                file_path=script,
                chunk_size=50,
                max_chunks=2
            )
            
            if result.status.value == "success":
                print(f"\n[INFO] Analyzing: {os.path.basename(script)}")
                print(f"Lines: {result.data['total_lines']}")
                
                # Cautam ce component activeaza
                content = result.data['chunks'][0]['text'].lower()
                components = []
                if 'ana' in content:
                    components.append("ANA")
                if 'ollama' in content:
                    components.append("Ollama")
                if 'frida' in content:
                    components.append("Frida")
                if 'dashboard' in content:
                    components.append("Dashboard")
                
                print(f"Activates: {components}")

def main():
    print("=" * 70)
    print("PROFESSIONAL OS27 ANALYSIS - Large File Reader")
    print("=" * 70)
    
    print("\n1. Analyzing OS27 Dashboard...")
    components = analyze_os27_dashboard()
    
    print("\n2. Analyzing OS27 Startup Scripts...")
    analyze_os27_startup_scripts()
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print("[INFO] OS27 is a dashboard-based monitoring system")
    print("[INFO] Integrates: Frida, Memory, Reflex, Vision, Ollama")
    print("[NEXT] Need to analyze actual implementation in Python code")

if __name__ == "__main__":
    main()
