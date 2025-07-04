# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building and uv
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install only the dependencies (not the local package)
RUN uv sync --frozen --no-dev --no-install-project

# Multi-stage build for smaller final image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install only runtime dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

# Copy the entire uv environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Create non-root user first
RUN groupadd -r openstates && useradd -r -g openstates -m openstates

# Create source directory structure
WORKDIR /src

# Copy application code into /src/app directory
COPY --chown=openstates:openstates app /src/app

# Ensure proper ownership
RUN chown -R openstates:openstates /src

# Switch to non-root user
USER openstates

# Set Python-related environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/src \
    PATH="/app/.venv/bin:$PATH" \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    API_BASE_URL=https://v3.openstates.org

# Expose port (optional - not needed for stdio but doesn't hurt)
EXPOSE 8775

# Labels for container metadata
LABEL org.opencontainers.image.title="OpenStates MCP Server" \
      org.opencontainers.image.description="MCP server for OpenStates" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/Travis-Prall/open-states-mcp"

# No HEALTHCHECK needed for stdio transport

# No CMD needed - docker-compose.yml handles the command
