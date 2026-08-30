"""Undoing a correction: the borders of H5 (RF-30 to RF-33).

The Developer already walked the main path in `test_manual_corrections.py`
(`TestUndoingACorrection`): two corrections in a row, the portal's number comes
back, the log says who undid it. What is here is everything around that path,
which is where undoing is actually easy to get wrong:

* **what comes back** after three corrections in a row, and after the portal
  spoke in between — `portal_value` is the only number that was never
  rewritten, and every other candidate is wrong (RF-31);
* **the three ways there is nothing to undo** — an id that never existed, a
  correction already undone, and a datum the portal never brought (RF-33). The
  third one is pinned from both sides: a value a person typed offers nothing to
  go back to, and a value the portal brought stays correctable even when the
  product around it was incorporated by a rule;
* **who may ask** — undoing is the owner's alone, even for sales, who may
  correct (RF-30). The asymmetry is deliberate and signed;
* **what is left behind** — a line in the log with who and when, and a
  correction row marked rather than deleted (RF-32);
* **that the field stays correctable afterwards**, because the unique index
  covers only the corrections still in force.

Everything runs against a real session: this is authorisation, SQL and a
partial unique index, and none of the three is exercised by a mock.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Correction, Product
from app.modules.catalog.service import CatalogService
from app.modules.identity.models import User
from app.modules.operations.service import OperationsService
from app.shared.corrections import CorrectionReason, CorrectionStatus
from app.shared.errors import NotFoundError
from app.shared.events import AuditAction, NormalizedPriceRow
from tests.conftest import API_PREFIX, Queued
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

REASON = CorrectionReason.PORTAL_WAS_WRONG.value
CODE = "REV-0001"

PRICE_ENTITY = "catalog.product_price"
PRODUCT_ENTITY = "catalog.product"

CATALOG = f"{API_PREFIX}/catalog"
CORRECTIONS = f"{CATALOG}/corrections"
AUDIT = f"{API_PREFIX}/operations/audit"

# What the portal reported the day the product was registered, and what every
# reversal in this file has to give back.
PORTAL_PRICE = Decimal("1000.0000")


def portal_row(price: Decimal | int, *, row_id: int) -> NormalizedPriceRow:
    """One row of a daily list, for the product these tests correct."""
    return NormalizedPriceRow(
        staging_row_id=row_id,
        product_code=CODE,
        description="Producto corregido",
        price=Decimal(str(price)),
        currency="ARS",
    )


async def correct(
    session: AsyncSession,
    product_id: int,
    *,
    value: Any,
    field: str = "price",
    actor_user_id: int = 1,
    reason_detail: str | None = None,
) -> int | None:
    """Correct one field by hand and return the id of the correction row.

    Local to this file on purpose: `conftest.py` is shared with other agents
    working on the same checkout, and a helper this narrow does not earn a
    place in it.
    """
    result = await CatalogService(session).apply_correction(
        product_id=product_id,
        field=field,
        value=value,
        reason_code=REASON,
        reason_detail=reason_detail,
        actor_user_id=actor_user_id,
    )
    await session.commit()
    return result.correction_id


async def correction_rows(
    session: AsyncSession, product_id: int, *, field: str = "price"
) -> list[Correction]:
    """Every correction row on a field, undone ones included."""
    result = await session.execute(
        select(Correction)
        .where(Correction.entity_id == str(product_id), Correction.field == field)
        .order_by(Correction.id)
    )
    return list(result.scalars().all())


class TestWhatAReversalGivesBack:
    """RF-31: the portal's value, and never the previous person's."""

    async def test_three_corrections_in_a_row_still_restore_the_portal_value(
        self, session: AsyncSession
    ) -> None:
        """The previous value is 1300 and the portal's is 1000. Only one is the answer.

        Three and not two because a reversal that restored "the one before the
        last" would already look right with two: 1000 -> 1200 -> 1300 hides the
        bug behind an off-by-one, and 1400 on top of it does not.
        """
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        first = await correct(session, product.id, value="1200")
        second = await correct(session, product.id, value="1300")
        third = await correct(session, product.id, value="1400")

        # A re-correction refreshes the row standing on the field instead of
        # opening a second one, which is exactly why `portal_value` survives.
        assert first is not None
        assert (second, third) == (first, first)
        assert len(await correction_rows(session, product.id)) == 1

        # Act
        reverted = await CatalogService(session).revert_correction(first, actor_user_id=2)
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.price == PORTAL_PRICE
        assert reverted.value == "1000.0000"

    async def test_a_list_that_arrived_between_two_corrections_does_not_move_it(
        self, session: AsyncSession
    ) -> None:
        """The portal spoke again mid-way, and `portal_value` still means the first word.

        1000 corrected to 1200, the portal comes back with 1500 — a conflict,
        not an overwrite — and somebody corrects again to 1300. Undoing that
        has to land on 1000: the 1500 was never applied and the 1200 was never
        the portal's.
        """
        # Arrange
        product = await ProductFactory.create(session, code=CODE, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        await CatalogService(session).apply_price_batch(
            batch_id=2, rows=(portal_row(1500, row_id=2),), seen_codes=(CODE,)
        )
        await session.commit()
        assert await correct(session, product.id, value="1300") == correction_id

        # Act
        await CatalogService(session).revert_correction(correction_id, actor_user_id=2)
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.price == PORTAL_PRICE
        assert history.corrections == []

    async def test_undoing_a_correction_in_conflict_restores_what_the_portal_first_said(
        self, session: AsyncSession
    ) -> None:
        """The open question of an undone conflict: which number stays.

        The design answers `portal_value` — the column that is written once and
        is the evidence of what the origin said (Artículo III). The number the
        portal came back with is kept on the row as what raised the conflict,
        not applied: the spec closes a conflict where the datum lives, and
        undoing the correction is one of the two ways to close it.
        """
        # Arrange
        product = await ProductFactory.create(session, code=CODE, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        await CatalogService(session).apply_price_batch(
            batch_id=2, rows=(portal_row(1500, row_id=2),), seen_codes=(CODE,)
        )
        await session.commit()
        standing = await correction_rows(session, product.id)
        assert standing[0].status is CorrectionStatus.CONFLICTED

        # Act
        await CatalogService(session).revert_correction(correction_id, actor_user_id=2)
        await session.commit()

        # Assert
        assert (await CatalogService(session).price_history(product.id)).price == PORTAL_PRICE
        row = (await correction_rows(session, product.id))[0]
        assert row.status is CorrectionStatus.REVERTED
        assert row.conflict_value == "1500"

    async def test_once_the_correction_is_gone_the_next_list_writes_the_price_again(
        self, session: AsyncSession
    ) -> None:
        """Undoing hands the datum back to the portal, including for tomorrow.

        A reverted correction no longer stands, so the daily list stops being
        held off and the number the portal reports lands normally.
        """
        # Arrange
        product = await ProductFactory.create(session, code=CODE, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        await CatalogService(session).revert_correction(correction_id, actor_user_id=2)
        await session.commit()

        # Act
        await CatalogService(session).apply_price_batch(
            batch_id=3, rows=(portal_row(1500, row_id=3),), seen_codes=(CODE,)
        )
        await session.commit()

        # Assert
        assert (await CatalogService(session).price_history(product.id)).price == Decimal("1500")


class TestWhenThereIsNothingToUndo:
    """RF-33, from its ends: no row, an undone row, and a datum nobody reported.

    Four of them are about where a value came from, and they answer it the way
    the platform now does: through `incorporate_product`, the path a person
    takes out of the review queue. A rule incorporating a product is the other
    half — it replays what the list said, so that value stays the portal's and
    stays correctable.
    """

    async def test_an_id_that_never_existed_fails_clean(self, session: AsyncSession) -> None:
        """Not a 500 and not a silent success: there is no such correction.

        The error carries the id it was asked about, which is what lets the 404
        name what was not found. That assertion is also what this adds over the
        Developer's version of the same case, in
        `test_manual_corrections.py::TestUndoingACorrection`.
        """
        # Act / Assert
        with pytest.raises(NotFoundError) as error:
            await CatalogService(session).revert_correction(987654321, actor_user_id=1)

        assert error.value.details == {"correction_id": 987654321}

    async def test_a_correction_already_undone_cannot_be_undone_twice(
        self, session: AsyncSession
    ) -> None:
        """The second attempt refuses, and nothing moves a second time."""
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        await CatalogService(session).revert_correction(correction_id, actor_user_id=2)
        await session.commit()

        # Act / Assert
        product_id = product.id
        with pytest.raises(NotFoundError):
            await CatalogService(session).revert_correction(correction_id, actor_user_id=2)

        assert (await CatalogService(session).price_history(product_id)).price == PORTAL_PRICE
        log = await OperationsService(session).list_audit(sections=None)
        reverted = [e for e in log.items if e.action == AuditAction.CORRECTION_REVERTED]
        assert len(reverted) == 1

    async def test_a_datum_loaded_entirely_by_hand_opens_no_correction_to_undo(
        self, session: AsyncSession
    ) -> None:
        """The branch exists and closes cleanly: nothing to undo, and no row anywhere.

        What the test below asserts about the reversal, this one asserts about
        the whole table: correcting a value nobody reported leaves the
        corrections empty, so there is no id anyone could ever send to a
        reversal in the first place.
        """
        # Arrange — incorporated from the review queue with the price the person
        # typed, which is the path that marks a value as nobody's but theirs.
        await CatalogService(session).incorporate_product(
            product_code=CODE, description="Cargado a mano", price=PORTAL_PRICE
        )
        await session.commit()
        product_id = await session.scalar(select(Product.id).where(Product.code == CODE))
        assert product_id is not None

        # Act
        correction_id = await correct(session, product_id, value="1200")

        # Assert
        assert correction_id is None
        assert await correction_rows(session, product_id) == []
        total = await session.scalar(select(func.count()).select_from(Correction))
        assert total == 0

    async def test_a_price_the_portal_brought_is_correctable_even_if_a_rule_registered_it(
        self, session: AsyncSession, queued_history: Queued
    ) -> None:
        """A rule incorporated the product; the portal still priced it.

        What a person decided in the review queue was to incorporate the
        product. The number came in the list, like every number this module
        holds, and RF-28 says a list does not overwrite a correction.
        """
        # Arrange — through `incorporate_product`, which is the path
        # `apply_decision` takes, so the premise of the bug is exercised and not
        # asserted by hand: the price comes from the list the case carried.
        await CatalogService(session).incorporate_product(
            product_code=CODE,
            description="Producto corregido",
            price=PORTAL_PRICE,
            rule_id=7,
        )
        await session.commit()
        product_id = await session.scalar(select(Product.id).where(Product.code == CODE))
        assert product_id is not None

        # Act
        correction_id = await correct(session, product_id, value="1200")
        await CatalogService(session).apply_price_batch(
            batch_id=4, rows=(portal_row(1500, row_id=4),), seen_codes=(CODE,)
        )
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(product_id)
        assert history.price == Decimal("1200")
        assert correction_id is not None

    async def test_a_price_a_person_typed_offers_no_portal_value_to_go_back_to(
        self, session: AsyncSession, queued_history: Queued
    ) -> None:
        """RF-33 as the spec means it: nobody ever reported this number.

        The person did not only decide to incorporate the product, they wrote
        what it costs — `apply_decision` takes the price from the decision
        before it falls back to the row. There is no portal value to give back,
        so no correction row should open.
        """
        # Arrange
        await CatalogService(session).incorporate_product(
            product_code=CODE, description="Cargado a mano", price=Decimal("999.0000")
        )
        await session.commit()
        product_id = await session.scalar(select(Product.id).where(Product.code == CODE))
        assert product_id is not None

        # Act
        correction_id = await correct(session, product_id, value="1200")

        # Assert
        assert correction_id is None
        assert await correction_rows(session, product_id) == []

    async def test_over_http_a_correction_without_a_portal_value_offers_no_undo(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """`correction_id: null` is what keeps the button off the screen.

        The same state as
        `test_a_datum_loaded_entirely_by_hand_opens_no_correction_to_undo`, but
        over HTTP, which is the half that decides what the owner sees: the API
        returns no id to undo, and asking for one anyway is answered rather
        than crashed.
        """
        # Arrange — incorporated from the review queue with the price the person
        # typed, which is the path that marks a value as nobody's but theirs.
        await CatalogService(session).incorporate_product(
            product_code=CODE, description="Cargado a mano", price=PORTAL_PRICE
        )
        await session.commit()
        product_id = await session.scalar(select(Product.id).where(Product.code == CODE))
        assert product_id is not None

        # Act
        corrected = await owner_client.post(
            f"{CATALOG}/products/{product_id}/corrections",
            json={
                "field": "price",
                "value": "1200",
                "reason_code": REASON,
                "reason_detail": "lo cargamos nosotros",
            },
        )
        refused = await owner_client.delete(f"{CORRECTIONS}/424242")

        # Assert
        assert corrected.status_code == 200
        assert corrected.json()["correction_id"] is None
        assert corrected.json()["portal_value"] is None
        assert refused.status_code == 404


class TestOnlyTheOwnerMayUndo:
    """RF-30, over HTTP, with the three roles the business has."""

    @pytest.fixture
    async def corrected_by_sales(
        self, session: AsyncSession, sales_client: AsyncClient, sales_user: User
    ) -> tuple[int, int]:
        """A price sales corrected by hand. Returns (product id, correction id).

        Made through the API and not through the service: who may correct is
        half of the asymmetry this class is about, and asserting it here keeps
        the refusal below from being read as "sales cannot touch the datum".
        """
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        response = await sales_client.post(
            f"{CATALOG}/products/{product.id}/corrections",
            json={
                "field": "price",
                "value": "1200",
                "reason_code": REASON,
                "reason_detail": "el remito dice 1200",
            },
        )
        assert response.status_code == 200
        return product.id, response.json()["correction_id"]

    async def test_the_owner_undoes_a_correction_somebody_else_made(
        self, session: AsyncSession, owner_client: AsyncClient, corrected_by_sales: tuple[int, int]
    ) -> None:
        """Whoever corrected it, undoing it is the owner's call."""
        # Arrange
        product_id, correction_id = corrected_by_sales

        # Act
        response = await owner_client.delete(f"{CORRECTIONS}/{correction_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "REVERTED"
        assert response.json()["value"] == "1000.0000"
        assert (await CatalogService(session).price_history(product_id)).price == PORTAL_PRICE

    async def test_sales_may_correct_and_still_may_not_undo(
        self, session: AsyncSession, sales_client: AsyncClient, corrected_by_sales: tuple[int, int]
    ) -> None:
        """The asymmetry the spec signed: correcting is theirs, undoing is not."""
        # Arrange
        product_id, correction_id = corrected_by_sales

        # Act
        response = await sales_client.delete(f"{CORRECTIONS}/{correction_id}")

        # Assert
        assert response.status_code == 403
        # The refusal did not half-apply: the correction is still standing.
        assert (await CatalogService(session).price_history(product_id)).price == Decimal("1200")
        row = (await correction_rows(session, product_id))[0]
        assert row.status is CorrectionStatus.ACTIVE
        assert row.reverted_by_user_id is None

    async def test_purchasing_may_not_undo_either(
        self, purchasing_client: AsyncClient, corrected_by_sales: tuple[int, int]
    ) -> None:
        """Purchasing does not reach the catalog at all, and does not reach this."""
        # Arrange
        _, correction_id = corrected_by_sales

        # Act
        response = await purchasing_client.delete(f"{CORRECTIONS}/{correction_id}")

        # Assert
        assert response.status_code == 403

    async def test_an_anonymous_caller_is_asked_to_log_in(
        self, client: AsyncClient, corrected_by_sales: tuple[int, int]
    ) -> None:
        """No session, no answer about the datum: 401 before any 403."""
        # Arrange
        _, correction_id = corrected_by_sales

        # Act
        response = await client.delete(f"{CORRECTIONS}/{correction_id}")

        # Assert
        assert response.status_code == 401


class TestWhatAReversalLeavesBehind:
    """RF-32: a line in the log, and a row marked instead of deleted."""

    async def test_the_log_says_who_undid_it_and_when(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Who and when, as its own named action rather than another correction."""
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        before = datetime.now(UTC)

        # Act
        await CatalogService(session).revert_correction(correction_id, actor_user_id=owner.id)
        await session.commit()

        # Assert
        after = datetime.now(UTC)
        entry = (await OperationsService(session).list_audit(sections=None)).items[0]
        assert entry.action == "CORRECTION_REVERTED"
        assert entry.actor_user_id == owner.id
        assert before <= entry.occurred_at <= after
        assert entry.old_value == "1200"
        assert entry.new_value == "1000.0000"

    async def test_the_correction_row_is_marked_and_not_deleted(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Nothing is deleted here either: a log line pointing at nothing explains nothing."""
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        before = datetime.now(UTC)

        # Act
        await CatalogService(session).revert_correction(correction_id, actor_user_id=owner.id)
        await session.commit()

        # Assert
        rows = await correction_rows(session, product.id)
        assert len(rows) == 1
        assert rows[0].id == correction_id
        assert rows[0].status is CorrectionStatus.REVERTED
        assert rows[0].reverted_by_user_id == owner.id
        assert rows[0].reverted_at is not None
        assert rows[0].reverted_at >= before
        # What the portal said is still there, untouched by the reversal.
        assert rows[0].portal_value == "1000.0000"
        assert rows[0].corrected_value == "1200"

    async def test_the_reversal_reads_from_the_history_of_the_datum_itself(
        self, session: AsyncSession, owner_client: AsyncClient, owner: User
    ) -> None:
        """RF-32 as the owner meets it: both lines, on the datum's own screen."""
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, value="1200")
        assert correction_id is not None
        await CatalogService(session).revert_correction(correction_id, actor_user_id=owner.id)
        await session.commit()

        # Act
        response = await owner_client.get(f"{AUDIT}/{PRICE_ENTITY}/{product.id}")

        # Assert
        assert response.status_code == 200
        actions = [entry["action"] for entry in response.json()]
        assert "CORRECTION_REVERTED" in actions
        assert "CORRECTED" in actions
        undone = next(e for e in response.json() if e["action"] == "CORRECTION_REVERTED")
        assert undone["actor_user_id"] == owner.id
        assert undone["actor_name"] is not None
        assert owner.name in undone["actor_name"]


class TestTheBordersOfUndoing:
    """The cases that are not a price, and the life a field has after a reversal."""

    async def test_undoing_a_field_that_is_not_an_amount(self, session: AsyncSession) -> None:
        """RF-23 is any field the portal brought, so RF-31 is too."""
        # Arrange
        product = await ProductFactory.create(
            session, price=PORTAL_PRICE, description="Tornllo hexagonl"
        )
        correction_id = await correct(
            session, product.id, field="description", value="Tornillo hexagonal 8mm"
        )
        assert correction_id is not None

        # Act
        reverted = await CatalogService(session).revert_correction(correction_id, actor_user_id=2)
        await session.commit()

        # Assert
        assert reverted.entity_type == PRODUCT_ENTITY
        assert (
            await CatalogService(session).price_history(product.id)
        ).description == "Tornllo hexagonl"

    async def test_undoing_the_currency_gives_back_the_one_the_portal_reported(
        self, session: AsyncSession
    ) -> None:
        """The third correctable field: text, but living beside the price."""
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        correction_id = await correct(session, product.id, field="currency", value="USD")
        assert correction_id is not None

        # Act
        await CatalogService(session).revert_correction(correction_id, actor_user_id=2)
        await session.commit()

        # Assert
        assert (await CatalogService(session).price_history(product.id)).currency == "ARS"

    async def test_the_same_field_can_be_corrected_again_after_a_reversal(
        self, session: AsyncSession
    ) -> None:
        """The unique index covers only what is in force, and this is what that buys.

        An undone correction stays in the table for good. If the index covered
        it too, a field could be corrected exactly once in its life and the
        second attempt would die on a constraint the person cannot even see.
        """
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        first = await correct(session, product.id, value="1200")
        assert first is not None
        await CatalogService(session).revert_correction(first, actor_user_id=2)
        await session.commit()

        # Act
        second = await correct(session, product.id, value="1400")

        # Assert
        assert second is not None
        assert second != first
        rows = await correction_rows(session, product.id)
        assert [row.status for row in rows] == [
            CorrectionStatus.REVERTED,
            CorrectionStatus.ACTIVE,
        ]
        # The new row opens against the portal's value, which is what came back.
        assert rows[1].portal_value == "1000.0000"
        history = await CatalogService(session).price_history(product.id)
        assert history.price == Decimal("1400")
        assert [mark.correction_id for mark in history.corrections] == [second]

    async def test_undoing_the_second_correction_leaves_the_field_free_again(
        self, session: AsyncSession
    ) -> None:
        """And undoing that one lands on the portal's number all the same."""
        # Arrange
        product = await ProductFactory.create(session, price=PORTAL_PRICE)
        first = await correct(session, product.id, value="1200")
        assert first is not None
        await CatalogService(session).revert_correction(first, actor_user_id=2)
        await session.commit()
        second = await correct(session, product.id, value="1400")
        assert second is not None

        # Act
        await CatalogService(session).revert_correction(second, actor_user_id=2)
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.price == PORTAL_PRICE
        assert history.corrections == []
