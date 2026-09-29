"""
OS27 Hyper++ Tool Auto-Discovery Engine
Descopera tooluri noi in filesystem si le adauga automat in registry.
"""

from pathlib import Path
from typing import Dict, List, Set

TOOLS_DIR = Path(__file__).resolve().parents[0]
EXCLUDED_FILES = {"__init__.py", "base.py", "tool_priority_map.py", "tool_health_dashboard.py", "tool_auto_discovery.py", "tool_smoke_test.py", "tool_auto_fix.py"}


def discover_tool_files() -> List[str]:
    """Discover all Python files in tools directory that could be tools."""
    py_files = [
        f.stem for f in TOOLS_DIR.glob("*.py")
        if f.name not in EXCLUDED_FILES and not f.name.startswith("_")
    ]
    return sorted(py_files)


def get_registered_tools() -> Set[str]:
    """
    Get list of currently registered tools from the base registry.
    This scans for Tool subclasses in the tools directory.
    """
    registered = set()
    
    for tool_file in discover_tool_files():
        try:
            module_name = f"tools.{tool_file}"
            module = __import__(module_name, fromlist=["Tool"])
            
            # Check if module has Tool subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                try:
                    from tools.base import Tool
                    if isinstance(attr, type) and issubclass(attr, Tool) and attr != Tool:
                        registered.add(tool_file)
                except Exception:
                    pass
        except Exception:
            pass
    
    return registered


def auto_discover_tools() -> Dict[str, Dict[str, any]]:
    """
    Auto-discover tools and report missing/orphaned tools.
    
    Returns:
        Dictionary with:
        - missing_tools: tools in filesystem but not registered
        - orphaned_tools: tools registered but not in filesystem
        - total_files: total tool files found
        - total_registered: total registered tools
    """
    tool_files = set(discover_tool_files())
    registered = get_registered_tools()
    
    missing = tool_files - registered
    orphaned = registered - tool_files
    
    return {
        "schema": "ana.tool_auto_discovery.v1",
        "missing_tools": sorted(list(missing)),
        "orphaned_tools": sorted(list(orphaned)),
        "total_files": len(tool_files),
        "total_registered": len(registered),
        "discovery_timestamp": Path(__file__).stat().st_mtime,
    }


def get_tool_file_info(tool_name: str) -> Dict[str, any]:
    """Get metadata about a specific tool file."""
    tool_path = TOOLS_DIR / f"{tool_name}.py"
    
    if not tool_path.exists():
        return {"error": "file_not_found", "tool_name": tool_name}
    
    stat = tool_path.stat()
    
    return {
        "tool_name": tool_name,
        "path": str(tool_path),
        "size_bytes": stat.st_size,
        "size_human": f"{stat.st_size / 1024:.2f} KB",
        "modified_time": stat.st_mtime,
        "is_registered": tool_name in get_registered_tools(),
    }


def validate_tool_integrity(tool_name: str) -> Dict[str, any]:
    """
    Validate if a tool file has proper structure.
    Checks for Tool class, get_definition method, execute method.
    """
    tool_path = TOOLS_DIR / f"{tool_name}.py"
    
    if not tool_path.exists():
        return {"valid": False, "error": "file_not_found"}
    
    try:
        module_name = f"tools.{tool_name}"
        module = __import__(module_name, fromlist=["Tool"])
        
        from tools.base import Tool
        
        # Find Tool subclass
        tool_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Tool) and attr != Tool:
                tool_class = attr
                break
        
        if not tool_class:
            return {"valid": False, "error": "no_tool_class"}
        
        # Check for required methods
        has_get_definition = hasattr(tool_class, "get_definition")
        has_execute = hasattr(tool_class, "execute")
        
        if not has_get_definition:
            return {"valid": False, "error": "missing_get_definition"}
        
        if not has_execute:
            return {"valid": False, "error": "missing_execute"}
        
        # Try to instantiate
        try:
            instance = tool_class()
            definition = instance.get_definition()
            
            return {
                "valid": True,
                "tool_class": tool_class.__name__,
                "definition": {
                    "name": definition.name if hasattr(definition, "name") else "unknown",
                    "category": definition.category if hasattr(definition, "category") else "unknown",
                },
            }
        except Exception as e:
            return {"valid": False, "error": f"instantiation_failed: {str(e)}"}
            
    except Exception as e:
        return {"valid": False, "error": f"import_failed: {str(e)}"}


def generate_discovery_report() -> Dict[str, any]:
    """Generate comprehensive discovery report with validation."""
    discovery = auto_discover_tools()
    
    # Validate missing tools
    missing_validation = {}
    for tool in discovery["missing_tools"]:
        missing_validation[tool] = validate_tool_integrity(tool)
    
    # Validate orphaned tools
    orphaned_info = {}
    for tool in discovery["orphaned_tools"]:
        orphaned_info[tool] = get_tool_file_info(tool)
    
    return {
        "schema": "ana.tool_discovery_report.v1",
        "discovery": discovery,
        "missing_tools_validation": missing_validation,
        "orphaned_tools_info": orphaned_info,
        "summary": {
            "can_register": sum(1 for v in missing_validation.values() if v.get("valid")),
            "cannot_register": sum(1 for v in missing_validation.values() if not v.get("valid")),
            "cleanup_needed": len(discovery["orphaned_tools"]),
        },
    }
