#!/usr/bin/env node

const http = require('http');

const serverUrl = 'http://localhost:8000/mcp';
const authToken = 'test-token';

function makeRequest(payload) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(payload);
        
        const options = {
            hostname: 'localhost',
            port: 8000,
            path: '/mcp',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
                'Content-Length': Buffer.byteLength(data)
            }
        };
        
        const req = http.request(options, (res) => {
            let responseData = '';
            
            res.on('data', (chunk) => {
                responseData += chunk;
            });
            
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(responseData);
                    resolve(parsed);
                } catch (e) {
                    reject(new Error(`Failed to parse response: ${responseData}`));
                }
            });
        });
        
        req.on('error', (error) => {
            reject(error);
        });
        
        req.write(data);
        req.end();
    });
}

async function testGoogleSearchTool() {
    console.log('🚀 Testing Google Search and Scrape Tool with Playwright');
    
    try {
        console.log('1️⃣ Initializing MCP session...');
        const initResponse = await makeRequest({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "direct-test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        });
        
        console.log('✅ Session initialized:', initResponse.result.serverInfo);
        
        console.log('2️⃣ Calling google_search_and_scrape tool with playwright enabled...');
        const searchResponse = await makeRequest({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "googleSearchAndScrape",
                "arguments": {
                    "query": "typescript MCP client",
                    "num_results": 2,
                    "use_playwright": true,
                    "use_rag": false,
                    "chunk_size": 500
                }
            },
            "id": 2
        });
        
        if (searchResponse.result) {
            console.log('✅ Google search tool executed successfully with playwright!');
            console.log('📊 Results summary:');
            
            const content = JSON.parse(searchResponse.result.content[0].text);
            console.log(`   Query: ${content.query}`);
            console.log(`   Total results: ${content.total_results}`);
            
            content.results.forEach((result, index) => {
                console.log(`   ${index + 1}. ${result.title}`);
                console.log(`      URL: ${result.url}`);
                console.log(`      Scraping method: ${result.scraping_method}`);
                console.log(`      Content length: ${result.scraped_content.length} characters`);
            });
            
            console.log('🎉 SUCCESS: Google search and scrape tool with playwright works correctly!');
            return true;
        } else if (searchResponse.error) {
            console.log('❌ Tool call failed:', searchResponse.error);
            return false;
        }
        
    } catch (error) {
        console.log('❌ Test failed:', error.message);
        return false;
    }
}

testGoogleSearchTool().then(success => {
    process.exit(success ? 0 : 1);
});
