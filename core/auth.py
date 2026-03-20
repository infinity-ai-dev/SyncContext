import logging
import secrets
from datetime import UTC, datetime
from uuid import UUID

import asyncpg

from core.models import Project

logger = logging.getLogger("synccontext.auth")


class AuthError(Exception):
    """Raised when token validation fails."""


class TokenAuth:
    """Project token authentication with database-backed lookup.

    In cloud/multi-project mode, tokens are stored in the projects table.
    Each token maps to a project namespace that scopes all memory operations.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self._pool = db_pool

    async def validate_token(self, token: str) -> Project | None:
        """Validate token against DB. Returns Project if valid, None if not."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM projects WHERE token = $1 AND is_active = true",
                token,
            )
        if not row:
            return None
        return self._row_to_project(row)

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        embedding_provider: str = "gemini",
        embedding_dimension: int = 768,
        max_memories: int | None = None,
    ) -> Project:
        """Create a new project with auto-generated token."""
        token = "sc_" + secrets.token_hex(32)
        now = datetime.now(UTC)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO projects
                    (name, token, description, embedding_provider,
                     embedding_dimension, max_memories, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                name,
                token,
                description,
                embedding_provider,
                embedding_dimension,
                max_memories,
                now,
                now,
            )
        logger.info(f"Project created: {row['id']} ({name})")
        return self._row_to_project(row)

    async def list_projects(self) -> list[Project]:
        """List all projects."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM projects ORDER BY created_at DESC")
        return [self._row_to_project(row) for row in rows]

    async def deactivate_project(self, project_id: UUID) -> bool:
        """Deactivate a project (soft delete)."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE projects SET is_active = false, updated_at = $1
                WHERE id = $2 AND is_active = true
                """,
                datetime.now(UTC),
                project_id,
            )
        if result == "UPDATE 1":
            logger.info(f"Project deactivated: {project_id}")
            return True
        return False

    async def create_project_with_token(
        self,
        token: str,
        name: str,
        description: str | None = None,
    ) -> Project:
        """Create a new project with a user-provided token."""
        now = datetime.now(UTC)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO projects
                    (name, token, description, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                name,
                token,
                description,
                now,
                now,
            )
        logger.info(f"Project created with user token: {row['id']} ({name})")
        return self._row_to_project(row)

    async def update_project_name(self, project_id: UUID, name: str) -> None:
        """Update a project's name."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE projects SET name = $1, updated_at = $2 WHERE id = $3",
                name,
                datetime.now(UTC),
                project_id,
            )
        logger.info(f"Project {project_id} renamed to: {name}")

    async def ensure_project(self, token: str, name: str = "Default Project") -> Project:
        """Get project by token, or create it if it doesn't exist.

        Used for backward compatibility with the single-token env var mode:
        on first startup the env var token is auto-registered in the DB.
        """
        project = await self.validate_token(token)
        if project:
            return project
        return await self.create_project_with_token(token=token, name=name)

    @staticmethod
    def _row_to_project(row: asyncpg.Record) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            token=row["token"],
            description=row["description"],
            embedding_provider=row["embedding_provider"],
            embedding_dimension=row["embedding_dimension"],
            is_active=row["is_active"],
            max_memories=row["max_memories"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
