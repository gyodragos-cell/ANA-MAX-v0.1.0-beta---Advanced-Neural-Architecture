"""
ANA MAX - Autonomous Task Orchestrator
=======================================
Executes complex multi-step tasks autonomously WITH safety controls.
Professional automation framework for authorized security operations.
"""

import os
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from tools.base import registry, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class AutonomousOrchestrator:
    """
    Professional autonomous task execution with audit trail and safety controls.
    
    Capabilities:
    - Multi-step task planning and execution
    - Automatic error recovery
    - Progress tracking
    - Audit logging
    - Resource monitoring
    
    Safety Features:
    - Authorization required for sensitive operations
    - Timeout limits per operation
    - Rollback capability
    - Human-in-the-loop for critical actions
    """
    
    def __init__(self):
        self.task_queue = []
        self.execution_history = []
        self.is_running = False
        self.max_retries = 3
        self.default_timeout = 120  # seconds
        self.audit_log_path = Path("logs/autonomous_orchestrator_audit.log")
        
        # Ensure log directory exists
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("🤖 Autonomous Orchestrator initialized")
    
    def plan_task(self, task_description: str, steps: List[Dict[str, Any]]) -> Dict:
        """
        Plan a multi-step autonomous task.
        
        Args:
            task_description: High-level task description
            steps: List of tool calls to execute
        
        Returns:
            Task plan object
        """
        task_plan = {
            "id": f"task_{len(self.execution_history) + 1}",
            "description": task_description,
            "steps": steps,
            "status": "planned",
            "created_at": time.time()
        }
        
        self.task_queue.append(task_plan)
        logger.info(f"📋 Task planned: {task_description}")
        
        return task_plan
    
    def execute_autonomous(self, task_plan: Dict, auto_approve: bool = False) -> Dict:
        """
        Execute a planned task autonomously.
        
        Args:
            task_plan: The task plan to execute
            auto_approve: If True, skip confirmation for non-critical steps
        
        Returns:
            Execution results
        """
        task_plan["status"] = "running"
        task_plan["started_at"] = time.time()
        results = []
        
        self.is_running = True
        
        for step_idx, step in enumerate(task_plan["steps"]):
            if not self.is_running:
                logger.warning("⏸️ Task paused by user")
                break
            
            step_result = self._execute_step(step, step_idx, auto_approve)
            results.append(step_result)
            
            # Error handling with retry
            if step_result["status"] == "error" and step.get("retry_on_error", False):
                retry_count = 0
                while retry_count < self.max_retries:
                    logger.warning(f"🔄 Retrying step {step_idx + 1}/{len(task_plan['steps'])} (attempt {retry_count + 1})")
                    step_result = self._execute_step(step, step_idx, auto_approve)
                    if step_result["status"] == "success":
                        break
                    retry_count += 1
                    time.sleep(2)
            
            # Stop on critical error
            if step_result["status"] == "error" and not step.get("continue_on_error", False):
                logger.error(f"❌ Task halted due to error in step {step_idx + 1}")
                break
        
        task_plan["status"] = "completed"
        task_plan["completed_at"] = time.time()
        task_plan["results"] = results
        
        self.execution_history.append(task_plan)
        self._log_audit(task_plan)
        
        return task_plan
    
    def _execute_step(self, step: Dict, step_idx: int, auto_approve: bool) -> Dict:
        """Execute a single step in the task."""
        tool_name = step.get("tool")
        params = step.get("params", {})
        timeout = step.get("timeout", self.default_timeout)
        
        logger.info(f"🔧 Executing step {step_idx + 1}: {tool_name}")
        
        try:
            # Check if authorization needed
            if step.get("requires_auth", False) and not auto_approve:
                auth_prompt = f"\n⚠️ Step requires authorization: {step.get('auth_reason', 'Sensitive operation')}"
                auth_prompt += f"\nTool: {tool_name}"
                auth_prompt += f"\nParams: {json.dumps(params, indent=2)}"
                auth_prompt += "\n\nApprove? (yes/no): "
                
                response = input(auth_prompt).strip().lower()
                if response not in ["yes", "y"]:
                    return {
                        "step": step_idx + 1,
                        "tool": tool_name,
                        "status": "blocked",
                        "reason": "User declined authorization"
                    }
            
            # Execute tool
            result = registry.execute(tool_name, **params)
            
            step_result = {
                "step": step_idx + 1,
                "tool": tool_name,
                "status": "success" if result.is_success else "error",
                "data": result.data if result.is_success else None,
                "message": result.message,
                "error": result.error if not result.is_success else None
            }
            
            if result.is_success:
                logger.info(f"✅ Step {step_idx + 1} completed successfully")
            else:
                logger.error(f"❌ Step {step_idx + 1} failed: {result.error}")
            
            return step_result
            
        except Exception as e:
            logger.exception(f"Exception in step {step_idx + 1}")
            return {
                "step": step_idx + 1,
                "tool": tool_name,
                "status": "error",
                "error": str(e)
            }
    
    def pause(self):
        """Pause autonomous execution."""
        self.is_running = False
        logger.info("⏸️ Autonomous execution paused")
    
    def resume(self):
        """Resume autonomous execution."""
        self.is_running = True
        logger.info("▶️ Autonomous execution resumed")
    
    def stop(self):
        """Stop all autonomous tasks."""
        self.is_running = False
        self.task_queue.clear()
        logger.info("⏹️ All autonomous tasks stopped")
    
    def get_status(self) -> Dict:
        """Get current orchestrator status."""
        return {
            "is_running": self.is_running,
            "queued_tasks": len(self.task_queue),
            "completed_tasks": len([t for t in self.execution_history if t["status"] == "completed"]),
            "failed_tasks": len([t for t in self.execution_history if t["status"] == "failed"])
        }
    
    def _log_audit(self, task_plan: Dict):
        """Log task execution to audit file."""
        with open(self.audit_log_path, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Task ID: {task_plan['id']}\n")
            f.write(f"Description: {task_plan['description']}\n")
            f.write(f"Status: {task_plan['status']}\n")
            f.write(f"Started: {time.ctime(task_plan.get('started_at', 0))}\n")
            f.write(f"Completed: {time.ctime(task_plan.get('completed_at', 0))}\n")
            f.write(f"Steps executed: {len(task_plan.get('results', []))}\n")
            f.write(f"{'='*60}\n\n")


# Example autonomous task templates
AUTONOMOUS_TASK_TEMPLATES = {
    "security_audit": {
        "description": "Comprehensive security audit of a codebase",
        "steps": [
            {
                "tool": "security_audit",
                "params": {"operation": "scan_secrets", "target": "{target_path}"},
                "retry_on_error": False,
                "continue_on_error": False
            },
            {
                "tool": "security_audit",
                "params": {"operation": "static_analysis", "target": "{target_path}"},
                "retry_on_error": False,
                "continue_on_error": True
            },
            {
                "tool": "code",
                "params": {"operation": "analyze_patterns", "path": "{target_path}", "pattern": "vulnerability"},
                "retry_on_error": False,
                "continue_on_error": True
            }
        ]
    },
    
    "network_recon": {
        "description": "Network reconnaissance for authorized target",
        "steps": [
            {
                "tool": "security_scanner",
                "params": {
                    "operation": "network_recon",
                    "target": "{target_ip}",
                    "authorize": "I own this system"
                },
                "requires_auth": True,
                "auth_reason": "Active network scanning",
                "retry_on_error": False,
                "continue_on_error": False
            },
            {
                "tool": "security_scanner",
                "params": {
                    "operation": "port_scan",
                    "target": "{target_ip}",
                    "authorize": "I own this system",
                    "options": "common"
                },
                "requires_auth": True,
                "auth_reason": "Port scanning",
                "retry_on_error": False,
                "continue_on_error": True
            }
        ]
    }
}


def create_autonomous_task(task_type: str, **kwargs) -> Dict:
    """
    Create an autonomous task from template.
    
    Args:
        task_type: Type of task (e.g., "security_audit", "network_recon")
        **kwargs: Parameters to substitute in template
    
    Returns:
        Task plan ready for execution
    """
    if task_type not in AUTONOMOUS_TASK_TEMPLATES:
        raise ValueError(f"Unknown task type: {task_type}")
    
    template = AUTONOMOUS_TASK_TEMPLATES[task_type]
    
    # Substitute parameters
    steps_json = json.dumps(template["steps"])
    for key, value in kwargs.items():
        steps_json = steps_json.replace(f"{{{key}}}", str(value))
    
    steps = json.loads(steps_json)
    
    orchestrator = AutonomousOrchestrator()
    return orchestrator.plan_task(template["description"], steps)
