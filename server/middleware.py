"""ASGI middleware for per-request project authentication.

Extracts the project token from ``x-project-token`` or ``Authorization``.
When a shared project token is configured for hosted MCPize deployments,
it is used as a fallback so capability discovery and calls can succeed
without per-user credential injection.
"""

import json
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.auth import TokenAuth
from server.context import current_project

logger = logging.getLogger("synccontext.middleware")
DISCOVERY_METHODS = {"initialize", "tools/list", "resources/list", "prompts/list"}
DISCOVERY_PATHS = {"/", "/mcp", "/sse", "/ping"}


class ProjectAuthMiddleware:
    """Resolve project from Bearer token on every HTTP request."""

    def __init__(
        self,
        app: ASGIApp,
        token_auth: TokenAuth,
        fallback_project_token: str | None = None,
        fallback_project_name: str = "",
    ):
        self.app = app
        self._token_auth = token_auth
        self._fallback_project_token = (fallback_project_token or "").strip()
        self._fallback_project_name = fallback_project_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body = await self._read_body(receive)
        request = Request(scope)

        if self._is_discovery_request(request, body):
            await self.app(scope, self._build_receive(body, receive), send)
            return

        token = self._extract_project_token(request)
        if not token:
            response = JSONResponse(
                {
                    "error": (
                        "Missing project token. Use header "
                        "x-project-token: <token> or Authorization: Bearer <token>"
                    )
                },
                status_code=401,
            )
            await response(scope, self._build_receive(body, receive), send)
            return

        # Extract optional project name from header (used on first connection)
        project_name = request.headers.get("x-project-name", "").strip() or self._fallback_project_name

        try:
            # Resolve project: look up token in DB, auto-create if new
            project = await self._token_auth.validate_token(token)

            if not project:
                # New token — create project automatically
                name = project_name if project_name else f"Project {token[:12]}"
                project = await self._token_auth.create_project_with_token(
                    token=token,
                    name=name,
                )
                logger.info(f"New project auto-created: {project.name} (token={token[:12]}...)")
            else:
                # Update name if provided and different
                if project_name and project_name != project.name:
                    await self._token_auth.update_project_name(project.id, project_name)
                    project.name = project_name
        except RuntimeError as exc:
            if "TokenAuth not yet initialized" not in str(exc):
                raise
            logger.warning("Request received before TokenAuth was ready")
            response = JSONResponse(
                {"error": "Server startup incomplete. Retry in a few seconds."},
                status_code=503,
            )
            await response(scope, self._build_receive(body, receive), send)
            return

        # Set the project in contextvar for tool handlers
        ctx_token = current_project.set(project)

        try:
            await self.app(scope, self._build_receive(body, receive), send)
        finally:
            current_project.reset(ctx_token)

    def _extract_project_token(self, request: Request) -> str:
        """Prefer explicit header, then Authorization, then shared fallback."""
        project_token = request.headers.get("x-project-token", "").strip()
        if project_token:
            return project_token

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.removeprefix("Bearer ").strip()

        if self._fallback_project_token:
            return self._fallback_project_token

        return ""

    def _is_discovery_request(self, request: Request, body: bytes) -> bool:
        """Allow MCP capability discovery requests without project auth."""
        if request.method == "GET" and request.url.path in DISCOVERY_PATHS:
            return True

        if request.method != "POST" or request.url.path not in {"/", "/mcp"}:
            return False

        if not body:
            return False

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return False

        return payload.get("method") in DISCOVERY_METHODS

    @staticmethod
    async def _read_body(receive: Receive) -> bytes:
        """Buffer the request body once so it can be replayed downstream."""
        chunks: list[bytes] = []

        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break

            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

        return b"".join(chunks)

    @staticmethod
    def _build_receive(body: bytes, original_receive: Receive) -> Receive:
        """Replay the buffered body, then forward later events such as disconnects."""
        body_sent = False

        async def receive() -> Message:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}

            return await original_receive()

        return receive
