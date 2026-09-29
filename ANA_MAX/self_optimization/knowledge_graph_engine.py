#!/usr/bin/env python3
"""
ANA MAX OS-3 Knowledge Graph Engine
Autonomy Zone: This module operates with maximum autonomy inside the project workspace.
It may analyze, modify, and extend project components as needed.
It must remain safe and operate only within project boundaries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

# Add workspace root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ANA_MAX.self_optimization.os3_common import print_raw_json


WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = WORKSPACE_ROOT / "docs"
KNOWLEDGE_GRAPH_MD = DOCS_DIR / "KNOWLEDGE_GRAPH.md"
KNOWLEDGE_GRAPH_JSON = WORKSPACE_ROOT / "ANA_MAX" / "memory" / "knowledge_graph.json"
KNOWLEDGE_GRAPH_HISTORY = WORKSPACE_ROOT / "ANA_MAX" / "memory" / "knowledge_graph_history"


@dataclass
class Node:
    """Represents a node in the knowledge graph."""
    id: str
    type: str  # "module", "tool", "doc", "script", "directory"
    name: str
    path: str
    description: str
    metadata: Dict[str, Any]


@dataclass
class Edge:
    """Represents a relationship between nodes."""
    source: str
    target: str
    type: str  # "imports", "uses", "documents", "contains", "depends_on"
    weight: float


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph structure."""
    nodes: Dict[str, Node]
    edges: List[Edge]
    timestamp: str
    metadata: Dict[str, Any]


class KnowledgeGraphEngine:
    """Maps relationships between tools, modules, and docs; generates diagrams and structured descriptions."""

    def __init__(
        self,
        *,
        workspace_root: Path = WORKSPACE_ROOT,
        knowledge_graph_md: Path = KNOWLEDGE_GRAPH_MD,
        knowledge_graph_json: Path = KNOWLEDGE_GRAPH_JSON,
        history_dir: Path = KNOWLEDGE_GRAPH_HISTORY,
    ) -> None:
        self.workspace_root = workspace_root
        self.knowledge_graph_md = knowledge_graph_md
        self.knowledge_graph_json = knowledge_graph_json
        self.history_dir = history_dir
        self.graph: KnowledgeGraph | None = None
        self.graph_evolution: Dict[str, Any] = {}

    def scan_project(self) -> Dict[str, Node]:
        """Scan project and build node map."""
        nodes: Dict[str, Node] = {}

        # Scan ANA_MAX/core modules
        core_dir = self.workspace_root / "ANA_MAX" / "core"
        if core_dir.exists():
            for file in core_dir.glob("*.py"):
                node_id = f"core_{file.stem}"
                nodes[node_id] = Node(
                    id=node_id,
                    type="module",
                    name=file.stem,
                    path=str(file.relative_to(self.workspace_root)),
                    description=f"Core module: {file.stem}",
                    metadata={"size": file.stat().st_size},
                )

        # Scan ANA_MAX/tools
        tools_dir = self.workspace_root / "ANA_MAX" / "tools"
        if tools_dir.exists():
            for file in tools_dir.glob("*_tool.py"):
                node_id = f"tool_{file.stem}"
                nodes[node_id] = Node(
                    id=node_id,
                    type="tool",
                    name=file.stem,
                    path=str(file.relative_to(self.workspace_root)),
                    description=f"Tool: {file.stem}",
                    metadata={"size": file.stat().st_size},
                )

        # Scan docs
        docs_dir = self.workspace_root / "docs"
        if docs_dir.exists():
            for file in docs_dir.glob("*.md"):
                node_id = f"doc_{file.stem}"
                nodes[node_id] = Node(
                    id=node_id,
                    type="doc",
                    name=file.stem,
                    path=str(file.relative_to(self.workspace_root)),
                    description=f"Documentation: {file.stem}",
                    metadata={"size": file.stat().st_size},
                )

        # Scan scripts
        scripts_dir = self.workspace_root / "scripts"
        if scripts_dir.exists():
            for file in scripts_dir.glob("*.ps1"):
                node_id = f"script_{file.stem}"
                nodes[node_id] = Node(
                    id=node_id,
                    type="script",
                    name=file.stem,
                    path=str(file.relative_to(self.workspace_root)),
                    description=f"Script: {file.stem}",
                    metadata={"size": file.stat().st_size},
                )

        # Scan self_optimization modules
        self_opt_dir = self.workspace_root / "ANA_MAX" / "self_optimization"
        if self_opt_dir.exists():
            for file in self_opt_dir.glob("*.py"):
                node_id = f"self_opt_{file.stem}"
                nodes[node_id] = Node(
                    id=node_id,
                    type="module",
                    name=file.stem,
                    path=str(file.relative_to(self.workspace_root)),
                    description=f"Self-optimization module: {file.stem}",
                    metadata={"size": file.stat().st_size},
                )

        return nodes

    def build_graph(self) -> KnowledgeGraph:
        """Build the complete knowledge graph with nodes and edges."""
        nodes = self.scan_project()
        edges: List[Edge] = []

        # Build edges based on relationships
        node_ids = list(nodes.keys())

        # Module-to-module relationships (imports)
        for node_id, node in nodes.items():
            if node.type in ["module", "tool"]:
                # Tools are used by modules
                if node.type == "tool":
                    for other_id in node_ids:
                        other = nodes[other_id]
                        if other.type == "module":
                            edges.append(Edge(
                                source=other_id,
                                target=node_id,
                                type="uses",
                                weight=1.0,
                            ))

        # Doc-to-module relationships (documentation)
        for node_id, node in nodes.items():
            if node.type == "doc":
                # Docs document modules/tools
                doc_name = node.name.lower()
                for other_id in node_ids:
                    other = nodes[other_id]
                    if other.type in ["module", "tool"]:
                        if other.name.lower() in doc_name or doc_name in other.name.lower():
                            edges.append(Edge(
                                source=node_id,
                                target=other_id,
                                type="documents",
                                weight=1.0,
                            ))

        # Directory containment
        for node_id, node in nodes.items():
            parent_dir = str(Path(node.path).parent)
            for other_id, other in nodes.items():
                if other_id != node_id and other.type == "directory":
                    if parent_dir.startswith(other.path):
                        edges.append(Edge(
                            source=other_id,
                            target=node_id,
                            type="contains",
                            weight=1.0,
                        ))

        self.graph = KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            timestamp=datetime.now().isoformat(),
            metadata={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_types": {t: sum(1 for n in nodes.values() if n.type == t) for t in set(n.type for n in nodes.values())},
            },
        )
        self.graph.metadata["evolution"] = self.compute_evolution_metadata(self.graph)

        return self.graph

    def _load_previous_graph(self) -> Dict[str, Any]:
        if self.knowledge_graph_json.exists():
            try:
                data = json.loads(self.knowledge_graph_json.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _node_degrees(self, graph: KnowledgeGraph) -> Dict[str, int]:
        degrees = {node_id: 0 for node_id in graph.nodes}
        for edge in graph.edges:
            if edge.source in degrees:
                degrees[edge.source] += 1
            if edge.target in degrees:
                degrees[edge.target] += 1
        return degrees

    def compute_evolution_metadata(self, graph: KnowledgeGraph) -> Dict[str, Any]:
        previous = self._load_previous_graph()
        previous_nodes = set((previous.get("nodes") or {}).keys())
        previous_edges = {
            (edge.get("source"), edge.get("target"), edge.get("type"))
            for edge in previous.get("edges", [])
            if isinstance(edge, dict)
        }
        current_nodes = set(graph.nodes)
        current_edges = {(edge.source, edge.target, edge.type) for edge in graph.edges}
        degrees = self._node_degrees(graph)
        hot_nodes = sorted(
            [
                {
                    "id": node_id,
                    "name": graph.nodes[node_id].name,
                    "type": graph.nodes[node_id].type,
                    "degree": degree,
                }
                for node_id, degree in degrees.items()
                if degree >= 5
            ],
            key=lambda item: (-int(item["degree"]), str(item["id"])),
        )[:20]
        cold_nodes = sorted(
            [
                {
                    "id": node_id,
                    "name": node.name,
                    "type": node.type,
                    "path": node.path,
                    "degree": degrees.get(node_id, 0),
                }
                for node_id, node in graph.nodes.items()
                if degrees.get(node_id, 0) == 0
            ],
            key=lambda item: (str(item["type"]), str(item["id"])),
        )[:30]
        metadata = {
            "schema": "ana.os4.knowledge_graph_evolution.v1",
            "previous_graph_present": bool(previous),
            "added_nodes": sorted(current_nodes - previous_nodes),
            "removed_nodes": sorted(previous_nodes - current_nodes),
            "added_edges": [
                {"source": source, "target": target, "type": edge_type}
                for source, target, edge_type in sorted(current_edges - previous_edges)
            ][:100],
            "removed_edges": [
                {"source": source, "target": target, "type": edge_type}
                for source, target, edge_type in sorted(previous_edges - current_edges)
            ][:100],
            "hot_nodes": hot_nodes,
            "cold_nodes": cold_nodes,
            "hot_node_count": len(hot_nodes),
            "cold_node_count": len(cold_nodes),
        }
        self.graph_evolution = metadata
        return metadata

    def render_markdown(self) -> str:
        """Render knowledge graph as markdown documentation."""
        if not self.graph:
            self.build_graph()

        md = f"# ANA MAX Knowledge Graph\n\n"
        md += f"Generated: {self.graph.timestamp}\n\n"
        md += f"**Total Nodes**: {self.graph.metadata['total_nodes']}\n"
        md += f"**Total Edges**: {self.graph.metadata['total_edges']}\n\n"

        # Nodes by type
        md += "## Nodes by Type\n\n"
        for node_type, count in self.graph.metadata["node_types"].items():
            md += f"- **{node_type}**: {count}\n"

        # Core modules
        md += "\n## Core Modules\n\n"
        for node_id, node in sorted(self.graph.nodes.items()):
            if node.type == "module" and node_id.startswith("core_"):
                md += f"- **{node.name}**: {node.description}\n"
                md += f"  Path: `{node.path}`\n"

        # Tools
        md += "\n## Tools\n\n"
        for node_id, node in sorted(self.graph.nodes.items()):
            if node.type == "tool":
                md += f"- **{node.name}**: {node.description}\n"
                md += f"  Path: `{node.path}`\n"

        # Self-optimization modules
        md += "\n## Self-Optimization Modules\n\n"
        for node_id, node in sorted(self.graph.nodes.items()):
            if node.type == "module" and node_id.startswith("self_opt_"):
                md += f"- **{node.name}**: {node.description}\n"
                md += f"  Path: `{node.path}`\n"

        # Documentation
        md += "\n## Documentation\n\n"
        for node_id, node in sorted(self.graph.nodes.items()):
            if node.type == "doc":
                md += f"- **{node.name}**: {node.description}\n"
                md += f"  Path: `{node.path}`\n"

        # Scripts
        md += "\n## Scripts\n\n"
        for node_id, node in sorted(self.graph.nodes.items()):
            if node.type == "script":
                md += f"- **{node.name}**: {node.description}\n"
                md += f"  Path: `{node.path}`\n"

        # Key relationships
        md += "\n## Key Relationships\n\n"
        edge_types: Dict[str, int] = {}
        for edge in self.graph.edges:
            edge_types[edge.type] = edge_types.get(edge.type, 0) + 1

        for edge_type, count in edge_types.items():
            md += f"- **{edge_type}**: {count} relationships\n"

        evolution = self.graph.metadata.get("evolution", {})
        md += "\n## Evolution\n\n"
        md += f"- Previous graph present: {evolution.get('previous_graph_present', False)}\n"
        md += f"- Added nodes: {len(evolution.get('added_nodes', []))}\n"
        md += f"- Removed nodes: {len(evolution.get('removed_nodes', []))}\n"
        md += f"- Added edges sample: {len(evolution.get('added_edges', []))}\n"
        md += f"- Removed edges sample: {len(evolution.get('removed_edges', []))}\n"

        md += "\n## Hot Areas\n\n"
        hot_nodes = evolution.get("hot_nodes", [])
        if hot_nodes:
            for item in hot_nodes[:15]:
                md += f"- **{item['name']}** (`{item['type']}`): degree {item['degree']}\n"
        else:
            md += "- No hot nodes detected yet.\n"

        md += "\n## Cold Areas / Refactor Candidates\n\n"
        cold_nodes = evolution.get("cold_nodes", [])
        if cold_nodes:
            for item in cold_nodes[:15]:
                md += f"- **{item['name']}** (`{item['type']}`): `{item['path']}`\n"
        else:
            md += "- No cold nodes detected yet.\n"

        return md

    def save_graph(self) -> None:
        """Save knowledge graph to JSON and markdown files."""
        if not self.graph:
            self.build_graph()

        # Save JSON
        self.knowledge_graph_json.parent.mkdir(parents=True, exist_ok=True)
        graph_data = {
            "timestamp": self.graph.timestamp,
            "metadata": self.graph.metadata,
            "nodes": {id: asdict(node) for id, node in self.graph.nodes.items()},
            "edges": [asdict(edge) for edge in self.graph.edges],
        }

        with self.knowledge_graph_json.open("w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, default=str)

        self.history_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        history_path = self.history_dir / f"knowledge_graph_{stamp}.json"
        with history_path.open("w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, default=str)

        # Save Markdown
        md_content = self.render_markdown()
        with self.knowledge_graph_md.open("w", encoding="utf-8") as f:
            f.write(md_content)

    def run_cycle(self) -> Dict[str, Any]:
        """Run a complete knowledge graph cycle."""
        self.build_graph()
        self.save_graph()

        return {
            "nodes_count": len(self.graph.nodes),
            "edges_count": len(self.graph.edges),
            "node_types": self.graph.metadata["node_types"],
            "evolution": self.graph.metadata.get("evolution", {}),
            "json_saved": str(self.knowledge_graph_json),
            "markdown_saved": str(self.knowledge_graph_md),
            "history_dir": str(self.history_dir),
        }


def main() -> int:
    """CLI entry point for knowledge graph engine."""
    import argparse

    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Knowledge Graph Engine")
    parser.add_argument("--scan-only", action="store_true", help="Only scan project")
    parser.add_argument("--build-only", action="store_true", help="Scan and build graph")
    parser.add_argument("--render-only", action="store_true", help="Build and render markdown")
    parser.add_argument("--cycle", action="store_true", help="Run complete knowledge graph cycle")
    args = parser.parse_args()

    engine = KnowledgeGraphEngine()

    if args.scan_only:
        nodes = engine.scan_project()
        print_raw_json({id: asdict(node) for id, node in nodes.items()})
        return 0

    if args.build_only:
        graph = engine.build_graph()
        print_raw_json({
            "metadata": graph.metadata,
            "nodes": {id: asdict(node) for id, node in graph.nodes.items()},
            "edges": [asdict(edge) for edge in graph.edges],
        })
        return 0

    if args.render_only:
        md = engine.render_markdown()
        print(md)
        return 0

    if args.cycle:
        result = engine.run_cycle()
        print_raw_json(result)
        return 0

    # Default: run cycle
    result = engine.run_cycle()
    print_raw_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
