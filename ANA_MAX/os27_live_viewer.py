#!/usr/bin/env python3
"""
OS27 Live Log Viewer - Tool pentru vizualizare live debugging
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Paths
ANA_ROOT = Path(__file__).parent.parent
LOG_DIR = ANA_ROOT / "ANA_MAX" / "logs"
LIVE_LOG_JSON = LOG_DIR / "os27_live_debug.json"

def print_live_status():
    """Printeaza status live din JSON log"""
    if not LIVE_LOG_JSON.exists():
        print("[INFO] No live log file found - run START_ANA_OLLAMA.bat first")
        return
    
    try:
        with open(LIVE_LOG_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        status = data.get("status", {})
        events = data.get("events", [])
        
        print("=" * 60)
        print("OS27 LIVE DEBUG STATUS")
        print("=" * 60)
        print(f"Session Start: {data.get('session_start', 'N/A')}")
        print(f"Last Update: {data.get('last_update', 'N/A')}")
        print(f"Uptime: {status.get('uptime_seconds', 0):.1f}s")
        print(f"Memory Events: {status.get('memory_events_count', 0)}")
        print()
        
        # Active failures
        failures = status.get('active_failures', {})
        if failures:
            print("ACTIVE FAILURES:")
            for tool, count in sorted(failures.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {tool}: {count} failures")
        else:
            print("No active failures")
        print()
        
        # Blocked tools
        blocked = status.get('blocked_tools', [])
        if blocked:
            print("BLOCKED TOOLS:")
            for tool in blocked:
                print(f"  - {tool}")
        else:
            print("No blocked tools")
        print()
        
        # Error patterns
        patterns = status.get('error_patterns', {})
        if patterns:
            print("ERROR PATTERNS:")
            for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {pattern}: {count} occurrences")
        else:
            print("No error patterns detected")
        print()
        
        # Recent events
        recent = status.get('recent_events', [])
        if recent:
            print("RECENT EVENTS (last 10):")
            for event in recent:
                timestamp = event.get('timestamp', 'N/A')[-19:]  # Take last 19 chars
                event_type = event.get('type', 'unknown')
                details = str(event.get('tool', event.get('decision', event.get('blockage_type', 'unknown'))))
                print(f"  [{timestamp}] {event_type}: {details[:60]}")
        else:
            print("No recent events")
        print()
        
        # Failure analysis
        print("FAILURE ANALYSIS:")
        try:
            from core.backends.os27_live_logger import get_os27_live_logger
            live_logger = get_os27_live_logger()
            analysis = live_logger.get_failure_analysis()
            
            print(f"Total Failures: {analysis.get('total_failures', 0)}")
            
            most_failing = analysis.get('most_failing_tools', [])
            if most_failing:
                print("Most Failing Tools:")
                for tool, count in most_failing:
                    print(f"  - {tool}: {count} failures")
            
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                print("Recommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
            
        except Exception as e:
            print(f"Analysis failed: {e}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Failed to read live log: {e}")

def tail_live_log(lines=20):
    """Arata ultimele linii din log file"""
    live_log_file = LOG_DIR / "os27_live_debug.log"
    if not live_log_file.exists():
        print("[INFO] No live log file found")
        return
    
    try:
        with open(live_log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        print("=" * 60)
        print(f"LIVE LOG (last {len(recent_lines)} lines)")
        print("=" * 60)
        for line in recent_lines:
            print(line.rstrip())
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Failed to tail log: {e}")

def watch_live_log(interval=2):
    """Watch live log in timp real"""
    print("[WATCH] Watching OS27 live log (Ctrl+C to stop)...")
    print()
    
    try:
        while True:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Updating...")
            print_live_status()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped watching")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python os27_live_viewer.py <command>")
        print("Commands: status, tail, watch")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "status":
        print_live_status()
    elif command == "tail":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        tail_live_log(lines)
    elif command == "watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        watch_live_log(interval)
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())