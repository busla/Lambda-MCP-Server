#!/usr/bin/env python3
"""Test script to verify standalone MCP server can be imported successfully"""
import os
import sys

os.environ['AWS_REGION'] = 'us-west-2'
os.environ['AWS_ACCESS_KEY_ID'] = 'test-key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret'

try:
    from standalone_server import mcp_server
    print('✅ MCP server imported successfully')
    print(f'✅ Server name: {mcp_server.name}')
    print(f'✅ Server version: {mcp_server.version}')
    print(f'✅ Available tools: {list(mcp_server.tools.keys())}')
    print('✅ Standalone server creation completed successfully')
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
