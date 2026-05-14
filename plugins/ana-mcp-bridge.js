import { tool } from "@opencode-ai/plugin";

export const ANAMCPBridge = async ({ client }) => {
  const ANA_MCP_URL = "http://127.0.0.1:8765/mcp";

  async function callANA(toolName, args = {}) {
    const body = JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: {
        name: toolName,
        arguments: args
      }
    });

    const resp = await fetch(ANA_MCP_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body
    });
    return await resp.json();
  }

  // Tool definitions for ANA tools that opencode lacks
  const tools = {
    ana_browser_control: tool({
      description: "ANA MCP: Browser control - open, inspect, click, type, screenshot.",
      args: {
        operation: tool.schema.string(),
        url: tool.schema.optional(tool.schema.string()),
        selector: tool.schema.optional(tool.schema.string()),
        text: tool.schema.optional(tool.schema.string())
      },
      async execute(args) {
        const result = await callANA("browser_control", {
          operation: args.operation,
          ...(args.url && { url: args.url }),
          ...(args.selector && { selector: args.selector }),
          ...(args.text && { text: args.text })
        });
        return result?.result?.content?.[0]?.text || JSON.stringify(result);
      }
    }),

    ana_security_audit: tool({
      description: "ANA MCP: Security audit - scan secrets, static analysis, hash gen.",
      args: {
        operation: tool.schema.string(),
        target: tool.schema.string()
      },
      async execute(args) {
        const result = await callANA("security_audit", {
          operation: args.operation,
          target: args.target
        });
        return result?.result?.content?.[0]?.text || JSON.stringify(result);
      }
    }),

    ana_network_diag: tool({
      description: "ANA MCP: Network diagnostics - ping, port scan, DNS, IP info.",
      args: {
        operation: tool.schema.string(),
        target: tool.schema.string()
      },
      async execute(args) {
        const result = await callANA("network_diag", {
          operation: args.operation,
          target: args.target
        });
        return result?.result?.content?.[0]?.text || JSON.stringify(result);
      }
    }),

    ana_memory: tool({
      description: "ANA MCP: Persistent memory - save knowledge, search, errors.",
      args: {
        action: tool.schema.string(),
        query: tool.schema.optional(tool.schema.string()),
        content: tool.schema.optional(tool.schema.string())
      },
      async execute(args) {
        const result = await callANA("ana_memory", {
          action: args.action,
          ...(args.query && { query: args.query }),
          ...(args.content && { content: args.content })
        });
        return result?.result?.content?.[0]?.text || JSON.stringify(result);
      }
    }),

    ana_qa_testing: tool({
      description: "ANA MCP: QA testing - generate tests, edge cases, mock data.",
      args: {
        operation: tool.schema.string(),
        target: tool.schema.string()
      },
      async execute(args) {
        const result = await callANA("qa_testing", {
          operation: args.operation,
          target: args.target
        });
        return result?.result?.content?.[0]?.text || JSON.stringify(result);
      }
    })
  };

  await client.app.log({
    body: {
      service: "ana-mcp-bridge",
      level: "info",
      message: "ANA MCP Bridge initialized with 5 tools"
    }
  });

  return { tool: tools };
};
