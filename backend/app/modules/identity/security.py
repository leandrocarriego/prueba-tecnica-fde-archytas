"""Password hashing and opaque token handling for the identity module.

Two kinds of secret live here and they are hashed differently on purpose.

A **password** is chosen by a person, so it has little entropy and has to
survive an offline brute force: bcrypt, deliberately slow.

A **token** — a session, an invitation, a recovery link — is 32 random bytes
from `secrets`. There is no guessing it, and a session token is verified on
*every* request, where bcrypt would cost a hundred milliseconds per lookup. So
tokens get SHA-256: fast, and enough, because the thing it protects against is
somebody reading the table, not somebody guessing the value.
"""

import hashlib
import secrets

import bcrypt

# bcrypt silently ignores anything past 72 bytes, so truncate explicitly rather
# than letting two different passwords hash to the same value unnoticed.
BCRYPT_MAX_BYTES = 72

TOKEN_BYTES = 32


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Return the bcrypt hash of a plaintext password."""
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against its hash."""
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash in the database: treat as a failed login, not a crash.
        return False


def generate_token() -> str:
    """Return a URL-safe opaque token: a session, an invitation or a reset link."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the stored form of a token.

    What travels to the browser is the token; what the database holds is this.
    A stolen dump therefore does not let anybody in.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
