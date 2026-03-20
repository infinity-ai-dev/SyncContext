from uuid import UUID, uuid4

from core.models import Memory, MemoryCreate, MemoryUpdate, Project, ProjectContext, SearchResult


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
    pid = uuid4()
    m = Memory(project_id=pid, content="test")
    assert isinstance(m.id, UUID)
    assert m.project_id == pid


def test_memory_update_partial():
    mu = MemoryUpdate(content="new content")
    assert mu.content == "new content"
    assert mu.tags is None
    assert mu.file_path is None


def test_search_result():
    pid = uuid4()
    m = Memory(project_id=pid, content="test")
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


def test_project_defaults():
    p = Project(name="Test Project", token="sc_abc123")
    assert isinstance(p.id, UUID)
    assert p.name == "Test Project"
    assert p.token == "sc_abc123"
    assert p.description is None
    assert p.embedding_provider == "gemini"
    assert p.embedding_dimension == 768
    assert p.is_active is True
    assert p.max_memories is None


def test_project_with_all_fields():
    pid = uuid4()
    p = Project(
        id=pid,
        name="Full Project",
        token="sc_full",
        description="A fully specified project",
        embedding_provider="openai",
        embedding_dimension=1536,
        is_active=False,
        max_memories=1000,
    )
    assert p.id == pid
    assert p.name == "Full Project"
    assert p.description == "A fully specified project"
    assert p.embedding_provider == "openai"
    assert p.embedding_dimension == 1536
    assert p.is_active is False
    assert p.max_memories == 1000
