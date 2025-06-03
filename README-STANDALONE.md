# Standalone MCP Server Setup

This document provides instructions for running the MCP server as a standalone Flask application for local development and testing, bypassing the need for AWS Lambda and API Gateway.

## Overview

The standalone server extracts the MCP functionality from the Lambda handler and runs it as an independent HTTP server that can communicate directly with TypeScript clients without requiring AWS infrastructure.

## Prerequisites

- Python 3.12+
- Node.js 18+ (for TypeScript client)
- Virtual environment setup
- Required environment variables

## Environment Setup

1. **Create and activate Python virtual environment:**
   ```bash
   cd server-http-python-lambda
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r server/requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the repository root with the following variables:
   ```bash
   AWS_REGION=us-west-2
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   GOOGLE_API_KEY=your-google-api-key
   GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
   MCP_AUTH_TOKEN=your-auth-token
   ```

## Running the Standalone Server

1. **Start the standalone MCP server:**
   ```bash
   cd server-http-python-lambda
   source .venv/bin/activate
   python standalone_server.py
   ```

   The server will start on `http://localhost:8000` with the following endpoints:
   - Health check: `GET /health`
   - MCP JSON-RPC: `POST /mcp`

2. **Verify server is running:**
   ```bash
   curl http://localhost:8000/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "server": "mcp-lambda-server",
     "version": "1.0.0",
     "tools": ["getTime", "getWeather", "countS3Buckets", "googleSearchAndScrape"]
   }
   ```

## Available Tools

The standalone server provides the following tools:

1. **getTime** - Get the current UTC date and time
2. **getWeather** - Get current weather for a city
3. **countS3Buckets** - Count the number of S3 buckets
4. **googleSearchAndScrape** - Search Google and scrape content with optional Playwright support

### Google Search and Scrape Tool

The `googleSearchAndScrape` tool supports the following parameters:

- `query` (required): The search query to execute
- `num_results` (required): Number of results to return (max 10)
- `use_playwright` (required): Whether to use Playwright for JavaScript-rendered content
- `use_rag` (optional): Whether to apply RAG processing with chunking
- `chunk_size` (optional): Size of text chunks for RAG processing (default 500)

Example tool call:
```json
{
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
  "id": 1
}
```

## TypeScript Client Configuration

1. **Install client dependencies:**
   ```bash
   cd client-http-typescript-docker/client
   npm install
   npm run build
   ```

2. **Configure client to connect to standalone server:**
   The client configuration in `src/config/bedrock.ts` should point to:
   ```typescript
   export const serverConfig = {
     url: process.env.MCP_URL || 'http://localhost:8000/mcp',
     apiToken: process.env.MCP_TOKEN || 'test-token'
   };
   ```

3. **Run the TypeScript client:**
   ```bash
   MCP_URL=http://localhost:8000/mcp MCP_TOKEN=test-token npm start
   ```

## Testing the Integration

### Manual Testing

Use the provided test scripts to verify functionality:

1. **Test standalone server:**
   ```bash
   python test_standalone_server.py
   ```

2. **Test MCP integration:**
   ```bash
   ./test_mcp_integration.sh
   ```

3. **Test direct tool calls:**
   ```bash
   node test_direct_tool_call.js
   ```

### Expected Test Results

All tests should pass with output similar to:
- ✅ Health check endpoint working
- ✅ MCP initialize request working
- ✅ Tools list request working
- ✅ Google search and scrape tool working

## Session Management

The standalone server uses in-memory session management by default, which is suitable for local development. Sessions are automatically created and managed without requiring DynamoDB.

## Troubleshooting

### Common Issues

1. **Import errors:** Ensure the virtual environment is activated and all dependencies are installed
2. **AWS region errors:** Set the `AWS_REGION` environment variable before starting the server
3. **Google API errors:** Verify `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID` are correctly set
4. **Connection refused:** Ensure the standalone server is running on port 8000

### Debug Mode

The standalone server runs in debug mode by default, providing detailed logging for troubleshooting:
- Request/response logging
- Tool execution details
- Session management information
- Error stack traces

## Advantages of Standalone Mode

- **Faster development cycle:** No need to build and deploy Lambda functions
- **Direct debugging:** Full access to Python debugger and logging
- **Simplified testing:** Direct HTTP requests without API Gateway complexity
- **Local development:** Works without AWS infrastructure dependencies
- **Real-time changes:** Code changes take effect immediately without redeployment

## Production Deployment

For production use, deploy the MCP server using AWS SAM:
```bash
sam build --use-container
sam deploy
```

The standalone server is intended for development and testing purposes only.
