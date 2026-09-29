#!/usr/bin/env python3
"""
Terminal Monitor - Enhanced Terminal Output Monitoring
========================================================
Real-time terminal output capture, error detection, and command tracking.
Specifically designed for 7B models to provide terminal visibility.
"""

import re
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import deque
import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class TerminalMonitorTool(Tool):
    """
    Enhanced terminal monitoring with real-time output capture,
    error pattern detection, and command execution tracking.
    """

    def __init__(self):
        super().__init__()

        # Error patterns to detect
        self.error_patterns = {
            'python': [
                r'Traceback \(most recent call last\):',
                r'Error: .*',
                r'Exception: .*',
                r'ModuleNotFoundError: .*',
                r'ImportError: .*',
                r'SyntaxError: .*',
                r'NameError: .*',
                r'TypeError: .*',
                r'ValueError: .*',
                r'AssertionError: .*',
            ],
            'npm': [
                r'ERR! .*',
                r'npm ERR! .*',
                r'error .*',
                r'failed .*',
            ],
            'git': [
                r'error: .*',
                r'fatal: .*',
                r'warning: .*',
            ],
            'general': [
                r'error',
                r'Error',
                r'ERROR',
                r'failed',
                r'Failed',
                r'FAILED',
                r'exception',
                r'Exception',
                r'EXCEPTION',
            ]
        }

        # Command history
        self.command_history = deque(maxlen=100)

        # Terminal state
        self.terminal_state = {
            'active_processes': [],
            'recent_errors': [],
            'last_command': None,
            'last_output': None,
            'terminal_type': None
        }

    def get_definition(self) -> ToolDefinition:
        """Return tool definition."""
        return ToolDefinition(
            name="terminal_monitor",
            description="Monitor terminal output, detect errors, track commands, and list processes",
            category="SYSTEM INSPECTOR",
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform: capture, monitor, detect_errors, track_command, list_processes",
                    required=True,
                    choices=["capture", "monitor", "detect_errors", "track_command", "list_processes"]
                ),
                ToolParameter(
                    name="pid",
                    type="integer",
                    description="Process ID to monitor (for monitor operation)",
                    required=False
                ),
                ToolParameter(
                    name="duration",
                    type="integer",
                    description="Monitoring duration in seconds (for monitor operation)",
                    required=False
                ),
                ToolParameter(
                    name="output",
                    type="array",
                    description="Output lines to analyze (for detect_errors operation)",
                    required=False
                ),
                ToolParameter(
                    name="command",
                    type="string",
                    description="Command to execute (for track_command operation)",
                    required=False
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory (for track_command operation)",
                    required=False
                ),
                ToolParameter(
                    name="max_lines",
                    type="integer",
                    description="Maximum lines to capture (for capture operation)",
                    required=False
                ),
            ],
            requires_confirmation=False
        )

    def execute(self, **kwargs) -> ToolResult:
        """
        Execute terminal monitoring operations.

        Operations:
        - capture: Capture current terminal state
        - monitor: Start monitoring a process
        - detect_errors: Detect errors in recent output
        - track_command: Track a command execution
        - list_processes: List active terminal processes
        """
        try:
            operation = kwargs.get('operation')

            if operation == 'capture':
                return self._capture_terminal_state(**kwargs)
            elif operation == 'monitor':
                return self._monitor_process(**kwargs)
            elif operation == 'detect_errors':
                return self._detect_errors(**kwargs)
            elif operation == 'track_command':
                return self._track_command(**kwargs)
            elif operation == 'list_processes':
                return self._list_processes(**kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown operation: {operation}"
                )
        except Exception as e:
            logger.error(f"Error in terminal_monitor: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error executing operation: {str(e)}"
            )

    def _capture_terminal_state(self, max_lines: int = 50, **kwargs) -> ToolResult:
        """
        Capture current terminal state snapshot.

        Args:
            max_lines: Maximum number of lines to capture

        Returns:
            ToolResult with terminal state information
        """
        try:
            # Detect terminal type
            terminal_type = self._detect_terminal_type()

            # Get active processes
            processes = self._get_terminal_processes()

            # Update state
            self.terminal_state.update({
                'terminal_type': terminal_type,
                'active_processes': processes,
                'recent_errors': self.terminal_state['recent_errors'][-10:],
                'timestamp': datetime.now().isoformat()
            })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'terminal_type': terminal_type,
                    'active_processes': processes,
                    'detected_errors': self.terminal_state['recent_errors'][-5:],
                    'command_history_count': len(self.command_history),
                    'last_command': self.command_history[-1] if self.command_history else None,
                    'timestamp': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error capturing terminal state: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error capturing terminal state: {str(e)}"
            )

    def _monitor_process(self, pid: int, duration: int = 30, **kwargs) -> ToolResult:
        """
        Monitor a process for specified duration.

        Args:
            pid: Process ID to monitor
            duration: Monitoring duration in seconds

        Returns:
            ToolResult with monitoring results
        """
        try:
            import psutil

            process = psutil.Process(pid)
            monitor_data = {
                'pid': pid,
                'name': process.name(),
                'start_time': datetime.now().isoformat(),
                'monitoring_duration': duration,
                'samples': []
            }

            # Monitor for specified duration
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    sample = {
                        'timestamp': datetime.now().isoformat(),
                        'cpu_percent': process.cpu_percent(),
                        'memory_percent': process.memory_percent(),
                        'status': process.status(),
                        'num_threads': process.num_threads()
                    }
                    monitor_data['samples'].append(sample)
                    time.sleep(1)
                except psutil.NoSuchProcess:
                    monitor_data['status'] = 'process_terminated'
                    break

            monitor_data['end_time'] = datetime.now().isoformat()
            monitor_data['status'] = 'monitoring_complete'

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=monitor_data
            )

        except ImportError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="psutil not installed. Install with: pip install psutil"
            )
        except Exception as e:
            logger.error(f"Error monitoring process: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error monitoring process: {str(e)}"
            )

    def _detect_errors(self, output: List[str] = None, **kwargs) -> ToolResult:
        """
        Detect error patterns in terminal output.

        Args:
            output: List of output lines to analyze

        Returns:
            ToolResult with detected errors
        """
        try:
            if output is None:
                output = []

            detected_errors = []

            for line in output:
                for category, patterns in self.error_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            detected_errors.append({
                                'line': line.strip(),
                                'category': category,
                                'pattern': pattern,
                                'timestamp': datetime.now().isoformat()
                            })

            # Update state
            self.terminal_state['recent_errors'] = detected_errors

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'total_errors': len(detected_errors),
                    'errors': detected_errors[-20:],
                    'error_categories': self._categorize_errors(detected_errors)
                }
            )

        except Exception as e:
            logger.error(f"Error detecting errors: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error detecting errors: {str(e)}"
            )

    def _track_command(self, command: str, cwd: str = None, **kwargs) -> ToolResult:
        """
        Track and execute a command, capturing output.

        Args:
            command: Command to execute
            cwd: Working directory

        Returns:
            ToolResult with command execution results
        """
        try:
            # Record command in history
            self.command_history.append({
                'command': command,
                'timestamp': datetime.now().isoformat(),
                'cwd': cwd
            })

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Detect errors in output
            combined_output = result.stdout + result.stderr
            errors = self._detect_error_patterns([combined_output])

            # Update state
            self.terminal_state['last_command'] = command
            self.terminal_state['last_output'] = combined_output[-1000:]  # Last 1000 chars

            return ToolResult(
                status=ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR,
                data={
                    'command': command,
                    'return_code': result.returncode,
                    'stdout': result.stdout[-2000:] if result.stdout else '',
                    'stderr': result.stderr[-2000:] if result.stderr else '',
                    'detected_errors': errors[-5:],
                    'success': result.returncode == 0,
                    'timestamp': datetime.now().isoformat()
                }
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Command execution timed out"
            )
        except Exception as e:
            logger.error(f"Error tracking command: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error tracking command: {str(e)}"
            )

    def _list_processes(self, **kwargs) -> ToolResult:
        """
        List active terminal-related processes.

        Returns:
            ToolResult with process list
        """
        try:
            import psutil

            terminal_processes = []

            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
                try:
                    # Filter for terminal-related processes
                    name = proc.info['name'].lower()
                    if any(term in name for term in ['cmd', 'powershell', 'bash', 'zsh', 'terminal', 'python', 'node']):
                        terminal_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline'] or []),
                            'status': proc.info['status']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'total_processes': len(terminal_processes),
                    'processes': terminal_processes,
                    'timestamp': datetime.now().isoformat()
                }
            )

        except ImportError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="psutil not installed. Install with: pip install psutil"
            )
        except Exception as e:
            logger.error(f"Error listing processes: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error listing processes: {str(e)}"
            )

    def _detect_terminal_type(self) -> str:
        """Detect the type of terminal being used."""
        try:
            # Check if PowerShell
            if 'powershell' in os.environ.get('PSModulePath', '').lower():
                return 'powershell'
            # Check if CMD
            if 'comspec' in os.environ:
                return 'cmd'
        except:
            pass
        return 'unknown'

    def _get_terminal_processes(self) -> List[Dict]:
        """Get active terminal processes."""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name'].lower()
                    if any(term in name for term in ['cmd', 'powershell', 'bash', 'zsh']):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes
        except ImportError:
            return []

    def _detect_error_patterns(self, output: List[str]) -> List[Dict]:
        """Detect error patterns in output lines."""
        detected_errors = []
        for line in output:
            for category, patterns in self.error_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        detected_errors.append({
                            'line': line.strip(),
                            'category': category,
                            'pattern': pattern
                        })
        return detected_errors

    def _categorize_errors(self, errors: List[Dict]) -> Dict:
        """Categorize errors by type."""
        categories = {}
        for error in errors:
            category = error.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        return categories


# Standalone usage for testing
if __name__ == "__main__":
    monitor = TerminalMonitor()

    # Test 1: Capture terminal state
    print("Test 1: Capture terminal state")
    result = monitor.execute(operation='capture')
    print(json.dumps(result.data, indent=2))

    # Test 2: Track a command
    print("\nTest 2: Track command")
    result = monitor.execute(operation='track_command', command='echo "Hello World"')
    print(json.dumps(result.data, indent=2))

    # Test 3: Detect errors
    print("\nTest 3: Detect errors")
    result = monitor.execute(operation='detect_errors', output=[
        "Starting process...",
        "Error: Module not found",
        "Traceback (most recent call last):",
        "Process completed"
    ])
    print(json.dumps(result.data, indent=2))

    # Test 4: List processes
    print("\nTest 4: List processes")
    result = monitor.execute(operation='list_processes')
    print(json.dumps(result.data, indent=2))
