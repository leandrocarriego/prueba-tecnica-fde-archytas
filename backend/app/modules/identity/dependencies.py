"""FastAPI dependencies for authentication and authorisation.

This is the one file of this module that other modules may import, and the
reason is timing: a request has to know whether it may continue *before* its
handler runs, and an event cannot answer that in time. The exception is fixed
by file name in `tests/architecture/test_module_boundaries.py`.

Because of that, a route in any module declares what it needs — a section and
a level — without ever importing `UserRole`. Roles are identity's vocabulary
and they stay here.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, params, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.models import User
from app.modules.identity.permissions import Level, Section, level_for

__all__ = [
    "CurrentUser",
    "IdentityDep",
    "Level",
    "Section",
    "get_current_user",
    "get_identity_service",
    "require_section",
]
from app.modules.identity.service import IdentityService

bearer_scheme = HTTPBearer(auto_error=False)

Session = Annotated[AsyncSession, Depends(get_session)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_identity_service(session: Session) -> IdentityService:
    """Provide the identity service for a request."""
    return IdentityService(session)


IdentityDep = Annotated[IdentityService, Depends(get_identity_service)]


async def get_current_user(
    request: Request, credentials: Credentials, service: IdentityDep
) -> User:
    """Return the person behind the session, or fail with 401."""
    if credentials is None:
        raise UNAUTHORIZED
    user = await service.resolve_session(credentials.credentials)
    if user is None:
        raise UNAUTHORIZED
    # The middleware that records a refusal reads this: by the time a 403 is
    # raised, the dependency that knew who was calling is long gone.
    request.state.current_user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_section(section: Section, level: Level = Level.READ) -> params.Depends:
    """Build a dependency that admits whoever reaches `level` in `section`.

    Levels are ordered, so asking for `READ` admits somebody with `WRITE`.
    Seeing a section never implies being able to change it: that is the whole
    point of asking for a level and not just a role.
    """

    async def checker(request: Request, current_user: CurrentUser) -> User:
        granted = level_for(current_user.role.value, section)
        if granted < level:
            request.state.denied_reason = (
                "SECTION_FORBIDDEN" if granted is Level.NONE else "LEVEL_FORBIDDEN"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permiso para esta sección",
            )
        return current_user

    dependency: params.Depends = Depends(checker)
    return dependency
