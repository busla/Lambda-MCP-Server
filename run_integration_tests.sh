#!/bin/bash
set -e

echo "🐳 REAL Lambda MCP Server Integration Test Runner"
echo "================================================="
echo "⚠️  This script runs REAL integration tests with actual API calls"
echo "================================================="

if [ -z "$GOOGLE_API_KEY" ] || [ -z "$GOOGLE_SEARCH_ENGINE_ID" ]; then
    echo "❌ ERROR: Real integration tests require valid Google API credentials"
    echo "Please set the following environment variables:"
    echo "  export GOOGLE_API_KEY='your-google-api-key'"
    echo "  export GOOGLE_SEARCH_ENGINE_ID='your-search-engine-id'"
    echo ""
    echo "To get these credentials:"
    echo "1. Go to https://console.developers.google.com/"
    echo "2. Create a project and enable Custom Search JSON API"
    echo "3. Create API credentials (API key)"
    echo "4. Go to https://cse.google.com/ to create a Custom Search Engine"
    echo "5. Get the Search Engine ID from the control panel"
    exit 1
fi

echo "✅ Google API credentials found - proceeding with real integration tests"

CONTAINER_NAME="lambda-mcp-real-integration-test"
CONTAINER_PORT="9000"
IMAGE_NAME="lambda-mcp-server:latest"
LAMBDA_URL="http://localhost:${CONTAINER_PORT}/2015-03-31/functions/function/invocations"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

cleanup() {
    log_info "Cleaning up containers..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
}

trap cleanup EXIT

if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

log_info "Building Lambda container image..."
cd server-http-python-lambda
if docker build -t $IMAGE_NAME .; then
    log_success "Container image built successfully"
else
    log_error "Failed to build container image"
    exit 1
fi
cd ..

cleanup

log_info "Starting Lambda container with REAL API credentials..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $CONTAINER_PORT:8080 \
    -e AWS_DEFAULT_REGION=us-east-1 \
    -e AWS_ACCESS_KEY_ID=dummy \
    -e AWS_SECRET_ACCESS_KEY=dummy \
    -e MCP_SESSION_TABLE=test-sessions \
    -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
    -e GOOGLE_SEARCH_ENGINE_ID="$GOOGLE_SEARCH_ENGINE_ID" \
    $IMAGE_NAME

log_info "Waiting for container to be ready..."
sleep 8

if ! docker ps | grep -q $CONTAINER_NAME; then
    log_error "Container failed to start"
    docker logs $CONTAINER_NAME
    exit 1
fi

log_success "Container is running"

log_info "Waiting for Lambda runtime to initialize..."
sleep 5

log_info "Testing basic connectivity..."
max_retries=10
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s -f "$LAMBDA_URL" >/dev/null 2>&1; then
        log_success "Lambda endpoint is responding"
        break
    else
        retry_count=$((retry_count + 1))
        log_warning "Attempt $retry_count/$max_retries - Lambda not ready yet, waiting..."
        sleep 2
    fi
done

if [ $retry_count -eq $max_retries ]; then
    log_error "Lambda endpoint not responding after $max_retries attempts"
    log_info "Container logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi

log_info "Running REAL integration tests with actual API calls..."
export LAMBDA_CONTAINER_URL="$LAMBDA_URL"

if python3 integration_tests.py; then
    log_success "All REAL integration tests passed!"
    log_success "Lambda MCP Server is fully functional with real Google API integration!"
    exit_code=0
else
    log_error "Some real integration tests failed"
    log_info "Container logs for debugging:"
    docker logs $CONTAINER_NAME
    exit_code=1
fi

exit $exit_code
