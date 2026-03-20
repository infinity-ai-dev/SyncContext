# SyncContext

**Shared team memory for AI coding agents.** Sync context, decisions, and knowledge across your entire team via the [Model Context Protocol](https://modelcontextprotocol.io/).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

---

## The Problem

AI coding agents (Claude Code, Cursor, Windsurf) each maintain **isolated context**. Developer A's agent knows nothing about Developer B's decisions. This leads to:

- Conflicting architecture decisions across team members
- Repeated mistakes and lost institutional knowledge
- Painful onboarding for new developers
- No shared understanding between frontend, backend, and infra

## The Solution

SyncContext provides a **shared semantic memory layer** that connects your team's AI agents. One token, one shared brain, unlimited team members.

```
Developer A (Frontend) ──► saves: "Button uses Tailwind, prop X is required"
Developer B (Backend)  ──► searches: "frontend patterns" ──► gets full context
Developer C (New hire) ──► runs: get_project_context ──► instant onboarding
```

---

## Quick Start

### Self-Hosted with Docker (recommended)

```bash
git clone https://github.com/infinity-ai-dev/SyncContext.git
cd SyncContext
cp .env.example .env
# Edit .env: set SYNCCONTEXT_PROJECT_TOKEN and SYNCCONTEXT_GEMINI_API_KEY

docker compose up -d
```

### Without Docker

```bash
# Requires PostgreSQL 15+ with pgvector extension
cp .env.example .env
# Edit .env with your settings

uv sync
uv run synccontext
```

### With Redis (alternative vector store)

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up -d
```

---

## Connect Your MCP Client

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "synccontext": {
      "command": "uv",
      "args": ["--directory", "/path/to/SyncContext", "run", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "my-team-token",
        "SYNCCONTEXT_DATABASE_URL": "postgresql://synccontext:synccontext@localhost:5432/synccontext",
        "SYNCCONTEXT_GEMINI_API_KEY": "your-gemini-key"
      }
    }
  }
}
```

### Docker-based

```json
{
  "mcpServers": {
    "synccontext": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/SyncContext/docker-compose.yml", "run", "--rm", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "my-team-token",
        "SYNCCONTEXT_GEMINI_API_KEY": "your-gemini-key"
      }
    }
  }
}
```

---

## Tools

| Tool | Description |
|------|-------------|
| `save_memory` | Store decisions, patterns, bugs, conventions with metadata |
| `search_memories` | Semantic search across all team knowledge |
| `list_memories` | Browse recent memories with tag/author/type filters |
| `get_memory` | Retrieve a specific memory by UUID |
| `update_memory` | Update content (auto re-embeds if changed) |
| `delete_memory` | Remove a specific memory |
| `get_project_context` | Full project summary for onboarding |
| `list_tags` | Discover all knowledge categories with counts |
| `list_contributors` | See who's contributing knowledge |
| `search_by_file` | Find context about specific files |
| `bulk_save_memories` | Import multiple memories at once |
| `find_similar` | Discover related memories by similarity |

---

## Architecture

```
┌─────────────────────────────────┐
│    Claude Code / Cursor / IDE   │
│         (MCP Client)            │
└──────────┬──────────────────────┘
           │ MCP Protocol (stdio/sse)
┌──────────▼──────────────────────┐
│      SyncContext MCP Server     │
│  ┌──────────┐  ┌──────────────┐ │
│  │ Embedding│  │   Memory     │ │
│  │ Provider │  │   Service    │ │
│  └──────────┘  └──────────────┘ │
└──────────┬──────────────────────┘
           │
     ┌─────┴──────┐
     │             │
┌────▼────┐  ┌────▼─────┐
│PostgreSQL│  │  Redis   │
│+pgvector │  │  Stack   │
└─────────┘  └──────────┘
```

### Embedding Providers

| Provider | Dimensions | Cost | Offline |
|----------|-----------|------|---------|
| **Gemini** (default) | 768 | Free (1500 req/min) | No |
| **OpenAI** | 1536 | $0.02/1M tokens | No |
| **Ollama** | 768 | Free | Yes |

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
| `PROJECT_TOKEN` | **required** | Shared team token (namespace for memories) |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `VECTOR_STORE` | `pgvector` | `pgvector` or `redis` |
| `EMBEDDING_PROVIDER` | `gemini` | `gemini`, `openai`, or `ollama` |
| `GEMINI_API_KEY` | — | Required if using Gemini |
| `OPENAI_API_KEY` | — | Required if using OpenAI |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `TRANSPORT` | `stdio` | `stdio`, `sse`, or `streamable-http` |

---

## Development

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check core/ server/

# Run locally
uv run synccontext
```

---

## Multi-Team Setup

Each team uses its own `PROJECT_TOKEN`. Multiple teams can share the same PostgreSQL — memories are isolated by token.

```env
# Team Frontend
SYNCCONTEXT_PROJECT_TOKEN=project-alpha-frontend

# Team Backend
SYNCCONTEXT_PROJECT_TOKEN=project-alpha-backend
```

---

## Docker Images

Multi-arch images available for `linux/amd64` and `linux/arm64`:

```bash
docker pull ghcr.io/infinity-ai-dev/synccontext:latest
```

---

## Roadmap

- [x] Core MCP server with 12 tools
- [x] pgvector + Redis backends
- [x] Gemini / OpenAI / Ollama embeddings
- [x] Docker multi-arch builds
- [ ] SyncContext Cloud (managed SaaS)
- [ ] Web dashboard for memory management
- [ ] Webhook notifications on memory changes
- [ ] Memory expiration / archival policies
- [ ] RAG integration (index entire codebases)

## License

MIT — see [LICENSE](LICENSE) for details.
