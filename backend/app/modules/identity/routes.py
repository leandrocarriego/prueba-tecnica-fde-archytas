"""HTTP routes for the identity module.

Three routers instead of one. `/auth` is the session surface — getting in,
reading who you are, changing your own password, recovering it — and everyone
uses it. `/users` is administration and belongs to the owner. `/access-log` is
the record, and belongs to the owner too. Splitting them keeps each group's
authorisation visible at a glance.

Every route states who may call it: a public route says so in its docstring
and is listed in the architecture test, and a protected one declares a
dependency. There is no implicit access.
"""

from typing import Annotated

from fastapi import APIRouter, Header, Query, status
from pydantic import BaseModel

from app.logging import get_logger
from app.modules.identity.dependencies import (
    CurrentUser,
    IdentityDep,
    Level,
    Section,
    require_section,
)
from app.modules.identity.models import AccessEventKind, TokenPurpose
from app.modules.identity.permissions import permissions_for
from app.modules.identity.schemas import (
    AccessEventList,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordSet,
    UserCreate,
    UserList,
    UserRead,
    UserUpdate,
)
from app.modules.identity.schemas import (
    CurrentUser as CurrentUserRead,
)

logger = get_logger(__name__)

# Deliberately vague: the wording must read the same whether or not the address
# belongs to an account.
PASSWORD_RESET_ACK = "Si ese correo corresponde a un acceso, el enlace ya salió"

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

SkipParam = Annotated[int, Query(ge=0, description="Rows to skip")]
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
SearchParam = Annotated[str | None, Query(max_length=255, description="Match name or email")]
KindParam = Annotated[list[AccessEventKind] | None, Query(description="Filter by kind")]
# Read to spare the caller's own session when their password changes; never to
# identify anybody, which is what the dependency is for.
BearerHeader = Annotated[str | None, Header(alias="Authorization")]


class MessageResponse(BaseModel):
    """A bare acknowledgement."""

    message: str


class TokenStatus(BaseModel):
    """Whether a single-use link still works."""

    usable: bool


auth_router = APIRouter(prefix="/auth", tags=["Auth"])
users_router = APIRouter(prefix="/users", tags=["Users"])
access_log_router = APIRouter(prefix="/access-log", tags=["Access log"])


def _bearer(header: str | None) -> str | None:
    """Return the raw token of an Authorization header, if it carries one."""
    if header and header.lower().startswith("bearer "):
        return header[7:]
    return None


# --- Session -------------------------------------------------------------


@auth_router.post("/login", summary="Exchange credentials for a session")
async def login(payload: LoginRequest, service: IdentityDep) -> LoginResponse:
    """Public: anyone may attempt to log in.

    An unknown email, a wrong password, a deactivated access and a temporarily
    locked one all fail the same way, so the endpoint cannot be used to find
    out which addresses exist or which accounts are blocked.
    """
    token, user = await service.authenticate(payload.email, payload.password)
    return LoginResponse(access_token=token, user=user)


@auth_router.get("/me", summary="Who is working, and what they may reach")
async def read_current_user(current_user: CurrentUser) -> CurrentUserRead:
    """Any live session, restricted to the caller's own account.

    Returns the permission map so the menu is drawn from what the backend
    enforces instead of from a second copy of the rules in the frontend.
    """
    return CurrentUserRead(
        user=UserRead.model_validate(current_user),
        permissions=permissions_for(current_user.role.value),
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Close your session")
async def logout(
    current_user: CurrentUser, service: IdentityDep, authorization: BearerHeader = None
) -> None:
    """Any live session. Closes the one the caller is using, not the others."""
    token = _bearer(authorization)
    if token:
        await service.logout(token)


@auth_router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change your own password",
)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser,
    service: IdentityDep,
    authorization: BearerHeader = None,
) -> None:
    """Any live session, and only on the caller's own account.

    The target is taken from the session, never from the body, so this route
    cannot be pointed at somebody else. Every other session of the same person
    is closed: a password that stopped being valid must not survive elsewhere.
    """
    await service.change_password(
        current_user.id,
        payload.current_password,
        payload.new_password,
        current_token=_bearer(authorization),
    )


@auth_router.post(
    "/password-reset/request",
    status_code=status.HTTP_200_OK,
    summary="Ask for a recovery link",
)
async def request_password_reset(
    payload: PasswordResetRequest, service: IdentityDep
) -> MessageResponse:
    """Public, and always answers the same.

    Saying whether the address is registered would turn a recovery form into a
    way of finding out who has an account, so the answer never varies. The link
    itself goes out by WhatsApp and is never returned here.
    """
    await service.request_password_reset(payload.email)
    logger.info("Password reset requested")
    return MessageResponse(message=PASSWORD_RESET_ACK)


@auth_router.get("/password-reset/{token}", summary="Is this recovery link still good?")
async def check_reset_token(token: str, service: IdentityDep) -> TokenStatus:
    """Public: the single-use token is the credential."""
    return TokenStatus(usable=await service.token_is_usable(token, TokenPurpose.PASSWORD_RESET))


@auth_router.post(
    "/password-reset/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password with a recovery link",
)
async def confirm_password_reset(token: str, payload: PasswordSet, service: IdentityDep) -> None:
    """Public: the single-use token is the credential. Spending it kills it."""
    await service.redeem_token(token, TokenPurpose.PASSWORD_RESET, payload.new_password)


@auth_router.get("/invitation/{token}", summary="Is this invitation still good?")
async def check_invitation(token: str, service: IdentityDep) -> TokenStatus:
    """Public: whoever was invited holds no session yet."""
    return TokenStatus(usable=await service.token_is_usable(token, TokenPurpose.INVITATION))


@auth_router.post(
    "/invitation/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Accept an invitation and set your password",
)
async def accept_invitation(token: str, payload: PasswordSet, service: IdentityDep) -> None:
    """Public: the invitation is the credential, and it works once.

    This is the only way a password is ever set for the first time. The owner
    never types one for somebody else.
    """
    await service.redeem_token(token, TokenPurpose.INVITATION, payload.new_password)


# --- Administration ------------------------------------------------------


@users_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_section(Section.ACCESS_ADMIN, Level.WRITE)],
    summary="Create an access and invite its person",
)
async def create_user(
    payload: UserCreate, current_user: CurrentUser, service: IdentityDep
) -> UserRead:
    """Owner only. Returns no credential: the invitation goes out by WhatsApp."""
    return await service.create_user(payload, actor_id=current_user.id)


@users_router.get(
    "",
    dependencies=[require_section(Section.ACCESS_ADMIN)],
    summary="List accesses",
)
async def list_users(
    service: IdentityDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    q: SearchParam = None,
) -> UserList:
    """Owner only: administering accesses is the owner's, and so is seeing them."""
    items, total = await service.list_users(skip=skip, limit=limit, query=q)
    return UserList(items=items, total=total, skip=skip, limit=limit)


@users_router.get(
    "/{user_id}",
    dependencies=[require_section(Section.ACCESS_ADMIN)],
    summary="Read one access",
)
async def get_user(user_id: int, service: IdentityDep) -> UserRead:
    """Owner only."""
    return await service.get_user(user_id)


@users_router.patch(
    "/{user_id}",
    dependencies=[require_section(Section.ACCESS_ADMIN, Level.WRITE)],
    summary="Update an access",
)
async def update_user(
    user_id: int, payload: UserUpdate, current_user: CurrentUser, service: IdentityDep
) -> UserRead:
    """Owner only: this route can change a role, so it changes what someone may do."""
    return await service.update_user(user_id, payload, actor_id=current_user.id)


@users_router.post(
    "/{user_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_section(Section.ACCESS_ADMIN, Level.WRITE)],
    summary="Deactivate an access",
)
async def deactivate_user(user_id: int, current_user: CurrentUser, service: IdentityDep) -> None:
    """Owner only, and never on themselves.

    The access is deactivated, not deleted: everything it authored has to keep
    pointing at a real person. Its open sessions are closed on the spot.
    """
    await service.deactivate_user(user_id, actor_id=current_user.id)


@users_router.post(
    "/{user_id}/reactivate",
    dependencies=[require_section(Section.ACCESS_ADMIN, Level.WRITE)],
    summary="Reactivate an access",
)
async def reactivate_user(
    user_id: int, current_user: CurrentUser, service: IdentityDep
) -> UserRead:
    """Owner only. The same person comes back, with a new invitation and no old password."""
    return await service.reactivate_user(user_id, actor_id=current_user.id)


# --- The record ----------------------------------------------------------


@access_log_router.get(
    "",
    dependencies=[require_section(Section.ACCESS_LOG)],
    summary="Who got in, and who was turned away",
)
async def list_access_events(
    service: IdentityDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    kind: KindParam = None,
) -> AccessEventList:
    """Owner only: nobody else sees other people's activity."""
    items, total = await service.list_access_events(skip=skip, limit=limit, kinds=kind)
    return AccessEventList(items=items, total=total, skip=skip, limit=limit)
