.PHONY: dev test lint docker-build docker-up docker-down docker-up-redis

# ── Local development ─────────────────────────────────────────────────────────

## dev: Run the MCP server locally with uv (stdio transport)
dev:
	uv run synccontext

## test: Run the test suite
test:
	uv run pytest tests/ -v

## lint: Run ruff linter and formatter check
lint:
	uv run ruff check core/ server/
	uv run ruff format --check core/ server/

# ── Docker ────────────────────────────────────────────────────────────────────

## docker-build: Build the Docker image locally (current platform)
docker-build:
	docker build -t synccontext:local .

## docker-up: Start SyncContext + Postgres with docker compose
docker-up:
	docker compose up --build

## docker-down: Stop and remove all containers
docker-down:
	docker compose down

## docker-up-redis: Start SyncContext + Postgres + Redis (Redis vector store)
docker-up-redis:
	docker compose -f docker-compose.yml -f docker-compose.redis.yml up --build
