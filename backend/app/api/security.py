"""Household access tokens.

No login yet, so a long random token is the only key to a household. Only its SHA-256 hash is
stored. A slow password hash (bcrypt) would add nothing here: those exist because people choose
guessable passwords, and this token is 256 random bits that nobody can guess or brute-force.
"""

import hashlib
import hmac
import secrets


def new_token() -> str:
    return secrets.token_urlsafe(32)  # 32 random bytes = 256 bits


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hashes_match(a: str, b: str) -> bool:
    # Constant-time comparison: how long it takes must not reveal how many characters matched.
    return hmac.compare_digest(a, b)
