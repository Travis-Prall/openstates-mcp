# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder
# Resolve and install only the runtime dependencies into a virtualenv.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS builder

# uv is copied from the official image (no pip bootstrap, no extra system deps).
COPY --from=ghcr.io/astral-sh/uv:0.12.12@sha256:73d2665b478d8fa2de1cf105c6841f8e9cb6b09e568fc7700440c09f8fcd7ac4 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependency manifests first: this layer only rebuilds when they change.
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: runtime
# Same base digest as the builder so the virtualenv's symlinks stay valid.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS runtime

ARG APP_VERSION=0.0.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/src \
    PATH="/app/.venv/bin:$PATH" \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8797 \
    OPENSTATES_LOG_LEVEL=INFO \
    LOG_DIR=/tmp/logs

# Non-root runtime account plus the directories it must own.
RUN groupadd --system --gid 1001 openstates \
    && useradd --system --uid 1001 --gid openstates --no-create-home \
       --shell /usr/sbin/nologin openstates \
    && install -d --owner openstates --group openstates /src /tmp/logs

# Dependencies, package metadata (version lookup) and application source.
# Everything is root-owned and world-readable; nothing is written at runtime.
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml /app/pyproject.toml
WORKDIR /src
COPY pyproject.toml ./pyproject.toml
COPY --chown=openstates:openstates app ./app

USER openstates

# Streamable HTTP endpoint. The health probe below is unauthenticated.
EXPOSE 8797
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('MCP_PORT', '8797') + '/healthz', timeout=4).read()"]

LABEL org.opencontainers.image.title="OpenStates MCP Server" \
      org.opencontainers.image.description="MCP server exposing OpenStates legislative data" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/Travis-Prall/open-states-mcp" \
      org.opencontainers.image.licenses="MIT"

# Exec form so the server receives SIGTERM directly and shuts down gracefully.
CMD ["python", "-m", "app"]

