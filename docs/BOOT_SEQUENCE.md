# Boot Sequence

When OS-22 starts, it loads components in this order:

1. Configuration loader
2. RAGBridge initialization
3. ToolBridge initialization
4. MCP server startup
5. Self-Healing v2 activation
6. Autonomy v3 activation
7. Interactive chat ready

## Launch Script

```bash
scripts\os22\start_os22_lab_chat.bat
```
