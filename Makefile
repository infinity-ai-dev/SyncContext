.PHONY: dev test lint docker-build docker-up docker-up-redis docker-down docker-logs docker-pull

# ── Local development ─────────────────────────────────────────────────────────

dev:
	uv run synccontext

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check core/ server/
	uv run ruff format --check core/ server/

format:
	uv run ruff format core/ server/

# ── Docker ────────────────────────────────────────────────────────────────────

docker-pull:
	docker pull ghcr.io/infinity-ai-dev/synccontext:latest

docker-up:
	docker compose up -d

docker-up-redis:
	docker compose --profile redis up -d

docker-down:
	docker compose --profile redis down

docker-logs:
	docker compose logs -f synccontext

docker-build:
	docker build -t synccontext:local .
