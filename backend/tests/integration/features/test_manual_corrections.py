"""Correcting a value by hand, and everything that has to survive it.

The main paths of H4 and H5, exercised once each against a real session: what a
correction does to the datum, what it leaves in the log, what happens when the
portal later disagrees, and what comes back when somebody undoes it.

The exhaustive edge cases belong to the `Tester` — tasks 26 and 30 of
`tasks.md` name them one by one. What is here is the `Developer` checking that
the engine they wrote runs, and it is deliberately one assertion per behaviour
rather than a grid.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product
from app.modules.catalog.service import CatalogService
from app.modules.operations.service import OperationsService
from app.shared.corrections import CorrectionReason
from app.shared.errors import NotFoundError, ValidationError
from app.shared.events import NormalizedPriceRow
from tests.conftest import Queued
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

REASON = CorrectionReason.PORTAL_WAS_WRONG.value
CODE = "CONF-0001"


def portal_row(price: Decimal | int, *, row_id: int) -> NormalizedPriceRow:
    """One row of a daily list, for the product the conflict tests use."""
    return NormalizedPriceRow(
        staging_row_id=row_id,
        product_code=CODE,
        description="Producto en conflicto",
        price=Decimal(str(price)),
        currency="ARS",
    )


class TestCorrectingAValue:
    """H4: the value changes and what the portal said stays."""

    async def test_the_portal_value_survives_the_correction(self, session: AsyncSession) -> None:
        """RF-25: what the portal informed is kept, and RF-27 shows it beside."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        result = await CatalogService(session).apply_correction(
            product_id=product.id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail="la factura del proveedor dice 1200",
            actor_user_id=1,
        )
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(product.id)
        assert history.price == Decimal("1200")
        assert result.portal_value == "1000.0000"
        assert history.corrections[0].portal_value == "1000.0000"

    async def test_it_leaves_a_line_in_the_log_with_its_reason(self, session: AsyncSession) -> None:
        """RF-09, RF-10 and RF-12: who, when, what it said, and why."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act
        await CatalogService(session).apply_correction(
            product_id=product.id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail="la factura del proveedor dice 1200",
            actor_user_id=7,
        )
        await session.commit()

        # Assert
        log = await OperationsService(session).list_audit(sections=None)
        assert log.total == 1
        assert log.items[0].action == "CORRECTED"
        assert log.items[0].actor_user_id == 7
        assert log.items[0].old_value == "1000.0000"
        assert log.items[0].reason_label == "El portal lo informó mal"

    async def test_a_field_that_is_not_an_amount(self, session: AsyncSession) -> None:
        """RF-23 asks for any field the portal brought, not only the numbers."""
        # Arrange
        product = await ProductFactory.create(session, price=1000, description="Tornllo hexagonl")

        # Act
        await CatalogService(session).apply_correction(
            product_id=product.id,
            field="description",
            value="Tornillo hexagonal 8mm",
            reason_code=CorrectionReason.MISREAD_FROM_DOCUMENT.value,
            reason_detail=None,
            actor_user_id=1,
        )
        await session.commit()

        # Assert
        assert (
            await CatalogService(session).price_history(product.id)
        ).description == "Tornillo hexagonal 8mm"

    async def test_without_a_reason_there_is_no_correction(self, session: AsyncSession) -> None:
        """RF-11: the reason is what makes it a decision and not a number that appeared."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)

        # Act / Assert
        with pytest.raises(ValidationError):
            await CatalogService(session).apply_correction(
                product_id=product.id,
                field="price",
                value="1200",
                reason_code="",
                reason_detail=None,
                actor_user_id=1,
            )

    async def test_a_datum_nobody_brought_from_the_portal_gets_no_correction(
        self, session: AsyncSession
    ) -> None:
        """RF-33 from its other end: there is no original value to keep.

        The change is still recorded — RF-11 asks for a reason on any manual
        change to something that already existed — but as an update, because
        there is nothing it is being corrected against.
        """
        # Arrange — incorporated from the review queue with the price the person
        # typed, which is the path that marks a value as nobody's but theirs.
        await CatalogService(session).incorporate_product(
            product_code=CODE, description="Cargado a mano", price=Decimal("1000")
        )
        product_id = await session.scalar(select(Product.id).where(Product.code == CODE))
        assert product_id is not None

        # Act
        result = await CatalogService(session).apply_correction(
            product_id=product_id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=1,
        )
        await session.commit()

        # Assert
        assert result.correction_id is None
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].action == "UPDATED"


class TestWhenThePortalDisagrees:
    """RF-28 and RF-29, in the three runs the handover asks for."""

    @pytest.fixture
    async def corrected(self, session: AsyncSession) -> int:
        """A product the portal priced at 1000 and somebody corrected to 1200."""
        product = await ProductFactory.create(session, code=CODE, price=1000)
        await CatalogService(session).apply_correction(
            product_id=product.id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=1,
        )
        await session.commit()
        return product.id

    async def test_the_portal_repeating_itself_is_not_news(
        self, session: AsyncSession, corrected: int, queued_alerts: Queued
    ) -> None:
        """The same 1000 it had already said: nothing to decide, nobody to warn."""
        # Act
        await CatalogService(session).apply_price_batch(
            batch_id=1, rows=(portal_row(1000, row_id=1),), seen_codes=(CODE,)
        )
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(corrected)
        assert history.price == Decimal("1200")
        assert history.corrections[0].status == "ACTIVE"
        assert queued_alerts.count == 0

    async def test_a_different_value_is_flagged_and_the_owner_is_told(
        self, session: AsyncSession, corrected: int, queued_alerts: Queued
    ) -> None:
        """The correction is **not** overwritten: it is flagged and warned about."""
        # Act
        await CatalogService(session).apply_price_batch(
            batch_id=2, rows=(portal_row(1500, row_id=2),), seen_codes=(CODE,)
        )
        await session.commit()

        # Assert
        history = await CatalogService(session).price_history(corrected)
        assert history.price == Decimal("1200")
        assert history.corrections[0].status == "CONFLICTED"
        assert history.corrections[0].conflict_value == "1500"
        assert queued_alerts.count == 1

    async def test_the_same_disagreement_twice_warns_once(
        self, session: AsyncSession, corrected: int, queued_alerts: Queued
    ) -> None:
        """A daily list is daily: the same conflict must not warn every morning."""
        # Arrange
        service = CatalogService(session)
        await service.apply_price_batch(
            batch_id=2, rows=(portal_row(1500, row_id=2),), seen_codes=(CODE,)
        )
        await session.commit()

        # Act
        await service.apply_price_batch(
            batch_id=3, rows=(portal_row(1500, row_id=3),), seen_codes=(CODE,)
        )
        await session.commit()

        # Assert
        assert (await service.price_history(corrected)).price == Decimal("1200")
        assert queued_alerts.count == 1


class TestUndoingACorrection:
    """H5: the datum goes back to what the portal said, and the row stays."""

    async def test_it_restores_the_portal_value_and_not_the_previous_one(
        self, session: AsyncSession
    ) -> None:
        """RF-31, and the reason `portal_value` is never rewritten.

        After two corrections the previous value is 1200 and the portal's is
        1000. They are different numbers, and only one of them is the answer.
        """
        # Arrange
        product = await ProductFactory.create(session, price=1000)
        service = CatalogService(session)
        first = await service.apply_correction(
            product_id=product.id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=1,
        )
        await service.apply_correction(
            product_id=product.id,
            field="price",
            value="1300",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=1,
        )
        await session.commit()
        assert first.correction_id is not None

        # Act
        reverted = await service.revert_correction(first.correction_id, actor_user_id=2)
        await session.commit()

        # Assert
        assert reverted.status == "REVERTED"
        history = await service.price_history(product.id)
        assert history.price == Decimal("1000")
        assert history.corrections == []

    async def test_undoing_is_recorded_like_everything_else(self, session: AsyncSession) -> None:
        """RF-32: who undid it and when."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)
        service = CatalogService(session)
        correction = await service.apply_correction(
            product_id=product.id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=1,
        )
        await session.commit()
        assert correction.correction_id is not None

        # Act
        await service.revert_correction(correction.correction_id, actor_user_id=2)
        await session.commit()

        # Assert
        log = await OperationsService(session).list_audit(sections=None)
        assert log.items[0].action == "CORRECTION_REVERTED"
        assert log.items[0].actor_user_id == 2
        assert log.items[0].new_value == "1000.0000"

    async def test_undoing_something_that_was_never_corrected_fails_clean(
        self, session: AsyncSession
    ) -> None:
        """RF-33: a datum loaded by hand has no correction, so there is none to undo."""
        # Act / Assert
        with pytest.raises(NotFoundError):
            await CatalogService(session).revert_correction(999999, actor_user_id=1)


class TestTheLogStaysWritten:
    """RF-16 and RF-17, against the database and not against the repository."""

    async def test_an_update_by_direct_sql_is_refused(self, session: AsyncSession) -> None:
        """A method the repository does not expose only prevents until somebody adds it."""
        # Arrange
        product = await ProductFactory.create(session, price=1000)
        await CatalogService(session).apply_correction(
            product_id=product.id,
            field="price",
            value="1200",
            reason_code=REASON,
            reason_detail=None,
            actor_user_id=1,
        )
        await session.commit()

        # Act / Assert
        with pytest.raises(DBAPIError):
            await session.execute(text("UPDATE operations.audit_entry SET entity_id = 'x'"))
