import os
import shutil
import tempfile
import ctypes
from pathlib import Path
from tools.base import Tool, ToolResult, ToolStatus

class SystemOptimizationTool(Tool):
    name = "system_optimization"
    description = "Optimizeaza sistemul Windows: curata temp, recycle bin, DNS cache. Alternativa CCleaner Pro."
    
    def get_definition(self) -> 'ToolDefinition':
        from tools.base import ToolDefinition, ToolParameter
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea: analyze, clean_temp, clean_recycle, clean_dns, full_optimize, scan_drivers, scan_software",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="target",
                    description="Tinta: user_temp, win_temp, recycle, all",
                    type="string",
                    required=False
                )
            ],
            category="system"
        )
    
    def execute(self, **kwargs):
        operation = kwargs.get("operation")
        target = kwargs.get("target", "all")
        
        if operation == "analyze":
            return self._analyze_system()
        elif operation == "clean_temp":
            return self._clean_temp_files(target)
        elif operation == "clean_recycle":
            return self._clean_recycle_bin()
        elif operation == "clean_dns":
            return self._clean_dns_cache()
        elif operation == "full_optimize":
            return self._full_optimization()
        elif operation == "scan_drivers":
            return self._scan_drivers()
        elif operation == "scan_software":
            return self._scan_software()
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
    
    def _scan_drivers(self):
        """Scan drivers and open Windows Update for optional updates (free, official)"""
        try:
            import subprocess
            import json
            
            # Get ALL drivers first
            result = subprocess.run(
                ["powershell", "-Command", "Get-WmiObject Win32_PnPSignedDriver | Where-Object {$_.DriverVersion -ne $null} | Select-Object DeviceName, DriverVersion, Manufacturer | Sort-Object DeviceName | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            
            # Parse drivers
            all_drivers = []
            if result.stdout:
                try:
                    all_drivers = json.loads(result.stdout)
                except Exception as e:
                    all_drivers = []
            
            # Filter only important ones in Python
            important_keywords = ['video', 'display', 'usb', 'thermal', 'processor', 'pci', 'smbus', 'spi', 'host bridge', 'wireless', 'bluetooth', 'audio', 'ethernet', 'gbe', 'nvidia', 'intel', 'realtek', 'bluetooth']
            drivers = []
            if isinstance(all_drivers, list):
                for d in all_drivers:
                    name = d.get('DeviceName', '').lower()
                    if any(kw in name for kw in important_keywords):
                        drivers.append(d)
            
            # Log drivers found
            driver_count = len(drivers)
            driver_list = "\n".join([f"{d.get('DeviceName', 'Unknown')} - v{d.get('DriverVersion', 'N/A')}" for d in (drivers[:18] if driver_count > 18 else drivers)])
            
            # Open Windows Update - Optional Updates (where drivers are)
            subprocess.Popen(["cmd", "/c", "start", "ms-settings:windowsupdate-optional"])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Found {driver_count} important drivers (showing first {min(18, driver_count)}):\n{driver_list}\n\nWindows Update (Optional Updates) opened - FREE official way to update drivers.",
                message=f"Found {driver_count} drivers. Windows Update opened (free, no CCleaner Pro needed)"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _scan_software(self):
        """Check installed software and open Windows Update for app updates"""
        try:
            import subprocess
            import json
            # Get installed programs
            result = subprocess.run(
                ["powershell", "-Command", "Get-WmiObject Win32_Product | Select-Object Name, Version, Vendor | Sort-Object Name | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            
            # Parse software
            software = []
            if result.stdout:
                try:
                    software = json.loads(result.stdout)
                except Exception as e:
                    software = []
            
            # Log software found
            sw_count = len(software) if isinstance(software, list) else 0
            sw_list = "\n".join([f"{s.get('Name', 'Unknown')} - v{s.get('Version', 'N/A')}" for s in (software[:24] if sw_count > 24 else software)])
            
            # Open Windows Update
            subprocess.Popen(["cmd", "/c", "start", "ms-settings:windowsupdate"])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Found {sw_count} installed programs (showing first {min(24, sw_count)}):\n{sw_list}\n\nWindows Update opened - some apps update via Windows Store/Update.",
                message=f"Found {sw_count} programs. Windows Update opened (free)"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _analyze_system(self):
        import subprocess
        
        # Temp sizes
        user_temp = Path(os.environ.get('TEMP', tempfile.gettempdir()))
        win_temp = Path('C:/Windows/Temp')
        
        user_size = sum(f.stat().st_size for f in user_temp.rglob('*') if f.is_file())
        win_size = sum(f.stat().st_size for f in win_temp.rglob('*') if f.is_file())
        
        # Recycle bin
        try:
            shell = ctypes.create_string_buffer(1024)
            ctypes.windll.shell32.SHGetSpecialFolderPath(None, shell, 0xA, False)
            recycle_path = Path(shell.value.decode())
            recycle_size = sum(f.stat().st_size for f in recycle_path.rglob('*') if f.is_file())
        except Exception as e:
            recycle_size = 0
        
        total_mb = round((user_size + win_size + recycle_size) / 1024 / 1024, 2)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "user_temp_mb": round(user_size / 1024 / 1024, 2),
                "win_temp_mb": round(win_size / 1024 / 1024, 2),
                "recycle_bin_mb": round(recycle_size / 1024 / 1024, 2),
                "total_cleanable_mb": total_mb
            },
            message=f"Analiza completa. {total_mb} MB de curatat"
        )
    
    def _clean_temp_files(self, target="all"):
        cleaned = 0
        
        if target in ["user_temp", "all"]:
            user_temp = Path(os.environ.get('TEMP', tempfile.gettempdir()))
            for f in user_temp.rglob('*'):
                try:
                    if f.is_file():
                        size = f.stat().st_size
                        f.unlink()
                        cleaned += size
                    elif f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
                except Exception as e:
                    pass
        
        if target in ["win_temp", "all"]:
            win_temp = Path('C:/Windows/Temp')
            for f in win_temp.rglob('*'):
                try:
                    if f.is_file():
                        size = f.stat().st_size
                        f.unlink()
                        cleaned += size
                    elif f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
                except Exception as e:
                    pass
        
        mb_cleaned = round(cleaned / 1024 / 1024, 2)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=f"Curatat {mb_cleaned} MB din temp",
            message=f"Curatat {mb_cleaned} MB din temp"
        )
    
    def _clean_recycle_bin(self):
        try:
            ctypes.windll.shell32.SHEmptyRecycleBin(None, None, 0)
            return ToolResult(status=ToolStatus.SUCCESS, data="Recycle Bin golit", message="Recycle Bin golit cu succes")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _clean_dns_cache(self):
        try:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, check=True)
            return ToolResult(status=ToolStatus.SUCCESS, data="DNS cache curatat", message="DNS cache curatat")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _full_optimization(self):
        results = []
        
        # Analyze before
        before = self._analyze_system()
        before_mb = before.data["total_cleanable_mb"]
        results.append(f"INAINTE: {before_mb} MB de curatat")
        
        # Clean
        self._clean_temp_files("all")
        self._clean_recycle_bin()
        self._clean_dns_cache()
        
        # Analyze after
        after = self._analyze_system()
        after_mb = after.data["total_cleanable_mb"]
        results.append(f"DUPA: {after_mb} MB ramas")
        results.append(f"ELIBERAT: {round(before_mb - after_mb, 2)} MB")
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data="\n".join(results),
            message="Optimizare completa terminata"
        )
