#!/usr/bin/env python3
"""
Real integration tests for Lambda MCP Server running in container
Tests actual functionality with real Google API calls (no mocks)
"""
import json
import requests
import time
import sys
import os
from typing import Dict, Any, List

class RealIntegrationTester:
    def __init__(self, lambda_url: str = "http://localhost:9000/2015-03-31/functions/function/invocations"):
        self.lambda_url = lambda_url
        self.session_id = f"real-integration-{int(time.time())}"
        
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.google_cx = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
        
        if not self.google_api_key or not self.google_cx:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables are required for real integration tests")
        
    def invoke_lambda(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Lambda function with given event"""
        try:
            response = requests.post(
                self.lambda_url,
                json=event,
                timeout=60,
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
    
    def test_real_google_search(self) -> bool:
        """Test real Google search with actual API calls"""
        print("🔍 Testing real Google search functionality...")
        
        event = self.create_mcp_event("tools/call", {
            "name": "googleSearchAndScrape",
            "arguments": {
                "query": "Python programming tutorial",
                "num_results": 3,
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
            
            if "error" in search_data:
                print(f"❌ Google search API error: {search_data['error']}")
                return False
            
            if "results" in search_data and len(search_data["results"]) > 0:
                results = search_data["results"]
                print(f"✅ Google search returned {len(results)} real results")
                
                for i, result_item in enumerate(results):
                    if not result_item.get("title") or not result_item.get("url"):
                        print(f"❌ Result {i+1} missing title or URL")
                        return False
                    
                    if not result_item.get("scraped_content") or len(result_item["scraped_content"]) < 50:
                        print(f"❌ Result {i+1} has insufficient scraped content")
                        return False
                
                print(f"✅ All {len(results)} results have valid scraped content")
                
                sample = results[0]
                print(f"   Sample result: {sample['title'][:50]}...")
                print(f"   Content length: {len(sample['scraped_content'])} chars")
                
                return True
            else:
                print(f"❌ No search results returned from Google API")
                return False
            
        except Exception as e:
            print(f"❌ Real Google search test failed: {e}")
            return False
    
    def test_real_rag_processing(self) -> bool:
        """Test RAG processing with real search results"""
        print("🧠 Testing RAG processing with real data...")
        
        event = self.create_mcp_event("tools/call", {
            "name": "googleSearchAndScrape",
            "arguments": {
                "query": "machine learning fundamentals",
                "num_results": 2,
                "use_playwright": False,
                "use_rag": True,
                "chunk_size": 500
            }
        })
        
        result = self.invoke_lambda(event)
        
        if "error" in result:
            print(f"❌ RAG processing failed: {result['error']}")
            return False
            
        try:
            body = json.loads(result["body"])
            
            if "error" in body:
                print(f"❌ RAG processing returned error: {body['error']}")
                return False
                
            content = body.get("result", {}).get("content", [])
            if not content:
                print("❌ No RAG processing results returned")
                return False
                
            search_data = json.loads(content[0]["text"])
            
            if "error" in search_data:
                print(f"❌ RAG processing error: {search_data['error']}")
                return False
            
            if "rag_analysis" in search_data:
                rag_analysis = search_data["rag_analysis"]
                
                if rag_analysis.get("status") != "completed":
                    print(f"❌ RAG processing not completed: {rag_analysis}")
                    return False
                
                total_chunks = rag_analysis.get("total_chunks", 0)
                relevant_chunks = rag_analysis.get("relevant_chunks", 0)
                
                if total_chunks == 0:
                    print(f"❌ No chunks processed in RAG analysis")
                    return False
                
                if relevant_chunks == 0:
                    print(f"❌ No relevant chunks found in RAG analysis")
                    return False
                
                print(f"✅ RAG processing completed successfully")
                print(f"   Total chunks processed: {total_chunks}")
                print(f"   Relevant chunks found: {relevant_chunks}")
                print(f"   Relevance ratio: {relevant_chunks/total_chunks*100:.1f}%")
                
                if "summary" in rag_analysis and rag_analysis["summary"]:
                    print(f"   Summary generated: {len(rag_analysis['summary'])} chars")
                
                return True
            else:
                print(f"❌ No RAG analysis in response")
                return False
            
        except Exception as e:
            print(f"❌ Real RAG processing test failed: {e}")
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

def run_real_integration_tests():
    """Run all real integration tests"""
    print("🚀 Starting REAL Lambda MCP Server Integration Tests")
    print("=" * 70)
    print("⚠️  These tests make actual API calls and require valid credentials")
    print("=" * 70)
    
    required_env_vars = ["GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("   Please set these variables before running real integration tests")
        print("   Example:")
        print("   export GOOGLE_API_KEY='your-api-key'")
        print("   export GOOGLE_SEARCH_ENGINE_ID='your-search-engine-id'")
        return False
    
    try:
        tester = RealIntegrationTester()
    except ValueError as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    tests = [
        ("MCP Initialize", tester.test_mcp_initialize),
        ("Tools List", tester.test_tools_list),
        ("Real Google Search", tester.test_real_google_search),
        ("Real RAG Processing", tester.test_real_rag_processing),
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
    
    print("\n" + "=" * 70)
    print(f"🎯 Real Integration Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All real integration tests passed!")
        print("   The Lambda MCP Server is fully functional with real API calls!")
        return True
    else:
        print(f"\n⚠️  {failed} real integration test(s) failed")
        print("   Check the error messages above for details")
        return False

if __name__ == "__main__":
    container_url = os.environ.get("LAMBDA_CONTAINER_URL", "http://localhost:9000/2015-03-31/functions/function/invocations")
    
    print(f"Testing Lambda container at: {container_url}")
    
    if not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("GOOGLE_SEARCH_ENGINE_ID"):
        print("\n❌ ERROR: Real integration tests require valid Google API credentials")
        print("Please set the following environment variables:")
        print("  export GOOGLE_API_KEY='your-google-api-key'")
        print("  export GOOGLE_SEARCH_ENGINE_ID='your-search-engine-id'")
        print("\nTo get these credentials:")
        print("1. Go to https://console.developers.google.com/")
        print("2. Create a project and enable Custom Search JSON API")
        print("3. Create API credentials (API key)")
        print("4. Go to https://cse.google.com/ to create a Custom Search Engine")
        print("5. Get the Search Engine ID from the control panel")
        sys.exit(1)
    
    success = run_real_integration_tests()
    sys.exit(0 if success else 1)
