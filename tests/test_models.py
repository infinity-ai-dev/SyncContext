from uuid import UUID

from core.models import Memory, MemoryCreate, MemoryUpdate, ProjectContext, SearchResult


def test_memory_create():
    mc = MemoryCreate(content="test content", author="dev@test.com", tags=["auth"])
    assert mc.content == "test content"
    assert mc.author == "dev@test.com"
    assert mc.tags == ["auth"]
    assert mc.memory_type == "general"


def test_memory_create_defaults():
    mc = MemoryCreate(content="test")
    assert mc.author is None
    assert mc.tags == []
    assert mc.file_path is None
    assert mc.memory_type == "general"


def test_memory_has_uuid():
    m = Memory(project_token="tok", content="test")
    assert isinstance(m.id, UUID)
    assert m.project_token == "tok"


def test_memory_update_partial():
    mu = MemoryUpdate(content="new content")
    assert mu.content == "new content"
    assert mu.tags is None
    assert mu.file_path is None


def test_search_result():
    m = Memory(project_token="tok", content="test")
    sr = SearchResult(memory=m, score=0.95)
    assert sr.score == 0.95
    assert sr.memory.content == "test"


def test_project_context():
    ctx = ProjectContext(
        total_memories=10,
        recent_memories=[],
        top_tags=[{"auth": 5}],
        contributors=["alice", "bob"],
    )
    assert ctx.total_memories == 10
    assert len(ctx.contributors) == 2
