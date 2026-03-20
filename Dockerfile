# syntax=docker/dockerfile:1
# Multi-stage build for SyncContext MCP server
# Supports linux/amd64 and linux/arm64

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5.21

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

ARG UV_VERSION

WORKDIR /build

# Install uv from the official image (single binary, no pip install needed)
COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /usr/local/bin/uv

# Configure uv: disable version check noise, keep bytecode for faster startup
ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    UV_LINK_MODE=copy

# Install dependencies first for layer-cache efficiency.
# uv.lock is copied separately so that source changes don't invalidate this layer.
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

# Copy source packages and install the project itself (no deps re-resolution)
COPY core/ ./core/
COPY server/ ./server/

RUN uv sync --frozen --no-dev

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="SyncContext" \
      org.opencontainers.image.description="Shared team memory MCP server with semantic search" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/naive/mcp-rat"

# Create a non-root user before copying any files
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/false --no-create-home appuser

WORKDIR /app

# Copy the complete virtualenv from the builder (includes installed packages + project)
COPY --from=builder --chown=appuser:appgroup /build/.venv /app/.venv

# Copy source that was installed as editable / in-tree references
COPY --from=builder --chown=appuser:appgroup /build/core  /app/core
COPY --from=builder --chown=appuser:appgroup /build/server /app/server

# Activate the venv for all subsequent RUN/CMD/ENTRYPOINT calls
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

# SyncContext runs as an MCP server over stdio by default.
# Override SYNCCONTEXT_TRANSPORT=sse or streamable-http to expose an HTTP endpoint.
ENTRYPOINT ["synccontext"]
