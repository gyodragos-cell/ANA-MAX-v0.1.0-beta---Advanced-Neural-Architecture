#!/usr/bin/env python3
"""Analiza esec website - Probleme de orchestration"""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from tools.large_file_reader import LargeFileReaderTool

def analyze_website_attempt():
    """Analizeaza incercarea de creare website din log-uri"""
    log_path = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log"
    
    tool = LargeFileReaderTool()
    
    # Cautam "website", "html", "index.html" in log-uri recente
    result = tool.execute(
        file_path=log_path,
        chunk_size=200,
        max_chunks=10
    )
    
    if result.status.value == "success":
        print("[INFO] Analyzing website creation attempt...")
        print(f"Total lines: {result.data['total_lines']}")
        print(f"Reading: {result.data['lines_returned']} lines")
        
        website_entries = []
        html_entries = []
        tool_errors = []
        
        for chunk in result.data['chunks']:
            lines = chunk['text'].split('\n')
            for line in lines:
                line_lower = line.lower()
                if 'website' in line_lower or 'html' in line_lower or 'index.html' in line_lower:
                    website_entries.append(line.strip())
                if 'error' in line_lower or 'failed' in line_lower:
                    tool_errors.append(line.strip())
        
        print(f"\n[FOUND] {len(website_entries)} website-related entries:")
        for entry in website_entries[-20:]:  # Ultimele 20
            print(f"  {entry}")
        
        print(f"\n[FOUND] {len(tool_errors)} error entries:")
        for error in tool_errors[-15:]:
            print(f"  {error}")
        
        return website_entries, tool_errors
    else:
        print("[FAIL] Could not read log file")
        return [], []

def identify_orchestration_issues():
    """Identifica probleme de orchestration"""
    log_path = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\logs\ana_max.log"
    
    tool = LargeFileReaderTool()
    
    # Cautam tool_router si agent_coach entries
    result = tool.execute(
        file_path=log_path,
        chunk_size=150,
        max_chunks=8
    )
    
    if result.status.value == "success":
        print("\n[INFO] Analyzing orchestration (tool_router, agent_coach)...")
        
        orchestration_entries = []
        for chunk in result.data['chunks']:
            lines = chunk['text'].split('\n')
            for line in lines:
                if 'tool_router' in line.lower() or 'agent_coach' in line.lower() or 'recommended' in line.lower():
                    orchestration_entries.append(line.strip())
        
        print(f"[FOUND] {len(orchestration_entries)} orchestration entries:")
        for entry in orchestration_entries[-15:]:
            print(f"  {entry}")
        
        return orchestration_entries
    else:
        print("[FAIL] Could not analyze orchestration")
        return []

def main():
    print("=" * 70)
    print("WEBSITE CREATION FAILURE ANALYSIS - Orchestration Issues")
    print("=" * 70)
    
    print("\n1. Analyzing website creation attempt...")
    website_entries, tool_errors = analyze_website_attempt()
    
    print("\n2. Identifying orchestration issues...")
    orchestration_entries = identify_orchestration_issues()
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    
    if website_entries:
        print("[INFO] Website creation was attempted")
        print("[ANALYSIS] Checking what went wrong...")
        
        # Cautam pattern-uri specifice de esec
        for entry in website_entries:
            if 'error' in entry.lower() or 'failed' in entry.lower():
                print(f"[ISSUE] {entry}")
    
    if tool_errors:
        print(f"[ISSUES] {len(tool_errors)} errors found - these indicate orchestration problems")
    
    if orchestration_entries:
        print("[INFO] Orchestration entries found - checking recommendations")
        for entry in orchestration_entries[-5:]:
            print(f"  {entry}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("1. The issue is orchestration, not the model")
    print("2. Tool routing may be inefficient for web tasks")
    print("3. Agent may be using wrong tools or wrong order")
    print("4. Will fix orchestration to work like I do")
    print("5. Can also create the website as example of correct workflow")

if __name__ == "__main__":
    main()
