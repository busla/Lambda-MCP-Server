const https = require('https');
const http = require('http');

async function testMCPConnection() {
    const serverUrl = process.env.MCP_URL || 'http://mcp-server:8080/2015-03-31/functions/function/invocations';
    const token = process.env.MCP_TOKEN || 'test-token';
    
    console.log('Testing MCP connection to:', serverUrl);
    
    const initRequest = {
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "initialize",
            params: {
                protocolVersion: "2024-11-05",
                capabilities: {},
                clientInfo: {
                    name: "test-client",
                    version: "1.0.0"
                }
            },
            id: 1
        }),
        headers: {
            "content-type": "application/json",
            "authorization": `Bearer ${token}`
        }
    };
    
    try {
        const response = await makeRequest(serverUrl, initRequest);
        console.log('✅ Initialize response:', response);
        
        const lambdaResponse = JSON.parse(response);
        if (lambdaResponse.statusCode === 200) {
            const mcpResponse = JSON.parse(lambdaResponse.body);
            console.log('✅ MCP Response:', mcpResponse);
            
            if (mcpResponse.result && mcpResponse.result.serverInfo) {
                console.log('✅ Server Info:', mcpResponse.result.serverInfo);
                console.log('✅ Session ID:', lambdaResponse.headers['mcp-session-id']);
                
                const sessionId = lambdaResponse.headers['mcp-session-id'];
                await testToolsList(serverUrl, token, sessionId);
                
                return true;
            }
        }
        
        console.log('❌ Unexpected response format');
        return false;
        
    } catch (error) {
        console.error('❌ Connection failed:', error.message);
        return false;
    }
}

async function testToolsList(serverUrl, token, sessionId) {
    const toolsRequest = {
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "tools/list",
            params: {},
            id: 2
        }),
        headers: {
            "content-type": "application/json",
            "authorization": `Bearer ${token}`,
            "mcp-session-id": sessionId
        }
    };
    
    try {
        const response = await makeRequest(serverUrl, toolsRequest);
        const lambdaResponse = JSON.parse(response);
        
        if (lambdaResponse.statusCode === 200) {
            const mcpResponse = JSON.parse(lambdaResponse.body);
            console.log('✅ Available tools:', mcpResponse.result.tools.length);
            mcpResponse.result.tools.forEach(tool => {
                console.log(`  - ${tool.name}: ${tool.description}`);
            });
            
            const searchTool = mcpResponse.result.tools.find(t => t.name === 'googleSearchAndScrape');
            if (searchTool) {
                await testGoogleSearchTool(serverUrl, token, sessionId);
            }
        }
    } catch (error) {
        console.error('❌ Tools list failed:', error.message);
    }
}

async function testGoogleSearchTool(serverUrl, token, sessionId) {
    const toolCallRequest = {
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "googleSearchAndScrape",
                arguments: {
                    query: "test search",
                    num_results: 1,
                    use_playwright: false
                }
            },
            id: 3
        }),
        headers: {
            "content-type": "application/json",
            "authorization": `Bearer ${token}`,
            "mcp-session-id": sessionId
        }
    };
    
    try {
        const response = await makeRequest(serverUrl, toolCallRequest);
        const lambdaResponse = JSON.parse(response);
        
        if (lambdaResponse.statusCode === 200) {
            const mcpResponse = JSON.parse(lambdaResponse.body);
            console.log('✅ Google search tool executed successfully');
            console.log('📄 Response content length:', mcpResponse.result.content[0].text.length);
        } else {
            console.log('❌ Tool call failed:', lambdaResponse.body);
        }
    } catch (error) {
        console.error('❌ Google search tool failed:', error.message);
    }
}

function makeRequest(url, data) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const isHttps = urlObj.protocol === 'https:';
        const client = isHttps ? https : http;
        
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port || (isHttps ? 443 : 80),
            path: urlObj.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(JSON.stringify(data))
            }
        };
        
        const req = client.request(options, (res) => {
            let responseData = '';
            
            res.on('data', (chunk) => {
                responseData += chunk;
            });
            
            res.on('end', () => {
                resolve(responseData);
            });
        });
        
        req.on('error', (error) => {
            reject(error);
        });
        
        req.write(JSON.stringify(data));
        req.end();
    });
}

testMCPConnection().then(success => {
    console.log(success ? '🎉 MCP connection test completed successfully!' : '❌ MCP connection test failed');
    process.exit(success ? 0 : 1);
});
