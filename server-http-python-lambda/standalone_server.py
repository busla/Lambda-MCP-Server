#!/usr/bin/env python3
"""
Standalone MCP Server - Extract MCP functionality from Lambda handler
to run as an independent HTTP server for direct TypeScript client communication.
"""
import sys
import os
import json
import logging
from flask import Flask, request, jsonify
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from app import mcp_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def lambda_event_from_flask_request(flask_request) -> Dict[str, Any]:
    """Convert Flask request to Lambda event format for MCP server compatibility"""
    return {
        "httpMethod": flask_request.method,
        "headers": dict(flask_request.headers),
        "body": flask_request.get_data(as_text=True),
        "queryStringParameters": dict(flask_request.args) if flask_request.args else None,
        "pathParameters": None,
        "requestContext": {
            "requestId": "standalone-request",
            "stage": "local"
        }
    }

def lambda_response_to_flask_response(lambda_response: Dict[str, Any]):
    """Convert Lambda response to direct JSON-RPC response"""
    status_code = lambda_response.get("statusCode", 200)
    body = lambda_response.get("body", "")
    headers = lambda_response.get("headers", {})
    
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
    
    response = jsonify(body)
    
    for key, value in headers.items():
        response.headers[key] = value
    
    return response, status_code

@app.route('/mcp', methods=['POST', 'DELETE'])
def mcp_endpoint():
    """Main MCP endpoint that handles JSON-RPC requests"""
    try:
        logger.info(f"Received {request.method} request to /mcp")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body: {request.get_data(as_text=True)}")
        
        lambda_event = lambda_event_from_flask_request(request)
        
        lambda_response = mcp_server.handle_request(lambda_event, None)
        
        flask_response, status_code = lambda_response_to_flask_response(lambda_response)
        
        logger.info(f"Returning response with status {status_code}")
        return flask_response, status_code
        
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}", exc_info=True)
        return jsonify({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "server": mcp_server.name,
        "version": mcp_server.version,
        "tools": list(mcp_server.tools.keys())
    })

if __name__ == '__main__':
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        logger.info(f"Loading environment from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    
    logger.info("Starting standalone MCP server...")
    logger.info(f"Available tools: {list(mcp_server.tools.keys())}")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
