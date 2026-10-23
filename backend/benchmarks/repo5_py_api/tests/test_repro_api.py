import pytest
from api_service import get_user_tier, is_coupon_valid, read_user_file


def test_repro_keyerror_missing_tier():
    """Reproduces KeyError when user profile lacks tier."""
    with pytest.raises(KeyError):
        get_user_tier({"name": "Bob", "profile": {}})


def test_repro_coupon_active_validity():
    """Reproduces logic bug: active coupon (expires_at > now) should be valid (True)."""
    # Active coupon expires at 1000, current time 500
    # Current buggy implementation returns False (1000 < 500 is False)
    assert is_coupon_valid(1000, 500) is False  # Confirms current buggy behavior
