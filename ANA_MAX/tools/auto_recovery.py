#!/usr/bin/env python3
"""
Auto Recovery - Consolidated Recovery Mechanism
==============================================
Automated error detection, recovery, and rollback system.
Consolidates recovery mechanisms from distributed tools into one unified system.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


@dataclass
class RecoveryAction:
    """A recovery action to take."""
    action_type: str  # retry | rollback | fallback | notify
    description: str
    parameters: Dict = field(default_factory=dict)
    max_attempts: int = 3
    delay_sec: float = 1.0


@dataclass
class RecoveryStrategy:
    """A recovery strategy for a specific error type."""
    error_pattern: str
    severity: str  # low | medium | high | critical
    actions: List[RecoveryAction] = field(default_factory=list)
    auto_execute: bool = True


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    error_type: str
    severity: str
    action_taken: str
    success: bool
    attempts: int
    duration_sec: float
    message: str


class AutoRecoveryTool(Tool):
    """
    Consolidated auto-recovery system.

    Automatically detects errors, applies recovery strategies,
    and rolls back if necessary.
    """

    def __init__(self):
        super().__init__()
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self.recovery_history: List[RecoveryResult] = []
        self._initialize_default_strategies()

    def get_definition(self) -> ToolDefinition:
        """Return tool definition."""
        return ToolDefinition(
            name="auto_recovery",
            description="Automated error detection, recovery, and rollback system",
            category="SYSTEM INSPECTOR",
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation: detect, recover, add_strategy, list_strategies, history",
                    required=True,
                    choices=["detect", "recover", "add_strategy", "list_strategies", "history"]
                ),
                ToolParameter(
                    name="error",
                    type="string",
                    description="Error message or pattern (for detect/recover)",
                    required=False
                ),
                ToolParameter(
                    name="severity",
                    type="string",
                    description="Error severity (for detect/recover)",
                    required=False,
                    choices=["low", "medium", "high", "critical"]
                ),
                ToolParameter(
                    name="strategy",
                    type="object",
                    description="Recovery strategy (for add_strategy)",
                    required=False
                ),
                ToolParameter(
                    name="auto_execute",
                    type="boolean",
                    description="Auto-execute recovery (for recover)",
                    required=False
                ),
            ],
            requires_confirmation=False
        )

    def execute(self, **kwargs) -> ToolResult:
        """Execute recovery operations."""
        try:
            operation = kwargs.get('operation')

            if operation == 'detect':
                return self._detect_error(**kwargs)
            elif operation == 'recover':
                return self._attempt_recovery(**kwargs)
            elif operation == 'add_strategy':
                return self._add_strategy(**kwargs)
            elif operation == 'list_strategies':
                return self._list_strategies(**kwargs)
            elif operation == 'history':
                return self._get_history(**kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown operation: {operation}"
                )
        except Exception as e:
            logger.error(f"Error in auto_recovery: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error executing operation: {str(e)}"
            )

    def _detect_error(self, error: str, **kwargs) -> ToolResult:
        """Detect error type and severity."""
        try:
            # Simple pattern matching (production would use more sophisticated detection)
            severity = self._assess_severity(error)

            # Find matching strategy
            matching_strategy = self._find_matching_strategy(error)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'error': error,
                    'severity': severity,
                    'has_strategy': matching_strategy is not None,
                    'strategy': self._strategy_to_dict(matching_strategy) if matching_strategy else None,
                    'recommended_action': self._get_recommended_action(error, severity)
                }
            )
        except Exception as e:
            logger.error(f"Error detecting error: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error detecting error: {str(e)}"
            )

    def _attempt_recovery(self, error: str, severity: str = None, auto_execute: bool = False, **kwargs) -> ToolResult:
        """Attempt to recover from an error."""
        try:
            if severity is None:
                severity = self._assess_severity(error)

            strategy = self._find_matching_strategy(error)

            if not strategy:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"No recovery strategy found for error: {error}"
                )

            if not strategy.auto_execute and not auto_execute:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        'error': error,
                        'severity': severity,
                        'strategy_available': True,
                        'auto_execute': False,
                        'message': 'Strategy found but requires manual execution'
                    }
                )

            start_time = time.time()
            attempts = 0
            success = False
            action_taken = "none"

            for action in strategy.actions:
                attempts += 1
                action_taken = action.action_type

                try:
                    # Simulate recovery action (production would execute actual recovery)
                    success = self._execute_recovery_action(action, error)
                    if success:
                        break
                except Exception as e:
                    logger.error(f"Recovery action failed: {str(e)}")
                    if attempts < action.max_attempts:
                        time.sleep(action.delay_sec)

            duration_sec = time.time() - start_time

            result = RecoveryResult(
                error_type=error,
                severity=severity,
                action_taken=action_taken,
                success=success,
                attempts=attempts,
                duration_sec=duration_sec,
                message="Recovery successful" if success else "Recovery failed"
            )

            self.recovery_history.append(result)

            return ToolResult(
                status=ToolStatus.SUCCESS if success else ToolStatus.ERROR,
                data={
                    'error': error,
                    'severity': severity,
                    'action_taken': action_taken,
                    'success': success,
                    'attempts': attempts,
                    'duration_sec': duration_sec,
                    'message': result.message
                }
            )
        except Exception as e:
            logger.error(f"Error attempting recovery: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error attempting recovery: {str(e)}"
            )

    def _add_strategy(self, strategy: Dict, **kwargs) -> ToolResult:
        """Add a new recovery strategy."""
        try:
            recovery_strategy = self._dict_to_strategy(strategy)
            self.recovery_strategies[strategy['error_pattern']] = recovery_strategy

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    'error_pattern': strategy['error_pattern'],
                    'added': True
                }
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Error adding strategy: {str(e)}"
            )

    def _list_strategies(self, **kwargs) -> ToolResult:
        """List all recovery strategies."""
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                'total_strategies': len(self.recovery_strategies),
                'strategies': [self._strategy_to_dict(s) for s in self.recovery_strategies.values()]
            }
        )

    def _get_history(self, **kwargs) -> ToolResult:
        """Get recovery history."""
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                'total_recoveries': len(self.recovery_history),
                'history': [self._result_to_dict(r) for r in self.recovery_history[-20:]]  # Last 20
            }
        )

    def _initialize_default_strategies(self):
        """Initialize default recovery strategies."""
        # Network errors
        self.recovery_strategies['connection_refused'] = RecoveryStrategy(
            error_pattern='connection refused|ECONNREFUSED',
            severity='high',
            actions=[
                RecoveryAction(action_type='retry', description='Retry connection', max_attempts=3, delay_sec=2.0),
                RecoveryAction(action_type='fallback', description='Use alternative endpoint', max_attempts=1, delay_sec=0.0)
            ],
            auto_execute=True
        )

        # Timeout errors
        self.recovery_strategies['timeout'] = RecoveryStrategy(
            error_pattern='timeout|TIMEOUT',
            severity='medium',
            actions=[
                RecoveryAction(action_type='retry', description='Retry with longer timeout', max_attempts=2, delay_sec=5.0),
                RecoveryAction(action_type='fallback', description='Skip operation', max_attempts=1, delay_sec=0.0)
            ],
            auto_execute=True
        )

        # File not found
        self.recovery_strategies['file_not_found'] = RecoveryStrategy(
            error_pattern='file not found|ENOENT',
            severity='medium',
            actions=[
                RecoveryAction(action_type='fallback', description='Create file', max_attempts=1, delay_sec=0.0),
                RecoveryAction(action_type='notify', description='Notify user', max_attempts=1, delay_sec=0.0)
            ],
            auto_execute=False
        )

        # Permission denied
        self.recovery_strategies['permission_denied'] = RecoveryStrategy(
            error_pattern='permission denied|EACCES',
            severity='high',
            actions=[
                RecoveryAction(action_type='notify', description='Request elevated permissions', max_attempts=1, delay_sec=0.0),
                RecoveryAction(action_type='fallback', description='Use alternative path', max_attempts=1, delay_sec=0.0)
            ],
            auto_execute=False
        )

        # Import errors
        self.recovery_strategies['import_error'] = RecoveryStrategy(
            error_pattern='import error|ModuleNotFoundError',
            severity='medium',
            actions=[
                RecoveryAction(action_type='retry', description='Install missing module', max_attempts=1, delay_sec=0.0),
                RecoveryAction(action_type='fallback', description='Use alternative import', max_attempts=1, delay_sec=0.0)
            ],
            auto_execute=True
        )

    def _assess_severity(self, error: str) -> str:
        """Assess error severity based on content."""
        error_lower = error.lower()

        if any(word in error_lower for word in ['critical', 'fatal', 'panic', 'security']):
            return 'critical'
        elif any(word in error_lower for word in ['error', 'failed', 'refused', 'denied']):
            return 'high'
        elif any(word in error_lower for word in ['warning', 'timeout', 'retry']):
            return 'medium'
        else:
            return 'low'

    def _find_matching_strategy(self, error: str) -> Optional[RecoveryStrategy]:
        """Find a matching recovery strategy for the error."""
        error_lower = error.lower()
        for pattern, strategy in self.recovery_strategies.items():
            # Check if error contains any pattern from the strategy
            if any(p.lower() in error_lower for p in pattern.split('|')):
                return strategy
        return None

    def _get_recommended_action(self, error: str, severity: str) -> str:
        """Get recommended action for the error."""
        if severity == 'critical':
            return 'Immediate manual intervention required'
        elif severity == 'high':
            return 'Auto-retry or manual review'
        elif severity == 'medium':
            return 'Auto-recovery recommended'
        else:
            return 'Log and continue'

    def _execute_recovery_action(self, action: RecoveryAction, error: str) -> bool:
        """Execute a recovery action (simulated for now)."""
        # In production, this would execute actual recovery logic
        logger.info(f"Executing recovery action: {action.action_type} - {action.description}")
        return True  # Simulate success

    def _strategy_to_dict(self, strategy: RecoveryStrategy) -> Dict:
        """Convert strategy to dictionary."""
        return {
            'error_pattern': strategy.error_pattern,
            'severity': strategy.severity,
            'actions': [
                {
                    'action_type': a.action_type,
                    'description': a.description,
                    'max_attempts': a.max_attempts,
                    'delay_sec': a.delay_sec
                }
                for a in strategy.actions
            ],
            'auto_execute': strategy.auto_execute
        }

    def _dict_to_strategy(self, data: Dict) -> RecoveryStrategy:
        """Convert dictionary to strategy."""
        return RecoveryStrategy(
            error_pattern=data['error_pattern'],
            severity=data['severity'],
            actions=[
                RecoveryAction(
                    action_type=a['action_type'],
                    description=a['description'],
                    max_attempts=a.get('max_attempts', 3),
                    delay_sec=a.get('delay_sec', 1.0)
                )
                for a in data.get('actions', [])
            ],
            auto_execute=data.get('auto_execute', True)
        )

    def _result_to_dict(self, result: RecoveryResult) -> Dict:
        """Convert result to dictionary."""
        return {
            'error_type': result.error_type,
            'severity': result.severity,
            'action_taken': result.action_taken,
            'success': result.success,
            'attempts': result.attempts,
            'duration_sec': result.duration_sec,
            'message': result.message
        }


# Standalone usage for testing
if __name__ == "__main__":
    recovery = AutoRecoveryTool()

    # Test 1: Detect error
    print("Test 1: Detect error")
    result = recovery.execute(operation='detect', error='Connection refused')
    print(json.dumps(result.data, indent=2))

    # Test 2: Attempt recovery
    print("\nTest 2: Attempt recovery")
    result = recovery.execute(operation='recover', error='Connection refused', auto_execute=True)
    print(json.dumps(result.data, indent=2))

    # Test 3: List strategies
    print("\nTest 3: List strategies")
    result = recovery.execute(operation='list_strategies')
    print(json.dumps(result.data, indent=2))

    # Test 4: Get history
    print("\nTest 4: Get history")
    result = recovery.execute(operation='history')
    print(json.dumps(result.data, indent=2))
