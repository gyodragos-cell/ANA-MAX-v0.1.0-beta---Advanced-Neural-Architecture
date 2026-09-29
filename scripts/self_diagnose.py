import os
import json
from pathlib import Path

def run_self_diagnose():
    py_files = list(Path('.').rglob('*.py'))
    report = []
    for f in py_files:
        print(f"Scanning {f}...")
        # Simulare apel error_radar
        # In practica, aici se va apela unealta error_radar
        report.append({
            'file': str(f),
            'status': 'ok'  # placeholder
        })
    with open('self_diagnose_report.md', 'w') as f:
        f.write('# Self-Diagnose Report\n')
        for r in report:
            f.write(f"- {r['file']}: {r['status']}\n")
    print("Report saved to self_diagnose_report.md")

if __name__ == '__main__':
    run_self_diagnose()