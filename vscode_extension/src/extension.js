const vscode = require('vscode');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const http = require('http');

let mcpProcess = null;

function resolvePythonCommand() {
    const candidates = process.platform === 'win32'
        ? ['python', 'py', 'python3']
        : ['python3', 'python'];

    for (const candidate of candidates) {
        try {
            const result = spawnSync(candidate, ['--version'], { stdio: 'ignore' });
            if (result.status === 0) {
                return candidate;
            }
        } catch (e) {
            continue;
        }
    }

    return null;
}

function activate(context) {
    console.log('ANA MAX MCP Extension is now active!');

    // Command to start the MCP server
    let startCmd = vscode.commands.registerCommand('anaMax.startMCP', () => {
        if (mcpProcess) {
            vscode.window.showInformationMessage('ANA MAX MCP Server is already running.');
            return;
        }

        // Get the workspace folder
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('Please open the ANA MAX folder in VS Code first.');
            return;
        }

        const projectPath = workspaceFolders[0].uri.fsPath;
        const scriptPath = path.join(projectPath, 'main.py');
        const pythonCmd = resolvePythonCommand();

        if (!pythonCmd) {
            vscode.window.showErrorMessage('Python nu a fost găsit în PATH. Instalează Python sau folosește py launcher.');
            return;
        }

        const pythonArgs = pythonCmd === 'py' ? ['-3', scriptPath] : [scriptPath];

        // Start the server using Python
        mcpProcess = spawn(pythonCmd, pythonArgs, { cwd: projectPath });

        mcpProcess.on('error', (error) => {
            vscode.window.showErrorMessage(`Nu s-a putut porni MCP: ${error.message}`);
            mcpProcess = null;
        });

        mcpProcess.stdout.on('data', (data) => {
            console.log(`MCP Output: ${data}`);
        });

        mcpProcess.stderr.on('data', (data) => {
            console.error(`MCP Error: ${data}`);
        });

        mcpProcess.on('close', (code) => {
            console.log(`MCP Server exited with code ${code}`);
            mcpProcess = null;
            vscode.window.showWarningMessage('ANA MAX MCP Server has stopped.');
        });

        vscode.window.showInformationMessage('ANA MAX MCP Server started on http://127.0.0.1:8765');
    });

    // Command to call a tool via HTTP to the MCP Server
    let callToolCmd = vscode.commands.registerCommand('anaMax.callTool', async () => {
        const toolName = await vscode.window.showInputBox({
            prompt: "Enter the tool name (e.g., windows_uia_bridge)",
            placeHolder: "windows_uia_bridge"
        });

        if (!toolName) return;

        // Simple example: sending an execute request
        const postData = JSON.stringify({
            tool: toolName,
            params: {}
        });

        const options = {
            hostname: '127.0.0.1',
            port: 8765,
            path: '/execute',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                vscode.window.showInformationMessage(`Response from ${toolName}: ${data.substring(0, 100)}...`);
            });
        });

        req.on('error', (e) => {
            vscode.window.showErrorMessage(`Failed to connect to ANA MAX: ${e.message}`);
        });

        req.write(postData);
        req.end();
    });

    context.subscriptions.push(startCmd, callToolCmd);
}

function deactivate() {
    if (mcpProcess) {
        mcpProcess.kill();
    }
}

module.exports = {
    activate,
    deactivate
};
