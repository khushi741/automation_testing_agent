import pytest
from app import init_db, find_user_by_name, authenticate_admin, ADMIN_TOKEN


def test_find_user_existing():
    conn = init_db()
    user = find_user_by_name(conn, "alice")
    assert user is not None
    assert user[1] == "alice"


def test_find_user_nonexistent():
    conn = init_db()
    user = find_user_by_name(conn, "charlie_not_found")
    assert user is None


def test_authenticate_admin():
    assert authenticate_admin(ADMIN_TOKEN) is True
    assert authenticate_admin("wrong_token") is False

