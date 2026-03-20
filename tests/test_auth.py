from core.auth import TokenAuth


def test_validate_token_correct():
    auth = TokenAuth("my-secret-token")
    assert auth.validate_token("my-secret-token") is True


def test_validate_token_wrong():
    auth = TokenAuth("my-secret-token")
    assert auth.validate_token("wrong-token") is False


def test_validate_token_empty():
    auth = TokenAuth("my-secret-token")
    assert auth.validate_token("") is False


def test_get_project_token():
    auth = TokenAuth("project-abc")
    assert auth.get_project_token() == "project-abc"
