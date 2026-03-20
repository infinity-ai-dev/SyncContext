import secrets


class AuthError(Exception):
    """Raised when token validation fails."""


class TokenAuth:
    """Simple project token authentication.

    In self-hosted mode, the token is a shared secret configured via env var.
    Every memory operation is scoped to this token (acts as project namespace).
    In cloud mode (Phase 2), this becomes a database-backed lookup.
    """

    def __init__(self, project_token: str):
        self._project_token = project_token

    def get_project_token(self) -> str:
        return self._project_token

    def validate_token(self, token: str) -> bool:
        return secrets.compare_digest(token, self._project_token)
