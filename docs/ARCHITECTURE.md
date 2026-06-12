# Architecture

## Local Runtime

- Workspace root: `C:\Users\billy\Desktop\ana_dev`
- ANA MAX tools root: `ANA_MAX/`
- Cascade integration: `cascade_integration/`
- Direct bridge: in-process ANA tool execution through local registry

## Execution Policy

- Default path: direct local tool execution
- MCP path: disabled by default for lab-only operation
- Risky local actions: require `--confirm` or `--dry-run`

