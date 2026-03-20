import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg

from core.embeddings.base import EmbeddingProvider
from core.models import Memory, MemoryCreate, MemoryUpdate, ProjectContext
from core.vectorstore.base import VectorStore

logger = logging.getLogger("synccontext.memory")


class MemoryService:
    """Core CRUD operations for project memories."""

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        project_id: UUID,
    ):
        self._pool = db_pool
        self._vector_store = vector_store
        self._embeddings = embedding_provider
        self._project_id = project_id

    async def save_memory(self, data: MemoryCreate) -> Memory:
        """Save a new memory with its embedding."""
        memory_id = uuid4()
        now = datetime.now(UTC)

        # 1. Generate embedding
        embedding = await self._embeddings.embed(data.content)

        # 2. Insert metadata into PostgreSQL
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memories
                    (id, project_id, project_token, content, author,
                     tags, file_path, memory_type, created_at, updated_at)
                VALUES ($1, $2, '', $3, $4, $5, $6, $7, $8, $9)
                """,
                memory_id,
                self._project_id,
                data.content,
                data.author,
                data.tags,
                data.file_path,
                data.memory_type,
                now,
                now,
            )

        # 3. Upsert vector into vector store
        await self._vector_store.upsert(
            id=memory_id,
            vector=embedding,
            metadata={"project_id": str(self._project_id)},
        )

        logger.info(f"Memory saved: {memory_id}")
        return Memory(
            id=memory_id,
            project_id=self._project_id,
            content=data.content,
            author=data.author,
            tags=data.tags,
            file_path=data.file_path,
            memory_type=data.memory_type,
            created_at=now,
            updated_at=now,
        )

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        """Get a single memory by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM memories WHERE id = $1 AND project_id = $2",
                memory_id,
                self._project_id,
            )
        if not row:
            return None
        return self._row_to_memory(row)

    async def update_memory(self, memory_id: UUID, data: MemoryUpdate) -> Memory | None:
        """Update an existing memory. Re-embeds if content changed."""
        existing = await self.get_memory(memory_id)
        if not existing:
            return None

        now = datetime.now(UTC)
        new_content = data.content if data.content is not None else existing.content
        new_tags = data.tags if data.tags is not None else existing.tags
        new_file_path = data.file_path if data.file_path is not None else existing.file_path
        new_memory_type = data.memory_type if data.memory_type is not None else existing.memory_type

        # Update metadata in PostgreSQL
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE memories
                SET content = $1, tags = $2, file_path = $3, memory_type = $4, updated_at = $5
                WHERE id = $6 AND project_id = $7
                """,
                new_content,
                new_tags,
                new_file_path,
                new_memory_type,
                now,
                memory_id,
                self._project_id,
            )

        # Re-embed if content changed
        if data.content is not None and data.content != existing.content:
            embedding = await self._embeddings.embed(new_content)
            await self._vector_store.upsert(
                id=memory_id,
                vector=embedding,
                metadata={"project_id": str(self._project_id)},
            )

        logger.info(f"Memory updated: {memory_id}")
        return Memory(
            id=memory_id,
            project_id=self._project_id,
            content=new_content,
            author=existing.author,
            tags=new_tags,
            file_path=new_file_path,
            memory_type=new_memory_type,
            created_at=existing.created_at,
            updated_at=now,
        )

    async def delete_memory(self, memory_id: UUID) -> bool:
        """Delete a memory and its vector."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM memories WHERE id = $1 AND project_id = $2",
                memory_id,
                self._project_id,
            )

        if result == "DELETE 1":
            await self._vector_store.delete(memory_id)
            logger.info(f"Memory deleted: {memory_id}")
            return True
        return False

    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0,
        tag: str | None = None,
        author: str | None = None,
        memory_type: str | None = None,
    ) -> list[Memory]:
        """List memories with optional filters."""
        query = "SELECT * FROM memories WHERE project_id = $1"
        params: list = [self._project_id]
        idx = 2

        if tag:
            query += f" AND ${idx} = ANY(tags)"
            params.append(tag)
            idx += 1

        if author:
            query += f" AND author = ${idx}"
            params.append(author)
            idx += 1

        if memory_type:
            query += f" AND memory_type = ${idx}"
            params.append(memory_type)
            idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_memory(row) for row in rows]

    async def list_tags(self) -> list[dict[str, int]]:
        """List all unique tags with their usage counts, sorted by count descending."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tag, COUNT(*) AS cnt
                FROM memories, UNNEST(tags) AS tag
                WHERE project_id = $1
                GROUP BY tag
                ORDER BY cnt DESC
                """,
                self._project_id,
            )
        return [{row["tag"]: row["cnt"]} for row in rows]

    async def list_contributors(self) -> list[dict[str, int]]:
        """List all distinct authors with their memory counts, sorted by count descending."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT author, COUNT(*) AS cnt
                FROM memories
                WHERE project_id = $1 AND author IS NOT NULL
                GROUP BY author
                ORDER BY cnt DESC
                """,
                self._project_id,
            )
        return [{row["author"]: row["cnt"]} for row in rows]

    async def search_by_file(self, file_path: str, limit: int = 20) -> list[Memory]:
        """Find memories whose file_path contains the given substring."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM memories
                WHERE project_id = $1 AND file_path ILIKE $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                self._project_id,
                f"%{file_path}%",
                limit,
            )
        return [self._row_to_memory(row) for row in rows]

    async def bulk_save_memories(self, items: list[MemoryCreate]) -> list[Memory]:
        """Save multiple memories in sequence, returning all created Memory objects."""
        results = []
        for item in items:
            memory = await self.save_memory(item)
            results.append(memory)
        return results

    async def get_project_context(self) -> ProjectContext:
        """Get aggregated project summary."""
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM memories WHERE project_id = $1",
                self._project_id,
            )

            recent_rows = await conn.fetch(
                "SELECT * FROM memories WHERE project_id = $1 ORDER BY created_at DESC LIMIT 10",
                self._project_id,
            )

            tag_rows = await conn.fetch(
                """
                SELECT tag, COUNT(*) as cnt
                FROM memories, UNNEST(tags) AS tag
                WHERE project_id = $1
                GROUP BY tag
                ORDER BY cnt DESC
                LIMIT 10
                """,
                self._project_id,
            )

            contributor_rows = await conn.fetch(
                """
                SELECT DISTINCT author FROM memories
                WHERE project_id = $1 AND author IS NOT NULL
                """,
                self._project_id,
            )

        return ProjectContext(
            total_memories=total or 0,
            recent_memories=[self._row_to_memory(r) for r in recent_rows],
            top_tags=[{row["tag"]: row["cnt"]} for row in tag_rows],
            contributors=[row["author"] for row in contributor_rows],
        )

    @staticmethod
    def _row_to_memory(row: asyncpg.Record) -> Memory:
        return Memory(
            id=row["id"],
            project_id=row["project_id"],
            content=row["content"],
            author=row["author"],
            tags=list(row["tags"]) if row["tags"] else [],
            file_path=row["file_path"],
            memory_type=row["memory_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
