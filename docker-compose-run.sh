#!/bin/bash

set -e

echo "🚀 Starting MCP Server and Client with Docker Compose..."

if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your actual credentials before running again."
    exit 1
fi

set -a
source .env
set +a

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ "$AWS_ACCESS_KEY_ID" = "your_aws_access_key_id" ]; then
    echo "🔑 Getting AWS credentials from current session..."
    
    CREDS=$(aws configure export-credentials 2>/dev/null || echo "")
    if [ -n "$CREDS" ]; then
        export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
        export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
        export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')
        echo "✅ AWS credentials loaded from current session"
    else
        echo "❌ Failed to get AWS credentials. Please configure AWS CLI or set credentials in .env"
        exit 1
    fi
fi

if [ -z "$AWS_REGION" ] || [ "$AWS_REGION" = "us-west-2" ]; then
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "")
    if [ -z "$AWS_REGION" ]; then
        AWS_REGION="${AWS_DEFAULT_REGION:-us-west-2}"
    fi
    export AWS_REGION
    echo "✅ Using AWS region: $AWS_REGION"
fi

if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your_google_api_key" ]; then
    echo "❌ GOOGLE_API_KEY not set in .env file"
    exit 1
fi

if [ -z "$GOOGLE_SEARCH_ENGINE_ID" ] || [ "$GOOGLE_SEARCH_ENGINE_ID" = "your_google_search_engine_id" ]; then
    echo "❌ GOOGLE_SEARCH_ENGINE_ID not set in .env file"
    exit 1
fi

if [ -z "$MCP_AUTH_TOKEN" ] || [ "$MCP_AUTH_TOKEN" = "your_mcp_auth_token" ]; then
    echo "❌ MCP_AUTH_TOKEN not set in .env file"
    exit 1
fi

echo "🏗️  Building and starting services..."
docker-compose up --build

echo "🎉 Docker Compose setup complete!"
