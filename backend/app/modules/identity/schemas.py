"""Identity schemas: the HTTP contract and the contract towards other modules."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.identity.models import AccessEventKind, UserRole
from app.modules.identity.permissions import Level, Section

PASSWORD_MIN = 8
PASSWORD_MAX = 72  # bcrypt's hard limit
PHONE_MIN = 6


class UserCreate(BaseModel):
    """Payload to create an access.

    There is no password field, and that is the point: the owner hands out
    accesses, not credentials. The person sets their own from the invitation.
    """

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    # Required: the invitation and the recovery link travel by WhatsApp.
    phone: str = Field(min_length=PHONE_MIN, max_length=20)
    role: UserRole = UserRole.SALES


class UserUpdate(BaseModel):
    """Payload to update an access. Every field is optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, min_length=PHONE_MIN, max_length=20)
    role: UserRole | None = None


class UserRead(BaseModel):
    """An access as exposed by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    last_name: str | None
    phone: str
    role: UserRole
    is_active: bool
    activated_at: datetime | None
    locked_until: datetime | None
    created_at: datetime

    @property
    def state(self) -> str:
        """The four states of the spec, derived rather than stored."""
        if not self.is_active:
            return "DESACTIVADO"
        if self.activated_at is None:
            return "INVITADO"
        if self.locked_until is not None:
            return "BLOQUEADO"
        return "ACTIVO"


class UserList(BaseModel):
    """A page of accesses."""

    items: list[UserRead]
    total: int
    skip: int
    limit: int


class LoginRequest(BaseModel):
    """Credentials submitted at login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class CurrentUser(BaseModel):
    """Who is working, and what they may reach.

    The permission map travels with the user so the menu is drawn from what the
    backend actually enforces. Without it the frontend would need its own copy
    of the rules, and two copies of a rule are one rule and one bug.
    """

    user: UserRead
    permissions: dict[Section, Level]


class LoginResponse(BaseModel):
    """A successful login."""

    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PasswordResetRequest(BaseModel):
    """Ask for a recovery link."""

    email: EmailStr


class PasswordSet(BaseModel):
    """Redeem a single-use link and set a password."""

    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class PasswordChangeRequest(BaseModel):
    """Change your own password while authenticated."""

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class AccessEventRead(BaseModel):
    """One line of the access log."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    kind: AccessEventKind
    user_id: int | None
    actor_user_id: int | None
    attempted_email: str | None
    resource: str | None
    reason: str | None
    details: dict[str, Any] | None


class AccessEventList(BaseModel):
    """A page of the access log."""

    items: list[AccessEventRead]
    total: int
    skip: int
    limit: int
