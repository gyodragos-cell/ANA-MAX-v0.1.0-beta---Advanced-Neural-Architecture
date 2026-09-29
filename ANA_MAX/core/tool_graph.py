"""
ANA MAX - Tool Graph (Graph-Based Tool Routing)
====================================================
Inspirat din self-healing-router GitHub
- Dijkstra algorithm pentru tool routing
- 93% mai putine LLM calls
- Auto-rerouting la failures
- Zero silent failures
"""

import heapq
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path

from core.session_logger import log_action, log_result, log_error, log_pattern

logger = logging.getLogger("TOOL_GRAPH")


@dataclass
class ToolNode:
    """Nod in graph reprezentand un tool."""
    name: str
    latency: float = 0.0  # Average latency in seconds
    failure_rate: float = 0.0  # Failure rate 0.0-1.0
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    
    @property
    def edge_weight(self) -> float:
        """Calculate edge weight based on latency and failure rate."""
        # Higher weight = worse path
        return self.latency * 0.5 + self.failure_rate * 10.0
    
    def record_success(self, latency: float):
        """Record a successful execution."""
        self.success_count += 1
        self.failure_count = 0  # Reset failure streak
        self.last_used = time.time()
        # Update latency with exponential moving average
        if self.latency == 0:
            self.latency = latency
        else:
            self.latency = 0.9 * self.latency + 0.1 * latency
        # Update failure rate
        self.failure_rate = max(0.0, self.failure_rate * 0.9)
    
    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_used = time.time()
        # Update failure rate
        self.failure_rate = min(1.0, self.failure_rate * 1.1 + 0.05)
    
    def reset_failure_streak(self):
        """Reset failure rate after recovery."""
        self.failure_count = 0
        self.failure_rate = max(0.0, self.failure_rate * 0.5)


@dataclass
class ToolEdge:
    """Edge intre doua tool-uri."""
    from_tool: str
    to_tool: str
    weight: float = 1.0
    active: bool = True


class ToolGraph:
    """Graph pentru tool routing cu Dijkstra algorithm."""
    
    def __init__(self):
        self.nodes: Dict[str, ToolNode] = {}
        self.edges: Dict[str, List[ToolEdge]] = {}  # from_tool -> edges
        self.start_node = "START"
        self.end_node = "END"
        
        # Add start and end nodes
        self.add_node(self.start_node, latency=0.0, failure_rate=0.0)
        self.add_node(self.end_node, latency=0.0, failure_rate=0.0)
        
        log_action("ToolGraph initialized", {"nodes": "START, END"})
    
    def add_node(self, name: str, latency: float = 0.0, failure_rate: float = 0.0):
        """Add a tool node to the graph."""
        if name not in self.nodes:
            self.nodes[name] = ToolNode(
                name=name,
                latency=latency,
                failure_rate=failure_rate
            )
            self.edges[name] = []
            log_action(f"Tool node added: {name}", {"latency": latency, "failure_rate": failure_rate})
    
    def add_edge(self, from_tool: str, to_tool: str, weight: float = 1.0):
        """Add a directed edge between tools."""
        if from_tool not in self.nodes or to_tool not in self.nodes:
            log_error(f"Cannot add edge: node not found {from_tool} -> {to_tool}")
            return
        
        edge = ToolEdge(from_tool=from_tool, to_tool=to_tool, weight=weight)
        self.edges[from_tool].append(edge)
        log_action(f"Edge added: {from_tool} -> {to_tool}", {"weight": weight})
    
    def set_edge_weight(self, from_tool: str, to_tool: str, weight: float):
        """Set edge weight (infinity for disabled edges)."""
        for edge in self.edges.get(from_tool, []):
            if edge.to_tool == to_tool:
                edge.weight = weight
                edge.active = weight < float('inf')
                break
    
    def disable_edge(self, from_tool: str, to_tool: str):
        """Disable an edge by setting weight to infinity."""
        self.set_edge_weight(from_tool, to_tool, float('inf'))
        log_pattern(f"Edge disabled: {from_tool} -> {to_tool}", "INFO")
    
    def enable_edge(self, from_tool: str, to_tool: str):
        """Enable an edge by resetting to default weight."""
        # Calculate default weight from node characteristics
        from_node = self.nodes.get(from_tool)
        to_node = self.nodes.get(to_tool)
        if from_node and to_node:
            default_weight = (from_node.edge_weight + to_node.edge_weight) / 2
            self.set_edge_weight(from_tool, to_tool, default_weight)
    
    def get_shortest_path(self, start: str, end: str) -> Tuple[List[str], float]:
        """Find shortest path using Dijkstra's algorithm."""
        if start not in self.nodes or end not in self.nodes:
            return [], float('inf')
        
        # Dijkstra's algorithm
        distances = {node: float('inf') for node in self.nodes}
        distances[start] = 0
        previous = {node: None for node in self.nodes}
        visited = set()
        
        # Priority queue: (distance, node)
        pq = [(0, start)]
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current in visited:
                continue
            visited.add(current)
            
            if current == end:
                # Reconstruct path
                path = []
                while current is not None:
                    path.append(current)
                    current = previous[current]
                path.reverse()
                return path, distances[end]
            
            # Explore neighbors
            for edge in self.edges.get(current, []):
                if not edge.active:
                    continue
                
                neighbor = edge.to_tool
                new_dist = current_dist + edge.weight
                
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))
        
        return [], float('inf')  # No path found
    
    def update_tool_performance(self, tool_name: str, success: bool, latency: float = 0.0):
        """Update tool performance metrics."""
        if tool_name not in self.nodes:
            return
        
        node = self.nodes[tool_name]
        
        if success:
            node.record_success(latency)
            log_result(f"Tool {tool_name} succeeded", success=True, context={
                "latency": latency,
                "new_failure_rate": node.failure_rate
            })
        else:
            node.record_failure()
            log_error(f"Tool {tool_name} failed", context={
                "failure_count": node.failure_count,
                "new_failure_rate": node.failure_rate
            })
            
            # Disable edges from this tool if failure rate is high
            if node.failure_rate > 0.5:
                for edge in self.edges.get(tool_name, []):
                    self.disable_edge(tool_name, edge.to_tool)
                log_pattern(f"Disabled edges from {tool_name} due to high failure rate", "WARNING")
    
    def recover_tool(self, tool_name: str):
        """Recover a tool after it becomes healthy again."""
        if tool_name not in self.nodes:
            return
        
        node = self.nodes[tool_name]
        node.reset_failure_streak()
        
        # Re-enable edges
        for edge in self.edges.get(tool_name, []):
            self.enable_edge(tool_name, edge.to_tool)
        
        log_result(f"Tool {tool_name} recovered", success=True)
    
    def get_tool_status(self, tool_name: str) -> Dict:
        """Get current status of a tool."""
        if tool_name not in self.nodes:
            return {"error": "Tool not found"}
        
        node = self.nodes[tool_name]
        return {
            "name": tool_name,
            "latency": node.latency,
            "failure_rate": node.failure_rate,
            "success_count": node.success_count,
            "failure_count": node.failure_count,
            "edge_weight": node.edge_weight,
            "last_used": node.last_used,
            "healthy": node.failure_rate < 0.3
        }
    
    def get_graph_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(edges) for edges in self.edges.values()),
            "healthy_tools": sum(1 for node in self.nodes.values() if node.failure_rate < 0.3),
            "degraded_tools": sum(1 for node in self.nodes.values() if 0.3 <= node.failure_rate < 0.7),
            "broken_tools": sum(1 for node in self.nodes.values() if node.failure_rate >= 0.7)
        }


# Singleton global
_tool_graph: Optional[ToolGraph] = None


def get_tool_graph() -> ToolGraph:
    """Returneaza instanta globala ToolGraph."""
    global _tool_graph
    if _tool_graph is None:
        _tool_graph = ToolGraph()
    return _tool_graph


def initialize_default_graph():
    """Initialize graph with default ANA tools."""
    global _tool_graph
    graph = get_tool_graph()
    _tool_graph = graph  # Ensure singleton is set
    
    # Add common tools with estimated latencies
    default_tools = {
        "file_operations": 0.1,  # Fast
        "code": 0.2,  # Medium
        "web": 0.5,  # Slower (network)
        "terminal": 0.15,  # Fast
        "system": 0.1,  # Fast
        "memory": 0.05,  # Very fast
        "desktop_control": 0.3,  # Medium
        "clipboard_manager": 0.02,  # Very fast
        "workspace_situational_awareness": 0.15,  # Medium
        "tool_healthcheck": 0.1,  # Fast
    }
    
    for tool_name, latency in default_tools.items():
        graph.add_node(tool_name, latency=latency)
    
    # Add edges representing common workflows
    # START -> file_operations -> code -> web -> END
    graph.add_edge("START", "file_operations", weight=0.1)
    graph.add_edge("file_operations", "code", weight=0.2)
    graph.add_edge("code", "web", weight=0.5)
    graph.add_edge("web", "END", weight=0.1)
    
    # Alternative paths
    graph.add_edge("START", "terminal", weight=0.15)
    graph.add_edge("terminal", "code", weight=0.2)
    graph.add_edge("code", "END", weight=0.1)
    
    graph.add_edge("START", "workspace_situational_awareness", weight=0.15)
    graph.add_edge("workspace_situational_awareness", "file_operations", weight=0.2)
    
    log_result("Default tool graph initialized", success=True, context={
        "tools": list(default_tools.keys()),
        "edges": "Common workflows configured"
    })
    
    return graph


def route_tool(task_type: str, available_tools: List[str]) -> str:
    """Route a task to the best tool using graph-based routing."""
    graph = get_tool_graph()
    
    # Ensure graph is initialized
    if len(graph.nodes) <= 2:  # Only START and END
        initialize_default_graph()
    
    # Find best tool based on graph routing
    # For now, use simple heuristic: choose tool with lowest edge weight from START
    best_tool = None
    best_weight = float('inf')
    
    for tool_name in available_tools:
        if tool_name in graph.nodes:
            # Find edge from START to this tool
            for edge in graph.edges.get("START", []):
                if edge.to_tool == tool_name and edge.active:
                    if edge.weight < best_weight:
                        best_weight = edge.weight
                        best_tool = tool_name
    
    if best_tool:
        log_action(f"Routed task {task_type} to {best_tool}", {
            "weight": best_weight,
            "alternatives": [t for t in available_tools if t != best_tool]
        })
        return best_tool
    else:
        # Fallback: return first available tool
        if available_tools:
            log_pattern(f"No graph path found, using fallback: {available_tools[0]}", "WARNING")
            return available_tools[0]
    
    log_error(f"No tool available for task: {task_type}")
    return None


def update_tool_metrics(tool_name: str, success: bool, latency: float = 0.0):
    """Update tool metrics in the graph."""
    graph = get_tool_graph()
    graph.update_tool_performance(tool_name, success, latency)
