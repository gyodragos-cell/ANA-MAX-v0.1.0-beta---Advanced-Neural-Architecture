"""
Git Plugin for A.N.A.
========================
Provides basic git operations like commit, status, and push.
"""

import subprocess
from plugins import Plugin, PluginMetadata
from typing import List, Callable, Optional


class GitPlugin(Plugin):
    """Plugin: Git Operations"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="git_plugin",
            version="1.0.0",
            description="Provides basic git operations (status, commit, push, pull)",
            author="Antigravity",
            capabilities=["git_ops"]
        )
    
    def initialize(self) -> bool:
        """Always initialize, but check git availability."""
        return True
    
    def get_tools(self) -> List[Callable]:
        """Return git tools."""
        return [self.git_status, self.git_commit, self.git_push, self.git_pull]
    
    def _run_git(self, args: List[str]) -> str:
        try:
            result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
            return result.stdout or "Success"
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def git_status(self) -> str:
        """Returns the current git status."""
        return self._run_git(["status"])
    
    def git_commit(self, message: str) -> str:
        """
        Commits changes with a message.
        
        Args:
            message: Commit message
        """
        add_result = self._run_git(["add", "."])
        if "Error" in add_result:
            return add_result
        return self._run_git(["commit", "-m", message])
    
    def git_push(self, remote: str = "origin", branch: str = "main") -> str:
        """
        Pushes changes to remote.
        
        Args:
            remote: Remote name (default: origin)
            branch: Branch name (default: main)
        """
        return self._run_git(["push", remote, branch])

    def git_pull(self, remote: str = "origin", branch: str = "main") -> str:
        """
        Pulls changes from remote.
        
        Args:
            remote: Remote name
            branch: Branch name
        """
        return self._run_git(["pull", remote, branch])
    
    def cleanup(self) -> None:
        pass
