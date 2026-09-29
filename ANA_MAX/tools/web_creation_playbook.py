"""Simple web creation playbook - HTML direct without npm/build steps"""

from typing import Dict, Any

def get_web_creation_playbook() -> Dict[str, Any]:
    """Return playbook for simple HTML/CSS website creation"""
    return {
        "headline": "Create simple HTML/CSS websites directly without npm/build steps.",
        "tools": [
            "file_operations",
            "terminal"
        ],
        "steps": [
            "Use file_operations operation=write to create HTML file directly.",
            "Use CSS inline in HTML for styling (no separate CSS files).",
            "Use terminal with browser_open command to view the result.",
            "DO NOT use npm, create-react-app, or build tools for simple websites.",
            "Keep structure simple: HTML → CSS inline → open in browser.",
            "If folder creation fails, write file directly to existing folder.",
            "For complex projects, consider simple static HTML first before React/npm.",
        ],
        "keywords": [
            r"\b(website|web page|html|css|javascript|create website|make website|build website|facebook clone|landing page)\b",
            r"\b(create-react-app|npm install|npm start|react|vue|angular)\b"
        ],
        "avoid": [
            "npm install",
            "create-react-app", 
            "npm start",
            "yarn",
            "build steps",
            "complex frameworks for simple tasks"
        ]
    }

def inject_playbook_to_router():
    """Inject web_creation playbook into tool_router"""
    import os
    router_path = os.path.join(os.path.dirname(__file__), "tool_router_tool.py")
    
    playbook = get_web_creation_playbook()
    
    # Read current router
    with open(router_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find where to insert (before web_research)
    if '"web_research"' in content:
        # Build the playbook string manually
        playbook_str = '''    "web_creation": {
        "headline": "Create simple HTML/CSS websites directly without npm/build steps.",
        "tools": [
            "file_operations",
            "terminal"
        ],
        "steps": [
            "Use file_operations operation=write to create HTML file directly.",
            "Use CSS inline in HTML for styling (no separate CSS files).",
            "Use terminal with browser_open command to view the result.",
            "DO NOT use npm, create-react-app, or build tools for simple websites.",
            "Keep structure simple: HTML → CSS inline → open in browser.",
            "If folder creation fails, write file directly to existing folder.",
            "For complex projects, consider simple static HTML first before React/npm.",
        ],
    },
    '''
        
        # Insert before web_research
        content = content.replace(
            '    "web_research": {',
            playbook_str + '    "web_research": {'
        )
        
        # Write back
        with open(router_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    return False

if __name__ == "__main__":
    if inject_playbook_to_router():
        print("[SUCCESS] web_creation playbook injected into tool_router")
    else:
        print("[FAIL] Could not inject playbook")
