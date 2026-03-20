import logging
from contextlib import asynccontextmanager

import asyncpg
from mcp.server.fastmcp import FastMCP

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
    logger.info("Starting SyncContext MCP server...")
    logger.info(f"Transport: {settings.transport} | Host: {settings.host}:{settings.port}")

    # 1. Connect to PostgreSQL
    pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    logger.info("PostgreSQL connected")

    # 2. Run migrations
    await run_migrations(pool)
    logger.info("Migrations applied")

    # 3. Initialize embedding provider
    embedding_kwargs = {}
    if settings.embedding_provider == "gemini":
        embedding_kwargs["api_key"] = settings.gemini_api_key
    elif settings.embedding_provider == "openai":
        embedding_kwargs["api_key"] = settings.openai_api_key
    elif settings.embedding_provider == "ollama":
        embedding_kwargs["base_url"] = settings.ollama_base_url
        embedding_kwargs["model"] = settings.ollama_model

    embeddings = create_embedding_provider(settings.embedding_provider, **embedding_kwargs)
    logger.info(f"Embedding provider: {settings.embedding_provider} (dim={embeddings.dimension})")

    # 4. Initialize vector store
    vector_store = create_vector_store(
        settings.vector_store,
        database_url=settings.database_url,
        redis_url=settings.redis_url,
        dimension=embeddings.dimension,
    )
    await vector_store.initialize()
    logger.info(f"Vector store: {settings.vector_store}")

    # 5. Create services
    memory_service = MemoryService(pool, vector_store, embeddings, settings.project_token)
    search_service = SearchService(memory_service, vector_store, embeddings, settings.project_token)
    logger.info("SyncContext ready")

    # 6. Yield context to tool handlers
    yield {
        "memory_service": memory_service,
        "search_service": search_service,
        "db_pool": pool,
    }

    # 7. Cleanup
    logger.info("Shutting down SyncContext...")
    await embeddings.close()
    await vector_store.close()
    await pool.close()
    logger.info("Shutdown complete")


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
