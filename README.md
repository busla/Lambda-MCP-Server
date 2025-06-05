# MCP StreamableHttp Lambda Container

A serverless implementation of the Model Context Protocol (MCP) StreamableHttp server deployed as an AWS Lambda container using AWS SAM.

## Overview

This project packages an MCP StreamableHttp server as a containerized AWS Lambda function, enabling AI applications to interact with external tools and services through the MCP protocol. The implementation uses Python 3.13, UV package manager, and AWS SAM for infrastructure-as-code deployment.

## Features

- ✅ **StreamableHttp Protocol** - JSON responses (not Server-Sent Events)
- ✅ **AWS Lambda Container** - Serverless deployment with automatic scaling
- ✅ **Regional API Gateway** - Optimized for low latency
- ✅ **UV Package Manager** - Fast dependency management
- ✅ **Taskfile Automation** - All commands available via `task`
- ✅ **MCP Inspector Compatible** - CLI testing support
- ✅ **Example Tools** - Multiplication and notification stream tools

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed and running
- UV package manager installed
- Task (Taskfile) installed

### Setup and Deploy

```bash
# Setup Python environment and dependencies
task setup

# Build the Lambda container
task build

# Deploy to AWS
task deploy
```

## Available Tasks

### Development Tasks

```bash
# Setup UV environment and install dependencies
task setup

# Run local development server
task test-local

# Format and lint code
task format
task lint

# Validate SAM template
task validate
```

### Build Tasks

```bash
# Build for default architecture
task build

# Build for specific architectures
task build-x86
task build-arm64
```

### Deployment Tasks

```bash
# Deploy with auto-resolved S3 and ECR
task deploy

# Deploy for specific architectures
task deploy-x86
task deploy-arm64

# View deployment logs
task logs

# Delete CloudFormation stack
task delete
```

### Testing Tasks

```bash
# Test deployed Lambda endpoints
task test-deployed
task test-deployed-tools

# Test with MCP Inspector CLI
task test-inspector-npx

# Start local API Gateway for testing
task local-api
```

## MCP Tools

The server includes two example tools:

### 1. Multiplication Tool

Multiplies two numbers and returns the result.

**Usage:**
```bash
curl -X POST https://YOUR-API-GATEWAY-URL/prod/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "multiply",
      "arguments": {"a": 5, "b": 7}
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The result of 5 × 7 = 35"
      }
    ],
    "isError": false
  }
}
```

### 2. Notification Stream Tool

Sends configurable log messages at set intervals to demonstrate streaming capabilities.

**Usage:**
```bash
curl -X POST https://YOUR-API-GATEWAY-URL/prod/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "start-notification-stream",
      "arguments": {
        "interval": 1.0,
        "count": 3,
        "caller": "test-client"
      }
    }
  }'
```

## Testing with MCP Inspector

The project includes configuration for testing with the MCP Inspector CLI:

```bash
# Test using npx (no installation required)
task test-inspector-npx

# Or manually with npx
npx @modelcontextprotocol/inspector --config mcp_inspector_config.json
```

## Architecture

### Components

- **AWS Lambda Function** - Runs the MCP server using Mangum ASGI adapter
- **API Gateway** - Regional endpoint for HTTP requests
- **ECR Repository** - Stores the container image (auto-created by SAM)
- **CloudFormation Stack** - Infrastructure-as-code management

### Key Files

- `app/server.py` - MCP server implementation with tools
- `app/main.py` - Lambda handler and local development entry point
- `template.yaml` - SAM infrastructure definition
- `Dockerfile` - Multi-stage container build with UV
- `Taskfile.yaml` - Task automation definitions
- `pyproject.toml` - Python dependencies and project configuration

## Configuration

### Environment Variables

The Lambda function uses these environment variables:

- `AWS_REGION` - Deployment region (default: eu-central-1)
- `PYTHONPATH` - Set to `/var/task` for Lambda runtime

### SAM Configuration

The `samconfig.toml` file contains deployment settings:

- **Region**: eu-central-1
- **Architecture**: Configurable (x86_64 or arm64)
- **Resolve S3**: Automatic S3 bucket management
- **Resolve Image Repos**: Automatic ECR repository creation

## Development

### Local Development

```bash
# Run the server locally
task test-local

# The server will be available at http://127.0.0.1:3000
```

### Adding New Tools

1. Add your tool function to `app/server.py` in the `call_tool()` handler
2. Update the `list_tools()` function with your tool's schema
3. Test locally with `task test-local`
4. Deploy with `task deploy`

### Architecture Support

The project supports both x86_64 and ARM64 architectures:

```bash
# Build and deploy for ARM64 (cost-optimized)
task build-arm64
task deploy-arm64

# Build and deploy for x86_64 (compatibility)
task build-x86
task deploy-x86
```

## Troubleshooting

### Common Issues

1. **"Not Acceptable" Error**: Ensure your requests include both `application/json` and `text/event-stream` in the Accept header
2. **Build Failures**: Check Docker is running and you have sufficient disk space
3. **Deployment Failures**: Verify AWS credentials and permissions

### Viewing Logs

```bash
# Tail Lambda function logs
task logs

# View specific log groups in CloudWatch
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/mcp-lambda"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `task test-local`
5. Deploy and test with `task deploy && task test-deployed`
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Links

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [UV Package Manager](https://docs.astral.sh/uv/)
