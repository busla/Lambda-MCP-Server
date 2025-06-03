#!/bin/bash


SERVER_URL=${1:-"http://localhost:3000/mcp"}
AUTH_TOKEN=${2:-"${MCP_AUTH_TOKEN:-"your-auth-token-here}"}"

echo "Testing MCP Server at: $SERVER_URL"
echo "Using auth token: ${AUTH_TOKEN:0:10}..."
echo "=================================="

if [ "$AUTH_TOKEN" = "your-auth-token-here" ]; then
    echo "Warning: Please set MCP_AUTH_TOKEN environment variable or pass token as second argument"
    echo "Usage: $0 [server_url] [auth_token]"
    echo "   or: MCP_AUTH_TOKEN=your-token $0 [server_url]"
    exit 1
fi

echo "1. Testing server initialization..."
curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     "$SERVER_URL" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"list":true,"call":true}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' | jq .

echo -e "\n=================================="

echo "2. Listing available tools..."
curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     "$SERVER_URL" \
     -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | jq .

echo -e "\n=================================="

echo "3. Testing basic search (no Playwright)..."
curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     "$SERVER_URL" \
     -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"googleSearchAndScrape","arguments":{"query":"AWS Lambda Python","num_results":2,"use_playwright":false,"use_rag":false,"chunk_size":500}}}' | jq .

echo -e "\n=================================="

echo "4. Testing search with Playwright..."
curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     "$SERVER_URL" \
     -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"googleSearchAndScrape","arguments":{"query":"Docker containers","num_results":1,"use_playwright":true,"use_rag":false,"chunk_size":500}}}' | jq .

echo -e "\n=================================="

echo "5. Testing search with RAG processing..."
curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     "$SERVER_URL" \
     -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"googleSearchAndScrape","arguments":{"query":"Machine learning","num_results":1,"use_playwright":false,"use_rag":true,"chunk_size":300}}}' | jq .

echo -e "\n=================================="
echo "Test completed!"
