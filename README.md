# SyncContext

**Shared team memory for AI coding agents.** Sync context, decisions, and knowledge across your entire team via the [Model Context Protocol](https://modelcontextprotocol.io/).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/docker/v/infinitytools/synccontext?label=Docker%20Hub)](https://hub.docker.com/r/infinitytools/synccontext)

---

## The Problem

AI coding agents (Claude Code, Cursor, Windsurf) each maintain **isolated context**. Developer A's agent knows nothing about Developer B's decisions. This leads to:

- Conflicting architecture decisions across team members
- Repeated mistakes and lost institutional knowledge
- Painful onboarding for new developers
- No shared understanding between frontend, backend, and infra

## The Solution

SyncContext provides a **shared semantic memory layer** that connects your team's AI agents. One token per project, shared brain, unlimited team members.

```
Developer A (Frontend) --> saves: "Button uses Tailwind, prop X is required"
Developer B (Backend)  --> searches: "frontend patterns" --> gets full context
Developer C (New hire) --> runs: get_project_context --> instant onboarding
```

---

## How It Works

1. Your team deploys SyncContext (self-hosted or cloud)
2. Each developer adds the server URL + their project token to their MCP client
3. On first connection, the project is auto-created in the database
4. AI agents read and write shared memories scoped to the project

```
MCP Client (Claude Code, Cursor)
    │
    │  Authorization: Bearer <project-token>
    │  X-Project-Name: "My Project"
    │
    ▼
SyncContext Server (HTTPS)
    │
    ├── New token? → Auto-create project in DB
    ├── Known token? → Load existing project
    │
    ▼
PostgreSQL + pgvector (semantic search)
```

---

## Quick Start

### Option 1: Connect to a hosted instance

Add to your `.mcp.json` (Claude Code) or MCP settings (Cursor):

```json
{
  "mcpServers": {
    "synccontext": {
      "url": "https://your-synccontext-server.com/mcp",
      "headers": {
        "Authorization": "Bearer your-project-token",
        "X-Project-Name": "My Project"
      }
    }
  }
}
```

That's it. The project is auto-created on first connection.

### Option 2: Self-hosted with Docker

```bash
git clone https://github.com/infinity-ai-dev/SyncContext.git
cd SyncContext
cp .env.example .env
# Edit .env: set SYNCCONTEXT_GEMINI_API_KEY

docker compose up -d
```

### Option 3: Local development (stdio)

```bash
# Requires PostgreSQL with pgvector
uv sync
uv run synccontext
```

---

## MCP Client Configuration

### Cloud / HTTP mode (recommended)

Works with any MCP client that supports HTTP transport:

```json
{
  "mcpServers": {
    "synccontext": {
      "url": "https://your-server.com/mcp",
      "headers": {
        "Authorization": "Bearer your-project-token",
        "X-Project-Name": "My Project"
      }
    }
  }
}
```

### Local / stdio mode

For local development with a direct database connection:

```json
{
  "mcpServers": {
    "synccontext": {
      "command": "uv",
      "args": ["--directory", "/path/to/SyncContext", "run", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "my-team-token",
        "SYNCCONTEXT_DATABASE_URL": "postgresql://user:pass@localhost:5432/synccontext",
        "SYNCCONTEXT_GEMINI_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Tools (14 total)

### Memory Management
| Tool | Description |
|------|-------------|
| `save_memory` | Store decisions, patterns, bugs, conventions with metadata |
| `get_memory` | Retrieve a specific memory by UUID |
| `update_memory` | Update content (auto re-embeds if changed) |
| `delete_memory` | Remove a specific memory |
| `bulk_save_memories` | Import multiple memories at once |

### Search & Discovery
| Tool | Description |
|------|-------------|
| `search_memories` | Semantic search across all team knowledge |
| `search_by_file` | Find context about specific files |
| `find_similar` | Discover related memories by similarity |
| `list_memories` | Browse recent memories with filters |

### Project Overview
| Tool | Description |
|------|-------------|
| `get_project_context` | Full project summary (onboarding) |
| `list_tags` | All knowledge categories with counts |
| `list_contributors` | Who's contributing knowledge |

### Admin
| Tool | Description |
|------|-------------|
| `create_project` | Create a new project (admin token required) |
| `list_projects` | List all registered projects (admin token required) |

---

## Architecture

```
┌─────────────────────────────────────┐
│  Claude Code / Cursor / Windsurf    │
│           (MCP Client)              │
└──────────┬──────────────────────────┘
           │ HTTPS + Bearer Token
┌──────────▼──────────────────────────┐
│     SyncContext MCP Server          │
│  ┌────────────┐  ┌───────────────┐  │
│  │ Auth       │  │ Per-request   │  │
│  │ Middleware │──│ Project Scope │  │
│  └────────────┘  └───────────────┘  │
│  ┌────────────┐  ┌───────────────┐  │
│  │ Embedding  │  │ Memory +      │  │
│  │ Provider   │  │ Search Service│  │
│  └────────────┘  └───────────────┘  │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│  PostgreSQL + pgvector              │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ projects │  │ memories +       │ │
│  │ (tokens) │──│ memory_vectors   │ │
│  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────┘
```

### Multi-Project Isolation

Each project token maps to an isolated namespace. Multiple teams share the same server with full data isolation:

```
Token A ("sc_frontend...")  → Project "Frontend App"  → memories scoped to frontend
Token B ("sc_backend...")   → Project "Backend API"   → memories scoped to backend
Token C ("sc_infra...")     → Project "Infrastructure" → memories scoped to infra
```

### Embedding Providers (auto-detected)

| Provider | Dimensions | Cost | Offline | Detected by |
|----------|-----------|------|---------|-------------|
| **Gemini** | 768 | Free (1500 req/min) | No | `GEMINI_API_KEY` set |
| **OpenAI** | 1536 | $0.02/1M tokens | No | `OPENAI_API_KEY` set |
| **Ollama** | 768 | Free | Yes | `OLLAMA_BASE_URL` set |

### Vector Store Backends

| Backend | Best For | Persistence |
|---------|----------|-------------|
| **pgvector** (default) | Relational queries + vectors | Disk (durable) |
| **Redis Stack** | Sub-ms latency | AOF + volume (durable) |

---

## Configuration

All settings via environment variables (prefix `SYNCCONTEXT_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_TOKEN` | — | Default project token (stdio mode) |
| `ADMIN_TOKEN` | — | Admin token for create/list projects |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `VECTOR_STORE` | `pgvector` | `pgvector` or `redis` |
| `EMBEDDING_PROVIDER` | `auto` | `auto`, `gemini`, `openai`, or `ollama` |
| `GEMINI_API_KEY` | — | Gemini API key |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OLLAMA_BASE_URL` | — | Ollama server URL |
| `TRANSPORT` | `stdio` | `stdio`, `sse`, or `streamable-http` |
| `HOST` | `0.0.0.0` | HTTP bind address |
| `PORT` | `8080` | HTTP port |

---

## Self-Hosted Deployment (Docker Swarm)

### Prerequisites
- Docker Swarm with Traefik
- PostgreSQL with pgvector extension
- A domain pointing to your server

### 1. Prepare the database

```bash
# Install pgvector
docker exec $(docker ps -q -f name=postgres) bash -c \
  "apt-get update && apt-get install -y postgresql-16-pgvector"

# Create database + extensions
docker exec $(docker ps -q -f name=postgres) psql -U postgres -c "CREATE DATABASE synccontext"
docker exec $(docker ps -q -f name=postgres) psql -U postgres -d synccontext -c \
  'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "vector";'
```

### 2. Deploy the stack

See `deploy/swarm-stack.yml` for a complete Portainer-ready stack with Traefik integration.

### 3. Tables are created automatically

On first startup, the container runs migrations and creates all tables. Check logs to confirm.

---

## Development

```bash
uv sync --extra dev
uv run pytest tests/ -v     # 53 tests
uv run ruff check core/ server/
uv run synccontext           # run locally (stdio)
```

---

## Docker Images

Multi-arch images for `linux/amd64` and `linux/arm64`:

```bash
docker pull infinitytools/synccontext:latest
```

---

## Roadmap

- [x] 14 MCP tools (CRUD, search, bulk, admin)
- [x] pgvector + Redis backends
- [x] Gemini / OpenAI / Ollama embeddings (auto-detected)
- [x] Docker multi-arch builds (amd64 + arm64)
- [x] Multi-project with per-request auth
- [x] Auto-create projects from Bearer token
- [x] Auto-migrations on container startup
- [ ] SyncContext Cloud (managed SaaS)
- [ ] Web dashboard for memory management
- [ ] Webhook notifications on memory changes
- [ ] Memory expiration / archival policies
- [ ] RAG integration (index entire codebases)

## License

MIT — see [LICENSE](LICENSE) for details.
