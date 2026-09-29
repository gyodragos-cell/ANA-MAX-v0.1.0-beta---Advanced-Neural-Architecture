"""
ANA MAX - temporal_branching_tool.py
======================================
Temporal Branching (Snapshot & Rollback)

Agentul poate "ingheta timpul" creand un snapshot local al workspace-ului si 
db-urilor. Daca actiunea urmatoare distruge sistemul, apeleaza rollback pentru a
se intoarce in timp exact la starea din acel punct (milisecunde, bazat pe shadow copy 
sau copiere rapida). Pentru limitari de laborator, implementam backup rapid de fisiere/DB.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.TemporalBranching")

ANA_ROOT = Path(__file__).parent.parent
SNAPSHOT_DIR = ANA_ROOT / ".ana_backups" / "temporal_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Ce protejam (focus limitat in lab pentru viteza)
TARGETS = ["ana_memory.db", "causal_memory.db"]


class TemporalBranchingTool(Tool):
    """Ramificare temporala: ingheata si deruleaza timpul la eroare."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="temporal_branch",
            description="Creaza un snapshot instantaneu (freeze_time) sau da timpul inapoi (rollback) in caz de eroare fatala.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="'freeze_time' (creeaza punct) sau 'rollback' (inapoi in timp)",
                    type="string",
                    required=True,
                    choices=["freeze_time", "rollback"],
                ),
                ToolParameter(
                    name="branch_id",
                    description="ID-ul branch-ului temporal. Daca e omis la freeze, se genereaza unul.",
                    type="string",
                    required=False,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        branch_id = kwargs.get("branch_id")

        if action == "freeze_time":
            branch_id = branch_id or f"branch_{int(time.time())}"
            branch_dir = SNAPSHOT_DIR / branch_id
            branch_dir.mkdir(exist_ok=True)
            
            saved = 0
            for t in TARGETS:
                src = ANA_ROOT / t
                if src.exists():
                    shutil.copy2(src, branch_dir / t)
                    saved += 1
                    
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"branch_id": branch_id, "files_frozen": saved},
                message=f"Timpul a fost inghetat. Branch creat: {branch_id}"
            )
            
        elif action == "rollback":
            if not branch_id:
                # Cauta cel mai recent branch
                branches = sorted([d for d in SNAPSHOT_DIR.iterdir() if d.is_dir()], key=os.path.getmtime, reverse=True)
                if not branches:
                    return ToolResult(status=ToolStatus.ERROR, error="Nu exista niciun branch in timp pentru rollback.")
                branch_dir = branches[0]
            else:
                branch_dir = SNAPSHOT_DIR / branch_id
                if not branch_dir.exists():
                    return ToolResult(status=ToolStatus.ERROR, error=f"Branch invalid: {branch_id}")
            
            restored = 0
            for t in TARGETS:
                src = branch_dir / t
                dest = ANA_ROOT / t
                if src.exists():
                    shutil.copy2(src, dest)
                    restored += 1
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"restored_to": branch_dir.name, "files_restored": restored},
                message=f"Rollback cu succes. Timpul a fost derulat inapoi la {branch_dir.name}."
            )
            
        return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
