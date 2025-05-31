#!/bin/bash
set -e

echo "🐳 Lambda MCP Server Integration Test Runner"
echo "============================================="

CONTAINER_NAME="lambda-mcp-integration-test"
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

log_info "Starting Lambda container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $CONTAINER_PORT:8080 \
    -e AWS_DEFAULT_REGION=us-east-1 \
    -e AWS_ACCESS_KEY_ID=dummy \
    -e AWS_SECRET_ACCESS_KEY=dummy \
    -e MCP_SESSION_TABLE=test-sessions \
    -e GOOGLE_API_KEY=dummy-key-for-testing \
    -e GOOGLE_SEARCH_ENGINE_ID=dummy-cx-for-testing \
    $IMAGE_NAME

log_info "Waiting for container to be ready..."
sleep 5

if ! docker ps | grep -q $CONTAINER_NAME; then
    log_error "Container failed to start"
    docker logs $CONTAINER_NAME
    exit 1
fi

log_success "Container is running"

log_info "Waiting for Lambda runtime to initialize..."
sleep 3

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

log_info "Running integration tests..."
export LAMBDA_CONTAINER_URL="$LAMBDA_URL"

if python3 integration_tests.py; then
    log_success "All integration tests passed!"
    exit_code=0
else
    log_error "Some integration tests failed"
    exit_code=1
fi

if [ $exit_code -ne 0 ]; then
    log_info "Container logs for debugging:"
    docker logs $CONTAINER_NAME
fi

exit $exit_code
