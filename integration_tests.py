#!/usr/bin/env python3
"""
Integration tests for Lambda MCP Server running in container
Tests MCP protocol, Google search tool, RAG processing, and error handling
"""
import json
import requests
import time
import sys
import os
from typing import Dict, Any, List

class LambdaContainerTester:
    def __init__(self, lambda_url: str = "http://localhost:9000/2015-03-31/functions/function/invocations"):
        self.lambda_url = lambda_url
        self.session_id = f"test-session-{int(time.time())}"
        
    def invoke_lambda(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Lambda function with given event"""
        try:
            response = requests.post(
                self.lambda_url,
                json=event,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Lambda invocation failed: {str(e)}"}
    
    def create_mcp_event(self, method: str, params: Dict[str, Any] = None, request_id: int = 1) -> Dict[str, Any]:
        """Create MCP JSON-RPC event for Lambda"""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        return {
            "httpMethod": "POST",
            "path": "/mcp",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token",
                "mcp-session-id": self.session_id
            },
            "body": json.dumps(mcp_request)
        }
    
    def test_mcp_initialize(self) -> bool:
        """Test MCP server initialization"""
        print("🧪 Testing MCP Initialize...")
        
        event = self.create_mcp_event("initialize", {
            "protocolVersion": "0.6",
            "capabilities": {},
            "clientInfo": {"name": "integration-test", "version": "1.0.0"}
        })
        
        result = self.invoke_lambda(event)
        
        if "error" in result:
            print(f"❌ Initialize failed: {result['error']}")
            return False
            
        if result.get("statusCode") != 200:
            print(f"❌ Initialize returned status {result.get('statusCode')}")
            return False
            
        try:
            body = json.loads(result["body"])
            if body.get("result", {}).get("serverInfo"):
                print("✅ MCP Initialize successful")
                return True
            else:
                print(f"❌ Invalid initialize response: {body}")
                return False
        except Exception as e:
            print(f"❌ Initialize response parsing failed: {e}")
            return False
    
    def test_tools_list(self) -> bool:
        """Test listing available tools"""
        print("🧪 Testing Tools List...")
        
        event = self.create_mcp_event("tools/list")
        result = self.invoke_lambda(event)
        
        if "error" in result:
            print(f"❌ Tools list failed: {result['error']}")
            return False
            
        try:
            body = json.loads(result["body"])
            tools = body.get("result", {}).get("tools", [])
            
            expected_tools = ["getTime", "getWeather", "countS3Buckets", "googleSearchAndScrape"]
            found_tools = [tool["name"] for tool in tools]
            
            missing_tools = [tool for tool in expected_tools if tool not in found_tools]
            if missing_tools:
                print(f"❌ Missing tools: {missing_tools}")
                return False
                
            google_tool = next((tool for tool in tools if tool["name"] == "googleSearchAndScrape"), None)
            if not google_tool:
                print("❌ Google search tool not found")
                return False
                
            required_params = ["query", "num_results", "use_playwright", "use_rag", "chunk_size"]
            tool_params = list(google_tool.get("inputSchema", {}).get("properties", {}).keys())
            missing_params = [param for param in required_params if param not in tool_params]
            
            if missing_params:
                print(f"❌ Google tool missing parameters: {missing_params}")
                return False
                
            print(f"✅ Tools list successful - found {len(tools)} tools")
            return True
            
        except Exception as e:
            print(f"❌ Tools list response parsing failed: {e}")
            return False
    
    def test_google_search_basic(self) -> bool:
        """Test basic Google search functionality"""
        print("🧪 Testing Google Search (Basic)...")
        
        event = self.create_mcp_event("tools/call", {
            "name": "googleSearchAndScrape",
            "arguments": {
                "query": "python programming tutorial",
                "num_results": 2,
                "use_playwright": False,
                "use_rag": False,
                "chunk_size": 500
            }
        })
        
        result = self.invoke_lambda(event)
        
        if "error" in result:
            print(f"❌ Google search failed: {result['error']}")
            return False
            
        try:
            body = json.loads(result["body"])
            
            if "error" in body:
                print(f"❌ Google search returned error: {body['error']}")
                return False
                
            content = body.get("result", {}).get("content", [])
            if not content:
                print("❌ No search results returned")
                return False
                
            search_data = json.loads(content[0]["text"])
            
            if search_data.get("total_results", 0) == 0:
                print("❌ No search results found")
                return False
                
            results = search_data.get("results", [])
            if not results:
                print("❌ Empty results array")
                return False
                
            first_result = results[0]
            required_fields = ["title", "url", "snippet", "scraped_content"]
            missing_fields = [field for field in required_fields if field not in first_result]
            
            if missing_fields:
                print(f"❌ Missing result fields: {missing_fields}")
                return False
                
            print(f"✅ Google search successful - {len(results)} results")
            return True
            
        except Exception as e:
            print(f"❌ Google search response parsing failed: {e}")
            return False
    
    def test_google_search_with_rag(self) -> bool:
        """Test Google search with RAG processing"""
        print("🧪 Testing Google Search with RAG...")
        
        event = self.create_mcp_event("tools/call", {
            "name": "googleSearchAndScrape",
            "arguments": {
                "query": "machine learning basics",
                "num_results": 1,
                "use_playwright": False,
                "use_rag": True,
                "chunk_size": 300
            }
        })
        
        result = self.invoke_lambda(event)
        
        if "error" in result:
            print(f"❌ RAG search failed: {result['error']}")
            return False
            
        try:
            body = json.loads(result["body"])
            content = body.get("result", {}).get("content", [])
            search_data = json.loads(content[0]["text"])
            
            rag_analysis = search_data.get("rag_analysis")
            if not rag_analysis:
                print("❌ RAG analysis not found in response")
                return False
                
            if rag_analysis.get("status") not in ["success", "fallback"]:
                print(f"❌ RAG processing failed: {rag_analysis.get('message', 'Unknown error')}")
                return False
                
            if rag_analysis.get("total_chunks", 0) == 0:
                print("❌ No chunks processed by RAG")
                return False
                
            print(f"✅ RAG processing successful - {rag_analysis.get('total_chunks')} chunks, {rag_analysis.get('relevant_chunks', 0)} relevant")
            return True
            
        except Exception as e:
            print(f"❌ RAG search response parsing failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling for invalid requests"""
        print("🧪 Testing Error Handling...")
        
        event = self.create_mcp_event("tools/call", {
            "name": "nonexistentTool",
            "arguments": {}
        })
        
        result = self.invoke_lambda(event)
        
        try:
            body = json.loads(result["body"])
            if "error" not in body:
                print("❌ Expected error for invalid tool name")
                return False
                
            print("✅ Invalid tool name handled correctly")
            
            event = self.create_mcp_event("tools/call", {
                "name": "googleSearchAndScrape",
                "arguments": {
                    "query": "",  # Empty query
                    "num_results": -1,  # Invalid number
                    "use_playwright": "invalid",  # Wrong type
                    "use_rag": False,
                    "chunk_size": 500
                }
            })
            
            result = self.invoke_lambda(event)
            body = json.loads(result["body"])
            
            if "error" in body:
                print("✅ Invalid parameters handled with error")
                return True
            else:
                content = body.get("result", {}).get("content", [])
                if content:
                    search_data = json.loads(content[0]["text"])
                    if "error" in search_data:
                        print("✅ Invalid parameters handled gracefully")
                        return True
                        
            print("❌ Invalid parameters not handled properly")
            return False
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    def test_session_management(self) -> bool:
        """Test session management functionality"""
        print("🧪 Testing Session Management...")
        
        new_session_id = f"test-session-{int(time.time())}-new"
        
        event = self.create_mcp_event("initialize", {
            "protocolVersion": "0.6",
            "capabilities": {},
            "clientInfo": {"name": "session-test", "version": "1.0.0"}
        })
        event["headers"]["mcp-session-id"] = new_session_id
        
        result = self.invoke_lambda(event)
        
        if "error" in result:
            print(f"❌ Session creation failed: {result['error']}")
            return False
            
        headers = result.get("headers", {})
        returned_session = headers.get("mcp-session-id")
        
        if not returned_session:
            print("❌ Session ID not returned in headers")
            return False
            
        print(f"✅ Session management successful - session: {returned_session}")
        return True

def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Lambda MCP Server Integration Tests")
    print("=" * 60)
    
    tester = LambdaContainerTester()
    
    tests = [
        ("MCP Initialize", tester.test_mcp_initialize),
        ("Tools List", tester.test_tools_list),
        ("Google Search Basic", tester.test_google_search_basic),
        ("Google Search with RAG", tester.test_google_search_with_rag),
        ("Error Handling", tester.test_error_handling),
        ("Session Management", tester.test_session_management)
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
    print(f"🎯 Integration Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All integration tests passed!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed - check container configuration")
        return False

if __name__ == "__main__":
    container_url = os.environ.get("LAMBDA_CONTAINER_URL", "http://localhost:9000/2015-03-31/functions/function/invocations")
    
    print(f"Testing Lambda container at: {container_url}")
    
    os.environ.setdefault("GOOGLE_API_KEY", "dummy-key-for-testing")
    os.environ.setdefault("GOOGLE_SEARCH_ENGINE_ID", "dummy-cx-for-testing")
    
    success = run_integration_tests()
    sys.exit(0 if success else 1)
