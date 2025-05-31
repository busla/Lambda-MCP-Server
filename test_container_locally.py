#!/usr/bin/env python3
"""
Local container test script for Lambda MCP Server
Tests the container build and basic functionality before running full integration tests
"""
import subprocess
import time
import requests
import json
import sys
import os

def run_command(cmd, cwd=None, capture_output=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=capture_output, 
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_docker_build():
    """Test building the Lambda container"""
    print("🐳 Testing Docker build...")
    
    success, stdout, stderr = run_command(
        "docker build -t lambda-mcp-test .",
        cwd="/home/ubuntu/repos/Lambda-MCP-Server/server-http-python-lambda"
    )
    
    if success:
        print("✅ Docker build successful")
        return True
    else:
        print(f"❌ Docker build failed: {stderr}")
        return False

def test_container_start():
    """Test starting the container"""
    print("🚀 Testing container startup...")
    
    run_command("docker stop lambda-mcp-test-container 2>/dev/null || true")
    run_command("docker rm lambda-mcp-test-container 2>/dev/null || true")
    
    success, stdout, stderr = run_command(
        "docker run -d --name lambda-mcp-test-container -p 9001:8080 "
        "-e AWS_DEFAULT_REGION=us-east-1 "
        "-e AWS_ACCESS_KEY_ID=dummy "
        "-e AWS_SECRET_ACCESS_KEY=dummy "
        "-e MCP_SESSION_TABLE=test-sessions "
        "-e GOOGLE_API_KEY=dummy-key "
        "-e GOOGLE_SEARCH_ENGINE_ID=dummy-cx "
        "lambda-mcp-test"
    )
    
    if success:
        print("✅ Container started successfully")
        time.sleep(5)  # Wait for container to initialize
        return True
    else:
        print(f"❌ Container start failed: {stderr}")
        return False

def test_container_health():
    """Test if container is responding"""
    print("🏥 Testing container health...")
    
    lambda_url = "http://localhost:9001/2015-03-31/functions/function/invocations"
    
    test_event = {
        "httpMethod": "POST",
        "path": "/mcp",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token",
            "mcp-session-id": "health-check"
        },
        "body": json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.6",
                "capabilities": {},
                "clientInfo": {"name": "health-test", "version": "1.0.0"}
            }
        })
    }
    
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = requests.post(lambda_url, json=test_event, timeout=10)
            if response.status_code == 200:
                body = response.json()
                if "result" in body and "serverInfo" in body["result"]:
                    print("✅ Container health check passed")
                    return True
            print(f"⏳ Attempt {attempt + 1}/{max_retries} - waiting for container...")
            time.sleep(2)
        except Exception as e:
            print(f"⏳ Attempt {attempt + 1}/{max_retries} - connection error: {e}")
            time.sleep(2)
    
    print("❌ Container health check failed")
    return False

def test_google_tool_availability():
    """Test if Google search tool is available"""
    print("🔍 Testing Google tool availability...")
    
    lambda_url = "http://localhost:9001/2015-03-31/functions/function/invocations"
    
    test_event = {
        "httpMethod": "POST",
        "path": "/mcp",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token",
            "mcp-session-id": "tool-test"
        },
        "body": json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        })
    }
    
    try:
        response = requests.post(lambda_url, json=test_event, timeout=10)
        if response.status_code == 200:
            body = response.json()
            tools = body.get("result", {}).get("tools", [])
            google_tool = next((tool for tool in tools if tool["name"] == "googleSearchAndScrape"), None)
            
            if google_tool:
                print("✅ Google search tool is available")
                print(f"   Tool parameters: {list(google_tool.get('inputSchema', {}).get('properties', {}).keys())}")
                return True
            else:
                print("❌ Google search tool not found")
                return False
        else:
            print(f"❌ Tools list request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Tools list test failed: {e}")
        return False

def cleanup_container():
    """Clean up test container"""
    print("🧹 Cleaning up test container...")
    run_command("docker stop lambda-mcp-test-container 2>/dev/null || true")
    run_command("docker rm lambda-mcp-test-container 2>/dev/null || true")

def main():
    """Run all container tests"""
    print("🧪 Lambda MCP Server Container Tests")
    print("=" * 50)
    
    tests = [
        ("Docker Build", test_docker_build),
        ("Container Start", test_container_start),
        ("Container Health", test_container_health),
        ("Google Tool Availability", test_google_tool_availability)
    ]
    
    passed = 0
    failed = 0
    
    try:
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            if test_func():
                passed += 1
            else:
                failed += 1
                break  # Stop on first failure for container tests
        
        print("\n" + "=" * 50)
        print(f"🎯 Container Test Results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 All container tests passed! Ready for integration tests.")
            return True
        else:
            print(f"\n⚠️  Container tests failed - check Docker configuration")
            return False
            
    finally:
        cleanup_container()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
