# syntax=docker/dockerfile:1
# Multi-stage build for SyncContext MCP server
# Supports linux/amd64 and linux/arm64

# ── UV binary stage ──────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.5.21 AS uv

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Build directly in /app so the venv shebangs point to /app/.venv/bin/python
WORKDIR /app

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
COPY migrations/ ./migrations/
COPY README.md ./

RUN uv sync --frozen --no-dev

# Verify the entrypoint was created
RUN test -f /app/.venv/bin/synccontext || (echo "ERROR: synccontext entrypoint not found" && exit 1)

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="SyncContext" \
      org.opencontainers.image.description="Shared team memory MCP server with semantic search" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/infinity-ai-dev/SyncContext"

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/false --no-create-home appuser

WORKDIR /app

# Copy everything from builder (venv shebangs already point to /app/.venv/bin/python)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/core /app/core
COPY --from=builder --chown=appuser:appgroup /app/server /app/server
COPY --from=builder --chown=appuser:appgroup /app/migrations /app/migrations

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["synccontext"]
