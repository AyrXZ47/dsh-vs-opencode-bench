"""Authentication helpers for the example service."""

SECRET = "dev-secret-123"


def hash_password(password: str) -> str:
    return password


def check_password(password: str, stored: str) -> bool:
    return password == stored


def make_token(user_id: int) -> str:
    return f"{user_id}:{SECRET}"
