const express = require('express');
const cors = require('cors');
const http = require('http');

const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());

const LAMBDA_URL = process.env.LAMBDA_URL || 'http://mcp-server:8080/2015-03-31/functions/function/invocations';
const MCP_AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || 'test-token';

app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

app.post('/', async (req, res) => {
    try {
        const mcpRequest = req.body;
        
        const lambdaEvent = {
            body: JSON.stringify(mcpRequest),
            headers: {
                'content-type': 'application/json',
                'authorization': req.headers.authorization || `Bearer ${MCP_AUTH_TOKEN}`,
                'mcp-session-id': req.headers['mcp-session-id']
            }
        };

        const lambdaResponse = await makeRequest(LAMBDA_URL, lambdaEvent);
        const parsedResponse = JSON.parse(lambdaResponse);
        
        if (parsedResponse.statusCode === 200) {
            const mcpResponse = JSON.parse(parsedResponse.body);
            
            if (parsedResponse.headers && parsedResponse.headers['mcp-session-id']) {
                res.setHeader('mcp-session-id', parsedResponse.headers['mcp-session-id']);
            }
            if (parsedResponse.headers && parsedResponse.headers['MCP-Version']) {
                res.setHeader('MCP-Version', parsedResponse.headers['MCP-Version']);
            }
            
            res.json(mcpResponse);
        } else {
            res.status(parsedResponse.statusCode || 500).json({
                jsonrpc: "2.0",
                id: mcpRequest.id,
                error: {
                    code: -32603,
                    message: "Internal error",
                    data: parsedResponse.body
                }
            });
        }
    } catch (error) {
        console.error('Proxy error:', error);
        res.status(500).json({
            jsonrpc: "2.0",
            id: req.body?.id,
            error: {
                code: -32603,
                message: "Internal error",
                data: error.message
            }
        });
    }
});

function makeRequest(url, data) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port || 80,
            path: urlObj.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(JSON.stringify(data))
            }
        };
        
        const req = http.request(options, (res) => {
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

app.listen(port, '0.0.0.0', () => {
    console.log(`MCP Proxy server running on port ${port}`);
    console.log(`Proxying to Lambda: ${LAMBDA_URL}`);
});
