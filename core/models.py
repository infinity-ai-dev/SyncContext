from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Project(BaseModel):
    """A project namespace with its own token and settings."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    token: str
    description: str | None = None
    embedding_provider: str = "gemini"
    embedding_dimension: int = 768
    is_active: bool = True
    max_memories: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Memory(BaseModel):
    """A single memory/context entry."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    content: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    file_path: str | None = None
    memory_type: str = "general"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryCreate(BaseModel):
    """Input model for creating a memory."""

    content: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    file_path: str | None = None
    memory_type: str = "general"


class MemoryUpdate(BaseModel):
    """Input model for updating a memory."""

    content: str | None = None
    tags: list[str] | None = None
    file_path: str | None = None
    memory_type: str | None = None


class SearchResult(BaseModel):
    """A memory with similarity score."""

    memory: Memory
    score: float


class ProjectContext(BaseModel):
    """Aggregated project summary for onboarding."""

    total_memories: int
    recent_memories: list[Memory]
    top_tags: list[dict[str, int]]
    contributors: list[str]
