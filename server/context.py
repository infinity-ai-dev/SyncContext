"""Per-request context using contextvars.

The auth middleware sets the current project for each HTTP request.
Tool handlers read it to scope memory operations to the correct project.
"""

from contextvars import ContextVar

from core.models import Project

current_project: ContextVar[Project | None] = ContextVar("current_project", default=None)
