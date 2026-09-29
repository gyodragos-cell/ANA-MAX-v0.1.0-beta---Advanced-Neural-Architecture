#!/usr/bin/env python3
"""ANALIZA RESURSE ANA MAX - Large File Reader pentru analiza completa"""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from tools.large_file_reader import LargeFileReaderTool

def analyze_memory_consumption():
    """Analizeaza consumul de memorie din log-uri"""
    log_path = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log"
    
    if not os.path.exists(log_path):
        print(f"[WARN] Log file not found: {log_path}")
        return
    
    tool = LargeFileReaderTool()
    
    # Citim log-ul in chunks pentru a gasi informatii despre memory
    result = tool.execute(
        file_path=log_path,
        chunk_size=500,
        max_chunks=5
    )
    
    if result.status.value == "success":
        print("[INFO] Reading ANA MAX log for memory analysis...")
        print(f"Total lines: {result.data['total_lines']}")
        print(f"Reading: {result.data['lines_returned']} lines")
        
        # Cautam pattern-uri de memory in log
        memory_patterns = []
        for chunk in result.data['chunks']:
            lines = chunk['text'].split('\n')
            for line in lines:
                if 'memory' in line.lower() or 'ram' in line.lower() or 'vram' in line.lower():
                    memory_patterns.append(line.strip())
        
        if memory_patterns:
            print(f"\n[FOUND] {len(memory_patterns)} memory-related entries:")
            for pattern in memory_patterns[:20]:  # Primele 20
                print(f"  {pattern}")
        else:
            print("[INFO] No direct memory patterns found in recent logs")
    
    return result

def analyze_process_consumption():
    """Analizeaza consumul proceselor din log-ul sistem"""
    log_path = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log"
    
    tool = LargeFileReaderTool()
    
    # Citim ultimele linii pentru a vedea procesele
    result = tool.execute(
        file_path=log_path,
        chunk_size=200,
        max_chunks=3
    )
    
    if result.status.value == "success":
        print("\n[INFO] Analyzing recent process activity...")
        
        # Cautam SYSTEM CONTROL tool calls
        process_entries = []
        for chunk in result.data['chunks']:
            lines = chunk['text'].split('\n')
            for line in lines:
                if 'system_control' in line.lower() or 'processes' in line.lower():
                    process_entries.append(line.strip())
        
        if process_entries:
            print(f"[FOUND] {len(process_entries)} process-related entries:")
            for entry in process_entries[:10]:
                print(f"  {entry}")
    
    return result

def analyze_tool_activity():
    """Analizeaza activitatea tool-urilor"""
    log_path = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log"
    
    tool = LargeFileReaderTool()
    
    # Citim pentru a vedea tool activity
    result = tool.execute(
        file_path=log_path,
        chunk_size=300,
        max_chunks=4
    )
    
    if result.status.value == "success":
        print("\n[INFO] Analyzing tool activity...")
        
        tool_calls = []
        for chunk in result.data['chunks']:
            lines = chunk['text'].split('\n')
            for line in lines:
                if 'TOOL START' in line or 'TOOL END' in line:
                    tool_calls.append(line.strip())
        
        if tool_calls:
            print(f"[FOUND] {len(tool_calls)} tool calls:")
            for call in tool_calls[-15:]:  # Ultimele 15
                print(f"  {call}")
    
    return result

def main():
    print("=" * 70)
    print("ANA MAX RESOURCE ANALYSIS - Using Large File Reader")
    print("=" * 70)
    
    print("\n1. Memory Consumption Analysis...")
    analyze_memory_consumption()
    
    print("\n2. Process Activity Analysis...")
    analyze_process_consumption()
    
    print("\n3. Tool Activity Analysis...")
    analyze_tool_activity()
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print("[INFO] Using large_file_reader to avoid high memory consumption")
    print("[INFO] Analysis done in chunks to minimize RAM usage")
    print("[NEXT] Check specific processes if needed")

if __name__ == "__main__":
    main()
