#!/usr/bin/env python3
"""
ANA MAX OS-3 GitHub Pattern Extractor
Autonomy Zone: This module operates with maximum autonomy inside the project workspace.
It may analyze, modify, and extend project components as needed.
It must remain safe and operate only within project boundaries.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add workspace root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ANA_MAX.self_optimization.os3_common import print_raw_json


WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = WORKSPACE_ROOT / "docs"
TECHNICAL_NOTES = DOCS_DIR / "TECHNICAL_NOTES.md"
OPTIMIZATIONS = DOCS_DIR / "OPTIMIZATIONS.md"


@dataclass
class Pattern:
    """Extracted pattern from a repository."""
    type: str  # "architecture", "tool", "testing", "documentation", "observability"
    name: str
    description: str
    source_path: str
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class IntegrationProposal:
    """Proposal for integrating a pattern into ANA MAX."""
    pattern_name: str
    integration_type: str  # "adopt", "adapt", "inspire"
    target_location: str
    rationale: str
    effort: str  # "low", "medium", "high"
    priority: str  # "low", "medium", "high"


class GitHubPatternExtractor:
    """Analyzes provided repositories, extracts patterns, proposes integrations."""

    def __init__(
        self,
        *,
        workspace_root: Path = WORKSPACE_ROOT,
        technical_notes: Path = TECHNICAL_NOTES,
        optimizations: Path = OPTIMIZATIONS,
    ) -> None:
        self.workspace_root = workspace_root
        self.technical_notes = technical_notes
        self.optimizations = optimizations
        self.patterns: List[Pattern] = []
        self.integration_proposals: List[IntegrationProposal] = []

    def analyze_repo(self, repo_path_or_snapshot: str | Path) -> Dict[str, Any]:
        """Analyze a repository snapshot or path."""
        repo_path = Path(repo_path_or_snapshot)

        if not repo_path.exists():
            return {"error": "Repository path does not exist", "path": str(repo_path)}

        analysis = {
            "repo_path": str(repo_path),
            "timestamp": datetime.now().isoformat(),
            "structure": self._analyze_structure(repo_path),
            "modules": self._analyze_modules(repo_path),
            "tools": self._analyze_tools(repo_path),
            "patterns": [],
            "integrations": [],
        }

        return analysis

    def _analyze_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository structure."""
        structure = {
            "directories": [],
            "files_by_extension": {},
            "total_files": 0,
        }

        for root, dirs, files in repo_path.walk():
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__", "node_modules"}]

            for dir_name in dirs:
                rel_path = Path(root) / dir_name
                structure["directories"].append(str(rel_path.relative_to(repo_path)))

            for file in files:
                structure["total_files"] += 1
                ext = Path(file).suffix
                structure["files_by_extension"][ext] = structure["files_by_extension"].get(ext, 0) + 1

        return structure

    def _analyze_modules(self, repo_path: Path) -> List[Dict[str, Any]]:
        """Analyze Python modules."""
        modules = []

        for py_file in repo_path.rglob("*.py"):
            try:
                with py_file.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                module_info = {
                    "path": str(py_file.relative_to(repo_path)),
                    "size": py_file.stat().st_size,
                    "imports": self._extract_imports(content),
                    "classes": self._extract_classes(content),
                    "functions": self._extract_functions(content),
                }
                modules.append(module_info)
            except Exception:
                pass

        return modules

    def _analyze_tools(self, repo_path: Path) -> List[Dict[str, Any]]:
        """Analyze tool-like files."""
        tools = []

        for py_file in repo_path.rglob("*tool*.py"):
            try:
                with py_file.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                tool_info = {
                    "path": str(py_file.relative_to(repo_path)),
                    "name": py_file.stem,
                    "size": py_file.stat().st_size,
                    "has_execute_method": "def execute" in content or "def run" in content,
                    "has_config": "config" in content.lower(),
                }
                tools.append(tool_info)
            except Exception:
                pass

        return tools

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements."""
        imports = []
        patterns = [
            r"^import\s+(\w+)",
            r"^from\s+(\w+)",
        ]

        for line in content.split("\n"):
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    imports.append(match.group(1))

        return imports

    def _extract_classes(self, content: str) -> List[str]:
        """Extract class definitions."""
        classes = []
        for match in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
            classes.append(match.group(1))
        return classes

    def _extract_functions(self, content: str) -> List[str]:
        """Extract function definitions."""
        functions = []
        for match in re.finditer(r"^def\s+(\w+)", content, re.MULTILINE):
            functions.append(match.group(1))
        return functions

    def extract_patterns(self, analysis: Dict[str, Any]) -> List[Pattern]:
        """Extract useful patterns from repository analysis."""
        patterns: List[Pattern] = []

        # Extract architecture patterns
        if "src" in str(analysis.get("structure", {}).get("directories", [])):
            patterns.append(Pattern(
                type="architecture",
                name="src_layout",
                description="Uses src/ directory layout for source code",
                source_path="src/",
                confidence=0.8,
                metadata={"category": "structure"},
            ))

        # Extract tool patterns
        tools = analysis.get("tools", [])
        for tool in tools:
            if tool.get("has_execute_method"):
                patterns.append(Pattern(
                    type="tool",
                    name=tool["name"],
                    description=f"Tool with execute/run method: {tool['name']}",
                    source_path=tool["path"],
                    confidence=0.7,
                    metadata=tool,
                ))

        # Extract testing patterns
        for py_file in analysis.get("structure", {}).get("files_by_extension", {}):
            if "test" in py_file:
                patterns.append(Pattern(
                    type="testing",
                    name="pytest_structure",
                    description="Uses pytest for testing",
                    source_path="test_*.py",
                    confidence=0.6,
                    metadata={"framework": "pytest"},
                ))

        self.patterns = patterns
        return patterns

    def propose_integrations(self, patterns: List[Pattern]) -> List[IntegrationProposal]:
        """Propose integrations for extracted patterns."""
        proposals: List[IntegrationProposal] = []

        for pattern in patterns:
            if pattern.type == "tool":
                proposals.append(IntegrationProposal(
                    pattern_name=pattern.name,
                    integration_type="adapt",
                    target_location="ANA_MAX/tools/",
                    rationale=f"Adapt tool pattern from {pattern.source_path} for ANA MAX",
                    effort="medium",
                    priority="medium",
                ))

            elif pattern.type == "architecture":
                proposals.append(IntegrationProposal(
                    pattern_name=pattern.name,
                    integration_type="inspire",
                    target_location="ANA_MAX/",
                    rationale=f"Consider {pattern.name} pattern for ANA MAX structure",
                    effort="low",
                    priority="low",
                ))

            elif pattern.type == "testing":
                proposals.append(IntegrationProposal(
                    pattern_name=pattern.name,
                    integration_type="adopt",
                    target_location="tests/",
                    rationale=f"Adopt {pattern.name} testing pattern",
                    effort="low",
                    priority="high",
                ))

        self.integration_proposals = proposals
        return proposals

    def write_patterns_to_docs(self) -> None:
        """Write patterns and integrations to TECHNICAL_NOTES.md and OPTIMIZATIONS.md."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update TECHNICAL_NOTES.md
        tech_entry = f"\n## {timestamp}\n\n"
        tech_entry += "- GitHub Pattern Extractor executed\n"
        tech_entry += f"- Extracted {len(self.patterns)} patterns\n"
        tech_entry += f"- Proposed {len(self.integration_proposals)} integrations\n\n"

        if self.patterns:
            tech_entry += "### Extracted Patterns\n\n"
            for pattern in self.patterns[:10]:  # Limit to top 10
                tech_entry += f"- **{pattern.type}**: {pattern.name}\n"
                tech_entry += f"  {pattern.description}\n"
                tech_entry += f"  Source: {pattern.source_path}\n"

        with self.technical_notes.open("a", encoding="utf-8") as f:
            f.write(tech_entry)

        # Update OPTIMIZATIONS.md
        opt_entry = f"\n## {timestamp}\n\n"

        if self.integration_proposals:
            opt_entry += "### Integration Proposals\n\n"
            for proposal in self.integration_proposals[:10]:  # Limit to top 10
                opt_entry += f"- **{proposal.pattern_name}** ({proposal.integration_type})\n"
                opt_entry += f"  Target: {proposal.target_location}\n"
                opt_entry += f"  Rationale: {proposal.rationale}\n"
                opt_entry += f"  Effort: {proposal.effort}, Priority: {proposal.priority}\n"

        with self.optimizations.open("a", encoding="utf-8") as f:
            f.write(opt_entry)

    def run_cycle(self, repo_path_or_snapshot: str | Path) -> Dict[str, Any]:
        """Run a complete pattern extraction cycle."""
        analysis = self.analyze_repo(repo_path_or_snapshot)
        patterns = self.extract_patterns(analysis)
        proposals = self.propose_integrations(patterns)
        self.write_patterns_to_docs()

        return {
            "analysis": analysis,
            "patterns_extracted": len(patterns),
            "integrations_proposed": len(proposals),
        }


def main() -> int:
    """CLI entry point for GitHub pattern extractor."""
    import argparse

    parser = argparse.ArgumentParser(description="ANA MAX OS-3 GitHub Pattern Extractor")
    parser.add_argument("repo_path", help="Path to repository snapshot or directory")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze repository")
    parser.add_argument("--extract-only", action="store_true", help="Analyze and extract patterns")
    parser.add_argument("--cycle", action="store_true", help="Run complete extraction cycle")
    args = parser.parse_args()

    extractor = GitHubPatternExtractor()

    if args.analyze_only:
        analysis = extractor.analyze_repo(args.repo_path)
        print_raw_json(analysis)
        return 0

    if args.extract_only:
        analysis = extractor.analyze_repo(args.repo_path)
        patterns = extractor.extract_patterns(analysis)
        print_raw_json([asdict(p) for p in patterns])
        return 0

    if args.cycle:
        result = extractor.run_cycle(args.repo_path)
        print_raw_json(result)
        return 0

    # Default: run cycle
    result = extractor.run_cycle(args.repo_path)
    print_raw_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
