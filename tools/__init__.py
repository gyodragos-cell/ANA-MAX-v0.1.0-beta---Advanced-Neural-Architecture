"""
A.N.A. MAX - Tools Package
============================
Module de unelte pentru agent.
"""

from tools.base import Tool, ToolResult, ToolRegistry

# Core tools
from tools.privacy import PrivacyTool
from tools.files import FilesTool
from tools.browser_control import BrowserControlTool
from tools.web import WebTool
from tools.system import SystemTool
from tools.code import CodeTool
from tools.git_tool import GitTool
from tools.network_tool import NetworkTool
from tools.security_tool import SecurityTool
from tools.qa_tool import QATool
from tools.memory_tool import MemoryTool
from tools.smart_search_tool import SmartSearchTool
from tools.debugger_tool import DebuggerTool
from tools.codebase_understanding_tool import CodebaseUnderstandingTool
from tools.conversation_learning_tool import ConversationLearningTool
from tools.session_log_miner_tool import SessionLogMinerTool
from tools.ana_context_tool import AnaContextTool
from tools.tool_healthcheck import ToolHealthcheckTool
from tools.terminal_tool import TerminalTool
from tools.todo_tool import TodoWriteTool
from tools.edit_tool import EditTool
from tools.system_optimization_tool import SystemOptimizationTool
from tools.task_tool import TaskTool

# Optional tools (pot lipsi dependinte externe)
try:
    from tools.web_ai_bridge import WebAIBridgeTool
except Exception:
    WebAIBridgeTool = None  # type: ignore

try:
    from tools.autonomous_tool import AutonomousTool
except Exception:
    AutonomousTool = None  # type: ignore

try:
    from tools.science_tool import ScienceTool
except Exception:
    ScienceTool = None  # type: ignore

try:
    from tools.adal_tool import AdaLTool
except Exception:
    AdaLTool = None  # type: ignore

try:
    from tools.advanced_scanner import AdvancedScannerTool
except Exception:
    AdvancedScannerTool = None  # type: ignore

try:
    from tools.mitm_analyzer_tool import MITMAnalyzerTool
except Exception:
    MITMAnalyzerTool = None  # type: ignore

try:
    from tools.network_pentest_tool import NetworkPentestTool
except Exception:
    NetworkPentestTool = None  # type: ignore

try:
    from tools.hardware_scanner_tool import HardwareScannerTool
except Exception:
    HardwareScannerTool = None  # type: ignore

# Mobile tools (2026-05-12)
try:
    from tools.adb_tool import ADBTool
except Exception:
    ADBTool = None  # type: ignore

try:
    from tools.frida_automation import FridaTool
except Exception:
    FridaTool = None  # type: ignore

try:
    from tools.apk_analyzer import APKAnalyzerTool
except Exception:
    APKAnalyzerTool = None  # type: ignore

try:
    from tools.code_search import CodeSearchTool
except Exception:
    CodeSearchTool = None  # type: ignore

try:
    from tools.web_scraper import WebScraperTool
except Exception:
    WebScraperTool = None  # type: ignore

# AI Desktop Control tools (2026-05-13)
try:
    from tools.desktop_capture import DesktopCaptureTool
except Exception:
    DesktopCaptureTool = None  # type: ignore

try:
    from tools.live_desktop_viewer import LiveDesktopViewerTool
except Exception:
    LiveDesktopViewerTool = None  # type: ignore

try:
    from tools.windows_uia_bridge import WindowsUiaBridgeTool
except Exception:
    WindowsUiaBridgeTool = None  # type: ignore

# Verdent tools (bash, grep, search, web)
try:
    from tools.verdent_tools import BashExecTool, GlobSearchTool, GrepContentTool, GrepFileTool, WebFetchTool
except Exception:
    BashExecTool = GlobSearchTool = GrepContentTool = GrepFileTool = WebFetchTool = None  # type: ignore

__all__ = [
    'Tool', 'ToolResult', 'ToolRegistry',
    'PrivacyTool', 'FilesTool', 'BrowserControlTool', 'WebTool',
    'SystemTool', 'CodeTool', 'GitTool', 'NetworkTool', 'SecurityTool',
    'QATool', 'MemoryTool', 'SmartSearchTool', 'DebuggerTool',
    'CodebaseUnderstandingTool', 'ConversationLearningTool',
    'SessionLogMinerTool', 'AnaContextTool', 'ToolHealthcheckTool',
    'TerminalTool', 'WebAIBridgeTool', 'AutonomousTool', 'ScienceTool',
    'AdaLTool', 'AdvancedScannerTool', 'TodoWriteTool', 'EditTool', 'TaskTool', 'SystemOptimizationTool',
    'MITMAnalyzerTool', 'NetworkPentestTool', 'HardwareScannerTool',
    # Mobile tools
    'ADBTool', 'FridaTool', 'APKAnalyzerTool', 'CodeSearchTool', 'WebScraperTool',
    # Desktop control
    'DesktopCaptureTool', 'LiveDesktopViewerTool', 'WindowsUiaBridgeTool',
    # Verdent tools
    'BashExecTool', 'GlobSearchTool', 'GrepContentTool', 'GrepFileTool', 'WebFetchTool',
]
