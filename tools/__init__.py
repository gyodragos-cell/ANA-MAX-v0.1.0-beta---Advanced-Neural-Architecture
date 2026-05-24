"""
A.N.A. MAX - Tools Package
============================
Module de unelte pentru agent.
"""

import logging

from tools.base import Tool, ToolResult, ToolRegistry

logger = logging.getLogger(__name__)

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
from tools.workspace_situational_awareness import WorkspaceSituationalAwarenessTool
from tools.terminal_tool import TerminalTool
from tools.file_patch_tool import FilePatchTool
from tools.project_navigator_tool import ProjectNavigatorTool
from tools.error_radar_tool import ErrorRadarTool
from tools.todo_tool import TodoWriteTool
from tools.edit_tool import EditTool
from tools.system_optimization_tool import SystemOptimizationTool
from tools.task_tool import TaskTool

# Optional tools (pot lipsi dependinte externe)
try:
    from tools.web_ai_bridge import WebAIBridgeTool
except Exception as exc:
    logger.debug("Optional tool import failed: WebAIBridgeTool: %s", exc)
    WebAIBridgeTool = None  # type: ignore

try:
    from tools.autonomous_tool import AutonomousTool
except Exception as exc:
    logger.debug("Optional tool import failed: AutonomousTool: %s", exc)
    AutonomousTool = None  # type: ignore

try:
    from tools.science_tool import ScienceTool
except Exception as exc:
    logger.debug("Optional tool import failed: ScienceTool: %s", exc)
    ScienceTool = None  # type: ignore

try:
    from tools.adal_tool import AdaLTool
except Exception as exc:
    logger.debug("Optional tool import failed: AdaLTool: %s", exc)
    AdaLTool = None  # type: ignore

try:
    from tools.advanced_scanner import AdvancedScannerTool
except Exception as exc:
    logger.debug("Optional tool import failed: AdvancedScannerTool: %s", exc)
    AdvancedScannerTool = None  # type: ignore

try:
    from tools.mitm_analyzer_tool import MITMAnalyzerTool
except Exception as exc:
    logger.debug("Optional tool import failed: MITMAnalyzerTool: %s", exc)
    MITMAnalyzerTool = None  # type: ignore

try:
    from tools.network_pentest_tool import NetworkPentestTool
except Exception as exc:
    logger.debug("Optional tool import failed: NetworkPentestTool: %s", exc)
    NetworkPentestTool = None  # type: ignore

try:
    from tools.hardware_scanner_tool import HardwareScannerTool
except Exception as exc:
    logger.debug("Optional tool import failed: HardwareScannerTool: %s", exc)
    HardwareScannerTool = None  # type: ignore

# Mobile tools (2026-05-12)
try:
    from tools.adb_tool import ADBTool
except Exception as exc:
    logger.debug("Optional tool import failed: ADBTool: %s", exc)
    ADBTool = None  # type: ignore

try:
    from tools.frida_automation import FridaTool
except Exception as exc:
    logger.debug("Optional tool import failed: FridaTool: %s", exc)
    FridaTool = None  # type: ignore

try:
    from tools.apk_analyzer import APKAnalyzerTool
except Exception as exc:
    logger.debug("Optional tool import failed: APKAnalyzerTool: %s", exc)
    APKAnalyzerTool = None  # type: ignore

try:
    from tools.code_search import CodeSearchTool
except Exception as exc:
    logger.debug("Optional tool import failed: CodeSearchTool: %s", exc)
    CodeSearchTool = None  # type: ignore

try:
    from tools.web_scraper import WebScraperTool
except Exception as exc:
    logger.debug("Optional tool import failed: WebScraperTool: %s", exc)
    WebScraperTool = None  # type: ignore

# AI Desktop Control tools (2026-05-13)
try:
    from tools.desktop_capture import DesktopCaptureTool
except Exception as exc:
    logger.debug("Optional tool import failed: DesktopCaptureTool: %s", exc)
    DesktopCaptureTool = None  # type: ignore

try:
    from tools.live_desktop_viewer import LiveDesktopViewerTool
except Exception as exc:
    logger.debug("Optional tool import failed: LiveDesktopViewerTool: %s", exc)
    LiveDesktopViewerTool = None  # type: ignore

try:
    from tools.desktop_control_tool import DesktopControlTool
except Exception as exc:
    logger.debug("Optional tool import failed: DesktopControlTool: %s", exc)
    DesktopControlTool = None  # type: ignore

try:
    from tools.windows_insight_tool import WindowsInsightTool
except Exception as exc:
    logger.debug("Optional tool import failed: WindowsInsightTool: %s", exc)
    WindowsInsightTool = None  # type: ignore

try:
    from tools.windows_uia_bridge import WindowsUiaBridgeTool
except Exception as exc:
    logger.debug("Optional tool import failed: WindowsUiaBridgeTool: %s", exc)
    WindowsUiaBridgeTool = None  # type: ignore

try:
    from tools.window_manager import WindowManagerTool
except Exception as exc:
    logger.debug("Optional tool import failed: WindowManagerTool: %s", exc)
    WindowManagerTool = None  # type: ignore

try:
    from tools.ocr_tool import OcrTool
except Exception as exc:
    logger.debug("Optional tool import failed: OcrTool: %s", exc)
    OcrTool = None  # type: ignore

try:
    from tools.uia_click_tool import UiaClickTool
except Exception as exc:
    logger.debug("Optional tool import failed: UiaClickTool: %s", exc)
    UiaClickTool = None  # type: ignore

try:
    from tools.uia_type_tool import UiaTypeTool
except Exception as exc:
    logger.debug("Optional tool import failed: UiaTypeTool: %s", exc)
    UiaTypeTool = None  # type: ignore

try:
    from tools.windows_deep_sight import WindowsDeepSightTool
except Exception as exc:
    logger.debug("Optional tool import failed: WindowsDeepSightTool: %s", exc)
    WindowsDeepSightTool = None  # type: ignore

try:
    from tools.foreground_ui_snapshot import ForegroundUISnapshotTool
except Exception as exc:
    logger.debug("Optional tool import failed: ForegroundUISnapshotTool: %s", exc)
    ForegroundUISnapshotTool = None  # type: ignore

try:
    from tools.vision_region_capture_tool import VisionRegionCaptureTool
except Exception as exc:
    logger.debug("Optional tool import failed: VisionRegionCaptureTool: %s", exc)
    VisionRegionCaptureTool = None  # type: ignore

try:
    from tools.vision_find_element_tool import VisionFindElementTool
except Exception as exc:
    logger.debug("Optional tool import failed: VisionFindElementTool: %s", exc)
    VisionFindElementTool = None  # type: ignore

# Voice tools (2026-05-14)
try:
    from tools.edge_tts_voice import EdgeTTSVoice
except Exception as exc:
    logger.debug("Optional tool import failed: EdgeTTSVoice: %s", exc)
    EdgeTTSVoice = None  # type: ignore

try:
    from tools.voice_commentary import VoiceCommentary
except Exception as exc:
    logger.debug("Optional tool import failed: VoiceCommentary: %s", exc)
    VoiceCommentary = None  # type: ignore

# Ruflo Integration (2026-05-19)
try:
    from tools.vector_memory_tool import VectorMemoryTool
except Exception as exc:
    logger.debug("Optional tool import failed: VectorMemoryTool: %s", exc)
    VectorMemoryTool = None  # type: ignore

try:
    from tools.swarm_tool import SwarmTool
except Exception as exc:
    logger.debug("Optional tool import failed: SwarmTool: %s", exc)
    SwarmTool = None  # type: ignore

# UI-TARS Integration (2026-05-19)
try:
    from tools.vision_fallback_tool import VisionFallbackTool
except Exception as exc:
    logger.debug("Optional tool import failed: VisionFallbackTool: %s", exc)
    VisionFallbackTool = None  # type: ignore

try:
    from tools.remote_control_tool import RemoteControlTool
except Exception as exc:
    logger.debug("Optional tool import failed: RemoteControlTool: %s", exc)
    RemoteControlTool = None  # type: ignore

try:
    from tools.event_stream_tool import EventStreamTool
except Exception as exc:
    logger.debug("Optional tool import failed: EventStreamTool: %s", exc)
    EventStreamTool = None  # type: ignore

# Verdent tools (bash, grep, search, web)
try:
    from tools.verdent_tools import BashExecTool, GlobSearchTool, GrepContentTool, GrepFileTool, WebFetchTool
except Exception as exc:
    logger.debug("Optional tool import failed: verdent_tools: %s", exc)
    BashExecTool = GlobSearchTool = GrepContentTool = GrepFileTool = WebFetchTool = None  # type: ignore

__all__ = [
    'Tool', 'ToolResult', 'ToolRegistry',
    'PrivacyTool', 'FilesTool', 'BrowserControlTool', 'WebTool',
    'SystemTool', 'CodeTool', 'GitTool', 'NetworkTool', 'SecurityTool',
    'QATool', 'MemoryTool', 'SmartSearchTool', 'DebuggerTool',
    'CodebaseUnderstandingTool', 'ConversationLearningTool',
    'SessionLogMinerTool', 'AnaContextTool', 'ToolHealthcheckTool', 'WorkspaceSituationalAwarenessTool',
    'TerminalTool', 'FilePatchTool', 'ProjectNavigatorTool', 'ErrorRadarTool',
    'WebAIBridgeTool', 'AutonomousTool', 'ScienceTool',
    'AdaLTool', 'AdvancedScannerTool', 'TodoWriteTool', 'EditTool', 'TaskTool', 'SystemOptimizationTool',
    'MITMAnalyzerTool', 'NetworkPentestTool', 'HardwareScannerTool',
    # Mobile tools
    'ADBTool', 'FridaTool', 'APKAnalyzerTool', 'CodeSearchTool', 'WebScraperTool',
    # Desktop control
    'DesktopCaptureTool', 'LiveDesktopViewerTool', 'DesktopControlTool',
    'WindowsInsightTool', 'WindowsUiaBridgeTool', 'WindowManagerTool', 'OcrTool',
    'UiaClickTool', 'UiaTypeTool', 'WindowsDeepSightTool', 'ForegroundUISnapshotTool',
    'VisionRegionCaptureTool', 'VisionFindElementTool',
    # Voice tools
    'EdgeTTSVoice', 'VoiceCommentary',
    # Ruflo Integration
    'VectorMemoryTool', 'SwarmTool',
    # UI-TARS Integration
    'VisionFallbackTool', 'RemoteControlTool', 'EventStreamTool',
    # Verdent tools
    'BashExecTool', 'GlobSearchTool', 'GrepContentTool', 'GrepFileTool', 'WebFetchTool',
]
