"""Tests for the database-backed TokenAuth.

These tests use unittest.mock to patch asyncpg pool interactions,
keeping them fast and free from a real database dependency.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.auth import TokenAuth
from core.models import Project


@pytest.fixture()
def mock_pool():
    """Create a mock asyncpg pool with acquire context manager."""
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


def _make_project_row(
    name="Test Project",
    token="sc_testtoken",
    is_active=True,
    **overrides,
):
    """Build a dict mimicking an asyncpg Record for the projects table."""
    now = datetime.now(UTC)
    base = {
        "id": uuid4(),
        "name": name,
        "token": token,
        "description": None,
        "embedding_provider": "gemini",
        "embedding_dimension": 768,
        "is_active": is_active,
        "max_memories": None,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_validate_token_returns_project(mock_pool):
    pool, conn = mock_pool
    row = _make_project_row(token="sc_valid")
    conn.fetchrow.return_value = row

    auth = TokenAuth(pool)
    project = await auth.validate_token("sc_valid")

    assert project is not None
    assert isinstance(project, Project)
    assert project.token == "sc_valid"
    assert project.is_active is True
    conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_token_returns_none_for_invalid(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    auth = TokenAuth(pool)
    project = await auth.validate_token("sc_invalid")

    assert project is None


@pytest.mark.asyncio
async def test_create_project(mock_pool):
    pool, conn = mock_pool
    row = _make_project_row(name="New Project")
    conn.fetchrow.return_value = row

    auth = TokenAuth(pool)
    project = await auth.create_project(name="New Project", description="desc")

    assert isinstance(project, Project)
    assert project.name == "New Project"
    conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_projects(mock_pool):
    pool, conn = mock_pool
    conn.fetch.return_value = [
        _make_project_row(name="P1", token="sc_1"),
        _make_project_row(name="P2", token="sc_2"),
    ]

    auth = TokenAuth(pool)
    projects = await auth.list_projects()

    assert len(projects) == 2
    assert projects[0].name == "P1"
    assert projects[1].name == "P2"


@pytest.mark.asyncio
async def test_deactivate_project_success(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 1"

    auth = TokenAuth(pool)
    result = await auth.deactivate_project(uuid4())

    assert result is True


@pytest.mark.asyncio
async def test_deactivate_project_not_found(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 0"

    auth = TokenAuth(pool)
    result = await auth.deactivate_project(uuid4())

    assert result is False


@pytest.mark.asyncio
async def test_ensure_project_existing(mock_pool):
    pool, conn = mock_pool
    row = _make_project_row(token="sc_existing")
    conn.fetchrow.return_value = row

    auth = TokenAuth(pool)
    project = await auth.ensure_project("sc_existing")

    assert project.token == "sc_existing"
    # validate_token should have been called (fetchrow), but not create_project
    assert conn.fetchrow.await_count == 1


@pytest.mark.asyncio
async def test_ensure_project_creates_new(mock_pool):
    pool, conn = mock_pool
    new_row = _make_project_row(name="Default Project", token="sc_newtoken")

    # First call to validate_token returns None, second call is create_project
    conn.fetchrow.side_effect = [None, new_row]

    auth = TokenAuth(pool)
    project = await auth.ensure_project("sc_nonexistent", name="Default Project")

    assert isinstance(project, Project)
    assert project.name == "Default Project"
    # Two fetchrow calls: one for validate_token, one for create_project (RETURNING *)
    assert conn.fetchrow.await_count == 2
