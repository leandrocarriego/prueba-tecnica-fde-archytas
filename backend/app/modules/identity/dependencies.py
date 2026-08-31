"""FastAPI dependencies for authentication and authorisation.

This is the one file of this module that other modules may import, and the
reason is timing: a request has to know whether it may continue *before* its
handler runs, and an event cannot answer that in time. The exception is fixed
by file name in `tests/architecture/test_module_boundaries.py`.

Because of that, a route in any module declares what it needs — a section and
a level — without ever importing `UserRole`. Roles are identity's vocabulary
and they stay here.
"""

from collections.abc import Collection
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, params, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.models import User
from app.modules.identity.permissions import Level, Section, level_for
from app.shared.sections import BusinessSection

__all__ = [
    "BusinessSection",
    "ActorDirectory",
    "Assignee",
    "ActorDirectoryDep",
    "CurrentUser",
    "IdentityDep",
    "Level",
    "Section",
    "VisibleSections",
    "get_current_user",
    "get_identity_service",
    "require_section",
    "visible_sections",
]
from app.modules.identity.service import IdentityService

# Which parts of the business each role gets to read *about*, as opposed to
# which screens they reach. The two questions are different and so are their
# answers: `Section` above says whether somebody may open the prices screen,
# `BusinessSection` here says whose manual changes show up in their history
# (RF-18, RF-19). The owner reads all three; everybody else reads their own.
#
# It lives in this file because this file is the one identity surface another
# module may import, and because translating a role into anything at all is
# identity's job — `operations` filters its log without ever learning that
# `UserRole` exists.
ROLE_SECTIONS: dict[str, frozenset[BusinessSection]] = {
    "OWNER": frozenset(BusinessSection),
    "PURCHASING": frozenset({BusinessSection.PURCHASING}),
    "SALES": frozenset({BusinessSection.SALES}),
}

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


def visible_sections(user: User) -> frozenset[BusinessSection]:
    """The parts of the business whose manual changes this person may read.

    An unknown role reads nothing. That is the safe end of the mistake: a role
    added without deciding what it sees shows an empty history, instead of
    showing somebody else's.
    """
    return ROLE_SECTIONS.get(user.role.value, frozenset())


async def get_visible_sections(current_user: CurrentUser) -> frozenset[BusinessSection]:
    """The same answer, as a dependency a route can declare."""
    return visible_sections(current_user)


VisibleSections = Annotated[frozenset[BusinessSection], Depends(get_visible_sections)]


@dataclass(frozen=True, slots=True)
class Assignee:
    """Somebody a piece of work can be handed to, as another module sees them."""

    user_id: int
    name: str
    role: str


class ActorDirectory:
    """Turns the user ids a screen is about into the names it shows.

    It is here for the same reason `require_section` is: this is the HTTP
    composition surface of `identity`, and a screen owned by another module
    cannot ask that module for a name without importing it. `operations` stores
    the id of whoever made a change — no foreign key, no name — and the name is
    resolved on the way out, once, by the one file allowed to cross.

    One `get` per distinct id, and that is not a loop worth optimising: a page
    of the history has at most a handful of authors, and this business has
    three people.
    """

    def __init__(self, service: IdentityService) -> None:
        self.service = service

    async def names_for(self, user_ids: Collection[int]) -> dict[int, str]:
        """The name behind each id. An id with no account left is left out."""
        names: dict[int, str] = {}
        for user_id in set(user_ids):
            user = await self.service.users.get(user_id)
            if user is None:
                continue
            names[user_id] = (
                f"{user.name} {user.last_name}".strip() if user.last_name else user.name
            )
        return names

    async def who_reaches(self, section: Section, level: Level = Level.WRITE) -> list[Assignee]:
        """The active people who reach this section at this level.

        It is here for the same reason `names_for` is: the question is about
        roles, roles are identity's vocabulary, and a module that needs to hand
        work to a person cannot ask who those people are without importing the
        module that knows (Artículo IV). `dependencies.py` is the one file
        allowed to answer.

        `messaging` uses it for RF-30 of 007 — a message is assigned to the
        owner or to somebody in purchasing, **and to nobody else**. The route
        used to take any `user_id` at all, so the screen could hand a supplier's
        claim to whoever does not work on suppliers.
        """
        users, _ = await self.service.list_users(limit=200)
        return [
            Assignee(user_id=user.id, name=user.name, role=user.role.value)
            for user in users
            if user.is_active and level_for(user.role.value, section) >= level
        ]


def get_actor_directory(service: IdentityDep) -> ActorDirectory:
    """Provide the directory for a request."""
    return ActorDirectory(service)


ActorDirectoryDep = Annotated[ActorDirectory, Depends(get_actor_directory)]
