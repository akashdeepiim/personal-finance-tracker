import pytest
from fastapi import HTTPException

import main


def test_api_token_is_enforced(monkeypatch):
    monkeypatch.setattr(main, "API_TOKEN", "secret")
    with pytest.raises(HTTPException) as error:
        main.require_api_token(None)
    assert error.value.status_code == 401
    main.require_api_token("Bearer secret")


def test_api_token_is_optional_in_local_development(monkeypatch):
    monkeypatch.setattr(main, "API_TOKEN", None)
    main.require_api_token(None)
