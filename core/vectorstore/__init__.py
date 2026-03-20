from core.vectorstore.base import VectorStore


def create_vector_store(backend: str, **kwargs) -> VectorStore:
    """Factory function to create the appropriate vector store backend."""
    match backend:
        case "pgvector":
            from core.vectorstore.pgvector_store import PgVectorStore

            return PgVectorStore(
                database_url=kwargs["database_url"],
                dimension=kwargs.get("dimension", 768),
            )
        case "redis":
            from core.vectorstore.redis_store import RedisVectorStore

            return RedisVectorStore(
                redis_url=kwargs["redis_url"],
                dimension=kwargs.get("dimension", 768),
            )
        case _:
            raise ValueError(f"Unknown vector store backend: {backend}")


__all__ = ["VectorStore", "create_vector_store"]
