"""HTTP routes for the messaging module.

Sales reaches none of them: RF-46 of 007 keeps the inbox to whoever answers a
supplier — purchasing — and to the owner, who is admitted everywhere.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import (
    ActorDirectoryDep,
    Assignee,
    CurrentUser,
    Level,
    Section,
    require_section,
)
from app.modules.messaging.models import MessageKind, MessageState
from app.modules.messaging.schemas import (
    MessageAssignment,
    MessageList,
    MessageNote,
    MessageRead,
)
from app.modules.messaging.service import MessagingService
from app.shared.errors import ValidationError

# What somebody reads when a message is handed to a person who does not work on
# them (RF-30). In Spanish, like every refusal that reaches a screen.
NOT_ASSIGNABLE = "Esa persona no trabaja sobre los mensajes de proveedores"

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

Session = Annotated[AsyncSession, Depends(get_session)]


def get_messaging_service(session: Session) -> MessagingService:
    """Provide the messaging service for a request."""
    return MessagingService(session)


MessagingDep = Annotated[MessagingService, Depends(get_messaging_service)]

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get(
    "",
    dependencies=[require_section(Section.SUPPLIER_MESSAGES, Level.READ)],
    summary="The messages of the portal inbox",
)
async def list_messages(
    service: MessagingDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    kind: Annotated[MessageKind | None, Query(description="By kind")] = None,
    state: Annotated[MessageState | None, Query(description="By state")] = None,
    supplier_name: Annotated[str | None, Query(max_length=255)] = None,
) -> MessageList:
    """The owner and purchasing (RF-22 to RF-26, RF-31 of 007)."""
    return await service.list_messages(
        skip=skip, limit=limit, kind=kind, state=state, supplier_name=supplier_name
    )


@router.get(
    "/senders",
    dependencies=[require_section(Section.SUPPLIER_MESSAGES, Level.READ)],
    summary="The suppliers the inbox can be filtered by",
)
async def list_senders(service: MessagingDep) -> list[str]:
    """The owner and purchasing (RF-26 of 007).

    What the filter offers is the register as **this** module keeps it, which is
    the same set of values `supplier_name` matches: a list taken from anywhere
    else would offer names that filter nothing.
    """
    return await service.senders()


@router.get(
    "/assignees",
    dependencies=[require_section(Section.SUPPLIER_MESSAGES, Level.WRITE)],
    summary="Who a message can be handed to",
)
async def list_assignees(directory: ActorDirectoryDep) -> list[Assignee]:
    """The owner and purchasing (RF-30 of 007).

    Derived from the permission matrix and not from a list of roles written
    here: whoever reaches this section in writing is exactly whoever can be
    made responsible for one of its messages, and keeping the two in one place
    is what stops them from drifting apart. Sales does not reach it, so Julián
    does not appear among the assignable.
    """
    return await directory.who_reaches(Section.SUPPLIER_MESSAGES)


@router.post(
    "/{message_id}/resolution",
    dependencies=[require_section(Section.SUPPLIER_MESSAGES, Level.WRITE)],
    summary="Mark a message as dealt with",
)
async def resolve_message(
    message_id: int, current_user: CurrentUser, service: MessagingDep
) -> MessageRead:
    """The owner and purchasing (RF-28, RF-29 of 007).

    Who resolved it comes from the token, never from the body.
    """
    return await service.resolve(message_id, actor_user_id=current_user.id)


@router.put(
    "/{message_id}/assignee",
    dependencies=[require_section(Section.SUPPLIER_MESSAGES, Level.WRITE)],
    summary="Say who is responsible for a message",
)
async def assign_message(
    message_id: int,
    payload: MessageAssignment,
    directory: ActorDirectoryDep,
    service: MessagingDep,
) -> MessageRead:
    """The owner and purchasing (RF-30 of 007).

    **Who may be named is checked, and it used to not be.** The route took any
    `user_id` at all, so a supplier's claim could be handed to whoever does not
    work on suppliers — and the signed acceptance criterion says in as many
    words that Julián is not among the assignable.
    """
    assignable = {
        person.user_id for person in await directory.who_reaches(Section.SUPPLIER_MESSAGES)
    }
    if payload.assignee_user_id is not None and payload.assignee_user_id not in assignable:
        raise ValidationError(
            NOT_ASSIGNABLE, details={"assignee_user_id": payload.assignee_user_id}
        )
    return await service.assign(message_id, assignee_user_id=payload.assignee_user_id)


@router.post(
    "/{message_id}/note",
    dependencies=[require_section(Section.SUPPLIER_MESSAGES, Level.WRITE)],
    summary="Write a note on a message",
)
async def annotate_message(
    message_id: int, payload: MessageNote, service: MessagingDep
) -> MessageRead:
    """The owner and purchasing (RF-32 of 007)."""
    return await service.annotate(message_id, note=payload.note)
