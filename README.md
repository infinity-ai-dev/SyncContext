# SyncContext

Shared team memory MCP server with semantic search. Allows multiple developers using Claude Code (or any MCP client) to share context, decisions, and knowledge across a project.

## Quick Start (Self-Hosted)

### With Docker (recommended)

```bash
cp .env.example .env
# Edit .env with your PROJECT_TOKEN and GEMINI_API_KEY

docker compose up -d
```

### Without Docker

```bash
# Requires PostgreSQL with pgvector extension
cp .env.example .env
# Edit .env with your settings

uv sync
uv run synccontext
```

## MCP Client Configuration

### Claude Code

Add to your project's `.mcp.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "synccontext": {
      "command": "uv",
      "args": ["--directory", "/path/to/MCP-RAT", "run", "synccontext"],
      "env": {
        "SYNCCONTEXT_PROJECT_TOKEN": "your-team-token",
        "SYNCCONTEXT_DATABASE_URL": "postgresql://...",
        "SYNCCONTEXT_GEMINI_API_KEY": "your-key"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `save_memory` | Save a memory with metadata (author, tags, file) |
| `search_memories` | Semantic search across team memories |
| `list_memories` | List recent project memories |
| `delete_memory` | Remove a specific memory |
| `update_memory` | Update an existing memory |
| `get_project_context` | Get project knowledge base summary |

## Configuration

All settings via environment variables (prefix `SYNCCONTEXT_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_TOKEN` | required | Shared team token |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `VECTOR_STORE` | `pgvector` | `pgvector` or `redis` |
| `EMBEDDING_PROVIDER` | `gemini` | `gemini`, `openai`, or `ollama` |

## License

MIT
