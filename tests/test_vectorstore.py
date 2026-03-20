import pytest

from core.vectorstore import create_vector_store
from core.vectorstore.pgvector_store import PgVectorStore
from core.vectorstore.redis_store import RedisVectorStore


def test_create_pgvector_store():
    store = create_vector_store("pgvector", database_url="postgresql://test:test@localhost/test")
    assert isinstance(store, PgVectorStore)


def test_create_redis_store():
    store = create_vector_store("redis", redis_url="redis://localhost:6379/0")
    assert isinstance(store, RedisVectorStore)


def test_create_unknown_store():
    with pytest.raises(ValueError, match="Unknown vector store"):
        create_vector_store("unknown", database_url="test")


def test_pgvector_default_dimension():
    store = create_vector_store("pgvector", database_url="postgresql://test:test@localhost/test")
    assert store._dimension == 768


def test_pgvector_custom_dimension():
    store = create_vector_store("pgvector", database_url="postgresql://test:test@localhost/test", dimension=1536)
    assert store._dimension == 1536


def test_redis_default_dimension():
    store = create_vector_store("redis", redis_url="redis://localhost:6379/0")
    assert store._dimension == 768
