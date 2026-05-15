const vscode = require('vscode');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const http = require('http');

let mcpProcess = null;
let statusBarItem = null;

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

function updateStatusBar(isRunning) {
    if (!statusBarItem) {
        statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
        statusBarItem.command = 'anaMax.checkLicense';
        statusBarItem.tooltip = 'ANA MAX MCP Server Status';
    }

    if (isRunning) {
        statusBarItem.text = '$(check) ANA MAX Running';
        statusBarItem.color = '#10B981'; // Green
    } else {
        statusBarItem.text = '$(circle-slash) ANA MAX Stopped';
        statusBarItem.color = '#94A3B8'; // Gray
    }

    statusBarItem.show();
}

function activate(context) {
    console.log('ANA MAX MCP Extension is now active!');

    // Create status bar item
    updateStatusBar(false);

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
            vscode.window.showErrorMessage('Python not found in PATH. Install Python or use py launcher.');
            return;
        }

        const pythonArgs = pythonCmd === 'py' ? ['-3', scriptPath] : [scriptPath];

        // Start the server using Python
        mcpProcess = spawn(pythonCmd, pythonArgs, { cwd: projectPath });

        mcpProcess.on('error', (error) => {
            vscode.window.showErrorMessage(`Could not start MCP: ${error.message}`);
            mcpProcess = null;
            updateStatusBar(false);
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
            updateStatusBar(false);
        });

        vscode.window.showInformationMessage('ANA MAX MCP Server started on http://127.0.0.1:8765');
        updateStatusBar(true);
    });

    // Command to stop the MCP server
    let stopCmd = vscode.commands.registerCommand('anaMax.stopMCP', () => {
        if (mcpProcess) {
            mcpProcess.kill();
            mcpProcess = null;
            vscode.window.showInformationMessage('ANA MAX MCP Server stopped.');
            updateStatusBar(false);
        } else {
            vscode.window.showInformationMessage('ANA MAX MCP Server is not running.');
        }
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
                vscode.window.showInformationMessage(`Response from ${toolName}: ${data.substring(0, 200)}...`);
            });
        });

        req.on('error', (e) => {
            vscode.window.showErrorMessage(`Failed to connect to ANA MAX: ${e.message}`);
        });

        req.write(postData);
        req.end();
    });

    // Command to check license status
    let checkLicenseCmd = vscode.commands.registerCommand('anaMax.checkLicense', async () => {
        const options = {
            hostname: '127.0.0.1',
            port: 8765,
            path: '/health',
            method: 'GET'
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    const health = JSON.parse(data);
                    const licenseType = health.license || 'free';
                    const toolCount = health.tools_count || 0;
                    
                    let message = `ANA MAX Status:\n`;
                    message += `• Server: ${health.status || 'unknown'}\n`;
                    message += `• License: ${licenseType.toUpperCase()}\n`;
                    message += `• Tools: ${toolCount} available\n`;
                    message += `• Version: ${health.version || 'unknown'}\n\n`;
                    
                    if (licenseType === 'free') {
                        message += `Upgrade to Pro for premium tools:\n`;
                        message += `• live_desktop_viewer\n`;
                        message += `• desktop_control\n`;
                        message += `• windows_insight\n`;
                        message += `• windows_deep_sight`;
                    } else {
                        message += `All premium tools unlocked!`;
                    }
                    
                    vscode.window.showInformationMessage(message);
                } catch (e) {
                    vscode.window.showErrorMessage('Could not parse server response');
                }
            });
        });

        req.on('error', (e) => {
            vscode.window.showErrorMessage(`Failed to connect to ANA MAX: ${e.message}\n\nMake sure the MCP server is running (python main.py)`);
        });

        req.end();
    });

    // Command to open documentation
    let openDocsCmd = vscode.commands.registerCommand('anaMax.openDocs', () => {
        const docs = [
            { label: 'Licensing Guide (docs/LICENSING.md)', path: 'docs/LICENSING.md' },
            { label: 'Installation Guide (INSTALL_GUIDE.md)', path: 'INSTALL_GUIDE.md' },
            { label: 'README.md', path: 'README.md' },
            { label: 'GitHub Repository', path: 'https://github.com/gyodragos-cell/ANA-MAX' },
            { label: 'Web Interface (index.html)', path: 'index.html' }
        ];

        vscode.window.showQuickPick(docs).then(selection => {
            if (selection) {
                if (selection.path.startsWith('http')) {
                    vscode.env.openExternal(vscode.Uri.parse(selection.path));
                } else {
                    const workspaceFolders = vscode.workspace.workspaceFolders;
                    if (workspaceFolders) {
                        const docPath = vscode.Uri.file(path.join(workspaceFolders[0].uri.fsPath, selection.path));
                        vscode.commands.executeCommand('vscode.open', docPath);
                    }
                }
            }
        });
    });

    context.subscriptions.push(startCmd, stopCmd, callToolCmd, checkLicenseCmd, openDocsCmd, statusBarItem);
}

function deactivate() {
    if (mcpProcess) {
        mcpProcess.kill();
        mcpProcess = null;
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

module.exports = {
    activate,
    deactivate
};
