#!/bin/bash


set -e

SERVER_URL="${MCP_URL:-http://localhost:8000}"
AUTH_TOKEN="${MCP_TOKEN:-test-token}"
HEALTH_URL="${SERVER_URL}/health"
MCP_URL="${SERVER_URL}/mcp"

echo "🚀 Testing MCP Server Integration"
echo "Server URL: $SERVER_URL"
echo "Auth Token: $AUTH_TOKEN"
echo ""

echo "1️⃣ Testing Health Check Endpoint..."
health_response=$(curl -s -w "\n%{http_code}" "$HEALTH_URL")
health_code=$(echo "$health_response" | tail -n1)
health_body=$(echo "$health_response" | head -n -1)

if [ "$health_code" = "200" ]; then
    echo "✅ Health check passed"
    echo "Response: $health_body"
else
    echo "❌ Health check failed with status $health_code"
    echo "Response: $health_body"
    exit 1
fi
echo ""

echo "2️⃣ Testing MCP Initialize Request..."
init_payload='{
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
}'

init_response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$init_payload" \
    "$MCP_URL")

init_code=$(echo "$init_response" | tail -n1)
init_body=$(echo "$init_response" | head -n -1)

if [ "$init_code" = "200" ]; then
    echo "✅ MCP initialize successful"
    echo "Response: $init_body"
    
    session_id=$(echo "$init_response" | grep -i "mcp-session-id" | cut -d: -f2 | tr -d ' \r\n' || echo "")
    if [ -n "$session_id" ]; then
        echo "Session ID: $session_id"
    fi
else
    echo "❌ MCP initialize failed with status $init_code"
    echo "Response: $init_body"
    exit 1
fi
echo ""

echo "3️⃣ Testing Tools List Request..."
tools_payload='{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
}'

tools_headers="-H \"Authorization: Bearer $AUTH_TOKEN\" -H \"Content-Type: application/json\""
if [ -n "$session_id" ]; then
    tools_headers="$tools_headers -H \"mcp-session-id: $session_id\""
fi

tools_response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$tools_payload" \
    "$MCP_URL")

tools_code=$(echo "$tools_response" | tail -n1)
tools_body=$(echo "$tools_response" | head -n -1)

if [ "$tools_code" = "200" ]; then
    echo "✅ Tools list successful"
    echo "Response: $tools_body"
    
    if echo "$tools_body" | grep -q "googleSearchAndScrape"; then
        echo "✅ Google search tool found"
    else
        echo "⚠️ Google search tool not found in tools list"
    fi
else
    echo "❌ Tools list failed with status $tools_code"
    echo "Response: $tools_body"
    exit 1
fi
echo ""

echo "4️⃣ Testing Google Search and Scrape Tool..."
search_payload='{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "googleSearchAndScrape",
        "arguments": {
            "query": "test search",
            "num_results": 1,
            "use_playwright": false
        }
    },
    "id": 3
}'

search_response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$search_payload" \
    "$MCP_URL")

search_code=$(echo "$search_response" | tail -n1)
search_body=$(echo "$search_response" | head -n -1)

if [ "$search_code" = "200" ]; then
    echo "✅ Google search tool executed successfully"
    echo "Response: $search_body"
    
    if echo "$search_body" | grep -q "result"; then
        echo "✅ Tool response has expected structure"
    else
        echo "⚠️ Tool response may not have expected structure"
    fi
else
    echo "❌ Google search tool failed with status $search_code"
    echo "Response: $search_body"
    exit 1
fi
echo ""

echo "🎉 All MCP integration tests passed!"
echo "✅ Health check endpoint working"
echo "✅ MCP initialize request working"
echo "✅ Tools list request working"
echo "✅ Google search and scrape tool working"
