"""Unit tests for `app.modules.identity.security`.

Nothing here touches the database: hashing is a pure function, and so is the
generation of the opaque tokens that replaced the signed ones.

The signed access token is gone on purpose, and so are its tests. A JWT proves
it was issued and cannot be asked whether it is still wanted, which is the one
question this feature has to answer: an owner deactivates somebody, a password
changes, an access comes back — all of them have to end a credential that was
already handed out. What replaced it is a random string whose hash is a row,
and everything worth asserting about it lives in the tests that touch that row.
"""

import pytest

from app.modules.identity.security import (
    BCRYPT_MAX_BYTES,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)

PASSWORD = "cordillera-2026"


@pytest.mark.unit
class TestPasswordHashing:
    """bcrypt, and the 72-byte limit it enforces silently."""

    def test_hash_is_not_the_password(self) -> None:
        """The plaintext must not survive anywhere in the hash."""
        # Act
        hashed = hash_password(PASSWORD)

        # Assert
        assert hashed != PASSWORD
        assert PASSWORD not in hashed
        assert hashed.startswith("$2b$")

    def test_verify_accepts_the_right_password(self) -> None:
        """The round trip works."""
        assert verify_password(PASSWORD, hash_password(PASSWORD)) is True

    def test_verify_rejects_the_wrong_password(self) -> None:
        """A near miss is still a miss."""
        assert verify_password("cordillera-2025", hash_password(PASSWORD)) is False

    def test_the_same_password_hashes_differently_every_time(self) -> None:
        """Each hash carries its own salt, so equal passwords are not equal rows."""
        # Act
        first, second = hash_password(PASSWORD), hash_password(PASSWORD)

        # Assert
        assert first != second
        assert verify_password(PASSWORD, first)
        assert verify_password(PASSWORD, second)

    def test_verify_rejects_a_malformed_hash_instead_of_raising(self) -> None:
        """A corrupted row is a failed login, not a 500."""
        assert verify_password(PASSWORD, "not-a-bcrypt-hash") is False

    def test_verify_rejects_an_empty_hash(self) -> None:
        """A user with no credential can never be verified into a session."""
        assert verify_password(PASSWORD, "") is False

    def test_a_password_is_truncated_to_72_bytes(self) -> None:
        """bcrypt ignores anything past 72 bytes, so the module truncates explicitly.

        Two passwords sharing their first 72 bytes are the same password as far
        as bcrypt is concerned. What matters is that this happens deliberately,
        and that hashing a longer value does not raise.
        """
        # Arrange
        limit = "a" * BCRYPT_MAX_BYTES

        # Act
        hashed = hash_password(limit + "-and-a-much-longer-tail")

        # Assert
        assert verify_password(limit, hashed) is True

    def test_truncation_counts_bytes_not_characters(self) -> None:
        """A Spanish password is shorter in characters than in bytes.

        'ñ' takes two bytes in UTF-8, so 40 of them are 80 bytes and get cut at
        the 36th character.
        """
        # Arrange
        long_password = "ñ" * 40
        truncated = "ñ" * (BCRYPT_MAX_BYTES // 2)

        # Act
        hashed = hash_password(long_password)

        # Assert
        assert len(long_password.encode("utf-8")) > BCRYPT_MAX_BYTES
        assert verify_password(truncated, hashed) is True

    def test_a_password_within_the_limit_is_not_truncated(self) -> None:
        """The truncation must not blur two passwords that differ inside 72 bytes."""
        # Arrange
        hashed = hash_password("a" * 71)

        # Assert
        assert verify_password("a" * 70, hashed) is False
        assert verify_password("a" * 71, hashed) is True


@pytest.mark.unit
class TestOpaqueTokens:
    """A session, an invitation and a recovery link are all the same shape."""

    def test_tokens_are_unique(self) -> None:
        """Two calls never produce the same token."""
        assert len({generate_token() for _ in range(100)}) == 100

    def test_tokens_are_url_safe(self) -> None:
        """They travel inside a link, so they cannot need escaping."""
        # Act
        token = generate_token()

        # Assert
        assert all(character.isalnum() or character in "-_" for character in token)

    def test_tokens_are_long_enough_not_to_be_guessed(self) -> None:
        """32 random bytes: there is nothing to brute-force."""
        assert len(generate_token()) >= 32

    def test_the_stored_form_is_not_the_token(self) -> None:
        """What the database holds must not let anybody in.

        This is the whole reason the column is called `token_hash`: a stolen
        dump of `sessions` or `credential_tokens` is not a set of valid
        credentials.
        """
        # Arrange
        token = generate_token()

        # Act
        stored = hash_token(token)

        # Assert
        assert stored != token
        assert token not in stored

    def test_hashing_is_deterministic(self) -> None:
        """The same token always resolves to the same row, or none does."""
        # Arrange
        token = generate_token()

        # Assert
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_hash_differently(self) -> None:
        """Two sessions must never collide onto one row."""
        assert hash_token(generate_token()) != hash_token(generate_token())

    def test_the_stored_form_has_the_length_the_column_declares(self) -> None:
        """`String(64)` is not a guess: SHA-256 in hex is exactly 64 characters."""
        assert len(hash_token(generate_token())) == 64


@pytest.mark.unit
class TestCredentialTokens:
    """Invitation and recovery share `generate_token` with the session.

    They used to have a generator of their own. They do not need one: what
    makes a token safe here is its entropy and the fact that only its hash is
    stored, and both are the same for the three uses.
    """

    def test_an_invitation_never_repeats_a_session(self) -> None:
        """The three uses draw from the same pool and still never collide."""
        assert len({generate_token() for _ in range(100)}) == 100
