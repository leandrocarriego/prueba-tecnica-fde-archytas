"""H4 at its edges: the conflict, the reason, and who gets to correct.

The `Developer` walked the main paths of H4 once each in
`test_manual_corrections.py`. This file is the grid around them.

Five runs of the conflict instead of three: the portal repeating what it first
said, contradicting it, contradicting it again with the same number, coming
back with a **third** number, and going back to the original. Plus the way a
conflict is meant to be closed — a person correcting again — and the way it is
not: by itself.

Around that, the rest of what H4 promises and the `Developer` left implicit:
every reason of the catalogue and one that is not in it, a field that is not an
amount, who may correct a product over HTTP, and the borders nobody asked for —
correcting to the value it already had, a product with no price, a written
detail that is empty rather than absent.

Where a scenario overlaps with the `Developer`'s, the assertions do not: this
file reads the correction **row** rather than the screen's view of it, checks
the text the owner is actually sent, and checks that a refused correction
leaves nothing behind.

Four tests here were `xfail(strict=True)` when the `Tester` wrote them, and
none of them was a test waiting to be relaxed: they were defects of `app/`,
written as the requirement reads and reported rather than accommodated. All
four are fixed and now guard their fix — the corrected **currency** a later
list overwrote, the two conflicts that reached the owner as the same message,
the null that emptied a text field, and a 404 answered in English.
"""

from decimal import Decimal
from typing import Any, NamedTuple

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Correction, CorrectionStatus, Product
from app.modules.catalog.schemas import CorrectionRead
from app.modules.catalog.service import CatalogService
from app.modules.identity.models import User
from app.modules.operations.service import OperationsService
from app.shared.corrections import REASON_LABELS, CorrectionReason
from app.shared.errors import NotFoundError, ValidationError
from app.shared.events import NormalizedPriceRow
from tests.conftest import API_PREFIX, Queued
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

REASON = CorrectionReason.PORTAL_WAS_WRONG.value
CODE = "CONF-T26"

# What the portal said the day the correction was made, and what a person left
# on top of it. Every conflict below is measured against these two.
PORTAL_PRICE = Decimal("1000.0000")
CORRECTED_PRICE = Decimal("1200")

CORRECTIONS = f"{API_PREFIX}/catalog/products/{{product_id}}/corrections"
PRICES = f"{API_PREFIX}/prices"


class Corrected(NamedTuple):
    """A product with a correction standing on its price."""

    product_id: int
    correction_id: int


def portal_row(
    price: Decimal | int, *, row_id: int, description: str | None = None, code: str = CODE
) -> NormalizedPriceRow:
    """One row of a daily list for the product these tests correct."""
    return NormalizedPriceRow(
        staging_row_id=row_id,
        product_code=code,
        description=description or "Producto en conflicto",
        price=Decimal(str(price)),
        currency="ARS",
    )


async def a_list_arrives(
    session: AsyncSession, price: Decimal | int, *, run: int, description: str | None = None
) -> None:
    """The daily list arrives once more, with this price for our product."""
    await CatalogService(session).apply_price_batch(
        batch_id=run,
        rows=(portal_row(price, row_id=run, description=description),),
        seen_codes=(CODE,),
    )
    await session.commit()


async def the_row(session: AsyncSession, correction_id: int) -> Correction:
    """The correction as it stands in the database, columns and all.

    The screen's view of a correction (`CorrectionMark`) leaves out
    `conflict_detected_at`, and half of what these tests are about is whether
    that timestamp moved.
    """
    row = await session.get(Correction, correction_id)
    assert row is not None
    return row


async def correct(
    session: AsyncSession,
    product_id: int,
    *,
    field: str = "price",
    value: Any = "1200",
    reason_code: str = REASON,
    reason_detail: str | None = None,
    actor_user_id: int = 1,
) -> CorrectionRead:
    """Somebody corrects a value and the change is committed."""
    result = await CatalogService(session).apply_correction(
        product_id=product_id,
        field=field,
        value=value,
        reason_code=reason_code,
        reason_detail=reason_detail,
        actor_user_id=actor_user_id,
    )
    await session.commit()
    return result


@pytest.fixture
async def corrected(session: AsyncSession) -> Corrected:
    """A product the portal priced at 1000 and somebody corrected to 1200."""
    product = await ProductFactory.create(session, code=CODE, price=PORTAL_PRICE)
    result = await correct(session, product.id, value=str(CORRECTED_PRICE))
    assert result.correction_id is not None
    return Corrected(product.id, result.correction_id)


class TestTheRunsOfAConflict:
    """RF-28 and RF-29, one daily list at a time."""

    async def test_the_portal_repeating_itself_changes_nothing_at_all(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """The same 1000 it had already said: no flag, no timestamp, no alert."""
        # Arrange
        before = (await the_row(session, corrected.correction_id)).corrected_at

        # Act
        await a_list_arrives(session, 1000, run=1)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.ACTIVE
        assert row.conflict_value is None
        assert row.conflict_detected_at is None
        assert row.corrected_at == before
        assert (await CatalogService(session).price_history(corrected.product_id)).price == (
            CORRECTED_PRICE
        )
        assert queued_alerts.count == 0

    async def test_a_different_value_is_flagged_and_the_correction_is_untouched(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """RF-28: the portal is recorded as disagreeing, not as deciding."""
        # Act
        await a_list_arrives(session, 1500, run=1)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.CONFLICTED
        assert row.conflict_value == "1500"
        assert row.conflict_detected_at is not None
        # The three things a conflict must not move.
        assert row.portal_value == str(PORTAL_PRICE)
        assert row.corrected_value == str(CORRECTED_PRICE)
        assert row.corrected_by_user_id == 1
        assert (await CatalogService(session).price_history(corrected.product_id)).price == (
            CORRECTED_PRICE
        )
        assert queued_alerts.count == 1

    async def test_a_corrected_currency_is_not_overwritten_by_the_next_list(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """The third correctable field, on the run that contradicts it.

        RF-28 is written about *a datum corrected by hand*, not about the
        amounts alone: `currency` is corrected through the same door as `price`
        and lives on the very same row, so a later list reporting something
        else has to be flagged rather than applied.

        The list has to bring a different **price** for the currency to be
        rewritten at all — the branch that keeps a repeated price never touches
        it — which is why the number moves here and the currency is the datum
        under test.
        """
        # Arrange — the portal priced it in pesos, a person read the invoice in dollars
        product = await ProductFactory.create(session, code=CODE, price=PORTAL_PRICE)
        result = await correct(
            session,
            product.id,
            field="currency",
            value="USD",
            reason_code=CorrectionReason.MISREAD_FROM_DOCUMENT.value,
        )
        assert result.correction_id is not None

        # Act — the list comes back with another price, still saying pesos
        await a_list_arrives(session, 1500, run=1)

        # Assert
        assert (await CatalogService(session).price_history(product.id)).currency == "USD"
        row = await the_row(session, result.correction_id)
        assert row.status is CorrectionStatus.CONFLICTED
        assert row.conflict_value == "ARS"
        assert row.corrected_value == "USD"
        assert queued_alerts.count == 1

    async def test_the_alert_carries_the_three_values_the_owner_needs(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """RF-29: an alert that does not say what disagrees is not an alert.

        The owner is told without having to be on that screen, so the message
        has to stand on its own: what the portal had said, what the correction
        left, and what the portal says now.
        """
        # Act
        await a_list_arrives(session, 1500, run=1)

        # Assert
        message = queued_alerts.calls[0]["args"][0]
        assert "1000.0000" in message
        assert "1200" in message
        assert "1500" in message
        assert "La corrección sigue en pie" in message

    async def test_two_conflicts_in_one_run_do_not_arrive_as_the_same_message(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """Two corrections contradicted by one list, on identical numbers.

        Everything `conflict_message` is handed is the same for both, which is
        the point: what has to tell the two alerts apart is the only thing they
        do not share — the datum each one is about. The three values and the
        closing sentence are already pinned by the test above and by
        `tests/unit/notifications/test_messages.py`; what only an end-to-end
        run can ask is whether the owner can act on the message alone.
        """
        # Arrange
        other_code = f"{CODE}-B"
        first = await ProductFactory.create(session, code=CODE, price=PORTAL_PRICE)
        second = await ProductFactory.create(session, code=other_code, price=PORTAL_PRICE)
        await correct(session, first.id, value=str(CORRECTED_PRICE))
        await correct(session, second.id, value=str(CORRECTED_PRICE))

        # Act — one list, contradicting both with the same number
        await CatalogService(session).apply_price_batch(
            batch_id=1,
            rows=(portal_row(1500, row_id=1), portal_row(1500, row_id=2, code=other_code)),
            seen_codes=(CODE, other_code),
        )
        await session.commit()

        # Assert
        assert queued_alerts.count == 2
        first_message, second_message = (call["args"][0] for call in queued_alerts.calls)
        assert first_message != second_message

    async def test_the_same_disagreement_twice_warns_once_and_moves_nothing(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """A daily list is daily: the same conflict must not warn every morning."""
        # Arrange
        await a_list_arrives(session, 1500, run=1)
        first_seen = (await the_row(session, corrected.correction_id)).conflict_detected_at

        # Act
        await a_list_arrives(session, 1500, run=2)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.conflict_detected_at == first_seen
        assert row.conflict_value == "1500"
        assert queued_alerts.count == 1

    async def test_a_third_value_is_news_again_and_warns_again(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """The run the handover does not name, and the one that decides the rule.

        RF-29 fires on *a value distinct from the original*, and 1700 is one:
        the owner was told about 1500 and 1500 is no longer what the portal
        says. Warning again is the behaviour the requirement asks for — the
        silence of the previous test is about repetition, not about conflicts.
        """
        # Arrange
        await a_list_arrives(session, 1500, run=1)
        first_seen = (await the_row(session, corrected.correction_id)).conflict_detected_at

        # Act
        await a_list_arrives(session, 1700, run=2)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.CONFLICTED
        assert row.conflict_value == "1700"
        assert row.conflict_detected_at != first_seen
        assert row.corrected_value == str(CORRECTED_PRICE)
        assert queued_alerts.count == 2
        assert "1700" in queued_alerts.calls[1]["args"][0]

    async def test_the_portal_backing_down_does_not_close_the_case(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """A conflict is closed by a person, and the signed rule names the two ways.

        *"El caso se cierra donde vive el dato —corrigiéndolo otra vez o
        dejando sin efecto la corrección—"*. The portal going back to 1000 is
        neither, so the flag stays up and waits for somebody.
        """
        # Arrange
        await a_list_arrives(session, 1500, run=1)

        # Act
        await a_list_arrives(session, 1000, run=2)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.CONFLICTED
        assert row.conflict_value == "1500"
        assert queued_alerts.count == 1

    async def test_correcting_again_over_a_conflict_closes_it(
        self, session: AsyncSession, corrected: Corrected
    ) -> None:
        """CONFLICTED goes back to ACTIVE where the datum lives (`data-model.md`)."""
        # Arrange
        await a_list_arrives(session, 1500, run=1)

        # Act
        await correct(session, corrected.product_id, value="1450", actor_user_id=9)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.ACTIVE
        assert row.conflict_value is None
        assert row.conflict_detected_at is None
        assert row.corrected_value == "1450"
        assert row.corrected_by_user_id == 9
        # And the one column a second correction still must not move (RF-25).
        assert row.portal_value == str(PORTAL_PRICE)
        assert (await CatalogService(session).price_history(corrected.product_id)).price == (
            Decimal("1450")
        )

    async def test_a_closed_conflict_can_open_again_if_the_portal_insists(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """Settling the case is not silencing it: 1500 is news once more.

        The second warning is the point. Somebody looked at 1500, decided
        1450, and the portal is still saying 1500 — that is a fresh
        disagreement with a fresh decision, not the repetition of an old one.
        """
        # Arrange
        await a_list_arrives(session, 1500, run=1)
        await correct(session, corrected.product_id, value="1450")

        # Act
        await a_list_arrives(session, 1500, run=2)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.CONFLICTED
        assert row.conflict_value == "1500"
        assert queued_alerts.count == 2

    async def test_the_portal_catching_up_to_the_correction_still_counts_as_one(
        self, session: AsyncSession, corrected: Corrected, queued_alerts: Queued
    ) -> None:
        """The portal ends up saying 1200 — the very number the person put there.

        It is flagged and the owner is warned, because RF-28 and RF-29 are
        written against **the original**: 1200 is not 1000, so the antecedent
        holds and the code follows it to the letter. Pinned here because it is
        the one run where the flag reads oddly on screen — the portal and the
        correction now agree, and the datum is still marked as a case to
        settle. Whether that is worth an alert is a question for the
        `Solution-Designer`, not a licence for the suite to decide.
        """
        # Act
        await a_list_arrives(session, CORRECTED_PRICE, run=1)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.status is CorrectionStatus.CONFLICTED
        assert Decimal(row.conflict_value) == CORRECTED_PRICE
        assert (await CatalogService(session).price_history(corrected.product_id)).price == (
            CORRECTED_PRICE
        )
        assert queued_alerts.count == 1

    async def test_a_product_with_no_correction_is_not_a_conflict(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """The control case: without a correction the list simply applies (RF-28).

        Worth its line because the conflict machinery sits inside the loop that
        applies every price, and a flag that fired for everybody would be as
        useless as one that never fires.
        """
        # Arrange
        product = await ProductFactory.create(session, code=CODE, price=1000)

        # Act
        await a_list_arrives(session, 1500, run=1)

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.price == Decimal("1500")
        assert history.corrections == []
        assert queued_alerts.count == 0


class TestTheReasonIsMandatory:
    """RF-11: no reason from the list, no correction — on any datum."""

    @pytest.mark.parametrize("reason", list(CorrectionReason))
    async def test_every_reason_of_the_catalogue_is_accepted_and_written_down(
        self, session: AsyncSession, reason: CorrectionReason
    ) -> None:
        """The five the API serves are the five the API takes (RF-12).

        The list a person picks from and the rule that validates it come from
        the same place on purpose, so the test walks the whole catalogue rather
        than a sample: a reason that renders but is refused would be found by
        nothing else.
        """
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        await correct(session, product.id, reason_code=reason.value)

        # Assert
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].reason_code == reason.value
        assert log.items[0].reason_label == REASON_LABELS[reason]

    async def test_the_reasons_the_api_offers_are_exactly_those(
        self, session: AsyncSession
    ) -> None:
        """The screen's list and the validated one are the same list."""
        # Act
        offered = OperationsService(session).correction_reasons()

        # Assert
        assert [entry.code for entry in offered] == [reason.value for reason in CorrectionReason]

    @pytest.mark.parametrize("reason_code", ["", "PORQUE_SI", "portal_was_wrong", "OTHER "])
    async def test_a_reason_that_is_not_in_the_list_is_refused(
        self, session: AsyncSession, reason_code: str
    ) -> None:
        """Invented, empty, mis-cased or padded: the list is the list."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="price",
                value="1200",
                reason_code=reason_code,
                reason_detail=None,
                actor_user_id=1,
            )

    async def test_a_refused_correction_leaves_nothing_behind(self, session: AsyncSession) -> None:
        """Neither the value nor a line in the log: it did not happen."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="price",
                value="1200",
                reason_code="PORQUE_SI",
                reason_detail=None,
                actor_user_id=1,
            )

        # Assert
        assert (await CatalogService(session).price_history(product.id)).price == Decimal("1000")
        assert (await OperationsService(session).list_audit(sections=None)).total == 0

    async def test_a_datum_a_person_loaded_needs_a_reason_too(self, session: AsyncSession) -> None:
        """RF-11 twice over: *"ni sobre un dato del portal ni sobre uno cargado a mano"*.

        A product somebody incorporated by hand has no correction to open
        (RF-33), and that is precisely why this needs its own test: the branch
        that skips the correction must not skip the reason with it.
        """
        # Arrange — incorporated from the review queue with the price the person
        # typed, which is the path that marks a value as nobody's but theirs.
        await CatalogService(session).incorporate_product(
            product_code=CODE, description="Cargado a mano", price=Decimal("1000")
        )
        product_id = await session.scalar(select(Product.id).where(Product.code == CODE))
        assert product_id is not None

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product_id,
                field="price",
                value="1200",
                reason_code="",
                reason_detail=None,
                actor_user_id=1,
            )
        assert (await CatalogService(session).price_history(product_id)).price == Decimal("1000")

    async def test_over_http_a_body_with_no_reason_never_reaches_the_service(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """The schema asks for it too, so the refusal costs no round trip."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=product.id), json={"field": "price", "value": "1200"}
        )

        # Assert
        assert response.status_code == 422
        assert (await CatalogService(session).price_history(product.id)).price == Decimal("1000")

    async def test_over_http_an_invented_reason_is_a_422(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """A code the schema admits and the catalogue does not."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={"field": "price", "value": "1200", "reason_code": "PORQUE_SI"},
        )

        # Assert
        assert response.status_code == 422
        assert (await CatalogService(session).price_history(product.id)).price == Decimal("1000")


class TestAFieldThatIsNotAnAmount:
    """RF-23 verified by analogy, as the human decided on 2026-08-29.

    The signed criterion names the receipt number of a purchase invoice, and
    there is no invoices module yet: the equivalent datum that does exist is a
    product's description, which is text the portal brought and nobody adds up.
    """

    async def test_the_description_is_corrected_and_the_portal_text_is_kept(
        self, session: AsyncSession
    ) -> None:
        """RF-23 with RF-25: a misread word behaves like a misread number."""
        # Arrange
        product = await ProductFactory.create(
            session, code=CODE, price=1000, description="Tornllo hexagonl"
        )

        # Act
        result = await correct(
            session,
            product.id,
            field="description",
            value="Tornillo hexagonal 8mm",
            reason_code=CorrectionReason.MISREAD_FROM_DOCUMENT.value,
            reason_detail="el remito dice hexagonal",
        )

        # Assert
        assert result.entity_type == "catalog.product"
        assert result.portal_value == "Tornllo hexagonl"
        history = await CatalogService(session).price_history(product.id)
        assert history.description == "Tornillo hexagonal 8mm"
        assert history.corrections[0].portal_value == "Tornllo hexagonl"
        assert history.corrections[0].corrected_value == "Tornillo hexagonal 8mm"

    async def test_correcting_the_text_does_not_touch_the_price(
        self, session: AsyncSession
    ) -> None:
        """Two fields of the same product, two corrections that do not collide.

        They live in different entities — the product and its price in force —
        and the screen has to show both marks on the one row (RF-26).
        """
        # Arrange
        product = await ProductFactory.create(
            session, code=CODE, price=1000, description="Tornllo hexagonl"
        )

        # Act
        await correct(session, product.id, field="description", value="Tornillo hexagonal")
        await correct(session, product.id, field="price", value="1200")

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.price == CORRECTED_PRICE
        assert history.description == "Tornillo hexagonal"
        assert {mark.field for mark in history.corrections} == {"description", "price"}

    async def test_a_corrected_description_survives_the_next_list(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """The list rewrites a price, never a description — so it cannot contradict one.

        A product that already exists takes only its price from the daily list:
        its description was written the day it was registered and no run
        touches it again. The correction therefore stands, and there is no
        conflict to raise because nothing was applied over it.
        """
        # Arrange
        product = await ProductFactory.create(
            session, code=CODE, price=1000, description="Tornllo hexagonl"
        )
        await correct(session, product.id, field="description", value="Tornillo hexagonal")

        # Act — the same list, still spelling it the way it always did
        await a_list_arrives(session, 1400, run=1, description="Tornllo hexagonl")

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.description == "Tornillo hexagonal"
        assert history.price == Decimal("1400")
        assert queued_alerts.count == 0

    async def test_the_next_list_spelling_it_otherwise_still_leaves_the_correction(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """The same crossing as above, with the antecedent RF-28 is written about.

        The test before it fixes what happens when the list repeats the
        description it always had — no contradiction, so no case. Here the list
        brings a **different** one over a corrected description, which is the
        antecedent of the requirement, and the answer today is neither of the
        two outcomes it names: the correction is not overwritten, and it is not
        flagged either, because a batch never writes a known product's
        description at all.

        Pinned as it stands rather than as a defect: whether a value the portal
        reported and the pipeline never applied counts as *"una actualización
        posterior que trae un valor distinto"* is a question for the
        `Solution-Designer`, not for the suite to answer on its own. What the
        suite can do is stop the answer from being an accident — the day a run
        starts rewriting descriptions, this is the test that says so.
        """
        # Arrange
        product = await ProductFactory.create(
            session, code=CODE, price=1000, description="Tornllo hexagonl"
        )
        await correct(session, product.id, field="description", value="Tornillo hexagonal")

        # Act — the list comes back calling it something else entirely
        await a_list_arrives(session, 1400, run=1, description="TORNILLO HEX. 8 MM")

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.description == "Tornillo hexagonal"
        assert history.price == Decimal("1400")
        mark = history.corrections[0]
        assert mark.field == "description"
        assert mark.status is CorrectionStatus.ACTIVE
        assert mark.conflict_value is None
        assert queued_alerts.count == 0

    async def test_text_cannot_be_corrected_into_nothing(self, session: AsyncSession) -> None:
        """Emptying a field is not correcting it, and whitespace is emptying it."""
        # Arrange
        product = await ProductFactory.create(session, description="Tornllo hexagonl")

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="description",
                value="   ",
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )

    async def test_an_amount_cannot_be_corrected_into_nothing_either(
        self, session: AsyncSession
    ) -> None:
        """A null amount is refused too — by the parser, not by the empty guard.

        Worth being exact about, because it is the contrast the next test rests
        on. The guard the test above trips (`if not numeric and not corrected`)
        never runs for an amount: what refuses a null price is `_as_number`,
        which cannot read `None` as a number, and that is why the message is
        about a number and not about an empty value. The text branch has no
        such parser in front of it, and that is precisely where a null gets
        through.
        """
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="price",
                value=None,
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )
        assert "número" in refusal.value.message
        assert refusal.value.details == {"field": "price"}

    async def test_text_cannot_be_corrected_into_a_null_either(self, session: AsyncSession) -> None:
        """A null is emptying the field just as much as an empty string is.

        RF-23 lets a person correct a text the portal brought; it does not let
        them erase it, which is why the empty string is already refused. A
        `null` is the same request through a different door and has to get the
        same answer.
        """
        # Arrange
        product = await ProductFactory.create(session, description="Tornllo hexagonl")

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="description",
                value=None,
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )

    async def test_the_supplier_code_is_not_a_correctable_field(
        self, session: AsyncSession
    ) -> None:
        """RF-23 has a floor: the key the daily list is matched by.

        Rewriting a product's code would silently detach it from every list
        that follows, which is a different product and not a correction.
        """
        # Arrange
        product = await ProductFactory.create(session, code=CODE, price=1000)

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="code",
                value="OTRO-9999",
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )


class TestWhoMayCorrectAProduct:
    """RF-24, end to end over HTTP with one client per role.

    Authorisation is answered by the request, so it is verified by a request.
    The signed criterion says *"Julián no puede corregir el total de una
    factura de compra"*; with no invoices module, the equivalent that exists is
    purchasing being refused a product, which belongs to sales.
    """

    async def test_purchasing_cannot_correct_a_product(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """The catalog is not theirs, so the answer is 403 and nothing moves."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await purchasing_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 403
        assert (await CatalogService(session).price_history(product.id)).price == Decimal("1000")
        assert (await OperationsService(session).list_audit(sections=None)).total == 0

    async def test_sales_can_correct_a_product(
        self, session: AsyncSession, sales_client: AsyncClient
    ) -> None:
        """Prices and the catalog are the section sales reaches."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await sales_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["portal_value"] == str(PORTAL_PRICE)
        assert (await CatalogService(session).price_history(product.id)).price == CORRECTED_PRICE

    async def test_the_owner_can_correct_a_product(
        self, session: AsyncSession, owner_client: AsyncClient, owner: User
    ) -> None:
        """And the log says it was them, taken from the session and not the body."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 200
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].actor_user_id == owner.id

    async def test_nobody_at_all_cannot_correct_a_product(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        """Without a session it is a 401, before any question about sections."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await client.post(
            CORRECTIONS.format(product_id=product.id),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 401


class TestThePortalValueOutlivesEverything:
    """RF-25: `portal_value` is written once and never again."""

    async def test_two_corrections_and_a_later_list_leave_it_where_it_was(
        self, session: AsyncSession, corrected: Corrected
    ) -> None:
        """The three things that could plausibly rewrite it, one after another."""
        # Arrange / Act
        await correct(session, corrected.product_id, value="1300", actor_user_id=2)
        await a_list_arrives(session, 1600, run=1)

        # Assert
        row = await the_row(session, corrected.correction_id)
        assert row.portal_value == str(PORTAL_PRICE)
        assert row.corrected_value == "1300"
        assert row.conflict_value == "1600"
        assert (await CatalogService(session).price_history(corrected.product_id)).price == (
            Decimal("1300")
        )

    async def test_the_history_of_the_price_gains_no_point_from_a_correction(
        self, session: AsyncSession, corrected: Corrected
    ) -> None:
        """A correction is not a price the portal published.

        Worth pinning: the points are what the price chart draws, and a manual
        value drawn among them would make the portal look like it said
        something it never said.
        """
        # Act
        history = await CatalogService(session).price_history(corrected.product_id)

        # Assert
        assert history.points == []
        assert history.price == CORRECTED_PRICE


class TestWhatTheScreenGetsBack:
    """RF-26 and RF-27, over HTTP: marked as corrected, with the original beside."""

    async def test_the_price_list_marks_the_corrected_row_and_leaves_the_others_alone(
        self, session: AsyncSession, owner_client: AsyncClient, corrected: Corrected
    ) -> None:
        """RF-26: telling them apart at a glance is telling them apart in the payload."""
        # Arrange
        untouched = await ProductFactory.create(session, price=500)

        # Act
        response = await owner_client.get(PRICES)

        # Assert
        assert response.status_code == 200
        rows = {row["product_id"]: row for row in response.json()["items"]}
        assert rows[untouched.id]["corrections"] == []
        mark = rows[corrected.product_id]["corrections"][0]
        assert mark["field"] == "price"
        assert mark["portal_value"] == str(PORTAL_PRICE)
        assert mark["corrected_value"] == str(CORRECTED_PRICE)
        assert mark["status"] == CorrectionStatus.ACTIVE.value

    async def test_the_product_page_shows_the_original_and_the_conflict(
        self, session: AsyncSession, owner_client: AsyncClient, corrected: Corrected
    ) -> None:
        """RF-27 and RF-28: both answers arrive where the case has to be settled."""
        # Arrange
        await a_list_arrives(session, 1500, run=1)

        # Act
        response = await owner_client.get(f"{PRICES}/{corrected.product_id}/history")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert Decimal(body["price"]) == CORRECTED_PRICE
        mark = body["corrections"][0]
        assert mark["portal_value"] == str(PORTAL_PRICE)
        assert mark["status"] == CorrectionStatus.CONFLICTED.value
        assert mark["conflict_value"] == "1500"

    async def test_the_datum_leads_to_its_own_history(
        self, session: AsyncSession, owner_client: AsyncClient, corrected: Corrected
    ) -> None:
        """RF-15 from H4's side: the correction says which entity to ask about."""
        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/operations/audit/catalog.product_price/{corrected.product_id}"
        )

        # Assert
        assert response.status_code == 200
        entries = response.json()
        assert [entry["action"] for entry in entries] == ["CORRECTED"]
        assert entries[0]["old_value"] == str(PORTAL_PRICE)


class TestTheBordersNobodyAskedFor:
    """The cases that are nobody's headline and break in production anyway."""

    async def test_correcting_a_value_to_the_one_it_already_had(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """Somebody confirms a number instead of changing it.

        It is a manual decision like any other, so it is recorded like any
        other (RF-09) — and because the two values agree, the next list that
        repeats that number is not a conflict.
        """
        # Arrange
        product = await ProductFactory.create(session, code=CODE, price=1000)

        # Act
        result = await correct(session, product.id, value="1000")
        await a_list_arrives(session, 1000, run=1)

        # Assert
        assert result.correction_id is not None
        row = await the_row(session, result.correction_id)
        assert row.status is CorrectionStatus.ACTIVE
        assert Decimal(row.portal_value) == Decimal(row.corrected_value)
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].action == "CORRECTED"
        assert queued_alerts.count == 0

    async def test_a_product_with_no_price_has_no_price_to_correct(
        self, session: AsyncSession
    ) -> None:
        """A product the list registered but never priced yet."""
        # Arrange
        product = await ProductFactory.create(session, price=None)

        # Act / Assert
        with pytest.raises(NotFoundError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="price",
                value="1200",
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )

    async def test_a_product_with_no_price_still_has_a_description_to_correct(
        self, session: AsyncSession
    ) -> None:
        """The refusal above is about the price row, not about the product."""
        # Arrange
        product = await ProductFactory.create(session, price=None, description="Tornllo")

        # Act
        await correct(session, product.id, field="description", value="Tornillo")

        # Assert
        assert (await CatalogService(session).price_history(product.id)).description == "Tornillo"

    async def test_over_http_a_product_with_no_price_answers_404_in_spanish(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """RF-22: whoever ran the action is told it failed, and why."""
        # Arrange
        product = await ProductFactory.create(session, price=None)

        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 404
        assert "precio" in str(response.json()).lower()

    async def test_correcting_a_product_that_does_not_exist(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """404 rather than a correction pointing at nothing."""
        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=999999),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 404

    async def test_the_404_of_a_product_that_does_not_exist_is_in_spanish(
        self, owner_client: AsyncClient
    ) -> None:
        """RF-22 only reaches the person in a language they read."""
        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=999999),
            json={"field": "price", "value": "1200", "reason_code": REASON},
        )

        # Assert
        assert response.status_code == 404
        assert "producto" in str(response.json()).lower()

    async def test_a_written_detail_is_kept_word_for_word(self, session: AsyncSession) -> None:
        """RF-11: the detail beside the reason is what carries the odd case."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        await correct(session, product.id, reason_detail="el remito 0001-00045678 dice 1200")

        # Assert
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].reason_detail == "el remito 0001-00045678 dice 1200"

    async def test_no_detail_and_an_empty_detail_are_both_no_detail(
        self, session: AsyncSession
    ) -> None:
        """The optional half of RF-11, from its two ends.

        Absent comes back as null and empty comes back as empty: different
        values in the column, the same nothing on the screen. What matters is
        that neither is refused — the reason is mandatory, the detail is not.
        """
        # Arrange
        absent = await ProductFactory.create(session, price=1000)
        empty = await ProductFactory.create(session, price=1000)

        # Act
        await correct(session, absent.id, reason_detail=None)
        await correct(session, empty.id, reason_detail="")

        # Assert
        log = await OperationsService(session).list_audit(sections=None)
        details = {entry.entity_id: entry.reason_detail for entry in log.items}
        assert details[str(absent.id)] is None
        assert details[str(empty.id)] == ""

    async def test_a_detail_longer_than_the_column_is_refused_at_the_edge(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """1000 characters is the limit, and 1001 is a 422 and not a truncation."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={
                "field": "price",
                "value": "1200",
                "reason_code": REASON,
                "reason_detail": "x" * 1001,
            },
        )

        # Assert
        assert response.status_code == 422
        assert (await CatalogService(session).price_history(product.id)).price == Decimal("1000")

    async def test_a_detail_of_exactly_a_thousand_characters_is_kept_whole(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """The other side of the same edge: 1000 is taken, and taken entire.

        A refusal at 1001 is only half a boundary — a `max_length` written as
        999 would pass it just as happily, and the person would lose the end of
        what they wrote. The number is spelled out here rather than imported
        from the schema on purpose: a test that reads the limit from the code
        it is testing cannot notice the limit moving.
        """
        # Arrange
        product = await ProductFactory.create(session, price=1000)
        detail = "x" * 1000

        # Act
        response = await owner_client.post(
            CORRECTIONS.format(product_id=product.id),
            json={
                "field": "price",
                "value": "1200",
                "reason_code": REASON,
                "reason_detail": detail,
            },
        )

        # Assert
        assert response.status_code == 200
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].reason_detail == detail

    async def test_a_price_that_is_not_a_number_is_refused(self, session: AsyncSession) -> None:
        """A field that holds an amount only takes an amount."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="price",
                value="mil doscientos",
                reason_code=REASON,
                reason_detail=None,
                actor_user_id=1,
            )
