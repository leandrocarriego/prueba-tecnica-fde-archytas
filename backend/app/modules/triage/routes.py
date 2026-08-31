"""HTTP routes for the triage module.

The review queue belongs to whoever handles purchasing — it is Marcela's screen
in the spec — and to the owner, who is admitted everywhere. Nothing here is
public: `require_section()` comes from `identity.dependencies`, the one file
that crosses a module boundary.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import (
    ActorDirectory,
    ActorDirectoryDep,
    CurrentUser,
    Level,
    Section,
    require_section,
)
from app.modules.triage.models import CaseStatus
from app.modules.triage.schemas import (
    CaseList,
    CaseRead,
    RedecisionRequest,
    ResolutionRequest,
    RuleRead,
)
from app.modules.triage.service import TriageService
from app.shared.errors import DomainError

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

Session = Annotated[AsyncSession, Depends(get_session)]


def get_triage_service(session: Session) -> TriageService:
    """Provide the triage service for a request."""
    return TriageService(session)


TriageDep = Annotated[TriageService, Depends(get_triage_service)]

SkipParam = Annotated[int, Query(ge=0, description="Rows to skip")]
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
StatusParam = Annotated[CaseStatus | None, Query(description="Filter by state")]
KindParam = Annotated[str | None, Query(max_length=50, description="Filter by kind of case")]
BatchParam = Annotated[int | None, Query(description="Only the cases of one run")]

router = APIRouter(prefix="/triage", tags=["Triage"])


@router.get(
    "/cases",
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="What the update set aside",
)
async def list_cases(
    service: TriageDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    status_filter: StatusParam = CaseStatus.PENDING,
    kind: KindParam = None,
    batch_id: BatchParam = None,
) -> CaseList:
    """The owner and purchasing: this is the screen where the queue is emptied."""
    return await service.list_cases(
        skip=skip, limit=limit, status=status_filter, kind=kind, batch_id=batch_id
    )


@router.post(
    "/cases/{case_id}/resolution",
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="Decide what to do with a case",
)
async def resolve_case(
    case_id: int,
    payload: ResolutionRequest,
    current_user: CurrentUser,
    service: TriageDep,
    directory: ActorDirectoryDep,
) -> CaseRead:
    """The owner and purchasing.

    Who decided is taken from the token, never from the body: RF-32 asks for the
    person who took the decision, and a body could name somebody else. The name
    travels as a plain string — the first name, which is how the business names
    these people — and not as a user of another module (Artículo IV).

    A refusal on the way out gets one more name put on it, and that is why this
    route knows about `identity` at all: a decision this queue publishes can be
    turned away by whoever handles the event, and the one refusal that happens
    for a *human* reason — an amount somebody already corrected — names that
    somebody by id, because the module that raised it may not read `identity`.
    Here it may: `dependencies.py` is the one file of `identity` a module is
    allowed to cross, and this is the same trip `operations` makes to put a name
    beside each line of the history.
    """
    try:
        return await service.resolve(
            case_id,
            decision=payload.decision,
            user_id=current_user.id,
            user_name=current_user.name,
            remember=payload.remember,
        )
    except DomainError as refusal:
        await _name_whoever_corrected(refusal, directory)
        raise


async def _name_whoever_corrected(refusal: DomainError, directory: ActorDirectory) -> None:
    """Put a name next to the id a refusal carries, when it carries one.

    `catalog` refuses an amount a correction holds back and says «está corregido
    a mano», with `corrected_by_user_id` in `details` and no name: naming the
    person from there would be the import the Artículo IV forbids. What the
    person reading the screen was promised is «hay una corrección de Julián», so
    the id is turned into a name here, at the edge, exactly the way
    `operations.routes._name_the_authors` does it for the history.

    Silent about anything else on purpose. A refusal that carries no such id —
    a case already resolved, a product that is not there — passes through
    untouched, and an id whose account is gone leaves the sentence as it was
    rather than inventing an empty name. It runs on a transaction that is
    already going to be rolled back and only reads from it: the refusal is
    re-raised untouched apart from the name, and `get_session` throws the rest
    away.
    """
    user_id = refusal.details.get("corrected_by_user_id")
    if not isinstance(user_id, int):
        return
    name = (await directory.names_for([user_id])).get(user_id)
    if name is not None:
        refusal.details["corrected_by_name"] = name


@router.get(
    "/rules",
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="The decisions that are being applied on their own",
)
async def list_rules(
    service: TriageDep,
    include_revoked: Annotated[bool, Query(description="Also the ones already revoked")] = False,
    kind: KindParam = None,
) -> list[RuleRead]:
    """The owner and purchasing (RF-36)."""
    return await service.list_rules(include_revoked=include_revoked, kind=kind)


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="Leave a rule without effect",
)
async def revoke_rule(rule_id: int, current_user: CurrentUser, service: TriageDep) -> None:
    """The owner and purchasing.

    The rule is revoked, not deleted, and what it was resolving comes back to
    the queue (RF-37).
    """
    await service.revoke_rule(rule_id, user_id=current_user.id)


@router.patch(
    "/rules/{rule_id}",
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="Point a rule at another decision",
)
async def redecide_rule(
    rule_id: int, payload: RedecisionRequest, current_user: CurrentUser, service: TriageDep
) -> RuleRead:
    """The owner and purchasing.

    The rule stays in force and what it had resolved is re-pointed — nothing
    comes back to the queue. That is the difference from `DELETE` right below,
    and it is the whole of RF-28 and RF-29 of 008.
    """
    return await service.redecide_rule(rule_id, decision=payload.decision, user_id=current_user.id)
