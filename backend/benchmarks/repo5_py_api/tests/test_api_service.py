import pytest
from api_service import get_user_tier, is_coupon_valid


def test_user_tier_valid():
    user = {"name": "Alice", "profile": {"tier": "gold"}}
    assert get_user_tier(user) == "gold"


def test_coupon_validity_structure():
    assert isinstance(is_coupon_valid(1000, 500), bool)
