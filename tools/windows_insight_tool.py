"""
ANA MAX - Windows Insight Tool (God View Prototype)
===================================================
Monitorizare in timp real a evenimentelor de sistem Windows (File I/O, Processes).
Foloseste PowerShell pentru a obtine acces la nivel de kernel/OS.
"""

import os
import subprocess
import threading
import queue
import logging
from typing import Optional, List, Dict
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class WindowsInsightTool(Tool):
    def __init__(self):
        self._event_queue = queue.Queue()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="windows_insight",
            description="Monitorizare 'God View' a sistemului Windows: evenimente fisiere, procese noi, erori API.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia: start_monitor, stop_monitor, get_events, trace_process, system_snapshot",
                    type="string",
                    required=True,
                    choices=["start_monitor", "stop_monitor", "get_events", "trace_process", "system_snapshot"]
                ),
                ToolParameter(
                    name="path",
                    description="Calea de monitorizat (default: current workspace)",
                    type="string",
                    required=False
                )
            ],
            category="system_intelligence"
        )

    def execute(self, operation: str, path: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            if operation == "start_monitor":
                return self._start_monitor(path or os.getcwd())
            if operation == "stop_monitor":
                return self._stop_monitor()
            if operation == "get_events":
                return self._get_events()
            if operation == "system_snapshot":
                return self._system_snapshot()
            if operation == "trace_process":
                return self._trace_process(target=kwargs.get("target"))
            
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _start_monitor(self, path: str) -> ToolResult:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return ToolResult(status=ToolStatus.SUCCESS, message="Monitorizarea ruleaza deja.")

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._ps_monitor_loop, args=(path,), daemon=True)
        self._monitor_thread.start()
        
        return ToolResult(status=ToolStatus.SUCCESS, message=f"God View activat pe calea: {path}")

    def _stop_monitor(self) -> ToolResult:
        self._stop_event.set()
        return ToolResult(status=ToolStatus.SUCCESS, message="God View dezactivat.")

    def _get_events(self) -> ToolResult:
        events = []
        while not self._event_queue.empty():
            events.append(self._event_queue.get())
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"events": events, "count": len(events)},
            message=f"Am colectat {len(events)} evenimente de sistem noi."
        )

    def _ps_monitor_loop(self, path: str):
        """Bucla PowerShell care urmareste: Fisiere si Procese."""
        ps_script = rf"""
        $path = "{path}"
        
        # 1. File Watcher
        $watcher = New-Object System.IO.FileSystemWatcher
        $watcher.Path = $path
        $watcher.IncludeSubdirectories = $true
        $watcher.EnableRaisingEvents = $true

        $fileAction = {{
            $p = $Event.SourceEventArgs.FullPath
            $t = $Event.SourceEventArgs.ChangeType
            $time = Get-Date -Format "HH:mm:ss"
            Write-Host "EVENT|FILE|$time|$t|$p"
        }}

        Register-ObjectEvent $watcher "Changed" -Action $fileAction | Out-Null
        Register-ObjectEvent $watcher "Created" -Action $fileAction | Out-Null

        # 2. Process Monitor (WMI)
        $procQuery = "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"
        Register-WmiEvent -Query $procQuery -Action {{
            $name = $Event.SourceEventArgs.NewEvent.TargetInstance.Name
            $pid = $Event.SourceEventArgs.NewEvent.TargetInstance.ProcessId
            $time = Get-Date -Format "HH:mm:ss"
            Write-Host "EVENT|PROC|$time|START|$name (PID: $pid)"
        }} | Out-Null

        # 3. Registry Monitor (Example: Personalization settings)
        $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        $regWatcher = New-Object System.IO.FileSystemWatcher # Folosim o metoda alternativa pentru Reg daca e nevoie, dar aici testam detectia WMI
        # Nota: WMI pentru Reg este mai complex, vom folosi un poll rapid pentru acest test
        $lastVal = (Get-ItemProperty $regPath).AppsUseLightTheme
        
        # 4. Clipboard Monitor
        $lastClip = ""
        try {{
            $lastClip = Get-Clipboard -ErrorAction SilentlyContinue
        }} catch {{}}
        
        while ($true) {{
            try {{
                $currentClip = Get-Clipboard -ErrorAction SilentlyContinue
                if ($currentClip -and ($currentClip -ne $lastClip)) {{
                    $time = Get-Date -Format "HH:mm:ss"
                    # Trimitem doar primele 50 caractere pentru siguranta
                    $preview = if ($currentClip.Length -gt 50) {{ $currentClip.Substring(0, 50) + "..." }} else {{ $currentClip }}
                    Write-Host "EVENT|CLIP|$time|COPY|$preview"
                    $lastClip = $currentClip
                }}
            }} catch {{}}
            
            # 3. Registry Monitor (Example: Personalization settings)
            $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            $currentVal = (Get-ItemProperty $regPath).AppsUseLightTheme
            if ($currentVal -ne $lastVal) {{
                $time = Get-Date -Format "HH:mm:ss"
                $mode = if ($currentVal -eq 0) {{ "Dark Mode" }} else {{ "Light Mode" }}
                Write-Host "EVENT|REG|$time|CHANGE|Windows Theme changed to $mode"
                $lastVal = $currentVal
            }}
            
            Start-Sleep -Seconds 1
        }}
        """
        
        process = subprocess.Popen(
            ["powershell", "-Command", ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        try:
            for line in iter(process.stdout.readline, ''):
                if self._stop_event.is_set():
                    process.terminate()
                    break
                
                if line.startswith("EVENT|"):
                    logger.info(line.strip())
                    parts = line.strip().split("|")
                    if len(parts) >= 5:
                        cat, etype, details = parts[1], parts[3], parts[4]
                        
                        # Logica de Gamification / Quests
                        if "error" in details.lower() or "failed" in details.lower():
                            logger.info(f"EVENT|QUEST|{parts[2]}|MISSION|🛡️ NEW QUEST: Analizeaza si repara {details[:30]}...")
                        
                        event_data = {
                            "category": cat,
                            "time": parts[2],
                            "type": etype,
                            "details": details
                        }
                        self._event_queue.put(event_data)
        finally:
            process.terminate()

    def _system_snapshot(self) -> ToolResult:
        """Face un snapshot instantaneu al sistemului (sub capota)."""
        ps_cmd = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, CPU, WorkingSet | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        return ToolResult(status=ToolStatus.SUCCESS, data=result.stdout, message="Snapshot 'sub capota' realizat.")

    def _trace_process(self, target: str) -> ToolResult:
        """Trace detaliat pe un singur proces."""
        if not target: return ToolResult(status=ToolStatus.ERROR, error="Target process missing")
        ps_cmd = f"Get-Process -Name {target} | Select-Object * | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        return ToolResult(status=ToolStatus.SUCCESS, data=result.stdout, message=f"Trace complet pe {target}")

