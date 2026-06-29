import secrets


def generate_self_view_token(length: int = 32) -> str:
    # 32 bytes gives a URL-safe token around 43 characters, under the 64-char DB limit.
    return secrets.token_urlsafe(length)
