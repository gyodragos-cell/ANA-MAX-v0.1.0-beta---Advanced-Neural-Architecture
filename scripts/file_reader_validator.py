#!/usr/bin/env python3
"""
ANA MAX File Reader & Validator
================================
Uses ANA MAX HTTP API for file reading and error detection.
Better than custom functions because it leverages 90+ enterprise tools.
"""

import json
from pathlib import Path

import requests


class ANAFileReaderValidator:
    """Uses ANA MAX HTTP API for file reading and validation"""
    
    def __init__(self, base_url="http://127.0.0.1:8767"):
        self.base_url = base_url
        self.api_url = f"{base_url}/mcp"
    
    def _call_tool(self, tool_name: str, params: dict) -> dict:
        """Call ANA MAX tool via HTTP API"""
        try:
            response = requests.post(
                self.api_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "ana.execute_tool",
                    "params": {
                        "tool": tool_name,
                        "arguments": params
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    return {
                        "success": True,
                        "data": data["result"]
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", "Unknown error")
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def read_file(self, file_path: str) -> dict:
        """Read file using ANA FilesTool"""
        result = self._call_tool("file_operations", {
            "operation": "read",
            "path": file_path
        })
        
        if result["success"]:
            return {
                "success": True,
                "content": result["data"].get("content", ""),
                "size": result["data"].get("size", 0)
            }
        else:
            return result
    
    def validate_json(self, content: str) -> dict:
        """Validate JSON structure"""
        try:
            data = json.loads(content)
            return {
                "valid": True,
                "structure": self._analyze_json_structure(data),
                "errors": []
            }
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [f"JSON decode error: {e.msg} at line {e.lineno}"]
            }
    
    def _analyze_json_structure(self, data) -> dict:
        """Analyze JSON structure"""
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys()),
                "key_count": len(data)
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "item_count": len(data),
                "item_types": [type(item).__name__ for item in data[:5]]
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100]
            }
    
    def detect_errors(self, content: str) -> dict:
        """Detect errors using ANA ErrorRadar"""
        result = self._call_tool("error_radar", {
            "scope": "quick",
            "limit": 10
        })
        
        if result["success"]:
            return {
                "success": True,
                "findings": result["data"].get("findings", []),
                "count": result["data"].get("count", 0)
            }
        else:
            return result
    
    def get_recommendations(self, error_text: str) -> dict:
        """Get fix recommendations using ANA AgentCoach"""
        result = self._call_tool("agent_coach", {
            "action": "recommend",
            "task": "File validation error",
            "error": error_text,
            "limit": 5
        })
        
        if result["success"]:
            return {
                "success": True,
                "recommendations": result["data"].get("recommendations", [])
            }
        else:
            return result
    
    def process_file(self, file_path: str) -> dict:
        """Complete file processing pipeline"""
        file_ext = Path(file_path).suffix.lower()
        
        # Step 1: Read file
        read_result = self.read_file(file_path)
        if not read_result["success"]:
            return {
                "file": file_path,
                "status": "read_failed",
                "error": read_result["error"]
            }
        
        content = read_result["content"]
        result = {
            "file": file_path,
            "status": "processed",
            "type": file_ext,
            "size": read_result["size"],
            "validation": {},
            "errors": [],
            "recommendations": []
        }
        
        # Step 2: Type-specific validation
        if file_ext == ".json":
            json_result = self.validate_json(content)
            result["validation"]["json"] = json_result
            if not json_result["valid"]:
                result["errors"].extend(json_result["errors"])
        
        # Step 3: Error detection
        error_result = self.detect_errors(content)
        if error_result["success"] and error_result["findings"]:
            result["error_detection"] = {
                "findings": error_result["findings"],
                "count": error_result["count"]
            }
            result["errors"].extend([f.get("summary", str(f)) for f in error_result["findings"]])
        
        # Step 4: Get recommendations if errors found
        if result["errors"]:
            error_text = "; ".join(result["errors"][:3])
            rec_result = self.get_recommendations(error_text)
            if rec_result["success"]:
                result["recommendations"] = rec_result["recommendations"]
        
        return result


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ANA MAX File Reader & Validator")
    parser.add_argument("file", help="File to process")
    parser.add_argument("--url", default="http://127.0.0.1:8767", help="ANA MAX server URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    validator = ANAFileReaderValidator(args.url)
    result = validator.process_file(args.file)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"File: {result['file']}")
        print(f"Status: {result['status']}")
        print(f"Type: {result['type']}")
        print(f"Size: {result['size']} bytes")
        
        if result.get("validation"):
            print("\nValidation:")
            for vtype, vdata in result["validation"].items():
                print(f"  {vtype}: {json.dumps(vdata, indent=4)}")
        
        if result.get("errors"):
            print("\nErrors found:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        if result.get("recommendations"):
            print("\nRecommendations:")
            for rec in result["recommendations"]:
                print(f"  - {rec}")


if __name__ == "__main__":
    main()
