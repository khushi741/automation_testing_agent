# AUTO-GENERATED REPRODUCTION TEST SUITE - SEPARATE FROM ORIGINAL BENCHMARK TESTS
import pytest
from app import authenticate_admin


def test_repro_authenticate_admin_empty_token_denied_when_unset(monkeypatch):
    import app
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    orig_token = app.ADMIN_TOKEN
    app.ADMIN_TOKEN = None
    try:
        # When variable is unset, empty token must NEVER be accepted and access is denied
        assert authenticate_admin("") is False
        assert authenticate_admin("wrong_token") is False
    finally:
        app.ADMIN_TOKEN = orig_token


def test_repro_authenticate_admin_non_ascii_token():
    # Non-ASCII tokens must safely evaluate without raising UnicodeEncodeError/crash
    assert authenticate_admin("token_with_unicode_ñ_🚀") is False
    assert authenticate_admin("   ") is False
