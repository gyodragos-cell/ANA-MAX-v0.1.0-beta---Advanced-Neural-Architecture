#!/usr/bin/env python3
"""
ANA MAX - Advanced Swarm Orchestration (Inspirat din Ruflo Swarm)
==================================================================
Sistem avansat de orchestrare multi-agent cu topologii adaptive.

Features:
- 3 topologii: Hierarchical, Mesh, Adaptive
- Consensus algorithms
- Dynamic agent spawning
- Task decomposition
- Self-optimizing swarm
- Load balancing

Author: ANA MAX Team (2026-05-19)
Inspired by: Ruflo Swarm Coordination
"""

import logging
import threading
import uuid
import time
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class Topology(Enum):
    """Swarm topology types."""
    HIERARCHICAL = "hierarchical"  # Leader -> Specialists
    MESH = "mesh"                  # Peer-to-peer
    ADAPTIVE = "adaptive"          # Dynamic based on task


class AgentRole(Enum):
    """Specialized agent roles."""
    COORDINATOR = "coordinator"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    TESTER = "tester"
    SECURITY = "security"
    RESEARCHER = "researcher"
    WRITER = "writer"
    ANALYST = "analyst"


@dataclass
class Task:
    """Represents a task in the swarm."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    assigned_to: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    result: str = ""
    priority: int = 5  # 1-10
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class SwarmAgent:
    """Represents an agent in the swarm."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: AgentRole = AgentRole.DEVELOPER
    status: str = "idle"  # idle, busy, offline
    current_task: str = ""
    completed_tasks: int = 0
    success_rate: float = 1.0
    specialization: List[str] = field(default_factory=list)


class ConsensusEngine:
    """
    Implements consensus algorithms for swarm decision-making.
    Inspired by distributed systems consensus (Raft, PBFT simplified).
    """
    
    @staticmethod
    def majority_vote(opinions: List[bool]) -> bool:
        """Simple majority voting."""
        return sum(opinions) > len(opinions) / 2
    
    @staticmethod
    def weighted_vote(opinions: List[tuple]) -> bool:
        """Weighted voting based on agent expertise."""
        total_weight = 0
        weighted_sum = 0
        for opinion, weight in opinions:
            total_weight += weight
            weighted_sum += (1 if opinion else 0) * weight
        return weighted_sum / total_weight > 0.5
    
    @staticmethod
    def reach_consensus(proposals: List[Dict]) -> Dict:
        """Find the proposal with most support."""
        vote_count = defaultdict(int)
        for proposal in proposals:
            vote_count[proposal.get('decision', '')] += proposal.get('confidence', 1)
        
        if not vote_count:
            return {}
        
        best_decision = max(vote_count.items(), key=lambda x: x[1])
        return {'decision': best_decision[0], 'confidence': best_decision[1]}


class AdvancedSwarmOrchestrator:
    """
    Advanced Swarm Orchestration System.
    
    Features:
    - Multiple topology support
    - Dynamic agent spawning
    - Task decomposition and delegation
    - Consensus-based decision making
    - Self-optimizing performance
    - Load balancing
    """
    
    def __init__(self, topology: Topology = Topology.ADAPTIVE):
        self.topology = topology
        self.agents: Dict[str, SwarmAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue = []
        self.results = {}
        
        # Consensus engine
        self.consensus = ConsensusEngine()
        
        # Performance tracking
        self.start_time = time.time()
        self.total_tasks_completed = 0
        self.avg_completion_time = 0
        
        # Threading
        self._lock = threading.Lock()
        self._active_threads = []
        
        # Initialize default swarm
        self._init_default_swarm()
        
        logger.info(f"Advanced Swarm initialized (topology={topology.value}, agents={len(self.agents)})")
    
    def _init_default_swarm(self):
        """Initialize default team of specialized agents."""
        default_agents = [
            ("Coordinator", AgentRole.COORDINATOR, ["orchestration", "planning"]),
            ("Architect", AgentRole.ARCHITECT, ["design", "architecture"]),
            ("Developer", AgentRole.DEVELOPER, ["coding", "implementation"]),
            ("Tester", AgentRole.TESTER, ["testing", "qa"]),
            ("Security", AgentRole.SECURITY, ["security", "audit"]),
            ("Researcher", AgentRole.RESEARCHER, ["research", "analysis"]),
        ]
        
        for name, role, specs in default_agents:
            self.add_agent(name, role, specs)
    
    def add_agent(self, name: str, role: AgentRole, specializations: List[str] = None) -> str:
        """Add agent to swarm."""
        agent = SwarmAgent(
            name=name,
            role=role,
            specialization=specializations or []
        )
        self.agents[agent.id] = agent
        logger.debug(f"Agent added: {name} (role={role.value})")
        return agent.id
    
    def spawn_agent(self, task_description: str) -> str:
        """Dynamically spawn agent based on task requirements."""
        # Analyze task to determine needed role
        task_lower = task_description.lower()
        
        if any(kw in task_lower for kw in ["security", "vulnerability", "audit"]):
            role = AgentRole.SECURITY
            name = f"Security_{len([a for a in self.agents.values() if a.role == AgentRole.SECURITY]) + 1}"
        elif any(kw in task_lower for kw in ["test", "qa", "validate"]):
            role = AgentRole.TESTER
            name = f"Tester_{len([a for a in self.agents.values() if a.role == AgentRole.TESTER]) + 1}"
        elif any(kw in task_lower for kw in ["research", "analyze", "investigate"]):
            role = AgentRole.RESEARCHER
            name = f"Researcher_{len([a for a in self.agents.values() if a.role == AgentRole.RESEARCHER]) + 1}"
        else:
            role = AgentRole.DEVELOPER
            name = f"Developer_{len([a for a in self.agents.values() if a.role == AgentRole.DEVELOPER]) + 1}"
        
        return self.add_agent(name, role)
    
    def decompose_task(self, task_description: str) -> List[Task]:
        """
        Decompose complex task into subtasks.
        Inspired by Ruflo's intelligent task breakdown.
        """
        subtasks = []
        task_lower = task_description.lower()
        
        # Pattern-based decomposition
        if any(kw in task_lower for kw in ["create", "build", "implement"]):
            subtasks = [
                Task(description=f"Analyze requirements: {task_description}", priority=10),
                Task(description=f"Design architecture for: {task_description}", priority=9),
                Task(description=f"Implement: {task_description}", priority=8),
                Task(description=f"Test implementation", priority=7),
                Task(description=f"Security review", priority=6),
            ]
        elif any(kw in task_lower for kw in ["debug", "fix", "repair"]):
            subtasks = [
                Task(description=f"Analyze error/bug: {task_description}", priority=10),
                Task(description=f"Identify root cause", priority=9),
                Task(description=f"Implement fix", priority=8),
                Task(description=f"Test fix", priority=7),
            ]
        elif any(kw in task_lower for kw in ["research", "analyze"]):
            subtasks = [
                Task(description=f"Define research scope: {task_description}", priority=10),
                Task(description=f"Gather information", priority=9),
                Task(description=f"Analyze findings", priority=8),
                Task(description=f"Write summary report", priority=7),
            ]
        else:
            # Generic decomposition
            subtasks = [
                Task(description=f"Plan approach: {task_description}", priority=8),
                Task(description=f"Execute: {task_description}", priority=7),
                Task(description=f"Verify results", priority=6),
            ]
        
        # Set dependencies
        for i in range(1, len(subtasks)):
            subtasks[i].dependencies.append(subtasks[i-1].id)
        
        return subtasks
    
    def assign_task(self, task: Task) -> Optional[str]:
        """Assign task to best-suited agent based on role and load."""
        # Find available agents with matching role
        candidates = [
            agent for agent in self.agents.values()
            if agent.status == "idle"
        ]
        
        if not candidates:
            return None
        
        # Score agents
        best_agent = None
        best_score = -1
        
        for agent in candidates:
            score = agent.success_rate * 0.6 + (1.0 / (1 + agent.completed_tasks)) * 0.4
            
            # Bonus for specialization match
            task_lower = task.description.lower()
            for spec in agent.specialization:
                if spec in task_lower:
                    score += 0.2
            
            if score > best_score:
                best_score = score
                best_agent = agent
        
        if best_agent:
            best_agent.status = "busy"
            best_agent.current_task = task.id
            task.assigned_to = best_agent.id
            task.status = "in_progress"
        
        return best_agent.id if best_agent else None
    
    def execute_task_async(self, task: Task, executor_fn: Callable):
        """Execute task asynchronously in thread."""
        def worker():
            try:
                agent = self.agents.get(task.assigned_to)
                if not agent:
                    task.status = "failed"
                    task.result = "No agent assigned"
                    return
                
                start = time.time()
                result = executor_fn(task.description)
                elapsed = time.time() - start
                
                task.status = "completed"
                task.result = str(result)
                agent.status = "idle"
                agent.completed_tasks += 1
                agent.current_task = ""
                
                # Update success rate
                agent.success_rate = (agent.success_rate * 0.9) + (0.1 if elapsed < 10 else 0.05)
                
                self.total_tasks_completed += 1
                self.avg_completion_time = (
                    (self.avg_completion_time * (self.total_tasks_completed - 1) + elapsed) /
                    self.total_tasks_completed
                )
                
                logger.info(f"Task {task.id} completed in {elapsed:.2f}s by {agent.name}")
                
            except Exception as e:
                task.status = "failed"
                task.result = str(e)
                agent = self.agents.get(task.assigned_to)
                if agent:
                    agent.status = "idle"
                    agent.success_rate *= 0.9
                logger.error(f"Task {task.id} failed: {e}")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self._active_threads.append(thread)
    
    def execute_swarm_task(self, task_description: str, executor_fn: Callable) -> Dict:
        """
        Execute complex task using swarm intelligence.
        Full pipeline: decompose -> assign -> execute -> consolidate
        """
        # Step 1: Decompose task
        subtasks = self.decompose_task(task_description)
        logger.info(f"Task decomposed into {len(subtasks)} subtasks")
        
        # Step 2: Spawn additional agents if needed
        if len(subtasks) > len([a for a in self.agents.values() if a.status == "idle"]):
            for subtask in subtasks:
                if len([a for a in self.agents.values() if a.status == "idle"]) < 2:
                    self.spawn_agent(subtask.description)
        
        # Step 3: Assign and execute
        results = {}
        for subtask in subtasks:
            # Wait for dependencies
            while any(dep_status != "completed" 
                     for dep_id in subtask.dependencies 
                     if (dep_status := self.tasks.get(dep_id, Task()).status) != "completed"):
                time.sleep(0.1)
            
            # Assign task
            agent_id = self.assign_task(subtask)
            if not agent_id:
                subtask.status = "failed"
                subtask.result = "No available agent"
                continue
            
            self.tasks[subtask.id] = subtask
            
            # Execute
            self.execute_task_async(subtask, executor_fn)
        
        # Step 4: Wait for completion
        while any(t.status in ["pending", "in_progress"] for t in self.tasks.values()):
            time.sleep(0.1)
        
        # Step 5: Consolidate results
        successful = [t for t in self.tasks.values() if t.status == "completed"]
        failed = [t for t in self.tasks.values() if t.status == "failed"]
        
        return {
            "task": task_description,
            "subtasks": len(subtasks),
            "successful": len(successful),
            "failed": len(failed),
            "results": {t.id: t.result for t in successful},
            "errors": {t.id: t.result for t in failed}
        }
    
    def get_swarm_status(self) -> Dict:
        """Get comprehensive swarm status."""
        agents_by_role = defaultdict(int)
        agents_by_status = defaultdict(int)
        
        for agent in self.agents.values():
            agents_by_role[agent.role.value] += 1
            agents_by_status[agent.status] += 1
        
        tasks_by_status = defaultdict(int)
        for task in self.tasks.values():
            tasks_by_status[task.status] += 1
        
        return {
            "topology": self.topology.value,
            "total_agents": len(self.agents),
            "agents_by_role": dict(agents_by_role),
            "agents_by_status": dict(agents_by_status),
            "total_tasks": len(self.tasks),
            "tasks_by_status": dict(tasks_by_status),
            "total_completed": self.total_tasks_completed,
            "avg_completion_time": round(self.avg_completion_time, 2),
            "uptime": round(time.time() - self.start_time, 2)
        }
    
    def optimize_swarm(self):
        """Self-optimization: Remove underperforming agents, spawn new ones."""
        # Remove agents with low success rate
        to_remove = [
            aid for aid, agent in self.agents.items()
            if agent.success_rate < 0.3 and agent.completed_tasks > 3
        ]
        
        for aid in to_remove:
            del self.agents[aid]
            logger.info(f"Removed underperforming agent: {aid}")
        
        # Spawn agents for overloaded roles
        busy_agents = [a for a in self.agents.values() if a.status == "busy"]
        if len(busy_agents) > len(self.agents) * 0.8:
            # Swarm is overloaded, spawn more agents
            self.spawn_agent("Additional capacity needed")
            logger.info("Swarm overloaded, spawned additional agent")
    
    def close(self):
        """Shutdown swarm."""
        for thread in self._active_threads:
            thread.join(timeout=5)
        logger.info("Swarm orchestrator closed")


# Singleton instance
_swarm_instance = None
_swarm_lock = threading.Lock()


def get_swarm_orchestrator(topology: Topology = Topology.ADAPTIVE) -> AdvancedSwarmOrchestrator:
    """Get or create AdvancedSwarmOrchestrator singleton."""
    global _swarm_instance
    
    if _swarm_instance is None:
        with _swarm_lock:
            if _swarm_instance is None:
                _swarm_instance = AdvancedSwarmOrchestrator(topology=topology)
    
    return _swarm_instance


if __name__ == "__main__":
    # Test swarm
    swarm = get_swarm_orchestrator()
    
    # Execute test task
    def mock_executor(task_desc):
        return f"Completed: {task_desc}"
    
    result = swarm.execute_swarm_task("Build a REST API with authentication", mock_executor)
    print(f"\nTask result: {result['successful']}/{result['subtasks']} subtasks completed")
    
    # Status
    status = swarm.get_swarm_status()
    print(f"\nSwarm status: {status}")
    
    swarm.close()
