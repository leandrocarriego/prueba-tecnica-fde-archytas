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
  covers only the corrections still in force;
* **the index itself**, asked of the database in raw SQL rather than through
  the service — the way `test_change_log.py` asks it about the append-only log.
  A rule the schema enforces is only enforced if the schema has it.

Everything runs against a real session: this is authorisation, SQL and a
partial unique index, and none of the three is exercised by a mock.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
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

# A product id no factory ever hands out. The rows written in raw SQL below
# hang from it so they cannot collide with a product some other test built.
UNCLAIMED_ID = 9_999_999


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


async def write_correction_row(
    session: AsyncSession,
    *,
    status: CorrectionStatus,
    entity_id: int = UNCLAIMED_ID,
    field: str = "price",
    corrected_value: str = "1200",
) -> None:
    """Put one correction row into the table in raw SQL, past the service.

    The question the tests below ask is what the **database** allows, so they
    ask it the way `test_change_log.py` asks about the append-only log: with
    the statement a `psql` session would type. Going through
    `apply_correction` would only prove that `apply_correction` checks first,
    and the index is there for the day something else writes the row.
    """
    await session.execute(
        text(
            "INSERT INTO core.correction "
            "(entity_type, entity_id, field, portal_value, corrected_value, "
            "reason_code, corrected_by_user_id, corrected_at, status) "
            "VALUES (:entity_type, :entity_id, :field, CAST(:portal AS jsonb), "
            "CAST(:corrected AS jsonb), :reason, 1, now(), "
            "CAST(:status AS correction_status))"
        ),
        {
            "entity_type": PRICE_ENTITY,
            "entity_id": str(entity_id),
            "field": field,
            "portal": json.dumps(str(PORTAL_PRICE)),
            "corrected": json.dumps(corrected_value),
            "reason": REASON,
            "status": status.value,
        },
    )


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


class TestOnlyOneCorrectionStandsPerField:
    """The invariant the schema keeps, asked of the schema and not of the service.

    `uq_correction_in_force` is unique over `(entity_type, entity_id, field)`
    among the rows that are **not** `REVERTED`, and it decides two things the
    spec signed. A datum cannot carry two corrections at once — with two, RF-27
    would have two answers to "what did the portal say" and RF-31 two numbers to
    give back. And a datum whose correction was undone stays correctable, which
    is what keeps RF-30 from costing the field every correction it might still
    need.

    The append-only log is checked this way already (`test_change_log.py`):
    around the repository, straight at the database. The reason is the same
    here — the service checking first proves the service checks, and the index
    exists for the day something else writes the row.
    """

    async def test_the_database_under_test_has_the_index(self, session: AsyncSession) -> None:
        """Named, unique, over the three columns, and only over what is in force.

        The suite builds its schema from the models with
        `Base.metadata.create_all()` and never runs Alembic (`tests/conftest.py`
        says why), so this asks the database the three tests below actually run
        against. It is also what keeps a green run from meaning less than it
        says: without it, a refused insert only proves that *something* refused
        it. Whether the migration declares the same index is a different
        question, and CI answers it with `alembic check`.
        """
        # Act
        definition = await session.scalar(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = 'core' AND tablename = 'correction' "
                "AND indexname = 'uq_correction_in_force'"
            )
        )

        # Assert
        assert definition is not None, (
            "core.correction has no uq_correction_in_force in the test database. "
            "The schema here comes from the models, so the index is missing from "
            "app/modules/catalog/models.py, and nothing stops a datum from "
            "carrying two corrections at once."
        )
        assert "UNIQUE" in definition
        assert "(entity_type, entity_id, field)" in definition
        assert "REVERTED" in definition

    async def test_a_second_correction_on_the_same_field_is_refused(
        self, session: AsyncSession
    ) -> None:
        """Two values standing on one datum is the state the table may not reach."""
        # Arrange
        await write_correction_row(session, status=CorrectionStatus.ACTIVE)
        await session.commit()

        # Act
        with pytest.raises(IntegrityError) as refused:
            await write_correction_row(
                session, status=CorrectionStatus.ACTIVE, corrected_value="1400"
            )

        # Assert — a refused statement aborts the transaction, so the session is
        # rolled back before it is asked anything else.
        await session.rollback()
        assert "uq_correction_in_force" in str(refused.value)
        assert [row.corrected_value for row in await correction_rows(session, UNCLAIMED_ID)] == [
            "1200"
        ]

    async def test_a_correction_in_conflict_still_holds_the_field(
        self, session: AsyncSession
    ) -> None:
        """`CONFLICTED` is in force too: the predicate reads `<> REVERTED`, not `= ACTIVE`.

        A conflict is an open question about a correction that is still applied
        (RF-28): the portal's new number was recorded, not written. A field
        holding one is as taken as a field holding an active correction, and
        writing a second row would be the overwrite RF-28 forbids, arriving by
        another door.
        """
        # Arrange
        await write_correction_row(session, status=CorrectionStatus.CONFLICTED)
        await session.commit()

        # Act
        with pytest.raises(IntegrityError) as refused:
            await write_correction_row(
                session, status=CorrectionStatus.ACTIVE, corrected_value="1400"
            )

        # Assert
        await session.rollback()
        assert "uq_correction_in_force" in str(refused.value)
        assert len(await correction_rows(session, UNCLAIMED_ID)) == 1

    async def test_a_reverted_correction_leaves_the_field_free(self, session: AsyncSession) -> None:
        """And undone rows never take it back, however many of them pile up.

        `test_the_same_field_can_be_corrected_again_after_a_reversal` tells this
        story through the service. This one asks the index, because the index is
        what the story depends on: drop the `WHERE` from it and a field could be
        corrected exactly once in its life, with the second attempt dying on a
        constraint the person cannot see.
        """
        # Arrange — corrected and undone twice, which is a run of two mistakes
        # and not a state the table forbids.
        await write_correction_row(session, status=CorrectionStatus.REVERTED)
        await write_correction_row(session, status=CorrectionStatus.REVERTED)
        await session.commit()

        # Act
        await write_correction_row(session, status=CorrectionStatus.ACTIVE, corrected_value="1400")
        await session.commit()

        # Assert
        rows = await correction_rows(session, UNCLAIMED_ID)
        assert [row.status for row in rows] == [
            CorrectionStatus.REVERTED,
            CorrectionStatus.REVERTED,
            CorrectionStatus.ACTIVE,
        ]


class TestFindingWhatThereIsToUndo:
    """RF-30 from the change log, which is where the acceptance criterion puts it.

    The product's own page knows which datum it is about, so `CorrectionMark` is
    all it needs. The log does not: it lists corrections of many products at
    once, and to offer the undo beside a row it has to know **which** correction
    stands on that datum. So the answer carries the datum with it, in the same
    words the log writes (`catalog.product_price`, the product id as text).

    One question for a page of the log, not one per row — and only for whoever
    may undo, because handing correction ids to a screen that cannot use them
    would be a permission decided twice.
    """

    @pytest.fixture
    async def two_corrected_products(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> tuple[int, int]:
        """A corrected price on one product and a corrected description on another."""
        first = await ProductFactory.create(session, price=PORTAL_PRICE)
        second = await ProductFactory.create(session, price=PORTAL_PRICE)
        for product_id, field, value in (
            (first.id, "price", "1200"),
            (second.id, "description", "Tornillo hexagonal 3/8"),
        ):
            response = await owner_client.post(
                f"{CATALOG}/products/{product_id}/corrections",
                json={"field": field, "value": value, "reason_code": REASON},
            )
            assert response.status_code == 200
        return first.id, second.id

    async def test_each_correction_says_which_datum_it_stands_on(
        self, owner_client: AsyncClient, two_corrected_products: tuple[int, int]
    ) -> None:
        """Both products in one question, and each answer names its own datum."""
        # Arrange
        priced, described = two_corrected_products

        # Act
        response = await owner_client.get(CORRECTIONS, params={"product_id": [priced, described]})

        # Assert
        assert response.status_code == 200
        standing = {
            (item["entity_type"], item["entity_id"], item["field"]): item
            for item in response.json()
        }
        assert set(standing) == {
            (PRICE_ENTITY, str(priced), "price"),
            (PRODUCT_ENTITY, str(described), "description"),
        }
        price = standing[(PRICE_ENTITY, str(priced), "price")]
        assert price["corrected_value"] == "1200"
        assert price["portal_value"] == "1000.0000"
        assert price["status"] == "ACTIVE"
        # The id is the whole point: it is what the undo button is built from.
        assert isinstance(price["correction_id"], int)

    async def test_a_product_nobody_corrected_answers_with_nothing(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """An empty list, not a 404: asking is how the screen finds out."""
        # Arrange
        untouched = await ProductFactory.create(session, price=PORTAL_PRICE)

        # Act
        response = await owner_client.get(CORRECTIONS, params={"product_id": untouched.id})

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    async def test_an_undone_correction_is_not_offered_again(
        self, owner_client: AsyncClient, two_corrected_products: tuple[int, int]
    ) -> None:
        """What was undone no longer stands, so the log stops offering to undo it."""
        # Arrange
        priced, _ = two_corrected_products
        listed = (await owner_client.get(CORRECTIONS, params={"product_id": priced})).json()
        assert await owner_client.delete(f"{CORRECTIONS}/{listed[0]['correction_id']}")

        # Act
        response = await owner_client.get(CORRECTIONS, params={"product_id": priced})

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    async def test_sales_may_not_ask_which_corrections_stand(
        self, sales_client: AsyncClient, two_corrected_products: tuple[int, int]
    ) -> None:
        """The same asymmetry as the undo itself: sales corrects, and does not undo."""
        # Arrange
        priced, _ = two_corrected_products

        # Act
        response = await sales_client.get(CORRECTIONS, params={"product_id": priced})

        # Assert
        assert response.status_code == 403

    async def test_purchasing_may_not_ask_either(
        self, purchasing_client: AsyncClient, two_corrected_products: tuple[int, int]
    ) -> None:
        """Purchasing does not reach the catalog, and does not reach this."""
        # Arrange
        priced, _ = two_corrected_products

        # Act
        response = await purchasing_client.get(CORRECTIONS, params={"product_id": priced})

        # Assert
        assert response.status_code == 403

    async def test_an_anonymous_caller_is_asked_to_log_in(
        self, client: AsyncClient, two_corrected_products: tuple[int, int]
    ) -> None:
        """401 before any 403, like every other route of this feature."""
        # Arrange
        priced, _ = two_corrected_products

        # Act
        response = await client.get(CORRECTIONS, params={"product_id": priced})

        # Assert
        assert response.status_code == 401

    async def test_a_question_about_no_product_at_all_is_refused(
        self, owner_client: AsyncClient
    ) -> None:
        """A bounded question or none: an unfiltered dump of every correction
        standing in the system is not what any screen asks for."""
        # Act
        response = await owner_client.get(CORRECTIONS)

        # Assert
        assert response.status_code == 422
