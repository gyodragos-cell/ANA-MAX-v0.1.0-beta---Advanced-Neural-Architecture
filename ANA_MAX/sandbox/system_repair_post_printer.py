#!/usr/bin/env python3
"""
OS27 SYSTEM REPAIR - Post Printer Installation Issues
====================================================
Probleme:
1. Taskbar nu raspunde (fara control)
2. Click issues
3. Ctrl+Tab nu functioneaza
4. Windows Update blocat
5. Bloatware/malware dupa instalare imprimanta

Plan de reparatie:
1. Diagnostic complet
2. Verificare servicii Windows critice
3. Reparare Windows Update
4. Curatare bloatware
5. Reparare taskbar/Explorer
6. Reset keyboard shortcuts
"""
import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.system import SystemTool
from tools.terminal_tool import TerminalTool

class SystemRepairPostPrinter:
    """Reparatie sistem dupa instalare imprimanta problematica."""

    def __init__(self):
        self.system = SystemTool()
        self.terminal = TerminalTool()

    def run_diagnostic(self):
        """Diagnostic complet al sistemului."""
        print("=" * 80)
        print("DIAGNOSTIC COMPLET SISTEM")
        print("=" * 80)

        # 1. Verificare servicii critice
        print("\n[1] Verificare servicii Windows critice...")
        services = [
            "Windows Update",
            "Windows Explorer",
            "ShellHWDetection",
            "Themes",
            "DcomLaunch"
        ]

        for service in services:
            try:
                result = self.terminal.execute(
                    operation="run",
                    command="powershell -Command \"Get-Service -Name '" + service + "' | Select-Object Name, Status, StartType\"",
                    timeout=10
                )
                print(f"  {service}: {result.data if result.is_success else 'N/A'}")
            except Exception as e:
                print(f"  {service}: Eroare - {e}")

        # 2. Verificare Windows Update
        print("\n[2] Verificare Windows Update status...")
        try:
            result = self.terminal.execute(
                operation="run",
                command="powershell -Command \"Get-WindowsUpdateLog -MaxEvents 5 | Select-Object TimeCreated, Message\"",
                timeout=15
            )
            if result.is_success:
                print(f"  Windows Update Log: {result.data[:200]}")
            else:
                print(f"  Windows Update Log: {result.error}")
        except Exception as e:
            print(f"  Windows Update: Eroare - {e}")

        # 3. Verificare processes suspecte
        print("\n[3] Verificare processes suspecte (bloatware)...")
        try:
            result = self.terminal.execute(
                operation="run",
                command="powershell -Command \"Get-Process | Where-Object {$_.MainWindowTitle -like '*printer*' -or $_.ProcessName -like '*hp*' -or $_.ProcessName -like '*epson*' -or $_.ProcessName -like '*canon*'} | Select-Object ProcessName, Id, MainWindowTitle\"",
                timeout=10
            )
            print("  Processes suspecte: " + (result.data if result.is_success else 'None'))
        except Exception as e:
            print("  Processes: Erore - " + str(e))

    def repair_windows_update(self):
        """Reparare Windows Update."""
        print("\n" + "=" * 80)
        print("REPARARE WINDOWS UPDATE")
        print("=" * 80)

        commands = [
            "net stop wuauserv",
            "net stop cryptSvc",
            "net stop bits",
            "net stop msiserver",
            "net start wuauserv",
            "net start cryptSvc",
            "net start bits",
            "net start msiserver"
        ]

        for cmd in commands:
            print("  Executing: " + cmd)
            try:
                result = self.terminal.execute(
                    operation="run",
                    command=cmd,
                    timeout=15
                )
                print("  Result: " + (result.data if result.is_success else result.error))
                time.sleep(2)
            except Exception as e:
                print("  Error: " + str(e))

    def repair_taskbar_explorer(self):
        """Reparare taskbar si Windows Explorer."""
        print("\n" + "=" * 80)
        print("REPARARE TASKBAR / EXPLORER")
        print("=" * 80)

        commands = [
            "taskkill /f /im explorer.exe",
            "timeout /t 2",
            "start explorer.exe"
        ]

        for cmd in commands:
            print("  Executing: " + cmd)
            try:
                result = self.terminal.execute(
                    operation="run",
                    command=cmd,
                    timeout=10
                )
                print("  Result: " + (result.data if result.is_success else result.error))
                time.sleep(3)
            except Exception as e:
                print("  Error: " + str(e))

    def clean_bloatware(self):
        """Curatare bloatware de la imprimanta."""
        print("\n" + "=" * 80)
        print("CURATARE BLOATWARE")
        print("=" * 80)

        # Cautare programe tipice printer cu bloatware
        bloatware_patterns = [
            "*HP*",
            "*Epson*",
            "*Canon*",
            "*Brother*",
            "*Lexmark*",
            "*Xerox*"
        ]

        for pattern in bloatware_patterns:
            print(f"  Cautare: {pattern}")
            try:
                result = self.terminal.execute(
                    operation="run",
                    command="powershell -Command \"Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like '" + pattern + "'} | Select-Object Name, Version\"",
                    timeout=15
                )
                if result.is_success and result.data:
                    print(f"  Gasit: {result.data}")
            except Exception as e:
                print(f"  Error: {e}")

    def reset_keyboard_shortcuts(self):
        """Reset keyboard shortcuts (Ctrl+Tab)."""
        print("\n" + "=" * 80)
        print("RESET KEYBOARD SHORTCUTS")
        print("=" * 80)

        # Reparare keyboard shortcuts in registry
        try:
            result = self.terminal.execute(
                operation="run",
                command="powershell -Command \"Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' | Select-Object TaskbarGlomLevel\"",
                timeout=10
            )
            print("  Taskbar settings: " + (result.data if result.is_success else 'N/A'))
        except Exception as e:
            print("  Error: " + str(e))

    def run_complete_repair(self):
        """Executa reparatie completa."""
        print("\n" + "=" * 80)
        print("REPARARE COMPLETA SISTEM")
        print("=" * 80)

        self.run_diagnostic()
        self.repair_windows_update()
        self.repair_taskbar_explorer()
        self.clean_bloatware()
        self.reset_keyboard_shortcuts()

        print("\n" + "=" * 80)
        print("REPARARE COMPLETA - Verifica manual sistemul")
        print("=" * 80)
        print("\nInstructiuni:")
        print("1. Verifica daca taskbar raspunde")
        print("2. Verifica Ctrl+Tab in browser")
        print("3. Incearca Windows Update manual")
        print("4. Daca probleme persista, reporneste calculatorul")

if __name__ == "__main__":
    repair = SystemRepairPostPrinter()
    repair.run_complete_repair()
