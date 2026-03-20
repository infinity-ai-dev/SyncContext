# SyncContext — MCPize Marketplace Listing

## Name
SyncContext

## Tagline
Shared team memory for AI coding agents — sync context across your entire team.

## Category
Developer Tools / Productivity

## Description

SyncContext is an MCP server that gives your team a **shared brain**. When one developer saves an architecture decision, a bug fix pattern, or a coding convention — every other team member's AI agent instantly has access to it.

### The Problem
AI coding agents (Claude Code, Cursor, Windsurf) each maintain their own isolated context. Developer A's Claude knows nothing about what Developer B's Claude learned. This leads to:
- Conflicting architecture decisions
- Repeated mistakes across team members
- Lost institutional knowledge when developers switch tasks
- Painful onboarding for new team members

### The Solution
SyncContext provides a shared semantic memory layer that sits between your team and your AI agents via the Model Context Protocol (MCP). One token, one shared brain, unlimited team members.

### How It Works
1. **Install**: `docker compose up -d` (self-hosted) or connect to SyncContext Cloud
2. **Configure**: Add the MCP server to your Claude Code / Cursor settings
3. **Use**: Your AI agent automatically reads and writes shared memories

```
Developer A (Frontend) → saves: "Button component uses Tailwind, prop X is required"
Developer B (Backend)  → searches: "frontend component patterns" → gets full context
Developer C (New hire) → runs: get_project_context → instant onboarding
```

## Features

### 12 MCP Tools
| Tool | What it does |
|------|-------------|
| `save_memory` | Store decisions, patterns, bugs, conventions |
| `search_memories` | Semantic search across all team knowledge |
| `list_memories` | Browse recent memories with filters |
| `get_memory` | Retrieve a specific memory by ID |
| `update_memory` | Update content (auto re-embeds) |
| `delete_memory` | Remove outdated memories |
| `get_project_context` | Full project summary for onboarding |
| `list_tags` | Discover all knowledge categories |
| `list_contributors` | See who's contributing knowledge |
| `search_by_file` | Find context about specific files |
| `bulk_save_memories` | Import multiple memories at once |
| `find_similar` | Discover related memories |

### Embedding Providers
- **Gemini** (default, free) — text-embedding-004, 768 dimensions
- **OpenAI** — text-embedding-3-small, 1536 dimensions
- **Ollama** — nomic-embed-text, fully offline, 768 dimensions

### Vector Store Backends
- **pgvector** (default) — PostgreSQL extension, battle-tested, relational queries
- **Redis Stack** — In-memory, sub-millisecond search, with persistence (AOF)

### Deployment Options
- **Self-hosted** (Free) — Docker Compose, your infrastructure, your data
- **SyncContext Cloud** (Paid) — Managed service, zero ops, instant setup

## Pricing

### Self-Hosted (Free)
- Full feature set
- Unlimited memories
- Unlimited team members
- Your infrastructure
- Community support

### Cloud (Coming Soon)
- Managed PostgreSQL + pgvector
- Dashboard & analytics
- Automatic backups
- SLA guarantee
- Priority support
- Starting at $29/month per project

## Quick Start

### Self-Hosted with Docker
```bash
git clone https://github.com/infinity-ai-dev/SyncContext.git
cd SyncContext
cp .env.example .env
# Set SYNCCONTEXT_PROJECT_TOKEN and SYNCCONTEXT_GEMINI_API_KEY
docker compose up -d
```

### MCP Client Configuration
```json
{
  "mcpServers": {
    "synccontext": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/SyncContext/docker-compose.yml", "run", "--rm", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "your-team-token",
        "SYNCCONTEXT_GEMINI_API_KEY": "your-key"
      }
    }
  }
}
```

## Tech Stack
- Python 3.12+
- MCP SDK (FastMCP)
- PostgreSQL 17 + pgvector
- Redis Stack (optional)
- Docker multi-arch (amd64 + arm64)

## Links
- GitHub: https://github.com/infinity-ai-dev/SyncContext
- License: MIT (self-hosted core)

## Tags
mcp, memory, semantic-search, team-collaboration, ai-agents, claude-code, cursor, pgvector, embeddings
