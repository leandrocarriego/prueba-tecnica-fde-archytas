"""The two numbers the prices screen shows next to a product, at their edges.

RF-24 — the variation against the previous calendar month — and RF-25 — which
rises get highlighted. Both are one subtraction and one division, and both are
exactly the kind of thing that is right in the middle of the range and wrong at
the borders.

What "the previous calendar month" means is not left to this file to decide:
`plan.md` and `data-model.md` define it as **the last point before the first day
of the current month**. So a month with no data at all does not blank the
number: it falls back to the last price the product carried into it, which is
the price it actually had.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import PriceSource
from app.modules.catalog.service import CatalogService
from app.modules.operations.schemas import PriceUpdateSettingsWrite
from app.modules.operations.service import OperationsService
from app.shared.events import NormalizedPriceRow
from tests.factories.catalog_factory import ProductFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]


def start_of_this_month() -> datetime:
    """Midnight on the first day of the current calendar month, in UTC."""
    return datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def last_day_of_previous_month() -> datetime:
    """A moment inside the previous calendar month, whatever month it is today."""
    return start_of_this_month() - timedelta(hours=6)


def months_back(count: int) -> datetime:
    """A moment `count` calendar months before the start of this one."""
    moment = start_of_this_month()
    for _ in range(count):
        moment = (moment - timedelta(days=1)).replace(day=1)
    return moment + timedelta(hours=12)


async def variation_of(session: AsyncSession, product_id: int) -> Decimal | None:
    """What the product page reports as its month-on-month variation."""
    return (await CatalogService(session).price_history(product_id)).monthly_variation_pct


class TestTheMonthlyVariation:
    """RF-24, and what it answers when the month it compares against is empty."""

    async def test_it_compares_against_the_close_of_the_previous_month(
        self, session: AsyncSession
    ) -> None:
        """The acceptance criterion, in its own numbers: $100 in July, $115 today."""
        # Arrange
        product = await ProductFactory.create(session, price=115)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=last_day_of_previous_month()
        )

        # Act
        variation = await variation_of(session, product.id)

        # Assert
        assert variation == Decimal("15.00")

    async def test_a_month_without_data_falls_back_to_the_last_price_before_it(
        self, session: AsyncSession
    ) -> None:
        """The product kept a price through that month; it did not stop having one.

        Nothing happened in the previous calendar month, so the comparison uses
        the last point before this month — which is the price the product was
        actually carrying. Blanking the number instead would hide a real rise.
        """
        # Arrange
        product = await ProductFactory.create(session, price=120)
        await ProductFactory.add_point(session, product, price=80, changed_at=months_back(4))

        # Act
        variation = await variation_of(session, product.id)

        # Assert
        assert variation == Decimal("50.00")

    async def test_a_product_with_no_history_before_this_month_has_no_variation(
        self, session: AsyncSession
    ) -> None:
        """None, not zero: there is nothing to compare against, and 0% is a claim."""
        # Arrange
        product = await ProductFactory.create(session, price=100)
        await ProductFactory.add_point(session, product, price=100, changed_at=datetime.now(UTC))

        # Act
        variation = await variation_of(session, product.id)

        # Assert
        assert variation is None

    async def test_a_product_without_a_price_has_no_variation(self, session: AsyncSession) -> None:
        """A product the catalog knows but has never priced does not divide by anything."""
        # Arrange
        product = await ProductFactory.create(session)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=last_day_of_previous_month()
        )

        # Act
        variation = await variation_of(session, product.id)

        # Assert
        assert variation is None

    async def test_a_price_that_went_down_reports_a_negative_variation(
        self, session: AsyncSession
    ) -> None:
        """Prices fall too, and the screen has to be able to say so."""
        # Arrange
        product = await ProductFactory.create(session, price=90)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=last_day_of_previous_month()
        )

        # Act
        variation = await variation_of(session, product.id)

        # Assert
        assert variation == Decimal("-10.00")

    async def test_the_listing_reports_the_same_number_as_the_product_page(
        self, session: AsyncSession
    ) -> None:
        """Two screens, one number: computing it twice is how they drift apart."""
        # Arrange
        product = await ProductFactory.create(session, price=115)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=last_day_of_previous_month()
        )

        # Act
        listing = await CatalogService(session).list_prices(query=product.code)

        # Assert
        assert listing.items[0].monthly_variation_pct == await variation_of(session, product.id)

    async def test_only_the_last_point_before_the_month_counts(self, session: AsyncSession) -> None:
        """Several points last month: the one that matters is how the month closed."""
        # Arrange
        product = await ProductFactory.create(session, price=110)
        await ProductFactory.add_point(session, product, price=50, changed_at=months_back(2))
        await ProductFactory.add_point(
            session, product, price=100, changed_at=last_day_of_previous_month()
        )

        # Act
        variation = await variation_of(session, product.id)

        # Assert
        assert variation == Decimal("10.00")


class TestTheHighlightThreshold:
    """RF-25 at the border, where "more than 10%" stops meaning "10%"."""

    @staticmethod
    async def apply(session: AsyncSession, product_code: str, price: int) -> None:
        """Apply a batch carrying one product at one price, as the pipeline does."""
        await CatalogService(session).apply_price_batch(
            batch_id=1,
            rows=(
                NormalizedPriceRow(
                    staging_row_id=1,
                    product_code=product_code,
                    description="Producto de prueba",
                    price=Decimal(price),
                    currency="ARS",
                ),
            ),
            seen_codes=(product_code,),
        )

    @pytest.mark.parametrize(
        ("new_price", "highlighted"),
        [(115, True), (111, True), (110, False), (105, False), (90, False)],
        ids=["+15%", "+11%", "+10% exacto", "+5%", "baja"],
    )
    async def test_the_edge_of_the_configured_threshold(
        self, session: AsyncSession, new_price: int, highlighted: bool
    ) -> None:
        """At 10%: $100 → $115 is highlighted and $100 → $110 is not.

        The acceptance criterion says "subió **más** que el porcentaje", so the
        threshold itself is not a rise worth flagging. A fall never is.
        """
        # Arrange
        product = await ProductFactory.create(session, price=100)
        await session.commit()

        # Act
        await self.apply(session, product.code, new_price)

        # Assert
        price = await CatalogService(session).catalog.get_price(product.id)
        assert price is not None
        assert price.is_highlighted is highlighted

    async def test_it_uses_the_threshold_the_owner_configured(self, session: AsyncSession) -> None:
        """RF-19: a rise of 15% stops being remarkable once the owner says 20%."""
        # Arrange
        await OperationsService(session).set_price_update_settings(
            PriceUpdateSettingsWrite(interval_hours=12, highlight_threshold_pct=20),
            actor_user_id=1,
        )
        product = await ProductFactory.create(session, price=100)
        await session.commit()

        # Act
        await self.apply(session, product.code, 115)

        # Assert
        price = await CatalogService(session).catalog.get_price(product.id)
        assert price is not None
        assert price.is_highlighted is False

    async def test_a_highlighted_product_is_measured_against_the_previous_update(
        self, session: AsyncSession
    ) -> None:
        """RF-25 compares against the previous **update**, not the previous point.

        A price that does not change adds no point to the history (RF-22), so
        the two are different numbers and only one of them is the right one.
        """
        # Arrange
        product = await ProductFactory.create(session, price=100)
        await ProductFactory.add_point(
            session, product, price=100, changed_at=months_back(1), source=PriceSource.PORTAL
        )
        await session.commit()

        # Act
        await self.apply(session, product.code, 115)

        # Assert
        price = await CatalogService(session).catalog.get_price(product.id)
        assert price is not None
        assert price.previous_price == Decimal("100")
        assert price.is_highlighted is True

    async def test_the_highlight_clears_when_the_price_stops_rising(
        self, session: AsyncSession
    ) -> None:
        """RF-25: the badge describes the last update, not a rise that once happened.

        The supplier publishes twice a day, so a mark that only ever turns on
        would be on every product within a week — and the screen it exists for,
        "mirar sólo lo que se salió de lo normal", would be the whole list again.
        """
        # Arrange: it rose 15% and got highlighted.
        product = await ProductFactory.create(session, price=100)
        await session.commit()
        await self.apply(session, product.code, 115)
        first = await CatalogService(session).catalog.get_price(product.id)
        assert first is not None and first.is_highlighted is True

        # Act: the next list brings the same price. A 0% rise.
        await self.apply(session, product.code, 115)

        # Assert
        price = await CatalogService(session).catalog.get_price(product.id)
        assert price is not None
        assert price.is_highlighted is False
        assert price.previous_price == Decimal("115")

    async def test_the_highlight_clears_when_the_product_stops_being_listed(
        self, session: AsyncSession
    ) -> None:
        """`estados-precio.mmd` draws Destacado → Conservado, and Conservado is not highlighted.

        There was no comparison for this product in this update, so there is no
        rise to flag: it keeps its last price, and it keeps it plainly.
        """
        # Arrange
        product = await ProductFactory.create(session, price=100)
        await session.commit()
        await self.apply(session, product.code, 115)

        # Act: an update that does not carry it at all.
        await CatalogService(session).apply_price_batch(batch_id=2, rows=(), seen_codes=())

        # Assert
        price = await CatalogService(session).catalog.get_price(product.id)
        assert price is not None
        assert price.is_stale is True
        assert price.is_highlighted is False
