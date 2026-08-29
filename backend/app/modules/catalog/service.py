"""Catalog business logic: what the business knows, and what it refuses to guess.

Three decisions live here, and all three come straight from the spec:

* **The first list establishes the catalog** (RF-02). Before it there are no
  products, so every row of that list becomes one.
* **After that, an unknown product is never created** (RF-07). It is reported so
  a person can decide, because the assumption that the list only changes prices
  is exactly that — an assumption, and one the client has not confirmed.
* **A known product that stops appearing keeps its last price** (RF-08). It is
  flagged, not deleted, and never estimated.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.catalog.models import PriceSource, Product, ProductPrice, ProductStatus
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import (
    PriceHistoryRead,
    PriceList,
    PricePointRead,
    PriceRead,
)
from app.shared.errors import NotFoundError
from app.shared.events import (
    KnownProductsMissing,
    MissingProduct,
    NormalizedHistoryPoint,
    NormalizedPriceRow,
    ProductPricesUpdated,
    ProductsRegistered,
    RegisteredProduct,
    UnknownProduct,
    UnknownProductsObserved,
    events,
)

logger = get_logger(__name__)

HIGHLIGHT_THRESHOLD_KEY = "price_update.highlight_threshold_pct"
# What the platform highlights while nobody has changed it (RF-20). The owner
# moves it from the settings screen, and the new value arrives as an event.
DEFAULT_HIGHLIGHT_THRESHOLD = Decimal("10")

HUNDRED = Decimal("100")

# The three kinds of decision this module reacts to. They are `triage`'s
# vocabulary, and they travel as strings so its queue stays generic.
UNREADABLE_ROW = "unreadable_row"
UNKNOWN_PRODUCT = "unknown_product"
MISSING_PRODUCT = "missing_product"


class CatalogService:
    """Applies a batch of prices, and answers what a product is worth."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogRepository(session)

    # --- Applying a batch -------------------------------------------------

    async def apply_price_batch(
        self,
        *,
        batch_id: int,
        rows: tuple[NormalizedPriceRow, ...],
        seen_codes: tuple[str, ...] = (),
        quarantined: int = 0,
        job_run_id: int | None = None,
    ) -> None:
        """Register the price in force of every known product in the batch."""
        now = datetime.now(UTC)
        threshold = await self.highlight_threshold()
        seeding = await self.catalog.count_products() == 0

        known = await self.catalog.products_by_code([row.product_code for row in rows])
        registered: list[RegisteredProduct] = []
        unknown: list[UnknownProduct] = []
        updated = unchanged = highlighted = 0

        for row in rows:
            product = known.get(row.product_code)
            if product is None:
                if not seeding:
                    # The assumption may be false, and the system says so
                    # instead of quietly growing the catalog (RF-07).
                    unknown.append(
                        UnknownProduct(
                            staging_row_id=row.staging_row_id,
                            product_code=row.product_code,
                            description=row.description,
                            price=row.price,
                        )
                    )
                    continue
                product = await self.catalog.add_product(
                    code=row.product_code, description=row.description, seen_at=now
                )
                known[row.product_code] = product
                registered.append(
                    RegisteredProduct(product_id=product.id, product_code=product.code)
                )

            changed, was_highlighted = await self._register_price(
                product=product,
                price=row.price,
                currency=row.currency,
                moment=now,
                threshold=threshold,
                batch_id=batch_id,
            )
            updated += int(changed)
            unchanged += int(not changed)
            highlighted += int(was_highlighted)

        # Everything the file carried, not only what could be read: a product
        # whose row was unreadable is already a case, and reporting it a second
        # time as one that stopped coming would be a lie (RF-28).
        missing = await self._flag_missing(
            seen_codes={row.product_code for row in rows} | set(seen_codes)
        )

        await events.publish(
            ProductPricesUpdated(
                batch_id=batch_id,
                updated=updated,
                unchanged=unchanged,
                highlighted=highlighted,
                quarantined=quarantined,
                job_run_id=job_run_id,
            ),
            self.session,
        )
        if registered:
            # The portal already publishes a history for each of these, and it
            # is brought in once, from the task the handler of this event
            # queues (RF-38).
            await events.publish(
                ProductsRegistered(batch_id=batch_id, products=tuple(registered)), self.session
            )
        if unknown:
            await events.publish(
                UnknownProductsObserved(batch_id=batch_id, cases=tuple(unknown)), self.session
            )
        if missing:
            await events.publish(
                KnownProductsMissing(batch_id=batch_id, products=tuple(missing)), self.session
            )

        logger.info(
            "Price batch applied",
            extra={
                "batch_id": batch_id,
                "updated": updated,
                "unchanged": unchanged,
                "highlighted": highlighted,
                "registered": len(registered),
                "unknown": len(unknown),
                "missing": len(missing),
            },
        )

    async def import_published_history(
        self, *, product_code: str, points: tuple[NormalizedHistoryPoint, ...]
    ) -> None:
        """Bring in the history the portal already publishes for a product (RF-38).

        Importing it twice leaves the same points: the uniqueness of
        `(product_id, changed_at)` is what says so, not a check in this method
        (RF-40).
        """
        product = await self.catalog.get_by_code(product_code)
        if product is None:
            # The history of a product the catalog does not know. Nothing to
            # attach it to, and nothing to lose: the screen it came from is
            # stored in `raw` either way.
            logger.warning("Published history for an unknown product", extra={"code": product_code})
            return

        for point in points:
            await self.catalog.add_point(
                product_id=product.id,
                price=point.price,
                changed_at=point.changed_at,
                source=PriceSource.PORTAL,
            )
        logger.info(
            "Published history imported",
            extra={"product_code": product_code, "points": len(points)},
        )

    # --- Reacting to a person's decision ----------------------------------

    async def incorporate_product(
        self,
        *,
        product_code: str,
        description: str,
        price: Decimal | None,
        currency: str = "ARS",
        rule_id: int | None = None,
        batch_id: int = 0,
    ) -> None:
        """Add a product a person decided to incorporate (RF-30)."""
        if await self.catalog.get_by_code(product_code) is not None:
            return
        now = datetime.now(UTC)
        product = await self.catalog.add_product(
            code=product_code,
            description=description,
            seen_at=now,
            registered_by_rule_id=rule_id,
        )
        if price is not None:
            await self._register_price(
                product=product,
                price=price,
                currency=currency,
                moment=now,
                threshold=await self.highlight_threshold(),
                batch_id=None,
            )
        await events.publish(
            ProductsRegistered(
                batch_id=batch_id,
                products=(RegisteredProduct(product_id=product.id, product_code=product.code),),
            ),
            self.session,
        )
        logger.info("Product incorporated", extra={"product_code": product_code})

    async def set_price_by_code(
        self, *, product_code: str, price: Decimal, currency: str = "ARS"
    ) -> None:
        """Register the price a person indicated for a known product (RF-29)."""
        product = await self.catalog.get_by_code(product_code)
        if product is None:
            raise NotFoundError("Product not found", details={"product_code": product_code})
        await self._register_price(
            product=product,
            price=price,
            currency=currency,
            moment=datetime.now(UTC),
            threshold=await self.highlight_threshold(),
            batch_id=None,
        )

    async def discontinue(self, product_id: int) -> None:
        """Give a product up for discontinued (RF-31)."""
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError("Product not found", details={"product_id": product_id})
        product.status = ProductStatus.DISCONTINUED
        await self.session.flush()
        logger.info("Product discontinued", extra={"product_id": product_id})

    async def keep_active(self, product_id: int) -> None:
        """Keep a product in force even though it stopped coming in the list (RF-31)."""
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError("Product not found", details={"product_id": product_id})
        product.status = ProductStatus.ACTIVE
        await self.session.flush()

    async def undo_rule(self, rule_id: int) -> None:
        """Undo what a revoked rule had done here (RF-37).

        Only what this module did *because of that rule*: the product it
        incorporated. A product registered by a list is not touched.
        """
        removed = 0
        for product in await self.catalog.active_products():
            if product.registered_by_rule_id == rule_id:
                await self.catalog.remove_product(product)
                removed += 1
        if removed:
            logger.info("Products un-registered by a revoked rule", extra={"rule_id": rule_id})

    async def remember_setting(self, key: str, value: object) -> None:
        """Keep the business parameter this module reads while it applies a batch."""
        await self.catalog.put_setting(key, value)

    # --- Reading ----------------------------------------------------------

    async def list_prices(
        self,
        *,
        skip: int = 0,
        limit: int = 200,
        query: str | None = None,
        highlighted: bool = False,
    ) -> PriceList:
        """The prices screen: code, description and the price in force (RF-04)."""
        rows = await self.catalog.list_prices(
            skip=skip, limit=limit, query=query, highlighted=highlighted
        )
        total = await self.catalog.count_prices(query=query, highlighted=highlighted)
        previous_month = await self.catalog.last_point_before(self._start_of_month())
        items = [
            self._price_read(product, price, previous_month.get(product.id))
            for product, price in rows
        ]
        return PriceList(items=items, total=total, skip=skip, limit=limit)

    async def price_history(self, product_id: int) -> PriceHistoryRead:
        """How the price of one product evolved (RF-23)."""
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError("Product not found", details={"product_id": product_id})
        current = await self.catalog.get_price(product_id)
        points = await self.catalog.points_of(product_id)
        previous_month = await self.catalog.last_point_before(self._start_of_month())
        return PriceHistoryRead(
            product_id=product.id,
            code=product.code,
            description=product.description,
            price=None if current is None else current.price,
            currency="ARS" if current is None else current.currency,
            monthly_variation_pct=self._variation(
                None if current is None else current.price, previous_month.get(product.id)
            ),
            points=[PricePointRead.model_validate(point) for point in points],
        )

    async def highlight_threshold(self) -> Decimal:
        """The percentage above which a rise is highlighted (RF-19, RF-20)."""
        value = await self.catalog.get_setting(HIGHLIGHT_THRESHOLD_KEY)
        if value is None:
            return DEFAULT_HIGHLIGHT_THRESHOLD
        try:
            return Decimal(str(value))
        except (ArithmeticError, ValueError):
            logger.warning("Highlight threshold is not a number, using the starting value")
            return DEFAULT_HIGHLIGHT_THRESHOLD

    # --- Internals --------------------------------------------------------

    async def _register_price(
        self,
        *,
        product: Product,
        price: Decimal,
        currency: str,
        moment: datetime,
        threshold: Decimal,
        batch_id: int | None,
    ) -> tuple[bool, bool]:
        """Write the price in force. Returns (it changed, it is highlighted).

        A price that did not change adds no point to the history (RF-22) and
        keeps the date on which it was registered: that date is what the screen
        shows next to a product that did not come in today's list (RF-08).
        """
        product.last_seen_at = moment
        current = await self.catalog.get_price(product.id)

        if current is None:
            await self.catalog.put_price(
                ProductPrice(
                    product_id=product.id,
                    price=price,
                    currency=currency,
                    effective_at=moment,
                    previous_price=None,
                    is_highlighted=False,
                    is_stale=False,
                )
            )
            await self.catalog.add_point(
                product_id=product.id,
                price=price,
                changed_at=moment,
                source=PriceSource.SYSTEM,
                batch_id=batch_id,
            )
            return True, False

        if current.price == price:
            # The list brought the same price: a 0% rise against the previous
            # update, so a product highlighted earlier stops being highlighted
            # now (RF-25). A badge that only ever turns on ends up on every
            # product and stops meaning anything.
            current.previous_price = price
            current.is_highlighted = False
            current.is_stale = False
            await self.session.flush()
            return False, False

        variation = self._variation(price, current.price)
        is_highlighted = variation is not None and variation > threshold
        current.previous_price = current.price
        current.price = price
        current.currency = currency
        current.effective_at = moment
        current.is_highlighted = is_highlighted
        current.is_stale = False
        await self.session.flush()
        await self.catalog.add_point(
            product_id=product.id,
            price=price,
            changed_at=moment,
            source=PriceSource.SYSTEM,
            batch_id=batch_id,
        )
        return True, is_highlighted

    async def _flag_missing(self, *, seen_codes: set[str]) -> list[MissingProduct]:
        """Flag the known products that did not come in this list (RF-08, RF-28)."""
        missing: list[MissingProduct] = []
        for product in await self.catalog.active_products():
            if product.code in seen_codes:
                continue
            price = await self.catalog.get_price(product.id)
            if price is not None:
                price.is_stale = True
                # There was no comparison for it in this update, so there is no
                # rise to flag either: it leaves the highlighted state the same
                # way it leaves the list (RF-25, `estados-precio.mmd`).
                price.is_highlighted = False
            missing.append(
                MissingProduct(
                    product_id=product.id,
                    product_code=product.code,
                    description=product.description,
                )
            )
        if missing:
            await self.session.flush()
        return missing

    @staticmethod
    def _variation(current: Decimal | None, before: Decimal | None) -> Decimal | None:
        """Percentage change between two prices, or None if there is nothing to compare."""
        if current is None or before is None or before == 0:
            return None
        return ((current - before) / before * HUNDRED).quantize(Decimal("0.01"))

    @staticmethod
    def _start_of_month() -> datetime:
        """Midnight on the first day of the current calendar month."""
        now = datetime.now(UTC)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _price_read(
        self, product: Product, price: ProductPrice | None, previous_month: Decimal | None
    ) -> PriceRead:
        """Assemble one row of the prices screen."""
        return PriceRead(
            product_id=product.id,
            code=product.code,
            description=product.description,
            status=product.status,
            price=None if price is None else price.price,
            currency="ARS" if price is None else price.currency,
            effective_at=None if price is None else price.effective_at,
            previous_price=None if price is None else price.previous_price,
            is_highlighted=False if price is None else price.is_highlighted,
            is_stale=False if price is None else price.is_stale,
            monthly_variation_pct=self._variation(
                None if price is None else price.price, previous_month
            ),
        )
