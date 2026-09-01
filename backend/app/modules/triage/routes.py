"""HTTP routes for the triage module.

**The queue is everybody's, and each person sees their own part of it.** Until
011 the two case routes asked for `Section.PRICES, WRITE`, which was right while
the only thing in the queue was the price list and stopped being right the day
the sales rows started opening cases: it locked the screen against the one
person the sales half belongs to.

So they now declare what is actually true — *you have to be signed in* — and the
fine-grained permission moves into the service, where it belongs: which area a
case is about is a fact of the **row**, and a `Depends` runs before any row is
read. `PY-09` asks every route to declare its authorisation and both still do;
it is the same shape the history of `operations` already has, and neither route
is public.

**Most of the queue stays purchasing's, and that is the point rather than an
accident.** The seven kinds that predate 011 all come out of the portal
ingestion, and resolving what the ingestion sets aside is Marcela's work — the
prices included, which is what the brief says of her in the client's own words.
What changes is that the queue can now hold a case that is *not* hers, and the
door stops being the thing that decides.

The three `/rules` routes do **not** open, deliberately: every learned rule is a
rule about prices — the four kinds 011 adds pass `remember=False`, because
learning is out of scope — so they stay where they were, and opening them would
only add one more surface to leak an area through.

`require_section()` and `visible_sections()` both come from
`identity.dependencies`, the one file that crosses a module boundary.
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
    VisibleSections,
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
from app.shared.sections import BusinessSection

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
SectionParam = Annotated[
    BusinessSection | None, Query(description="Only the cases of one area of the business")
]

router = APIRouter(prefix="/triage", tags=["Triage"])


@router.get("/cases", summary="What the platform set aside")
async def list_cases(
    service: TriageDep,
    visible: VisibleSections,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    status_filter: StatusParam = CaseStatus.PENDING,
    kind: KindParam = None,
    batch_id: BatchParam = None,
    section: SectionParam = None,
) -> CaseList:
    """Anybody signed in, and each of them sees the areas they reach (RF-12).

    `VisibleSections` is a dependency and not a parameter the caller may send:
    it is read off the token, so no query string can widen it. `section` can
    only ever narrow it.
    """
    return await service.list_cases(
        skip=skip,
        limit=limit,
        status=status_filter,
        kind=kind,
        batch_id=batch_id,
        visible=visible,
        section=section,
    )


@router.post("/cases/{case_id}/resolution", summary="Decide what to do with a case")
async def resolve_case(
    case_id: int,
    payload: ResolutionRequest,
    current_user: CurrentUser,
    service: TriageDep,
    directory: ActorDirectoryDep,
    visible: VisibleSections,
) -> CaseRead:
    """Anybody signed in, for a case of an area they reach — and no other.

    Resolving somebody else's area is refused with a 403 by the service, because
    the area is a fact of the case and only the case knows it (RF-13).

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
            visible=visible,
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
