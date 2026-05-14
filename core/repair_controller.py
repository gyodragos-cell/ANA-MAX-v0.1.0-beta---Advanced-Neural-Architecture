"""
Controlled repair pipeline for ANA Engineer.
"""

from __future__ import annotations

import ast
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


def normalize_error_signature(error_text: str) -> str:
    """Collapse volatile tokens so similar failures map to one signature."""
    signature = error_text.strip().lower()
    signature = re.sub(r"[a-z]:\\\\[^\\s:]+", "<path>", signature)
    signature = re.sub(r"/[^\\s:]+", "<path>", signature)
    signature = re.sub(r"line \\d+", "line <n>", signature)
    signature = re.sub(r"\\b\\d+\\b", "<n>", signature)
    signature = re.sub(r"\\s+", " ", signature)
    return signature[:240]


class RepairController:
    """Repair code inside a workspace using backup + syntax + tests."""

    def __init__(self, agent, memory, workspace_root: str,
                 backup_root: Optional[str] = None):
        self.agent = agent
        self.memory = memory
        self.workspace_root = Path(workspace_root).resolve()
        self.backup_root = Path(backup_root).resolve() if backup_root else (self.workspace_root / "backups" / "repair_runs")
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def inspect_target(self, target: str = ".", error_text: str = "") -> List[Dict[str, Any]]:
        """Return syntax issues or explicit repair targets inside the workspace."""
        target_path = self._resolve_path(target)
        findings: List[Dict[str, Any]] = []

        if target_path.is_file():
            explicit_finding = self._inspect_file(target_path, error_text=error_text)
            if explicit_finding:
                findings.extend(explicit_finding)
            return findings

        for file_path in target_path.rglob("*.py"):
            if any(part in {"venv", "__pycache__", ".pytest_cache", "backups"} for part in file_path.parts):
                continue
            findings.extend(self._inspect_file(file_path))

        return findings

    def repair_project(self, target: str = ".", test_command: Optional[Sequence[str] | str] = None,
                       error_text: str = "") -> Dict[str, Any]:
        """Repair syntax or explicit file failures in the current workspace."""
        target_path = self._resolve_path(target)
        task_label = f"repair_project:{target_path}"
        run_id = self.memory.create_engineer_run(
            profile="repair",
            task=task_label,
            workspace=str(self.workspace_root),
            metadata={"target": str(target_path), "test_command": self._serialize_command(test_command), "error_text": error_text},
        )

        findings = self.inspect_target(target=str(target_path), error_text=error_text)
        self.memory.log_engineer_step(
            run_id,
            stage="inspect",
            title="Inspect target",
            status="completed",
            details={"issues_found": len(findings), "target": str(target_path)},
            step_order=1,
        )

        if not findings:
            result = {
                "run_id": run_id,
                "status": "completed",
                "changed_files": [],
                "issues_found": 0,
                "verifications": [],
                "rolled_back": False,
            }
            self.memory.finalize_engineer_run(run_id, "completed", "No repairable issues found", result)
            return result

        changed_files: List[str] = []
        backup_map: Dict[str, str] = {}
        attempts: List[Dict[str, Any]] = []
        step_order = 2

        for finding in findings:
            file_path = Path(finding["file"])
            error_message = finding["error"]
            signature = normalize_error_signature(error_message)
            known_pattern = self.memory.get_repair_pattern(signature)
            original_content = file_path.read_text(encoding="utf-8")
            backup_path = self._backup_file(file_path, run_id)
            backup_map[str(file_path)] = str(backup_path)

            self.memory.log_engineer_step(
                run_id,
                stage="backup",
                title=f"Backup {file_path.name}",
                status="completed",
                details={"file": str(file_path), "backup": str(backup_path)},
                step_order=step_order,
            )
            step_order += 1

            candidate = self._generate_patch(
                file_path=file_path,
                content=original_content,
                error_text=error_message,
                known_pattern=known_pattern,
            )
            if not candidate or candidate == original_content:
                attempt = {
                    "file": str(file_path),
                    "status": "failed",
                    "error": "No patch candidate produced",
                    "signature": signature,
                }
                attempts.append(attempt)
                self.memory.log_engineer_step(
                    run_id,
                    stage="patch",
                    title=f"Patch {file_path.name}",
                    status="failed",
                    details=attempt,
                    step_order=step_order,
                )
                step_order += 1
                self._restore_file(file_path, backup_path)
                continue

            file_path.write_text(candidate, encoding="utf-8")
            syntax_result = self._verify_python_syntax(file_path)
            self.memory.log_engineer_step(
                run_id,
                stage="verify",
                title=f"Syntax check {file_path.name}",
                status="completed" if syntax_result["passed"] else "failed",
                details=syntax_result,
                step_order=step_order,
            )
            step_order += 1

            if not syntax_result["passed"]:
                self._restore_file(file_path, backup_path)
                attempt = {
                    "file": str(file_path),
                    "status": "failed",
                    "error": syntax_result["error"],
                    "signature": signature,
                    "rolled_back": True,
                }
                attempts.append(attempt)
                self.memory.record_repair_pattern(
                    signature,
                    strategy="llm_patch",
                    successful=False,
                    patch_hint="syntax verification failed",
                    example_error=error_message,
                    metadata={"file": str(file_path)},
                )
                continue

            changed_files.append(str(file_path))
            attempt = {
                "file": str(file_path),
                "status": "patched",
                "signature": signature,
                "known_pattern": bool(known_pattern),
            }
            attempts.append(attempt)
            self.memory.record_repair_pattern(
                signature,
                strategy="llm_patch",
                successful=True,
                patch_hint=(known_pattern or {}).get("patch_hint", ""),
                example_error=error_message,
                metadata={"file": str(file_path)},
            )
            self.memory.save_error_solution(signature, f"Repaired {file_path.name} after syntax/test validation")

        verification_results: List[Dict[str, Any]] = []
        rolled_back = False
        status = "completed" if changed_files else "failed"

        if changed_files and test_command:
            test_result = self._run_test_command(test_command)
            verification_results.append(test_result)
            self.memory.log_engineer_step(
                run_id,
                stage="test",
                title="Run verification command",
                status="completed" if test_result["passed"] else "failed",
                details=test_result,
                step_order=step_order,
            )
            if not test_result["passed"]:
                for changed_file in changed_files:
                    self._restore_file(Path(changed_file), Path(backup_map[changed_file]))
                rolled_back = True
                status = "failed"
                changed_files = []

        summary = f"Repair attempts: {len(attempts)}, applied: {len([a for a in attempts if a['status'] == 'patched'])}"
        result = {
            "run_id": run_id,
            "status": status,
            "target": str(target_path),
            "issues_found": len(findings),
            "attempts": attempts,
            "changed_files": changed_files,
            "backups": backup_map,
            "verifications": verification_results,
            "rolled_back": rolled_back,
        }
        self.memory.finalize_engineer_run(run_id, status, summary, result)
        return result

    def _inspect_file(self, file_path: Path, error_text: str = "") -> List[Dict[str, Any]]:
        if file_path.suffix != ".py":
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            return [{"file": str(file_path), "error": f"ReadError: {exc}", "kind": "read_error"}]

        findings: List[Dict[str, Any]] = []
        try:
            ast.parse(content)
        except SyntaxError as exc:
            findings.append({
                "file": str(file_path),
                "error": f"SyntaxError: {exc}",
                "kind": "syntax",
                "line": getattr(exc, "lineno", None),
            })

        if error_text and not findings:
            findings.append({
                "file": str(file_path),
                "error": error_text,
                "kind": "explicit",
                "line": None,
            })

        return findings

    def _generate_patch(self, file_path: Path, content: str, error_text: str,
                        known_pattern: Optional[Dict[str, Any]]) -> str:
        if not self.agent:
            return content

        prompt = (
            "You are ANA Engineer repair controller.\n"
            "Return ONLY the complete repaired file content.\n"
            f"Workspace root: {self.workspace_root}\n"
            f"File: {file_path}\n"
            f"Error: {error_text}\n"
        )
        if known_pattern:
            prompt += f"Known successful hint: {known_pattern.get('patch_hint', '')}\n"
            prompt += f"Known example error: {known_pattern.get('example_error', '')}\n"
        prompt += f"\nCurrent code:\n```python\n{content}\n```"

        response = self.agent.send_message(prompt, allow_auto_tools=False, save_to_memory=False)
        response_text = str(response).strip()
        if "```" not in response_text:
            return response_text

        parts = response_text.split("```")
        for part in parts:
            stripped = part.strip()
            if not stripped:
                continue
            if stripped.startswith("python"):
                return stripped[6:].lstrip()
            return stripped
        return response_text

    def _verify_python_syntax(self, file_path: Path) -> Dict[str, Any]:
        try:
            source = file_path.read_text(encoding="utf-8")
            ast.parse(source)
            return {"passed": True, "type": "syntax", "file": str(file_path)}
        except SyntaxError as exc:
            return {"passed": False, "type": "syntax", "file": str(file_path), "error": str(exc)}

    def _run_test_command(self, test_command: Sequence[str] | str) -> Dict[str, Any]:
        try:
            if isinstance(test_command, str):
                result = subprocess.run(
                    test_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=str(self.workspace_root),
                    timeout=120,
                )
            else:
                result = subprocess.run(
                    list(test_command),
                    shell=False,
                    capture_output=True,
                    text=True,
                    cwd=str(self.workspace_root),
                    timeout=120,
                )
            return {
                "passed": result.returncode == 0,
                "type": "test_command",
                "command": self._serialize_command(test_command),
                "exit_code": result.returncode,
                "stdout": result.stdout[:4000],
                "stderr": result.stderr[:2000],
            }
        except Exception as exc:
            return {
                "passed": False,
                "type": "test_command",
                "command": self._serialize_command(test_command),
                "error": str(exc),
            }

    def _backup_file(self, file_path: Path, run_id: str) -> Path:
        relative = file_path.resolve().relative_to(self.workspace_root)
        backup_path = self.backup_root / run_id / relative
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _restore_file(self, file_path: Path, backup_path: Path) -> None:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, file_path)

    def _resolve_path(self, target: str) -> Path:
        candidate = Path(target)
        if not candidate.is_absolute():
            candidate = (self.workspace_root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if self.workspace_root not in candidate.parents and candidate != self.workspace_root:
            raise PermissionError(f"Target outside workspace is blocked: {candidate}")
        return candidate

    @staticmethod
    def _serialize_command(command: Optional[Sequence[str] | str]) -> str:
        if not command:
            return ""
        if isinstance(command, str):
            return command
        return " ".join(command)
