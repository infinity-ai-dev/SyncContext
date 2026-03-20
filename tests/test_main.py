import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from server.config import Settings
from server.main import build_http_app


async def _mcp_endpoint(request):
    return JSONResponse({"path": request.url.path})


@pytest.mark.asyncio
async def test_build_http_app_exposes_ping_and_mcp_routes():
    settings = Settings(_env_file=None)
    inner_app = Starlette(routes=[Route("/mcp", _mcp_endpoint, methods=["GET"])])
    app = build_http_app(settings, inner_app)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        ping_response = await client.get("/ping")
        mcp_response = await client.get("/mcp")

    assert ping_response.status_code == 200
    assert ping_response.json() == {"status": "ok"}
    assert mcp_response.status_code == 200
    assert mcp_response.json() == {"path": "/mcp"}
