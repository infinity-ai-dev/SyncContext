import logging
from contextlib import asynccontextmanager

import asyncpg
from mcp.server.fastmcp import FastMCP

from core.auth import TokenAuth
from core.embeddings import create_embedding_provider
from core.memory import MemoryService
from core.migrations import run_migrations
from core.search import SearchService
from core.vectorstore import create_vector_store
from server.config import Settings
from server.tools import register_tools

_settings = Settings()


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize all resources on startup, cleanup on shutdown."""
    settings = _settings

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger = logging.getLogger("synccontext")

    logger.info("=" * 50)
    logger.info("SyncContext MCP Server — Starting up")
    logger.info("=" * 50)
    logger.info(f"Transport: {settings.transport}")
    if settings.transport != "stdio":
        logger.info(f"Listening: {settings.host}:{settings.port}")

    # 1. Connect to PostgreSQL
    logger.info("Connecting to PostgreSQL...")
    pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    version = await pool.fetchval("SELECT version()")
    logger.info(f"Database connected — {version.split(',')[0]}")

    # 2. Run migrations
    logger.info("Executing migrations...")
    await run_migrations(pool)

    # 3. Initialize auth and resolve project
    logger.info("Initializing authentication...")
    token_auth = TokenAuth(pool)
    project = await token_auth.ensure_project(
        token=settings.project_token,
        name="Default Project",
    )
    logger.info(f"Active project: {project.name} (id={project.id})")
    logger.info(f"Project token: {project.token[:12]}...{project.token[-4:]}")

    # 4. Initialize embedding provider (auto-detect from credentials)
    provider = settings.resolve_embedding_provider()
    if settings.embedding_provider == "auto":
        logger.info(f"Embedding provider auto-detected: {provider}")
    else:
        logger.info(f"Embedding provider: {provider}")

    embedding_kwargs = {}
    if provider == "gemini":
        embedding_kwargs["api_key"] = settings.gemini_api_key
    elif provider == "openai":
        embedding_kwargs["api_key"] = settings.openai_api_key
    elif provider == "ollama":
        embedding_kwargs["base_url"] = settings.ollama_base_url
        embedding_kwargs["model"] = settings.ollama_model
        logger.info(f"Ollama endpoint: {settings.ollama_base_url} (model={settings.ollama_model})")

    embeddings = create_embedding_provider(provider, **embedding_kwargs)
    logger.info(f"Embedding provider ready — dimension={embeddings.dimension}")

    # 5. Initialize vector store
    logger.info(f"Initializing vector store: {settings.vector_store}...")
    vector_store = create_vector_store(
        settings.vector_store,
        database_url=settings.database_url,
        redis_url=settings.redis_url,
        dimension=embeddings.dimension,
    )
    await vector_store.initialize()
    logger.info(f"Vector store ready — backend={settings.vector_store}")

    # 6. Create services scoped to the active project
    memory_service = MemoryService(pool, vector_store, embeddings, project.id)
    search_service = SearchService(memory_service, vector_store, embeddings, project.id)

    logger.info("=" * 50)
    logger.info("SyncContext ready — all systems operational")
    logger.info("=" * 50)

    # 7. Yield context to tool handlers
    yield {
        "memory_service": memory_service,
        "search_service": search_service,
        "token_auth": token_auth,
        "admin_token": settings.admin_token,
        "db_pool": pool,
    }

    # 8. Cleanup
    logger.info("Shutting down SyncContext...")
    await embeddings.close()
    await vector_store.close()
    await pool.close()
    logger.info("Shutdown complete — goodbye")


mcp = FastMCP(
    name="SyncContext",
    instructions=(
        "SyncContext is a shared team memory server. "
        "Use save_memory to store architecture decisions, patterns, bugs, and conventions. "
        "Use search_memories to find relevant context from team members. "
        "Use get_project_context when onboarding or needing an overview."
    ),
    host=_settings.host,
    port=_settings.port,
    lifespan=lifespan,
)

register_tools(mcp)


def main():
    mcp.run(transport=_settings.transport)


if __name__ == "__main__":
    main()
