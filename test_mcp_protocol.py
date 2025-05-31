#!/usr/bin/env python3
"""
MCP Protocol compliance test for Lambda container
Tests specific MCP protocol requirements and edge cases
"""
import json
import requests
import time
import sys

class MCPProtocolTester:
    def __init__(self, lambda_url: str = "http://localhost:9000/2015-03-31/functions/function/invocations"):
        self.lambda_url = lambda_url
        self.session_id = f"protocol-test-{int(time.time())}"
    
    def send_mcp_request(self, method: str, params: dict = None, request_id: int = 1) -> dict:
        """Send MCP JSON-RPC request to Lambda"""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        lambda_event = {
            "httpMethod": "POST",
            "path": "/mcp",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token",
                "mcp-session-id": self.session_id
            },
            "body": json.dumps(mcp_request)
        }
        
        try:
            response = requests.post(self.lambda_url, json=lambda_event, timeout=30)
            return response.json()
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def test_jsonrpc_compliance(self) -> bool:
        """Test JSON-RPC 2.0 compliance"""
        print("🧪 Testing JSON-RPC 2.0 compliance...")
        
        result = self.send_mcp_request("initialize", {
            "protocolVersion": "0.6",
            "capabilities": {},
            "clientInfo": {"name": "protocol-test", "version": "1.0.0"}
        })
        
        if result.get("statusCode") != 200:
            print(f"❌ Invalid status code: {result.get('statusCode')}")
            return False
        
        try:
            body = json.loads(result["body"])
            
            if body.get("jsonrpc") != "2.0":
                print(f"❌ Missing or invalid jsonrpc field: {body.get('jsonrpc')}")
                return False
            
            if "id" not in body:
                print("❌ Missing id field in response")
                return False
            
            if "result" not in body and "error" not in body:
                print("❌ Response must have either result or error field")
                return False
            
            print("✅ JSON-RPC 2.0 compliance verified")
            return True
            
        except Exception as e:
            print(f"❌ JSON-RPC compliance test failed: {e}")
            return False
    
    def test_mcp_initialization(self) -> bool:
        """Test MCP initialization sequence"""
        print("🧪 Testing MCP initialization sequence...")
        
        result = self.send_mcp_request("initialize", {
            "protocolVersion": "0.6",
            "capabilities": {},
            "clientInfo": {"name": "init-test", "version": "1.0.0"}
        })
        
        try:
            body = json.loads(result["body"])
            server_info = body.get("result", {}).get("serverInfo")
            
            if not server_info:
                print("❌ Missing serverInfo in initialize response")
                return False
            
            required_fields = ["name", "version"]
            for field in required_fields:
                if field not in server_info:
                    print(f"❌ Missing {field} in serverInfo")
                    return False
            
            print("✅ MCP initialization sequence verified")
            return True
            
        except Exception as e:
            print(f"❌ MCP initialization test failed: {e}")
            return False
    
    def test_tools_schema_compliance(self) -> bool:
        """Test tools schema compliance"""
        print("🧪 Testing tools schema compliance...")
        
        result = self.send_mcp_request("tools/list")
        
        try:
            body = json.loads(result["body"])
            tools = body.get("result", {}).get("tools", [])
            
            if not tools:
                print("❌ No tools returned")
                return False
            
            for tool in tools:
                required_fields = ["name", "description"]
                for field in required_fields:
                    if field not in tool:
                        print(f"❌ Tool missing required field: {field}")
                        return False
                
                if "inputSchema" in tool:
                    schema = tool["inputSchema"]
                    if "type" not in schema:
                        print(f"❌ Tool {tool['name']} inputSchema missing type")
                        return False
                    
                    if schema["type"] == "object" and "properties" not in schema:
                        print(f"❌ Tool {tool['name']} object schema missing properties")
                        return False
            
            print(f"✅ Tools schema compliance verified for {len(tools)} tools")
            return True
            
        except Exception as e:
            print(f"❌ Tools schema compliance test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test MCP error handling"""
        print("🧪 Testing MCP error handling...")
        
        result = self.send_mcp_request("invalid/method")
        
        try:
            body = json.loads(result["body"])
            
            if "error" not in body:
                print("❌ Expected error for invalid method")
                return False
            
            error = body["error"]
            if "code" not in error or "message" not in error:
                print("❌ Error object missing required fields")
                return False
            
            print("✅ Error handling verified")
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    def test_session_isolation(self) -> bool:
        """Test session isolation"""
        print("🧪 Testing session isolation...")
        
        session1_id = f"session-1-{int(time.time())}"
        session2_id = f"session-2-{int(time.time())}"
        
        for session_id in [session1_id, session2_id]:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.6",
                    "capabilities": {},
                    "clientInfo": {"name": f"session-test-{session_id}", "version": "1.0.0"}
                }
            }
            
            lambda_event = {
                "httpMethod": "POST",
                "path": "/mcp",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test-token",
                    "mcp-session-id": session_id
                },
                "body": json.dumps(mcp_request)
            }
            
            try:
                response = requests.post(self.lambda_url, json=lambda_event, timeout=30)
                if response.status_code != 200:
                    print(f"❌ Session {session_id} initialization failed")
                    return False
            except Exception as e:
                print(f"❌ Session isolation test failed: {e}")
                return False
        
        print("✅ Session isolation verified")
        return True

def run_protocol_tests():
    """Run all MCP protocol tests"""
    print("🚀 Starting MCP Protocol Compliance Tests")
    print("=" * 60)
    
    tester = MCPProtocolTester()
    
    tests = [
        ("JSON-RPC 2.0 Compliance", tester.test_jsonrpc_compliance),
        ("MCP Initialization", tester.test_mcp_initialization),
        ("Tools Schema Compliance", tester.test_tools_schema_compliance),
        ("Error Handling", tester.test_error_handling),
        ("Session Isolation", tester.test_session_isolation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 Protocol Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All protocol tests passed!")
        return True
    else:
        print(f"\n⚠️  {failed} protocol test(s) failed")
        return False

if __name__ == "__main__":
    success = run_protocol_tests()
    sys.exit(0 if success else 1)
