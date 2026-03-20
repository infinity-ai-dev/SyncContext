# SyncContext — Setup Guide

## Self-Hosted Deployment

### Prerequisites
- Docker and Docker Compose
- A Gemini API key (free) — [Get one here](https://aistudio.google.com/apikey)

### Step 1: Clone and Configure

```bash
git clone https://github.com/infinity-ai-dev/SyncContext.git
cd SyncContext
cp .env.example .env
```

Edit `.env`:
```env
SYNCCONTEXT_PROJECT_TOKEN=my-team-project-2024
SYNCCONTEXT_GEMINI_API_KEY=AIza...your-key
```

> **Tip**: Generate a strong token with `openssl rand -hex 32`

### Step 2: Start Services

**With pgvector (default, recommended):**
```bash
docker compose up -d
```

**With Redis Stack:**
```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up -d
```

### Step 3: Connect Your MCP Client

#### Claude Code

Add to your project's `.mcp.json`:
```json
{
  "mcpServers": {
    "synccontext": {
      "command": "uv",
      "args": ["--directory", "/path/to/SyncContext", "run", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "my-team-project-2024",
        "SYNCCONTEXT_DATABASE_URL": "postgresql://synccontext:synccontext@localhost:5432/synccontext",
        "SYNCCONTEXT_GEMINI_API_KEY": "AIza...your-key"
      }
    }
  }
}
```

Or via Docker:
```json
{
  "mcpServers": {
    "synccontext": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/SyncContext/docker-compose.yml", "run", "--rm", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "my-team-project-2024",
        "SYNCCONTEXT_GEMINI_API_KEY": "AIza...your-key"
      }
    }
  }
}
```

#### Cursor / VS Code (Copilot)

Add the same MCP configuration to your editor's MCP settings file.

### Step 4: Verify

Ask your AI agent:
> "Use the get_project_context tool to check the SyncContext connection"

If connected, it should respond with the project summary.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNCCONTEXT_PROJECT_TOKEN` | **required** | Shared secret for team access. All members use the same token. |
| `SYNCCONTEXT_DATABASE_URL` | `postgresql://synccontext:password@localhost:5432/synccontext` | PostgreSQL connection string |
| `SYNCCONTEXT_VECTOR_STORE` | `pgvector` | Vector backend: `pgvector` or `redis` |
| `SYNCCONTEXT_REDIS_URL` | `redis://localhost:6379/0` | Redis connection (if using Redis backend) |
| `SYNCCONTEXT_EMBEDDING_PROVIDER` | `gemini` | Embedding model: `gemini`, `openai`, `ollama` |
| `SYNCCONTEXT_GEMINI_API_KEY` | — | Gemini API key (required if using Gemini) |
| `SYNCCONTEXT_OPENAI_API_KEY` | — | OpenAI API key (required if using OpenAI) |
| `SYNCCONTEXT_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `SYNCCONTEXT_OLLAMA_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `SYNCCONTEXT_TRANSPORT` | `stdio` | MCP transport: `stdio`, `sse`, `streamable-http` |
| `SYNCCONTEXT_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Embedding Provider Comparison

| Provider | Dimensions | Cost | Offline | Best For |
|----------|-----------|------|---------|----------|
| **Gemini** (default) | 768 | Free (1500 req/min) | No | Most teams |
| **OpenAI** | 1536 | $0.02/1M tokens | No | Higher precision |
| **Ollama** | 768 | Free | Yes | Air-gapped / privacy |

> **Warning**: Switching embedding providers after storing memories requires re-embedding all content (vector dimensions differ). Plan your provider choice before production use.

---

## Multi-Team Setup

Each team/project uses its own `PROJECT_TOKEN`. You can run multiple SyncContext instances on the same PostgreSQL database — memories are isolated by token.

```bash
# Team A
SYNCCONTEXT_PROJECT_TOKEN=team-alpha-frontend

# Team B
SYNCCONTEXT_PROJECT_TOKEN=team-beta-backend
```

Both teams share the same PostgreSQL but see only their own memories.

---

## Troubleshooting

### "Connection refused" on PostgreSQL
```bash
docker compose ps  # Check if postgres is running
docker compose logs postgres  # Check for errors
```

### "Embedding provider error"
- **Gemini**: Verify your API key at https://aistudio.google.com/apikey
- **OpenAI**: Check billing at https://platform.openai.com/account/billing
- **Ollama**: Ensure `ollama serve` is running and the model is pulled: `ollama pull nomic-embed-text`

### "Vector dimension mismatch"
You switched embedding providers after storing data. Options:
1. Drop and recreate the `memory_vectors` table (loses search index, not data)
2. Re-embed all memories (run a migration script)
