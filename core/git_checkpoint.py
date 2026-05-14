"""
ANA MAX - Git Checkpoint System
================================
Automatic snapshot system for AI-assisted development.
Creates git checkpoints before AI modifications for safe undo/redo.
"""

import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class GitCheckpoint:
    """
    Manages automatic git checkpoints for AI code modifications.
    
    Features:
    - Auto-commit before AI edits
    - Easy rollback to previous states
    - Checkpoint history tracking
    - Branch management for experiments
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.checkpoint_history: List[Dict[str, Any]] = []
        self._verify_git_repo()
    
    def _verify_git_repo(self):
        """Verify current directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise Exception("Not a git repository")
            logger.info(f"✅ Git repository verified at: {self.repo_path}")
        except Exception as e:
            logger.error(f"❌ Git verification failed: {e}")
            raise
    
    def create_checkpoint(self, message: str = "AI Edit", save_staged: bool = True) -> Dict[str, Any]:
        """
        Create a checkpoint before AI makes changes.
        
        Args:
            message: Description of the upcoming change
            save_staged: If True, stage all changes before commit
        
        Returns:
            Checkpoint metadata (commit hash, timestamp, etc.)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_msg = f"🤖 AI Checkpoint [{timestamp}]: {message}"
        
        try:
            # Stage all changes if requested
            if save_staged:
                self._run_git_command(["add", "-A"])
                logger.info("✅ Staged all changes")
            
            # Create commit
            self._run_git_command(["commit", "-m", checkpoint_msg])
            
            # Get commit hash
            result = self._run_git_command(["rev-parse", "HEAD"])
            commit_hash = result.stdout.strip()
            
            checkpoint_data = {
                "hash": commit_hash,
                "message": checkpoint_msg,
                "timestamp": timestamp,
                "description": message,
                "parent": self._get_parent_commit()
            }
            
            self.checkpoint_history.append(checkpoint_data)
            
            logger.info(f"✅ Checkpoint created: {commit_hash[:8]}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"❌ Checkpoint creation failed: {e}")
            raise
    
    def rollback(self, steps: int = 1, hard: bool = False) -> Dict[str, Any]:
        """
        Rollback to a previous checkpoint.
        
        Args:
            steps: Number of commits to go back
            hard: If True, use --hard reset (discards all changes)
        
        Returns:
            Rollback result with new HEAD info
        """
        try:
            reset_flag = "--hard" if hard else "--soft"
            target = f"HEAD~{steps}"
            
            # Get target commit info before resetting
            result = self._run_git_command(["log", "-1", "--format=%H %s", target])
            target_info = result.stdout.strip()
            
            # Perform rollback
            self._run_git_command(["reset", reset_flag, target])
            
            rollback_data = {
                "success": True,
                "target": target,
                "new_head": target_info,
                "mode": "hard" if hard else "soft",
                "steps_rolled_back": steps
            }
            
            logger.warning(f"⚠️  Rolled back {steps} commit(s) to: {target_info[:40]}")
            return rollback_data
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return {"success": False, "error": str(e)}
    
    def list_checkpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent checkpoints.
        
        Args:
            limit: Maximum number of checkpoints to return
        
        Returns:
            List of recent checkpoint metadata
        """
        try:
            result = self._run_git_command([
                "log", f"-{limit}",
                "--oneline",
                "--grep=🤖 AI Checkpoint"
            ])
            
            checkpoints = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        checkpoints.append({
                            "hash": parts[0],
                            "message": parts[1]
                        })
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"❌ Failed to list checkpoints: {e}")
            return []
    
    def create_experiment_branch(self, branch_name: str) -> bool:
        """
        Create a new branch for AI experiments.
        
        Args:
            branch_name: Name for the experiment branch
        
        Returns:
            True if successful
        """
        try:
            # Create and checkout new branch
            self._run_git_command(["checkout", "-b", branch_name])
            logger.info(f"✅ Created experiment branch: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create branch: {e}")
            return False
    
    def restore_checkpoint(self, commit_hash: str, hard: bool = False) -> Dict[str, Any]:
        """
        Restore to a specific checkpoint by hash.
        
        Args:
            commit_hash: The commit hash to restore to
            hard: If True, discard all changes
        
        Returns:
            Restoration result
        """
        try:
            reset_flag = "--hard" if hard else "--soft"
            self._run_git_command(["reset", reset_flag, commit_hash])
            
            return {
                "success": True,
                "restored_to": commit_hash,
                "mode": "hard" if hard else "soft"
            }
        except Exception as e:
            logger.error(f"❌ Restoration failed: {e}")
            return {"success": False, "error": str(e)}
    
    def diff_since_checkpoint(self, commit_hash: str) -> str:
        """
        Show changes since a specific checkpoint.
        
        Args:
            commit_hash: The checkpoint to compare against
        
        Returns:
            Diff output as string
        """
        try:
            result = self._run_git_command(["diff", commit_hash])
            return result.stdout
        except Exception as e:
            logger.error(f"❌ Diff failed: {e}")
            return ""
    
    def _run_git_command(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a git command with error handling."""
        cmd = ["git"] + args
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        
        return result
    
    def _get_parent_commit(self) -> Optional[str]:
        """Get the parent commit hash."""
        try:
            result = self._run_git_command(["rev-parse", "HEAD^"])
            return result.stdout.strip()
        except Exception:
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current git status including checkpoint info."""
        try:
            # Current branch
            branch_result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            current_branch = branch_result.stdout.strip()
            
            # Current commit
            head_result = self._run_git_command(["rev-parse", "HEAD"])
            current_commit = head_result.stdout.strip()
            
            # Uncommitted changes
            status_result = self._run_git_command(["status", "--porcelain"])
            has_changes = bool(status_result.stdout.strip())
            
            return {
                "branch": current_branch,
                "commit": current_commit,
                "has_uncommitted_changes": has_changes,
                "recent_checkpoints": self.list_checkpoints(5),
                "checkpoint_count": len(self.checkpoint_history)
            }
        except Exception as e:
            logger.error(f"❌ Status check failed: {e}")
            return {}


# Convenience functions for AI tool integration
def auto_checkpoint(description: str = "AI modification") -> Dict[str, Any]:
    """Create a checkpoint automatically before AI edits."""
    cp = GitCheckpoint()
    return cp.create_checkpoint(message=description)


def undo_last_ai_edit(hard: bool = False) -> Dict[str, Any]:
    """Undo the last AI edit by rolling back one commit."""
    cp = GitCheckpoint()
    return cp.rollback(steps=1, hard=hard)


def list_recent_checkpoints(limit: int = 10) -> List[Dict[str, Any]]:
    """List recent AI checkpoints."""
    cp = GitCheckpoint()
    return cp.list_checkpoints(limit=limit)


def create_sandbox_branch(name: str) -> bool:
    """Create a sandbox branch for AI experimentation."""
    cp = GitCheckpoint()
    return cp.create_experiment_branch(f"sandbox/{name}")
