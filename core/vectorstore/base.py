from abc import ABC, abstractmethod
from uuid import UUID


class VectorStore(ABC):
    """Abstract interface for vector similarity search backends."""

    @abstractmethod
    async def initialize(self) -> None:
        """Create indexes, tables, etc. Called once at startup."""
        ...

    @abstractmethod
    async def upsert(self, id: UUID, vector: list[float], metadata: dict) -> None:
        """Insert or update a vector with metadata."""
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        """Find top_k most similar vectors. Returns list of {id, score, metadata}."""
        ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a vector by ID. Returns True if deleted."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Cleanup connections."""
        ...
