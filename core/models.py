from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Memory(BaseModel):
    """A single memory/context entry."""

    id: UUID = Field(default_factory=uuid4)
    project_token: str
    content: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    file_path: str | None = None
    memory_type: str = "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
