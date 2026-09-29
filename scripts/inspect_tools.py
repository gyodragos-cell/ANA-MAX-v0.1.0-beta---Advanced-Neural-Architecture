"""Inspectez parametrii corecti ai toolurilor WARN"""
import sys, os, re, inspect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

tools_to_check = [
    ("tools.system", "SystemTool", "system_control"),
    ("tools.code_search", "CodeSearchTool", "code_search"),
    ("tools.large_file_reader", "LargeFileReaderTool", "large_file_reader"),
    ("tools.project_navigator_tool", "ProjectNavigatorTool", "project_navigator"),
    ("tools.desktop_control_tool", "DesktopControlTool", "desktop_control"),
    ("tools.git_tool", "GitTool", "git_operations"),
    ("tools.network_tool", "NetworkTool", "network_diag"),
    ("tools.privacy", "PrivacyTool", "privacy_shield"),
    ("tools.security_tool", "SecurityTool", "security_audit"),
    ("tools.clipboard_manager", "ClipboardManagerTool", "clipboard_manager"),
    ("tools.window_manager", "WindowManagerTool", "window_manager"),
    ("tools.ocr_tool", "OcrTool", "ocr_tool"),
]

import importlib

for mod_name, cls_name, reg_name in tools_to_check:
    try:
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name, None)
        if not cls:
            print(f"[{reg_name}] class {cls_name} NOT FOUND in {mod_name}")
            continue
        
        src = inspect.getsource(cls.safe_execute)
        
        # Cauta operatiunile / actiunile suportate
        ops_list = re.findall(r'"operation"\s*:\s*\{[^}]*"enum"\s*:\s*\[([^\]]+)\]', src)
        action_eq = re.findall(r'operation\s*==\s*"(\w+)"', src)
        action_eq2 = re.findall(r'action\s*==\s*"(\w+)"', src)
        
        # Cauta primul required param
        req_params = re.findall(r'required_param\w*\(["\'](\w+)["\']', src)
        
        first_10 = src[:600].replace('\n', ' ')
        
        print(f"[{reg_name}]")
        print(f"  ops from enum: {ops_list}")
        print(f"  operation==: {action_eq[:8]}")
        print(f"  action==: {action_eq2[:8]}")
        print(f"  required: {req_params[:5]}")
        print()
    except Exception as ex:
        print(f"[{reg_name}] ERROR: {ex}")
        print()
