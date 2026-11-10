"""Session tokens and sign-in codes.

Session token: 256 random bits that nobody can guess, so a fast hash (SHA-256) is enough and
lookups stay an indexed equality. Only the hash is stored.

Sign-in code: only 6 digits (a million values). An unkeyed hash of it could be reversed in under a
second if the database leaked, so it is hashed with HMAC and a server-side secret (AUTH_SECRET)
that is not in the database, and the email is part of what is hashed.
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


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"  # leading zeros kept: "004217"


def hash_code(secret: str, email: str, code: str) -> str:
    return hmac.new(secret.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()
