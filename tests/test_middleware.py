from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from server.context import current_project
from server.middleware import ProjectAuthMiddleware


async def _echo_endpoint(request):
    if request.method == "POST":
        payload = await request.json()
        project = current_project.get()
        return JSONResponse(
            {
                "method": payload.get("method"),
                "project": getattr(project, "name", None),
            }
        )

    project = current_project.get()
    return JSONResponse(
        {
            "path": request.url.path,
            "project": getattr(project, "name", None),
        }
    )


async def _stream_endpoint(request):
    payload = await request.json()

    async def _events():
        yield f"data: {payload.get('method')}\n\n".encode()

    return StreamingResponse(_events(), media_type="text/event-stream")


def _build_app(token_auth, **middleware_kwargs):
    app = Starlette(routes=[Route("/{path:path}", _echo_endpoint, methods=["GET", "POST"])])
    app.add_middleware(ProjectAuthMiddleware, token_auth=token_auth, **middleware_kwargs)
    return app


@pytest.mark.asyncio
async def test_get_discovery_request_skips_auth():
    token_auth = AsyncMock()
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/mcp")

    assert response.status_code == 200
    assert response.json() == {"path": "/mcp", "project": None}
    token_auth.validate_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_initialize_request_skips_auth_and_preserves_body():
    token_auth = AsyncMock()
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response.status_code == 200
    assert response.json() == {"method": "initialize", "project": None}
    token_auth.validate_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_initialize_request_supports_streaming_response():
    token_auth = AsyncMock()
    app = Starlette(routes=[Route("/mcp", _stream_endpoint, methods=["POST"])])
    app.add_middleware(ProjectAuthMiddleware, token_auth=token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == "data: initialize\n\n"
    token_auth.validate_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_tools_list_request_skips_auth():
    token_auth = AsyncMock()
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response.status_code == 200
    assert response.json() == {"method": "tools/list", "project": None}
    token_auth.validate_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_discovery_request_requires_auth():
    token_auth = AsyncMock()
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"})

    assert response.status_code == 401
    assert "x-project-token" in response.json()["error"]
    token_auth.validate_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticated_request_sets_project_context():
    token_auth = AsyncMock()
    token_auth.validate_token.return_value = SimpleNamespace(id="p1", name="Demo Project")
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"},
            headers={"Authorization": "Bearer sc_token"},
        )

    assert response.status_code == 200
    assert response.json() == {"method": "tools/call", "project": "Demo Project"}
    token_auth.validate_token.assert_awaited_once_with("sc_token")


@pytest.mark.asyncio
async def test_project_token_header_sets_project_context():
    token_auth = AsyncMock()
    token_auth.validate_token.return_value = SimpleNamespace(id="p1", name="Header Project")
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"},
            headers={"X-Project-Token": "header_token"},
        )

    assert response.status_code == 200
    assert response.json() == {"method": "tools/call", "project": "Header Project"}
    token_auth.validate_token.assert_awaited_once_with("header_token")


@pytest.mark.asyncio
async def test_project_token_header_takes_precedence_over_authorization():
    token_auth = AsyncMock()
    token_auth.validate_token.return_value = SimpleNamespace(id="p1", name="Header Project")
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"},
            headers={
                "X-Project-Token": "header_token",
                "Authorization": "Bearer ignored_token",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"method": "tools/call", "project": "Header Project"}
    token_auth.validate_token.assert_awaited_once_with("header_token")


@pytest.mark.asyncio
async def test_shared_project_token_fallback_sets_project_context():
    token_auth = AsyncMock()
    token_auth.validate_token.return_value = SimpleNamespace(id="p1", name="Shared Project")
    app = _build_app(
        token_auth,
        fallback_project_token="shared_token",
        fallback_project_name="Shared Project",
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"})

    assert response.status_code == 200
    assert response.json() == {"method": "tools/call", "project": "Shared Project"}
    token_auth.validate_token.assert_awaited_once_with("shared_token")


@pytest.mark.asyncio
async def test_authorization_takes_precedence_over_shared_project_token_fallback():
    token_auth = AsyncMock()
    token_auth.validate_token.return_value = SimpleNamespace(id="p1", name="Bearer Project")
    app = _build_app(
        token_auth,
        fallback_project_token="shared_token",
        fallback_project_name="Shared Project",
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"},
            headers={"Authorization": "Bearer bearer_token"},
        )

    assert response.status_code == 200
    assert response.json() == {"method": "tools/call", "project": "Shared Project"}
    token_auth.validate_token.assert_awaited_once_with("bearer_token")


@pytest.mark.asyncio
async def test_uninitialized_token_auth_returns_503():
    token_auth = AsyncMock()
    token_auth.validate_token.side_effect = RuntimeError("TokenAuth not yet initialized — server startup incomplete")
    app = _build_app(token_auth)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call"},
            headers={"Authorization": "Bearer sc_token"},
        )

    assert response.status_code == 503
    assert response.json() == {"error": "Server startup incomplete. Retry in a few seconds."}
