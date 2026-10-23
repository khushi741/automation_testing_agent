import os
from pathlib import Path

BASE_STORAGE_DIR = Path("/tmp/storage")


def read_user_file(base_dir: str, filename: str) -> str:
    """
    Reads a file from user directory.
    INTENTIONAL BUG (Security): Path traversal vulnerability via unsanitized filename join!
    """
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def get_user_tier(user_data: dict) -> str:
    """
    Extracts the user membership tier.
    INTENTIONAL BUG (Crash): KeyError when 'profile' or 'tier' key is missing!
    """
    profile = user_data["profile"]
    return profile["tier"]


def is_coupon_valid(coupon_expires_at: int, current_time: int) -> bool:
    """
    Returns True if coupon has not yet expired.
    INTENTIONAL BUG (Logic): Inverted operator: checks if coupon_expires_at < current_time instead of >= !
    """
    # Bug: allows expired coupons and rejects active coupons
    return coupon_expires_at < current_time
