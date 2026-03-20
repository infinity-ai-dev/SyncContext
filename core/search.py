import logging
from uuid import UUID

from core.embeddings.base import EmbeddingProvider
from core.memory import MemoryService
from core.models import SearchResult
from core.vectorstore.base import VectorStore

logger = logging.getLogger("synccontext.search")


class SearchService:
    """Semantic search across project memories."""

    def __init__(
        self,
        memory_service: MemoryService,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        project_id: UUID,
    ):
        self._memory_service = memory_service
        self._vector_store = vector_store
        self._embeddings = embedding_provider
        self._project_id = project_id

    async def search(
        self,
        query: str,
        top_k: int = 5,
        tag: str | None = None,
        author: str | None = None,
        min_score: float = 0.3,
    ) -> list[SearchResult]:
        """Semantic search for relevant memories."""
        # 1. Embed the query
        query_vector = await self._embeddings.embed(query)

        # 2. Search vector store
        vector_results = await self._vector_store.search(
            query_vector=query_vector,
            top_k=top_k * 2,  # Fetch extra to compensate for post-filtering
            filter_metadata={"project_id": str(self._project_id)},
        )

        # 3. Fetch full memory metadata and apply filters
        results = []
        for vr in vector_results:
            if vr["score"] < min_score:
                continue

            memory = await self._memory_service.get_memory(UUID(str(vr["id"])))
            if not memory:
                continue

            if tag and tag not in memory.tags:
                continue
            if author and memory.author != author:
                continue

            results.append(SearchResult(memory=memory, score=vr["score"]))

            if len(results) >= top_k:
                break

        logger.info(f"Search for '{query[:50]}...' returned {len(results)} results")
        return results

    async def find_similar(
        self,
        memory_id: UUID,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[SearchResult]:
        """Find memories similar to the one identified by memory_id.

        The source memory itself is excluded from results.
        Returns an empty list if the memory does not exist.
        """
        source = await self._memory_service.get_memory(memory_id)
        if not source:
            return []

        # Re-embed the source content to use as the query vector
        query_vector = await self._embeddings.embed(source.content)

        vector_results = await self._vector_store.search(
            query_vector=query_vector,
            top_k=top_k * 2 + 1,  # +1 to account for the source memory itself
            filter_metadata={"project_id": str(self._project_id)},
        )

        results = []
        for vr in vector_results:
            if vr["score"] < min_score:
                continue

            candidate_id = UUID(str(vr["id"]))
            if candidate_id == memory_id:
                continue  # exclude the source memory

            memory = await self._memory_service.get_memory(candidate_id)
            if not memory:
                continue

            results.append(SearchResult(memory=memory, score=vr["score"]))

            if len(results) >= top_k:
                break

        logger.info(f"find_similar for {memory_id} returned {len(results)} results")
        return results
