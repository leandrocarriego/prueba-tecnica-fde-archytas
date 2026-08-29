"""User factory for the tests.

Writes through the models rather than through `IdentityService`, so a test can
build the exact state it needs — an inactive account, a user with no credential
— without going around the service it is about to exercise.
"""

import itertools
from datetime import UTC, datetime
from functools import cache
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User, UserPassword, UserRole
from app.modules.identity.security import hash_password

DEFAULT_PASSWORD = "cordillera-2026"

# Emails and names are unique per process: `users.email` is unique, and a test
# that does not care about the address should never collide with another.
_sequence = itertools.count(1)


@cache
def cached_hash(password: str) -> str:
    """Hash a password once per distinct value.

    bcrypt is deliberately slow (a few hundred milliseconds per call). Almost
    every fixture uses the same password, so hashing it once keeps the suite
    fast without weakening the cost factor the application ships with.
    """
    return hash_password(password)


class UserFactory:
    """Builds users, with or without a usable credential."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        email: str | None = None,
        name: str | None = None,
        role: UserRole = UserRole.SALES,
        password: str | None = DEFAULT_PASSWORD,
        is_active: bool = True,
        phone: str | None = None,
        **kwargs: Any,
    ) -> User:
        """Create a user.

        `password=None` leaves the account with no credential, which is the
        state of somebody who was invited and has not redeemed the invitation
        yet — so it also leaves `activated_at` unset, because those two go
        together in the application and a fixture that split them would be
        building a state the system never produces.
        """
        index = next(_sequence)
        kwargs.setdefault("activated_at", datetime.now(UTC) if password is not None else None)
        user = User(
            email=email or f"user{index}@example.com",
            name=name or f"Test User {index}",
            # Not optional any more: the invitation and the recovery link
            # travel by WhatsApp, so every access carries a number.
            phone=phone or f"+54911{index:07d}",
            role=role,
            is_active=is_active,
            **kwargs,
        )
        session.add(user)
        await session.flush()

        if password is not None:
            session.add(
                UserPassword(user_id=user.id, hashed_password=cached_hash(password)),
            )
            await session.flush()

        await session.refresh(user)
        return user

    @staticmethod
    async def create_batch(session: AsyncSession, count: int, **kwargs: Any) -> list[User]:
        """Create several users sharing the same attributes."""
        return [await UserFactory.create(session, **kwargs) for _ in range(count)]
