import logging
from contextlib import asynccontextmanager

import asyncpg
from mcp.server.fastmcp import FastMCP

from core.auth import TokenAuth
from core.db import connection_kwargs_from_url, redact_database_url
from core.embeddings import create_embedding_provider
from core.migrations import run_migrations
from core.vectorstore import create_vector_store
from server.config import Settings
from server.tools import register_tools

_settings = Settings()


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize shared resources on startup, cleanup on shutdown."""
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
    pool, runtime_database_url = await _create_database_pool(settings, logger)
    version = await pool.fetchval("SELECT version()")
    logger.info(f"Database connected — {version.split(',')[0]}")

    # 2. Run migrations
    migration_database_url = settings.resolve_migration_url(runtime_database_url)
    if migration_database_url == runtime_database_url:
        logger.info("Executing migrations...")
        await run_migrations(pool)
    else:
        logger.info("Executing migrations via direct database connection...")
        migration_pool = await asyncpg.create_pool(
            migration_database_url,
            min_size=1,
            max_size=2,
            **connection_kwargs_from_url(migration_database_url),
        )
        try:
            await run_migrations(migration_pool)
        finally:
            await migration_pool.close()

    # 3. Initialize auth
    logger.info("Initializing authentication...")
    token_auth = TokenAuth(pool)

    # When a shared project token is configured, ensure it exists on startup.
    if settings.has_shared_project_token():
        project = await token_auth.ensure_project(
            token=settings.project_token,
            name=settings.project_name,
        )
        if settings.transport == "stdio":
            logger.info(f"Stdio project: {project.name} (id={project.id})")
        else:
            logger.info(f"Shared HTTP project: {project.name} (id={project.id})")

    # 4. Initialize embedding provider
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
        database_url=runtime_database_url,
        redis_url=settings.redis_url,
        dimension=embeddings.dimension,
        direct_url=migration_database_url,
    )
    await vector_store.initialize()
    logger.info(f"Vector store ready — backend={settings.vector_store}")

    logger.info("=" * 50)
    logger.info("SyncContext ready — all systems operational")
    if settings.transport != "stdio":
        if settings.has_shared_project_token():
            logger.info("HTTP requests without x-project-token will use the shared project token")
        else:
            logger.info("Projects are resolved per-request from x-project-token or Authorization")
    logger.info("=" * 50)

    # 6. Yield shared resources (NOT project-specific services)
    yield {
        "db_pool": pool,
        "vector_store": vector_store,
        "embeddings": embeddings,
        "token_auth": token_auth,
        "admin_token": settings.admin_token,
        "project_token": settings.project_token,
    }

    # 7. Cleanup
    logger.info("Shutting down SyncContext...")
    await embeddings.close()
    await vector_store.close()
    await pool.close()
    logger.info("Shutdown complete — goodbye")


async def _create_database_pool(settings: Settings, logger: logging.Logger) -> tuple[asyncpg.Pool, str]:
    """Connect to the first reachable database DSN in fallback order."""
    errors: list[str] = []

    for database_url in settings.database_candidates():
        safe_url = redact_database_url(database_url)
        try:
            logger.info(f"Trying database: {safe_url}")
            pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                **connection_kwargs_from_url(database_url),
            )
            logger.info(f"Database selected: {safe_url}")
            return pool, database_url
        except Exception as exc:
            logger.warning(f"Database unavailable: {safe_url} ({exc})")
            errors.append(f"{safe_url} -> {exc}")

    raise RuntimeError("Unable to connect to any configured database URL: " + " | ".join(errors))


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
    settings = _settings

    if settings.transport in ("streamable-http", "sse"):
        # For HTTP transports, wrap the app with auth middleware
        import uvicorn

        from server.middleware import ProjectAuthMiddleware

        app = mcp.streamable_http_app()
        # Middleware needs token_auth, which is created in lifespan.
        # We pass a lazy reference that gets resolved after lifespan starts.
        app.add_middleware(
            ProjectAuthMiddleware,
            token_auth=_LazyTokenAuth(),
            fallback_project_token=settings.project_token if settings.has_shared_project_token() else None,
            fallback_project_name=settings.project_name if settings.has_shared_project_token() else "",
        )

        config = uvicorn.Config(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
        )
        server = uvicorn.Server(config)

        import anyio

        anyio.run(server.serve)
    else:
        mcp.run(transport="stdio")


class _LazyTokenAuth:
    """Proxy that lazily resolves TokenAuth from the lifespan context.

    The middleware is added before lifespan runs, so we use this proxy
    to defer access to the actual TokenAuth until the first request.
    """

    _instance: TokenAuth | None = None

    async def validate_token(self, token):
        return await self._get().validate_token(token)

    async def create_project_with_token(self, **kwargs):
        return await self._get().create_project_with_token(**kwargs)

    async def update_project_name(self, project_id, name):
        return await self._get().update_project_name(project_id, name)

    def _get(self) -> TokenAuth:
        if self._instance is None:
            # Resolve from the MCP server's session manager state
            ctx = mcp._session_manager
            if ctx and hasattr(ctx, "_app") and hasattr(ctx._app, "_lifespan_context"):
                lc = ctx._app._lifespan_context
                if lc and "token_auth" in lc:
                    self._instance = lc["token_auth"]
        if self._instance is None:
            raise RuntimeError("TokenAuth not yet initialized — lifespan hasn't started")
        return self._instance


if __name__ == "__main__":
    main()
