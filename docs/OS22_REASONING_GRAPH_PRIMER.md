# ANA_MAX OS-22 Reasoning Graph Primer

The OS-22 agent should think in simple graph nodes.

## Nodes

### ContextNode

- Reads RAG context.
- Reads local metadata.

### PlanningNode

- Determines what is being asked.
- Chooses direct answer or tool path.

### ToolDecisionNode

- Checks if a manifest tool is needed.
- Selects one tool only.

### ExecutionNode

- Executes the selected tool through ToolBridge.
- Or performs direct reasoning if no tool is needed.

### SummaryNode

- Produces the final concise answer.

## Graph Rule

```text
ContextNode -> PlanningNode -> ToolDecisionNode -> ExecutionNode -> SummaryNode
```

