"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const vscode = require("vscode");

function getConfig() {
  const config = vscode.workspace.getConfiguration("anaMax");
  return {
    safeMode: config.get("safeMode", true),
    runtimeUrl: config.get("runtimeUrl", "http://127.0.0.1:8766/mcp"),
    runtimeRoot: config.get("runtimeRoot", ""),
    pythonPath: config.get("pythonPath", ""),
    runtimePort: config.get("runtimePort", 8766),
    dashboardUrl: config.get("dashboardUrl", "http://127.0.0.1:8787"),
    codexServerName: config.get("codexServerName", "anamax"),
    antigravityServerName: config.get("antigravityServerName", "anamax")
  };
}

function runtimeBaseUrl(config) {
  return config.runtimeUrl.replace(/\/mcp\/?$/, "");
}

async function getHealth(config) {
  const res = await fetch(`${runtimeBaseUrl(config)}/health`);
  return res.json();
}

function resolveRuntimePaths(config) {
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || "";
  const baseRoot = path.resolve(config.runtimeRoot || workspaceRoot || "");
  const searchedRoots = [
    baseRoot,
    path.join(baseRoot, "ANA_MAX"),
    workspaceRoot ? path.resolve(workspaceRoot) : "",
    workspaceRoot ? path.join(path.resolve(workspaceRoot), "ANA_MAX") : ""
  ].filter((item, index, list) => item && list.indexOf(item) === index);
  const runtimeRoot = searchedRoots.find(candidate => fs.existsSync(path.join(candidate, "main.py"))) || baseRoot;
  const defaultPythonPath = path.join(runtimeRoot, "venv", "Scripts", "python.exe");
  const pythonPath = config.pythonPath
    ? path.resolve(config.pythonPath)
    : (fs.existsSync(defaultPythonPath) ? defaultPythonPath : "python");
  return {
    runtimeRoot,
    pythonPath,
    mainPy: path.join(runtimeRoot, "main.py"),
    searchedRoots
  };
}

async function startRuntime() {
  const config = getConfig();

  try {
    const readiness = await getSmartReadiness(config);
    if (readiness.ok) {
      vscode.window.showInformationMessage(
        `ANA MAX smart ready at ${runtimeBaseUrl(config)} with ${readiness.tool_count || "?"} tools.`
      );
      return;
    }
  } catch {
    // Offline is expected here; continue with launch.
  }

  const paths = resolveRuntimePaths(config);
  if (!fs.existsSync(paths.runtimeRoot)) {
    vscode.window.showErrorMessage(`ANA MAX runtimeRoot not found: ${paths.runtimeRoot}`);
    return;
  }
  if (!fs.existsSync(paths.mainPy)) {
    vscode.window.showErrorMessage(
      `ANA MAX main.py not found: ${paths.mainPy}. ` +
      `Checked: ${paths.searchedRoots.join(", ")}. ` +
      `Set anaMax.runtimeRoot to the ANA_MAX folder (e.g. C:\\path\\to\\ANA_MAX) in VS Code settings.`
    );
    return;
  }
  if (path.isAbsolute(paths.pythonPath) && !fs.existsSync(paths.pythonPath)) {
    vscode.window.showErrorMessage(`Python executable not found: ${paths.pythonPath}`);
    return;
  }

  const terminal = vscode.window.createTerminal({
    name: "ANA MAX MCP",
    cwd: paths.runtimeRoot
  });
  terminal.show(true);
  terminal.sendText(`& "${paths.pythonPath}" "${paths.mainPy}" --host 127.0.0.1 --port ${config.runtimePort}`);
  vscode.window.showInformationMessage(`Starting ANA MAX MCP on ${runtimeBaseUrl(config)}.`);
}

function safeModeMessage(action) {
  const config = getConfig();
  return `ANA & Antigravity ${action}: safe-mode ${config.safeMode ? "active" : "disabled"}.`;
}

function getDangerousActionPrompts(toolName, args) {
  const text = `${toolName || ""} ${JSON.stringify(args || {})}`.toLowerCase();
  const normalizedTool = String(toolName || "").toLowerCase();
  const readOnlyTools = new Set([
    "ana_identity",
    "agent_coach",
    "ana_health_check",
    "ana_runtime_inspector",
    "baseline_update_suggester",
    "codebase_understanding",
    "docs_generator",
    "error_radar",
    "foreground_ui_snapshot",
    "project_navigator",
    "runtime_guard",
    "schema_diff",
    "session_lifecycle",
    "session_rem_sleep",
    "tool_contract_validator",
    "tool_healthcheck",
    "tool_router",
    "workspace_situational_awareness"
  ]);
  const prompts = [];

  if (/(write|patch|edit|delete|remove|move|rename|save|commit|push|install|uninstall)/.test(text)) {
    prompts.push("Allow write?");
  }
  if (/(terminal|shell|powershell|cmd|subprocess|process|launch|start_runtime|exec)/.test(text)) {
    prompts.push("Allow subprocess?");
  }
  if (/(http|https|fetch|download|upload|network|browser|web|api|curl)/.test(text)) {
    prompts.push("Allow network call?");
  }

  return [...new Set(prompts)];
}

async function confirmDangerousAction(toolName, args) {
  const config = getConfig();
  if (!config.safeMode) {
    return true;
  }

  const prompts = getDangerousActionPrompts(toolName, args);
  for (const prompt of prompts) {
    const answer = await vscode.window.showWarningMessage(
      `${prompt} safe-mode blocks tool execution unless you approve this action.`,
      { modal: true },
      "Allow once"
    );
    if (answer !== "Allow once") {
      return false;
    }
  }
  return true;
}

function getHybridConfigText(config) {
  return [
    "ANA MAX Hybrid MCP",
    "",
    `Runtime URL: ${config.runtimeUrl}`,
    `Codex server name: ${config.codexServerName}`,
    `Antigravity/Qoder/Windsurf server name: ${config.antigravityServerName}`,
    "",
    "Antigravity / Qoder / Windsurf MCP JSON:",
    JSON.stringify({
      mcpServers: {
        [config.antigravityServerName]: {
          type: "http",
          url: config.runtimeUrl
        }
      }
    }, null, 2),
    "",
    "Codex config TOML:",
    `[mcp_servers.${config.codexServerName}]`,
    `url = "${config.runtimeUrl}"`
  ].join("\n");
}

function requestJson(url, payload) {
  return new Promise((resolve, reject) => {
    try {
      const parsed = new URL(url);
      const body = JSON.stringify(payload || {});
      const req = http.request({
        hostname: parsed.hostname,
        port: parsed.port,
        path: parsed.pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body)
        },
        timeout: 10000
      }, (res) => {
        let data = "";
        res.on("data", (chunk) => { data += chunk; });
        res.on("end", () => {
          try {
            resolve(data ? JSON.parse(data) : {});
          } catch (error) {
            reject(new Error(`Failed to parse response: ${error.message}`));
          }
        });
      });
      req.on("timeout", () => {
        req.destroy(new Error("ANA & Antigravity runtime request timed out"));
      });
      req.on("error", reject);
      req.write(body);
      req.end();
    } catch (e) {
      reject(e);
    }
  });
}

async function callTool(config, name, args) {
  if (!(await confirmDangerousAction(name, args))) {
    return { success: false, error: "safe-mode blocks tool execution" };
  }
  const res = await requestJson(config.runtimeUrl, {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "tools/call",
    params: { name, arguments: args || {} }
  });
  const text = res.result?.content?.[0]?.text;
  if (!text) {
    return { success: false, error: "Missing MCP tool content", raw: res };
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    return { success: false, error: `Non-JSON MCP tool content: ${error.message}`, raw: text };
  }
}

async function getSmartReadiness(config) {
  const health = await getHealth(config);
  const toolsRes = await requestJson(config.runtimeUrl, {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "tools/list",
    params: {}
  });
  const tools = toolsRes.result?.tools || [];
  const names = tools.map(t => t.name);
  const agentCoach = tools.find(t => t.name === "agent_coach") || {};
  const actions = agentCoach.inputSchema?.properties?.action?.enum || [];
  const router = await callTool(config, "tool_router", {
    task: "MCP tool failed with schema mismatch action versus operation",
    error: "Invalid value for operation",
    max_tools: 4
  });
  const recommend = await callTool(config, "agent_coach", {
    action: "recommend",
    task: "MCP tool failed with schema mismatch action versus operation",
    error: "Invalid value for operation",
    max_tools: 5,
    include_prompt: false
  });
  const checks = [
    { name: "health_online", ok: health.status === "online" && !!health.mcp_ready },
    { name: "tool_router_present", ok: names.includes("tool_router") },
    { name: "agent_coach_present", ok: names.includes("agent_coach") },
    { name: "agent_coach_recommend_schema", ok: actions.includes("recommend") },
    { name: "tool_router_call", ok: !!router.success && !!router.data?.recommended_tools?.length },
    {
      name: "agent_coach_recommend_call",
      ok: !!recommend.success
        && recommend.data?.schema === "ana.agent_coach.recommend.v1"
        && !!recommend.data?.primary_tool
    }
  ];
  return {
    ok: checks.every(c => c.ok),
    health,
    tool_count: tools.length,
    actions,
    checks,
    router: router.data || router,
    recommend: recommend.data || recommend
  };
}

function formatSmartReadiness(report) {
  const status = report.ok ? "SMART READY" : "NOT READY";
  const primary = report.recommend?.primary_tool || "none";
  const stack = (report.recommend?.tool_stack || []).join(", ") || "none";
  const checks = report.checks.map(c => `${c.ok ? "[OK]" : "[FAIL]"} ${c.name}`).join("\n");
  return [
    status,
    `health=${report.health?.status} mcp_ready=${report.health?.mcp_ready} tools=${report.tool_count}`,
    `primary_tool=${primary}`,
    `tool_stack=${stack}`,
    "",
    checks
  ].join("\n");
}

class AnaActionProvider {
  getTreeItem(element) {
    return element;
  }

  getChildren() {
    return [
      actionItem("1. Start Runtime", "anaMax.startRuntime", "play", "Start the local ANA MAX server."),
      actionItem("2. Smart Ready", "anaMax.showHealth", "pulse", "Check that ANA MAX is online and ready."),
      actionItem("3. Wake Session", "anaMax.wakeSession", "debug-restart", "Load the last session memory or create first-run context."),
      actionItem("Open Cockpit", "ana.openChat", "layout", "Open the ANA MAX guided panel."),
      actionItem("Ask Next Tool", "anaMax.showRouterDecisions", "list-tree", "Ask ANA MAX which tool should be used next."),
      actionItem("Preview REM Sleep", "anaMax.previewRest", "preview", "Review session lessons without saving."),
      actionItem("Save REM Sleep", "anaMax.runRemSleep", "repo-push", "Save the session handoff after review."),
      actionItem("Copy MCP Config", "ana.showHybridConfig", "json", "Show Codex and Antigravity/Qoder/Windsurf MCP config.")
    ];
  }
}

function actionItem(label, command, icon, tooltip) {
  const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
  item.command = { command, title: label };
  item.iconPath = new vscode.ThemeIcon(icon);
  item.tooltip = tooltip;
  return item;
}

function activate(context) {
  let panel = undefined;

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("anaMax.actions", new AnaActionProvider())
  );

  const openCockpit = vscode.commands.registerCommand("ana.openChat", () => {
    if (panel) {
      panel.reveal(vscode.ViewColumn.Beside);
      return;
    }

    panel = vscode.window.createWebviewPanel(
      "anaAntigravityCockpit",
      "ANA & Antigravity Cockpit",
      vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true }
    );

    panel.webview.html = getWebviewContent();

    panel.onDidDispose(() => {
      panel = undefined;
    });

    panel.webview.onDidReceiveMessage(async (message) => {
      const config = getConfig();
      const baseUrl = runtimeBaseUrl(config);

      if (message.command === "health") {
        try {
          const res = await fetch(`${baseUrl}/health`);
          const data = await res.json();
          post(panel, "health", data);
        } catch (e) {
          post(panel, "error", `Backend offline @ ${baseUrl}. Start ANA MAX via main.py.`);
        }
        return;
      }

      if (message.command === "startRuntime") {
        await vscode.commands.executeCommand("anaMax.startRuntime");
        return;
      }

      if (message.command === "smartReady") {
        try {
          const report = await getSmartReadiness(config);
          post(panel, "smartReady", report);
        } catch (e) {
          post(panel, "error", `Smart readiness failed @ ${baseUrl}: ${e.message}`);
        }
        return;
      }

      if (message.command === "recommend") {
        try {
          const payload = await callTool(config, "agent_coach", {
            action: "recommend",
            task: message.task || "Cockpit operator asks for the next best ANA MAX tool",
            max_tools: 5,
            include_prompt: false
          });
          post(panel, "recommend", payload.data || payload);
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "wakeSession") {
        try {
          const payload = await callTool(config, "session_lifecycle", {
            action: "wake"
          });
          post(panel, "lifecycle", payload.data || payload);
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "checkpoint") {
        try {
          const payload = await callTool(config, "session_checkpoint", {
            title: "Cockpit quick checkpoint",
            summary: message.summary || "Operator saved a quick checkpoint from the cockpit.",
            current_goal: "Continue ANA MAX MCP/tool orchestration without losing chat context.",
            next_steps: "Read docs/NEXT_SESSION_BOOTSTRAP.md; verify MCP smart readiness; continue from ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md",
            files_changed: "vscode_extension/extension.js; ANA_MAX/extension/_vsix_unpack_103/extension/extension.js; docs/AGENT_MEMORY.md; docs/NEXT_SESSION_BOOTSTRAP.md",
            validation: "MCP smart readiness should report OK before continuing.",
            risks: "Reloading the IDE can close the current chat; defer reload until operator is ready.",
            sync_status: "Mother lab only; public release sync pending review.",
            include_git: true
          });
          post(panel, "checkpoint", payload.data || payload);
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "remSleep") {
        try {
          const payload = await callTool(config, "session_lifecycle", {
            action: "rest",
            consolidate: true,
            save_memory: true
          });
          post(panel, "remSleep", payload.data || payload);
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "previewRest") {
        try {
          const payload = await callTool(config, "session_lifecycle", {
            action: "rest",
            consolidate: false
          });
          post(panel, "lifecycle", payload.data || payload);
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "listTools") {
        try {
          const res = await requestJson(config.runtimeUrl, {
            jsonrpc: "2.0",
            id: Date.now(),
            method: "tools/list",
            params: {}
          });
          const tools = res.result?.tools || [];
          const names = tools.map(t => t.name).sort().join("\n");
          post(panel, "response", names ? `Tools loaded (${tools.length}):\n\n${names}` : "No tools found.");
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "hybridConfig") {
        post(panel, "response", getHybridConfigText(config));
        return;
      }

      if (message.command === "execute") {
        try {
          if (!(await confirmDangerousAction(message.tool, message.args || {}))) {
            post(panel, "error", "safe-mode blocks tool execution");
            return;
          }
          const res = await requestJson(config.runtimeUrl, {
            jsonrpc: "2.0",
            id: Date.now(),
            method: "tools/call",
            params: { name: message.tool, arguments: message.args || {} }
          });
          const payloadText = res.result?.content?.[0]?.text;
          let payload = undefined;
          if (payloadText) {
            try {
              payload = JSON.parse(payloadText);
            } catch {
              payload = undefined;
            }
          }
          if (payload?.guidance_summary) {
            post(panel, "toolGuidance", {
              tool: message.tool,
              payload,
              guidance_summary: payload.guidance_summary
            });
          } else {
            post(panel, "response", JSON.stringify(res.result || res.error, null, 2));
          }
        } catch (e) {
          post(panel, "error", e.message);
        }
        return;
      }

      if (message.command === "sendMessage") {
        const text = message.text || "";
        if (text.startsWith("/tool ")) {
          const body = text.slice(6).trim();
          const space = body.indexOf(" ");
          const name = space === -1 ? body : body.slice(0, space);
          const argsStr = space === -1 ? "{}" : body.slice(space + 1);
          try {
            const args = JSON.parse(argsStr);
            panel.webview.postMessage({ command: "execute", tool: name, args });
          } catch (e) {
            post(panel, "error", "Invalid JSON arguments.");
          }
          return;
        }
        post(panel, "response", `Message received: ${text}\n\nAntigravity & ANA are bridged. Every tool in the mother-folder is available.`);
      }
    });
  });

  const callTool = vscode.commands.registerCommand("ana.callTool", async () => {
    const config = getConfig();
    const tool = await vscode.window.showInputBox({ prompt: "Enter MCP Tool Name (from mother-folder)" });
    if (!tool) return;
    const args = await vscode.window.showInputBox({ prompt: "Arguments JSON", value: "{}" });
    if (args === undefined) return;

    try {
      const parsedArgs = JSON.parse(args || "{}");
      if (!(await confirmDangerousAction(tool, parsedArgs))) {
        vscode.window.showWarningMessage("safe-mode blocks tool execution");
        return;
      }
      const response = await requestJson(config.runtimeUrl, {
        jsonrpc: "2.0",
        id: "vscode-tool-call",
        method: "tools/call",
        params: { name: tool, arguments: parsedArgs }
      });
      const doc = await vscode.workspace.openTextDocument({ content: JSON.stringify(response, null, 2), language: "json" });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(e.message);
    }
  });

  context.subscriptions.push(openCockpit, callTool);

  context.subscriptions.push(vscode.commands.registerCommand("ana.showHybridConfig", async () => {
    const config = getConfig();
    const doc = await vscode.workspace.openTextDocument({
      content: getHybridConfigText(config),
      language: "json"
    });
    await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.showHealth", async () => {
    const config = getConfig();
    try {
      const report = await getSmartReadiness(config);
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(report, null, 2),
        language: "json"
      });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(`ANA MAX smart readiness failed: ${e.message}`);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.showRouterDecisions", async () => {
    const config = getConfig();
    try {
      const payload = await callTool(config, "agent_coach", {
        action: "recommend",
        task: "VS Code command asks for the next best ANA MAX tool",
        max_tools: 5,
        include_prompt: false
      });
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(payload, null, 2),
        language: "json"
      });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(e.message);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.wakeSession", async () => {
    const config = getConfig();
    try {
      const payload = await callTool(config, "session_lifecycle", { action: "wake" });
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(payload, null, 2),
        language: "json"
      });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(e.message);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.previewRest", async () => {
    const config = getConfig();
    try {
      const payload = await callTool(config, "session_lifecycle", {
        action: "rest",
        consolidate: false
      });
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(payload, null, 2),
        language: "json"
      });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(e.message);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.runRemSleep", async () => {
    const config = getConfig();
    try {
      const payload = await callTool(config, "session_lifecycle", {
        action: "rest",
        consolidate: true,
        save_memory: true
      });
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(payload, null, 2),
        language: "json"
      });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(e.message);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.startRuntime", startRuntime));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.executeTool", async () => {
    await vscode.commands.executeCommand("ana.callTool");
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.inspectRuntime", async () => {
    const config = getConfig();
    try {
      const response = await requestJson(config.runtimeUrl, {
        jsonrpc: "2.0",
        id: "inspect-runtime",
        method: "tools/call",
        params: { name: "ana_runtime_inspector", arguments: { action: "snapshot" } }
      });
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(response, null, 2),
        language: "json"
      });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    } catch (e) {
      vscode.window.showErrorMessage(e.message);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.runScenario", async () => {
    vscode.window.showInformationMessage("ANA MAX scenario runner is not wired in this hybrid build yet.");
  }));

  context.subscriptions.push(vscode.commands.registerCommand("anaMax.showObservability", async () => {
    vscode.window.showInformationMessage("ANA MAX observability view is not wired in this hybrid build yet.");
  }));

  // Legacy commands
  context.subscriptions.push(vscode.commands.registerCommand("anaMax.openDashboard", async () => {
    const config = getConfig();
    await vscode.env.openExternal(vscode.Uri.parse(config.dashboardUrl));
  }));
}

function post(panel, type, content) {
  panel?.webview.postMessage({ type, content });
}

async function fetch(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => resolve({ json: () => JSON.parse(data) }));
    }).on("error", reject);
  });
}

function getWebviewContent() {
  return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; background: #1e1e1e; color: #ccc; padding: 20px; display: flex; flex-direction: column; height: 100vh; margin: 0; }
        .header { background: #252526; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 15px; }
        h1 { font-size: 18px; margin: 0 0 5px 0; color: #007acc; }
        p { font-size: 12px; margin: 0; color: #888; }
        .quickstart { background: #202832; border: 1px solid #33475f; border-radius: 6px; padding: 10px; margin-bottom: 12px; }
        .quickstart h2 { font-size: 13px; margin: 0 0 8px 0; color: #d7e8ff; }
        .quickstart ol { margin: 0; padding-left: 18px; color: #c7d8ea; font-size: 12px; line-height: 1.5; }
        .quickstart code { color: #8fd3ff; }
        .toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; }
        .group-label { width: 100%; color: #aab6c3; font-size: 11px; text-transform: uppercase; margin-top: 4px; }
        .status { background: #1f2a24; border: 1px solid #315c3f; border-radius: 6px; padding: 10px; margin-bottom: 12px; font-size: 12px; color: #b7e4c7; white-space: pre-wrap; }
        .status.bad { background: #3a2323; border-color: #713333; color: #ffc9c9; }
        button { background: #0e639c; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; min-height: 32px; }
        button.secondary { background: #3d4c5c; }
        button.safe { background: #1f7a54; }
        button.save { background: #76591f; }
        button:hover { background: #1177bb; }
        #chat { flex: 1; background: #252526; border: 1px solid #333; border-radius: 8px; overflow-y: auto; padding: 15px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px; }
        .msg { padding: 10px; border-radius: 6px; font-size: 13px; line-height: 1.4; white-space: pre-wrap; }
        .msg.user { background: #37373d; border-left: 4px solid #007acc; align-self: flex-end; max-width: 80%; }
        .msg.ai { background: #2d2d30; border-left: 4px solid #4ec9b0; align-self: flex-start; max-width: 90%; }
        .msg.error { background: #4b1a1a; border-left: 4px solid #f44336; }
        .input-box { display: flex; gap: 10px; }
        input { flex: 1; background: #3c3c3c; color: #eee; border: 1px solid #555; padding: 10px; border-radius: 4px; outline: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ANA MAX Hybrid AI Cockpit</h1>
        <p>Start ANA, check readiness, wake the last session, then let your AI agent ask ANA which tool to use next.</p>
    </div>
    <div class="quickstart">
        <h2>Beginner Flow</h2>
        <ol>
            <li>Press <code>Start Runtime</code> once when ANA is offline.</li>
            <li>Press <code>Smart Ready</code>. Green means the agent can use ANA tools.</li>
            <li>Press <code>Wake</code> so the agent loads the last session memory.</li>
            <li>Use <code>Recommend</code> before risky work, then <code>Rest Preview</code> before saving REM Sleep.</li>
        </ol>
    </div>
    <div class="toolbar">
        <div class="group-label">Start here</div>
        <button title="Start the local ANA MAX MCP server if it is offline." onclick="cmd('startRuntime')">1 Start Runtime</button>
        <button class="safe" title="Verify ANA MAX health, router, coach, and tool list." onclick="cmd('smartReady')">2 Smart Ready</button>
        <button class="safe" title="Load last REM Sleep context or create a first-run manifest." onclick="wakeSession()">3 Wake</button>
        <div class="group-label">Daily work</div>
        <button title="Ask ANA which tool should be used next." onclick="recommend()">Recommend</button>
        <button class="secondary" title="Save a compact handoff checkpoint." onclick="checkpoint()">Checkpoint</button>
        <button class="secondary" title="Analyze the session without writing memory." onclick="previewRest()">Rest Preview</button>
        <button class="save" title="Save REM Sleep after reviewing the preview." onclick="remSleep()">Save REM</button>
        <div class="group-label">Advanced</div>
        <button class="secondary" title="Show raw health JSON." onclick="cmd('health')">Health JSON</button>
        <button class="secondary" title="List MCP tools exposed by ANA MAX." onclick="cmd('listTools')">List Tools</button>
        <button class="secondary" title="Show MCP config snippets for agent IDEs." onclick="cmd('hybridConfig')">MCP Config</button>
        <button class="secondary" title="Call ANA identity." onclick="identity()">Identity</button>
    </div>
    <div id="status" class="status">Press Smart Ready. If it is green, press Wake before work.</div>
    <div id="chat"></div>
    <div class="input-box">
        <input type="text" id="in" placeholder="Optional task for Recommend, or /tool name {}" />
        <button onclick="send()">Send</button>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        const chat = document.getElementById('chat');
        const input = document.getElementById('in');

        input.onkeypress = (e) => { if(e.key === 'Enter') send(); };

        function cmd(command) {
            addMsg(command.toUpperCase(), 'user');
            vscode.postMessage({ command });
        }

        function identity() {
            addMsg('/tool ana_identity {}', 'user');
            vscode.postMessage({ command: "execute", tool: "ana_identity", args: {} });
        }

        function recommend() {
            const task = input.value.trim() || 'Cockpit operator asks for the next best ANA MAX tool';
            addMsg('RECOMMEND: ' + task, 'user');
            vscode.postMessage({ command: "recommend", task });
        }

        function wakeSession() {
            addMsg('WAKE: load last REM context or first-run manifest', 'user');
            vscode.postMessage({ command: "wakeSession" });
        }

        function checkpoint() {
            const summary = input.value.trim() || 'Operator saved a quick checkpoint before risking chat loss.';
            addMsg('CHECKPOINT: ' + summary, 'user');
            vscode.postMessage({ command: "checkpoint", summary });
        }

        function remSleep() {
            addMsg('REM SLEEP: save recent session lessons', 'user');
            vscode.postMessage({ command: "remSleep" });
        }

        function previewRest() {
            addMsg('REST PREVIEW: analyze recent session lessons without writing', 'user');
            vscode.postMessage({ command: "previewRest" });
        }

        function send() {
            const val = input.value.trim();
            if(!val) return;
            addMsg(val, 'user');
            vscode.postMessage({ command: 'sendMessage', text: val });
            input.value = '';
        }

        function addMsg(text, type) {
            const d = document.createElement('div');
            d.className = 'msg ' + type;
            // Sanitize carriage returns that can corrupt terminal output embedded in tool responses.
            d.textContent = String(text || '').replace(/\r/g, '');
            chat.appendChild(d);
            chat.scrollTop = chat.scrollHeight;
        }

        function formatSmartReadiness(report) {
            const checks = (report.checks || []).map(c => (c.ok ? '[OK] ' : '[FAIL] ') + c.name).join('\\n');
            const stack = ((report.recommend || {}).tool_stack || []).join(', ') || 'none';
            return (report.ok ? 'SMART READY' : 'NOT READY')
                + '\\nhealth=' + ((report.health || {}).status)
                + ' mcp_ready=' + ((report.health || {}).mcp_ready)
                + ' tools=' + report.tool_count
                + '\\nprimary_tool=' + (((report.recommend || {}).primary_tool) || 'none')
                + '\\ntool_stack=' + stack
                + '\\n\\n' + checks;
        }

        function formatToolGuidance(content) {
            const summary = content.guidance_summary || {};
            const stack = (summary.tool_stack || []).join(', ') || 'none';
            return 'Tool failed with guidance: ' + (content.tool || 'unknown')
                + '\\nprimary_tool=' + (summary.primary_tool || 'none')
                + '\\ntool_stack=' + stack
                + '\\nnext_action=' + (summary.next_action || '')
                + '\\nsource=' + (summary.source || '')
                + '\\n\\nFull payload:\\n' + JSON.stringify(content.payload, null, 2);
        }

        window.addEventListener('message', (e) => {
            const m = e.data;
            if(m.type === 'response') addMsg(m.content, 'ai');
            if(m.type === 'health') addMsg('Health Check:\\n' + JSON.stringify(m.content, null, 2), 'ai');
            if(m.type === 'smartReady') {
                const status = document.getElementById('status');
                status.textContent = formatSmartReadiness(m.content);
                status.className = 'status ' + (m.content.ok ? '' : 'bad');
                addMsg('Smart Readiness:\\n' + formatSmartReadiness(m.content), 'ai');
            }
            if(m.type === 'recommend') {
                const stack = (m.content.tool_stack || []).join(', ') || 'none';
                addMsg('Recommendation:\\nprimary_tool=' + (m.content.primary_tool || 'none') + '\\ntool_stack=' + stack + '\\nnext_action=' + (m.content.next_action || ''), 'ai');
            }
            if(m.type === 'checkpoint') {
                addMsg('Checkpoint saved:\\n' + JSON.stringify(m.content, null, 2), 'ai');
            }
            if(m.type === 'remSleep') {
                addMsg('REM sleep saved:\\n' + JSON.stringify(m.content, null, 2), 'ai');
            }
            if(m.type === 'lifecycle') {
                addMsg('Lifecycle:\\n' + JSON.stringify(m.content, null, 2), 'ai');
            }
            if(m.type === 'toolGuidance') {
                addMsg(formatToolGuidance(m.content), 'ai');
            }
            if(m.type === 'error') addMsg('Error: ' + m.content, 'error');
            if(m.command === 'execute') vscode.postMessage(m);
        });

        addMsg('Cockpit ready. Hybrid MCP active: Codex + Antigravity/Qoder + Windsurf + ANA MAX on 8766.', 'ai');
        vscode.postMessage({ command: 'smartReady' });
    </script>
</body>
</html>`;
}

function deactivate() { }

module.exports = { activate, deactivate };
