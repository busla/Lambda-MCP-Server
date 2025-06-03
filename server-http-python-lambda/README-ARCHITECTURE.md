# Architecture Override Configuration

This document explains how to configure the Lambda-MCP-Server for different CPU architectures (x86_64 and ARM64).

## Configuration Files

### samconfig.toml
The `samconfig.toml` file provides architecture-specific build profiles:

- **x86_64 profile**: Uses default Lambda Python base image
- **arm64 profile**: Uses ARM64-specific build image (experimental)

### template.yaml
The SAM template now includes an `Architecture` parameter that can be overridden:

```yaml
Parameters:
  Architecture:
    Type: String
    Default: x86_64
    AllowedValues:
      - x86_64
      - arm64
    Description: "Lambda function architecture"
```

## Usage

### Building for x86_64 (Recommended)
```bash
sam build --config-env x86_64
sam local start-api --config-env x86_64
```

### Building for ARM64 (Experimental)
```bash
sam build --config-env arm64
sam local start-api --config-env arm64
```

## Platform Compatibility

### ✅ x86_64 (Intel/AMD)
- **Status**: Fully supported
- **Local Development**: Works on all platforms
- **AWS Deployment**: Full compatibility

### ⚠️ ARM64 (Apple Silicon/ARM)
- **Status**: Experimental
- **Local Development**: May encounter "exec format error" on non-ARM hosts
- **AWS Deployment**: Supported by AWS Lambda
- **Recommendation**: Use x86_64 for local development, ARM64 for production if needed

## Troubleshooting

### macOS ARM (M1/M2) Issues
If you encounter Docker build errors on macOS ARM:

1. Use the x86_64 profile for local development:
   ```bash
   sam build --config-env x86_64
   ```

2. For production ARM64 deployment, build on ARM64 infrastructure or use AWS CodeBuild

### "exec format error"
This error occurs when trying to run ARM64 containers on x86_64 hosts. Solutions:
- Use x86_64 profile for local development
- Use Docker BuildKit with platform specification
- Build on matching architecture infrastructure

## Testing

Use the provided test script to verify functionality:
```bash
./test-mcp-server.sh
```

This script tests the google_search_and_scrape tool with various configurations.
