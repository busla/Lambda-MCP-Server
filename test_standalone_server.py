#!/usr/bin/env python3
"""Test script to start and verify the standalone MCP server functionality"""
import os
import sys
import time
import requests
import json
import subprocess
import signal
from threading import Thread

os.environ['AWS_REGION'] = 'us-west-2'
os.environ['AWS_ACCESS_KEY_ID'] = 'test-key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret'
os.environ['GOOGLE_API_KEY'] = 'test-google-key'
os.environ['GOOGLE_SEARCH_ENGINE_ID'] = 'test-search-engine-id'
os.environ['MCP_AUTH_TOKEN'] = 'test-token'

def start_server():
    """Start the standalone MCP server in a subprocess"""
    os.chdir('/home/ubuntu/repos/Lambda-MCP-Server/server-http-python-lambda')
    process = subprocess.Popen([
        'bash', '-c', 
        'source .venv/bin/activate && python standalone_server.py'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_mcp_initialize():
    """Test MCP initialize request"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        response = requests.post(
            'http://localhost:8000/mcp',
            json=payload,
            headers={'Authorization': 'Bearer test-token'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MCP initialize successful: {data.get('result', {}).get('serverInfo', {})}")
            return response.headers.get('mcp-session-id')
        else:
            print(f"❌ MCP initialize failed with status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ MCP initialize failed: {e}")
        return None

def test_tools_list(session_id):
    """Test tools/list request"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        headers = {'Authorization': 'Bearer test-token'}
        if session_id:
            headers['mcp-session-id'] = session_id
        
        response = requests.post(
            'http://localhost:8000/mcp',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            tools = data.get('result', {}).get('tools', [])
            print(f"✅ Tools list successful: {len(tools)} tools available")
            for tool in tools:
                print(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")
            return True
        else:
            print(f"❌ Tools list failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Tools list failed: {e}")
        return False

def main():
    print("🚀 Starting standalone MCP server test...")
    
    server_process = start_server()
    
    try:
        print("⏳ Waiting for server to start...")
        time.sleep(5)
        
        if not test_health_endpoint():
            return False
        
        session_id = test_mcp_initialize()
        if not session_id:
            return False
        
        if not test_tools_list(session_id):
            return False
        
        print("🎉 All standalone server tests passed!")
        return True
        
    finally:
        print("🛑 Stopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
