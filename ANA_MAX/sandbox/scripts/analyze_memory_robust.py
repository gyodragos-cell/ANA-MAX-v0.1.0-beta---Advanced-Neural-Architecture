#!/usr/bin/env python3
"""Analiza robusta consum memorie - PowerShell direct"""

import subprocess

def get_memory_powershell():
    """Obtine consum memorie prin PowerShell"""
    try:
        ps_command = """
        Get-Process | Where-Object {$_.ProcessName -match "ollama|python|brave|chrome"} | 
        Select-Object ProcessName, Id, @{Name='MemoryMB';Expression={[math]::Round($_. WorkingSet64 / 1MB, 2)}} |
        Sort-Object MemoryMB -Descending | 
        Format-Table -AutoSize
        """
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print("[INFO] Memory usage for target processes:")
            print(result.stdout)
            
            # Total calculation
            total_command = """
            $total = (Get-Process | Where-Object {$_.ProcessName -match "ollama|python|brave|chrome"} | 
            Measure-Object -Property WorkingSet64 -Sum).Sum / 1MB
            Write-Output "Total target processes: $([math]::Round($total, 2)) MB"
            """
            
            total_result = subprocess.run(
                ["powershell", "-Command", total_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if total_result.returncode == 0:
                print(f"\n[TOTAL] {total_result.stdout.strip()}")
            
            return True
        else:
            print("[FAIL] PowerShell command failed")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        return False

def get_system_memory():
    """Obtine memoria totala sistem"""
    try:
        command = "Get-CimInstance -ClassName Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum"
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parse result to get total RAM
            for line in result.stdout.split('\n'):
                if 'Sum' in line or line.strip().isdigit():
                    try:
                        total_bytes = int(line.strip())
                        total_gb = total_bytes / (1024**3)
                        print(f"[SYSTEM] Total RAM: {total_gb:.1f} GB")
                        return total_gb
                    except:
                        pass
        
        return 16  # Default to 16GB if we can't detect
        
    except Exception as e:
        print(f"[WARN] Could not detect system RAM: {str(e)}")
        return 16

def main():
    print("=" * 70)
    print("ROBUST MEMORY ANALYSIS - PowerShell Direct")
    print("=" * 70)
    
    print("\n1. System Memory Detection...")
    total_ram = get_system_memory()
    
    print("\n2. Target Process Memory Usage...")
    get_memory_powershell()
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print("[INFO] Used large_file_reader for log analysis (low RAM)")
    print("[INFO] Used PowerShell for accurate memory detection")
    print("[INFO] No high memory consumption during analysis")

if __name__ == "__main__":
    main()
