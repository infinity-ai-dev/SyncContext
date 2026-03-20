"""Starlette middleware for per-request project authentication.

Extracts the Bearer token from the Authorization header and
resolves/creates the project in the database. Stores the project
in a contextvar so tool handlers can access it.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.auth import TokenAuth
from server.context import current_project

logger = logging.getLogger("synccontext.middleware")


class ProjectAuthMiddleware(BaseHTTPMiddleware):
    """Resolve project from Bearer token on every HTTP request."""

    def __init__(self, app, token_auth: TokenAuth):
        super().__init__(app)
        self._token_auth = token_auth

    async def dispatch(self, request: Request, call_next):
        # Extract Bearer token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header. Use: Bearer <token>"},
                status_code=401,
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(
                {"error": "Empty token"},
                status_code=401,
            )

        # Extract optional project name from header (used on first connection)
        project_name = request.headers.get("x-project-name", "")

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

        # Set the project in contextvar for tool handlers
        ctx_token = current_project.set(project)

        try:
            response = await call_next(request)
            return response
        finally:
            current_project.reset(ctx_token)
