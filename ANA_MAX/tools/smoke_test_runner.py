"""
Smoke Test Runner - Test All ANA_MAX Tools
Author: ANA_MAX
Date: 2026-05-12
Category: infrastructure

Runs smoke tests for all tools to verify functionality.
Usage: python smoke_test_runner.py [--verbose] [--tool TOOL_NAME]
"""

from __future__ import annotations

import sys
import os
import logging
import importlib
import importlib.util
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Rezultat pentru un test."""
    tool_name: str
    test_name: str
    passed: bool
    message: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ToolTestReport:
    """Raport pentru un tool."""
    tool_name: str
    tests: List[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return len(self.tests)


class SmokeTestRunner:
    """Ruleaza smoke tests pentru toate tool-urile."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.reports: Dict[str, ToolTestReport] = {}
        # Adauga directorul parinte la sys.path
        parent_dir = str(Path(__file__).parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

    def _get_tools_dir(self) -> Path:
        """Gaseste directorul tools."""
        return Path(__file__).parent

    def _get_tool_files(self) -> List[Path]:
        """Gaseste toate fisierele de tool."""
        tools_dir = self._get_tools_dir()
        tools = []

        for file in tools_dir.glob("*_tool.py"):
            if file.stem not in ["smoke_test_runner", "base", "__init__"]:
                tools.append(file)

        return sorted(tools)

    def _load_tool(self, tool_path: Path) -> Optional[Any]:
        """Incarca un tool module."""
        try:
            module_name = f"tools.{tool_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, tool_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            logger.error(f"Failed to load {tool_path}: {e}")
        return None

    def _get_smoke_test_function(self, module: Any) -> Optional[callable]:
        """Gaseste functia de smoke test."""
        if hasattr(module, "smoke_test"):
            return module.smoke_test
        return None

    def run_tool_smoke_test(self, tool_name: str) -> ToolTestReport:
        """Ruleaza smoke test pentru un tool specific."""
        report = ToolTestReport(tool_name=tool_name)
        tools_dir = self._get_tools_dir()

        tool_file = tools_dir / f"{tool_name}.py"
        if not tool_file.exists():
            self._add_result(report, "load", False, error=f"File not found: {tool_file}")
            return report

        module = self._load_tool(tool_file)
        if not module:
            self._add_result(report, "load", False, error="Failed to load module")
            return report

        self._add_result(report, "load", True, message="Module loaded")

        smoke_test_fn = self._get_smoke_test_function(module)
        if not smoke_test_fn:
            self._add_result(report, "smoke_test", True, message="No smoke test function found (optional)")
            return report

        try:
            import io
            from contextlib import redirect_stdout, redirect_stderr

            output = io.StringIO()
            error_output = io.StringIO()

            start = datetime.now()
            with redirect_stdout(output), redirect_stderr(error_output):
                smoke_test_fn()
            duration = (datetime.now() - start).total_seconds() * 1000

            stdout = output.getvalue()
            stderr = error_output.getvalue()

            if stderr:
                self._add_result(report, "smoke_test", True, message=f"Test ran (with warnings: {stderr[:200]})", duration_ms=duration)
            else:
                self._add_result(report, "smoke_test", True, message=f"Test passed", duration_ms=duration)

        except Exception as e:
            self._add_result(report, "smoke_test", False, error=str(e))

        return report

    def _add_result(self, report: ToolTestReport, test_name: str, passed: bool, message: str = "", error: Optional[str] = None, duration_ms: float = 0.0) -> None:
        """Adauga un rezultat."""
        result = TestResult(
            tool_name=report.tool_name,
            test_name=test_name,
            passed=passed,
            message=message,
            error=error,
            duration_ms=duration_ms
        )
        report.tests.append(result)
        self.results.append(result)

        if passed:
            report.passed += 1
        else:
            report.failed += 1

    def run_all_tests(self, specific_tool: Optional[str] = None) -> Dict[str, ToolTestReport]:
        """Ruleaza toate smoke tests."""
        if specific_tool:
            tool_files = [Path(f"{specific_tool}.py")]
        else:
            tool_files = self._get_tool_files()

        for tool_file in tool_files:
            tool_name = tool_file.stem
            report = self.run_tool_smoke_test(tool_name)
            self.reports[tool_name] = report

        return self.reports

    def print_report(self) -> None:
        """Afiseaza raportul."""
        print("\n" + "=" * 70)
        print("ANA_MAX - SMOKE TEST REPORT")
        print("=" * 70)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        total_tools = len(self.reports)
        total_tests = sum(r.total for r in self.reports.values())
        total_passed = sum(r.passed for r in self.reports.values())
        total_failed = sum(r.failed for r in self.reports.values())

        print(f"Tools tested: {total_tools}")
        print(f"Tests run: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print()

        # Summary table
        print("-" * 70)
        print(f"{'TOOL':<30} {'STATUS':<10} {'PASSED':<10} {'FAILED':<10}")
        print("-" * 70)

        for tool_name, report in sorted(self.reports.items()):
            status = "OK" if report.failed == 0 else "FAIL"
            status_color = "\033[92m" if report.failed == 0 else "\033[91m"
            print(f"{tool_name:<30} {status_color}{status:<10}\033[0m {report.passed:<10} {report.failed:<10}")

        print("-" * 70)

        # Failed tests details
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print("\n\033[91mFAILED TESTS:\033[0m")
            for result in failed_tests:
                print(f"  - {result.tool_name}.{result.test_name}: {result.error}")

        print("\n" + "=" * 70)

    def get_summary(self) -> Dict[str, Any]:
        """Returneaza un summary dict."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tools": len(self.reports),
            "total_tests": sum(r.total for r in self.reports.values()),
            "passed": sum(r.passed for r in self.reports.values()),
            "failed": sum(r.failed for r in self.reports.values()),
            "failed_tools": [name for name, r in self.reports.items() if r.failed > 0]
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="ANA_MAX Smoke Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--tool", "-t", type=str, help="Test specific tool only")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    print("\033[94m[*] ANA_MAX Smoke Test Runner\033[0m")
    print(f"[*] Testing tools in: {Path(__file__).parent}")

    runner = SmokeTestRunner(verbose=args.verbose)
    
    reports = runner.run_all_tests(specific_tool=args.tool)
    
    if args.json:
        import json
        print(json.dumps(runner.get_summary(), indent=2))
    else:
        runner.print_report()
    
    # Exit with error code if any tests failed
    failed_count = sum(r.failed for r in reports.values())
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == "__main__":
    main()