"""Runtime state shared between HTTP middleware and server lifespan."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.auth import TokenAuth


class RuntimeState:
    """Mutable state populated during FastMCP lifespan startup."""

    def __init__(self) -> None:
        self.token_auth: "TokenAuth | None" = None


runtime_state = RuntimeState()
