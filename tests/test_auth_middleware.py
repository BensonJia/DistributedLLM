import pytest
from fastapi import HTTPException

from server.api.auth_middleware import require_internal_token


def test_require_internal_token_accepts_correct_value(monkeypatch):
    monkeypatch.setenv("DLLM_SERVER_INTERNAL_TOKEN", "secret-token")

    assert require_internal_token("secret-token") == "secret-token"


def test_require_internal_token_rejects_wrong_value(monkeypatch):
    monkeypatch.setenv("DLLM_SERVER_INTERNAL_TOKEN", "secret-token")

    with pytest.raises(HTTPException) as exc:
        require_internal_token("wrong-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid worker token"
