"""What `catalog` does when something happens elsewhere.

It never asks anybody anything. A batch was normalised, a history was read, a
person resolved a case, the owner moved a parameter: each of those is a fact
this module reacts to, in the transaction of whoever published it.
"""

from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.catalog.service import (
    HIGHLIGHT_THRESHOLD_KEY,
    MISSING_PRODUCT,
    UNKNOWN_CATEGORY,
    UNKNOWN_PRODUCT,
    UNREADABLE_ROW,
    CatalogService,
)
from app.shared.events import (
    BusinessParameterChanged,
    PriceHistoryNormalized,
    PriceListNormalized,
    QuarantineCaseResolved,
    QuarantineRuleRedecided,
    QuarantineRuleRevoked,
    events,
)

logger = get_logger(__name__)

INCORPORATE = "incorporate"
DISCONTINUE = "discontinue"


def _price_of(decision: dict[str, object]) -> Decimal | None:
    """Read the price a person typed, without trusting it to be a number.

    Parsing is not enough to trust it. `Decimal` builds `nan`, `snan` and
    `Infinity` without complaining, and this is the third door into
    `core.product_price.price` — the other two, `ParameterSpec._as_number` and
    `CatalogService._as_number`, already refuse them. A `NaN` that got through
    here would not sit quietly: the next daily list compares `variation >
    threshold` against it, `Decimal` signals on that comparison, and the whole
    batch falls over. That is not quarantine, it is an outage (Article II).

    Negative is refused for the same reason `ingestion` refuses it upstream: a
    price below zero is not a price, and a correction must not be the way in for
    what the daily list already sends to quarantine. Zero stays valid, exactly
    as the parser has it.
    """
    raw = decision.get("price")
    if raw is None:
        return None
    try:
        price = Decimal(str(raw))
    except (InvalidOperation, ArithmeticError):
        logger.warning("A decision carried a price that is not a number")
        return None
    if not price.is_finite():
        logger.warning("A decision carried a price that is not a finite number")
        return None
    if price < 0:
        logger.warning("A decision carried a negative price")
        return None
    return price


@events.subscribe(PriceListNormalized)
async def apply_batch(event: PriceListNormalized, session: AsyncSession) -> None:
    """Register the price in force of every known product of the batch."""
    await CatalogService(session).apply_price_batch(
        batch_id=event.batch_id,
        rows=event.rows,
        seen_codes=event.seen_codes,
        quarantined=event.quarantined,
        job_run_id=event.job_run_id,
    )


@events.subscribe(PriceHistoryNormalized)
async def import_history(event: PriceHistoryNormalized, session: AsyncSession) -> None:
    """Bring in the history the portal already published for a product."""
    await CatalogService(session).import_published_history(
        product_code=event.product_code, points=event.points
    )


@events.subscribe(QuarantineCaseResolved)
async def apply_decision(event: QuarantineCaseResolved, session: AsyncSession) -> None:
    """Do what the person decided: incorporate, price, discontinue or keep.

    Two of those four are the platform's only way of **loading** a datum by
    hand, and RF-09 covers loading with the same words it covers modifying. So
    who decided and when travel down with the decision: the event already knows
    both, and the module that writes the datum is the one that has to say so
    (`ManualChangeRecorded`). Reading them off `datetime.now()` here would date
    the line by however long the queue behind that person took.
    """
    service = CatalogService(session)
    action = str(event.decision.get("action", ""))
    payload = event.payload

    if event.kind == UNKNOWN_PRODUCT and action == INCORPORATE:
        await service.incorporate_product(
            product_code=str(payload.get("product_code", "")),
            description=str(payload.get("description", "")),
            price=_price_of(event.decision) or _price_of(payload),
            rule_id=event.rule_id,
            actor_user_id=event.decided_by_user_id,
            decided_at=event.decided_at,
        )
    elif event.kind == UNREADABLE_ROW:
        price = _price_of(event.decision)
        code = str(event.decision.get("product_code") or payload.get("product_code") or "")
        if price is not None and code:
            await service.set_price_by_code(
                product_code=code,
                price=price,
                actor_user_id=event.decided_by_user_id,
                decided_at=event.decided_at,
            )
    elif event.kind == UNKNOWN_CATEGORY:
        # The decision is about a **written form**, not about one product: the
        # matcher carries the text, and applying it classifies every product
        # that came with it (RF-24, RF-25 of 008).
        category_id = event.decision.get("category_id")
        text = str(event.matcher.get("category_text") or payload.get("category_text") or "")
        if category_id is not None and text:
            await service.learn_category_alias(
                rule_id=event.rule_id, category_text=text, category_id=int(category_id)
            )
    elif event.kind == MISSING_PRODUCT:
        product_id = int(payload.get("product_id", 0) or 0)
        if product_id and action == DISCONTINUE:
            await service.discontinue(product_id)
        elif product_id:
            await service.keep_active(product_id)


@events.subscribe(QuarantineRuleRevoked)
async def undo_rule(event: QuarantineRuleRevoked, session: AsyncSession) -> None:
    """Undo what that rule had done here, so its cases come back (RF-37).

    Two shapes of rule reach this module, and each undoes its own thing: a
    product this rule incorporated is removed, and an equivalence this rule
    projected is dropped, leaving its products «sin rubro» and back in the
    queue (RF-30, RF-31 of 008).
    """
    service = CatalogService(session)
    await service.undo_rule(event.rule_id)
    if event.kind == UNKNOWN_CATEGORY:
        await service.forget_category_alias(event.rule_id)


@events.subscribe(QuarantineRuleRedecided)
async def repoint_rule(event: QuarantineRuleRedecided, session: AsyncSession) -> None:
    """Point an equivalence at another rubro and move what it classified.

    Not a revocation: nothing goes back to review. That distinction is the
    easiest thing to get wrong in 008 — if the products show up in the queue
    after this, RF-31 was implemented where RF-29 went.
    """
    if event.kind != UNKNOWN_CATEGORY:
        return
    category_id = event.decision.get("category_id")
    if category_id is None:
        return
    await CatalogService(session).repoint_category_alias(
        rule_id=event.rule_id, category_id=int(category_id)
    )


@events.subscribe(BusinessParameterChanged)
async def remember_parameter(event: BusinessParameterChanged, session: AsyncSession) -> None:
    """Keep the threshold this module reads while it applies a batch (RF-19)."""
    if event.key != HIGHLIGHT_THRESHOLD_KEY:
        return
    await CatalogService(session).remember_setting(event.key, event.value)
