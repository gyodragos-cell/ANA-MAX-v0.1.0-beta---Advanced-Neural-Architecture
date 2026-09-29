#!/usr/bin/env python3
"""Analiza consumul proceselor specifice - Ollama, ANA, Brave"""

import subprocess
import json
import re

def get_process_memory():
    """Obtine consumul de memorie pentru procesele specifice"""
    target_processes = ["ollama", "python", "brave", "chrome", "ana"]
    
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            process_info = []
            
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                
                parts = [p.strip('"') for p in line.split(',')]
                if len(parts) >= 5:
                    process_name = parts[0].lower()
                    mem_usage = parts[4]  # Memory Usage
                    
                    for target in target_processes:
                        if target in process_name:
                            process_info.append({
                                "name": parts[0],
                                "pid": parts[1],
                                "mem": mem_usage
                            })
            
            return process_info
        else:
            print("[FAIL] tasklist command failed")
            return []
            
    except Exception as e:
        print(f"[FAIL] Error getting process info: {str(e)}")
        return []

def parse_memory(mem_str):
    """Converteste string de memorie in MB"""
    if 'K' in mem_str:
        return float(mem_str.replace('K', '').replace(' ', '')) / 1024
    elif 'M' in mem_str:
        return float(mem_str.replace('M', '').replace(' ', ''))
    elif 'G' in mem_str:
        return float(mem_str.replace('G', '').replace(' ', '')) * 1024
    return 0

def main():
    print("=" * 70)
    print("SPECIFIC PROCESS MEMORY ANALYSIS")
    print("=" * 70)
    
    print("\n[INFO] Analyzing memory usage for target processes...")
    processes = get_process_memory()
    
    if processes:
        total_mem = 0
        print(f"\n[FOUND] {len(processes)} target processes:")
        
        for proc in processes:
            mem_mb = parse_memory(proc['mem'])
            total_mem += mem_mb
            print(f"  {proc['name']} (PID: {proc['pid']}): {proc['mem']} ({mem_mb:.1f} MB)")
        
        print(f"\n[TOTAL] Target processes memory: {total_mem:.1f} MB")
        
        # Categorii
        ollama_mem = sum(parse_memory(p['mem']) for p in processes if 'ollama' in p['name'].lower())
        python_mem = sum(parse_memory(p['mem']) for p in processes if 'python' in p['name'].lower())
        browser_mem = sum(parse_memory(p['mem']) for p in processes if any(b in p['name'].lower() for b in ['brave', 'chrome']))
        
        print("\n[CATEGORY BREAKDOWN]")
        print(f"  Ollama: {ollama_mem:.1f} MB")
        print(f"  Python (ANA): {python_mem:.1f} MB")
        print(f"  Browser: {browser_mem:.1f} MB")
        
        print("\n" + "=" * 70)
        print("ANALYSIS RESULTS")
        print("=" * 70)
        
        if ollama_mem > 4000:
            print("[WARN] Ollama using >4GB RAM - consider using smaller model")
        elif ollama_mem > 3000:
            print("[INFO] Ollama using moderate RAM - acceptable for 7B model")
        else:
            print("[PASS] Ollama memory usage is optimal")
        
        if python_mem > 2000:
            print("[WARN] Python/ANA using >2GB RAM - consider optimization")
        else:
            print("[PASS] Python/ANA memory usage is acceptable")
        
        if browser_mem > 2000:
            print("[INFO] Browser using significant RAM - consider closing tabs")
        
    else:
        print("[INFO] No target processes found - may not be running")

if __name__ == "__main__":
    main()
