# syntax=docker/dockerfile:1
# Multi-stage build for SyncContext MCP server
# Supports linux/amd64 and linux/arm64

# ── UV binary stage ──────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.5.21 AS uv

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    UV_LINK_MODE=copy

# Install dependencies first for layer-cache efficiency
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

# Copy source packages and install the project
COPY core/ ./core/
COPY server/ ./server/
COPY README.md ./

RUN uv sync --frozen --no-dev

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="SyncContext" \
      org.opencontainers.image.description="Shared team memory MCP server with semantic search" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/infinity-ai-dev/SyncContext"

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/false --no-create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /build/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /build/core  /app/core
COPY --from=builder --chown=appuser:appgroup /build/server /app/server

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["synccontext"]
