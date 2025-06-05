# Build argument for architecture support
ARG ARCHITECTURE=x86_64

FROM public.ecr.aws/lambda/python:3.13 AS builder

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.7.11 /uv /usr/local/bin/uv

# Enable bytecode compilation, to improve cold-start performance.
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer.
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching.
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY uv.lock pyproject.toml ./

# Bundle the dependencies into the Lambda task root via `uv pip install --target`.
RUN uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

FROM public.ecr.aws/lambda/python:3.13

# Copy the runtime dependencies from the builder stage.
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the application code.
COPY ./app ${LAMBDA_TASK_ROOT}/app

# Set the AWS Lambda handler.
CMD ["app.main.lambda_handler"]
