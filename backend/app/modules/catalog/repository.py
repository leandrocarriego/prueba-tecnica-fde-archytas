"""Data access for the catalog module. Private to this module."""

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import (
    AliasSource,
    CatalogSetting,
    Category,
    CategoryAlias,
    Correction,
    CorrectionStatus,
    OrderSpend,
    PricePoint,
    PriceSource,
    Product,
    ProductPrice,
    ProductStatus,
    SaleRevenue,
    StockPoint,
)


class CatalogRepository:
    """Reads and writes products, their price in force and their history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Products --------------------------------------------------------

    async def count_products(self) -> int:
        """How many products the catalog knows. Zero means no list has landed yet."""
        result = await self.session.execute(select(func.count()).select_from(Product))
        return int(result.scalar_one())

    async def get_product(self, product_id: int) -> Product | None:
        """Return a product by id, or None."""
        return await self.session.get(Product, product_id)

    async def get_by_code(self, code: str) -> Product | None:
        """Return the product with this supplier code, or None."""
        result = await self.session.execute(select(Product).where(Product.code == code))
        return result.scalar_one_or_none()

    async def products_by_code(self, codes: list[str]) -> dict[str, Product]:
        """Return the products for these codes, indexed by code."""
        if not codes:
            return {}
        result = await self.session.execute(select(Product).where(Product.code.in_(codes)))
        return {product.code: product for product in result.scalars().all()}

    async def active_products(self) -> list[Product]:
        """Every product the business still buys."""
        result = await self.session.execute(
            select(Product).where(Product.status == ProductStatus.ACTIVE)
        )
        return list(result.scalars().all())

    async def add_product(
        self,
        *,
        code: str,
        description: str,
        seen_at: datetime,
        registered_by_rule_id: int | None = None,
    ) -> Product:
        """Register a product as known."""
        product = Product(
            code=code,
            description=description,
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            registered_by_rule_id=registered_by_rule_id,
        )
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def remove_product(self, product: Product) -> None:
        """Un-register a product. Its price and its points go with it."""
        await self.session.delete(product)
        await self.session.flush()

    # --- The price in force ----------------------------------------------

    async def get_price(self, product_id: int) -> ProductPrice | None:
        """Return the price in force for a product, or None."""
        return await self.session.get(ProductPrice, product_id)

    async def put_price(self, price: ProductPrice) -> ProductPrice:
        """Insert or refresh the price in force."""
        merged = await self.session.merge(price)
        await self.session.flush()
        return merged

    async def list_prices(
        self,
        *,
        skip: int = 0,
        limit: int = 200,
        query: str | None = None,
        highlighted: bool = False,
        changed: bool = False,
        category_id: int | None = None,
    ) -> list[tuple[Product, ProductPrice | None, Category | None]]:
        """Return a page of products with their price in force and their rubro.

        Priced products come first, then those the portal never priced. In a
        list *of prices*, a product without one is not what the screen is about,
        and leaving it up top buries the rows that are. `price IS NULL` is true
        only when there is no price row (the column itself is `NOT NULL`), so
        ordering by it ascending puts the priced ones ahead; the code keeps the
        order stable within each group.
        """
        statement = self._prices_query(query, highlighted, changed, category_id)
        result = await self.session.execute(
            statement.order_by(ProductPrice.price.is_(None), Product.code).offset(skip).limit(limit)
        )
        return [(row[0], row[1], row[2]) for row in result.all()]

    async def count_prices(
        self,
        *,
        query: str | None = None,
        highlighted: bool = False,
        changed: bool = False,
        category_id: int | None = None,
    ) -> int:
        """How many products match the same filters as `list_prices`."""
        subquery = self._prices_query(query, highlighted, changed, category_id).subquery()
        result = await self.session.execute(select(func.count()).select_from(subquery))
        return int(result.scalar_one())

    async def price_movement(self) -> dict[str, tuple[int, Decimal | None]]:
        """The whole-catalog counts the summary cards show, in one round trip.

        A product «rose» when the price in force is above `previous_price` and
        «fell» when it is below — the same comparison the table draws per row,
        run over the entire list rather than the page. The average travels with
        each direction so the «+ 9,2 %» under «subieron» is the mean of the
        rises, not of everything. Products with no price or no `previous_price`
        have not moved and count for neither.
        """
        moved = (
            ProductPrice.price.isnot(None)
            & ProductPrice.previous_price.isnot(None)
            & (ProductPrice.previous_price != 0)
        )
        pct = (ProductPrice.price - ProductPrice.previous_price) / ProductPrice.previous_price * 100
        result = await self.session.execute(
            select(
                func.count().filter(moved & (ProductPrice.price > ProductPrice.previous_price)),
                func.avg(pct).filter(moved & (ProductPrice.price > ProductPrice.previous_price)),
                func.count().filter(moved & (ProductPrice.price < ProductPrice.previous_price)),
                func.avg(pct).filter(moved & (ProductPrice.price < ProductPrice.previous_price)),
            )
        )
        raised_n, raised_avg, lowered_n, lowered_avg = result.one()
        return {
            "raised": (int(raised_n), None if raised_avg is None else Decimal(raised_avg)),
            "lowered": (int(lowered_n), None if lowered_avg is None else Decimal(lowered_avg)),
        }

    async def count_stale(self) -> int:
        """Products that stopped coming in the list and keep their last price (RF-08)."""
        result = await self.session.execute(
            select(func.count()).select_from(ProductPrice).where(ProductPrice.is_stale.is_(True))
        )
        return int(result.scalar_one())

    @staticmethod
    def _prices_query(
        query: str | None, highlighted: bool, changed: bool, category_id: int | None
    ) -> Select[Any]:
        """The one statement behind the listing and its count.

        The rubro travels on the same row as the price: one left join, so a
        product with no category still comes back (as «sin rubro») and the
        listing never drops a row for lacking one.
        """
        statement = (
            select(Product, ProductPrice, Category)
            .outerjoin(ProductPrice, ProductPrice.product_id == Product.id)
            .outerjoin(Category, Category.id == Product.category_id)
        )
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(Product.code.ilike(pattern), Product.description.ilike(pattern))
            )
        if highlighted:
            statement = statement.where(ProductPrice.is_highlighted.is_(True))
        if changed:
            # «Sólo con cambios»: the price in force differs from the one before
            # it. A product with no `previous_price` has nothing to differ from
            # and is not a change.
            statement = statement.where(
                ProductPrice.previous_price.isnot(None),
                ProductPrice.price != ProductPrice.previous_price,
            )
        if category_id is not None:
            statement = statement.where(Product.category_id == category_id)
        return statement

    # --- The history -----------------------------------------------------

    async def add_point(
        self,
        *,
        product_id: int,
        price: Decimal,
        changed_at: datetime,
        source: PriceSource,
        batch_id: int | None = None,
    ) -> None:
        """Add a point, or leave the one that is already there (RF-40).

        `ON CONFLICT DO NOTHING` over `(product_id, changed_at)`: importing a
        published history twice has to leave the same number of points, and the
        database is what guarantees it — no `SELECT` first, no race.
        """
        await self.session.execute(
            insert(PricePoint)
            .values(
                product_id=product_id,
                price=price,
                changed_at=changed_at,
                source=source,
                batch_id=batch_id,
            )
            .on_conflict_do_nothing(constraint="uq_price_point_product_changed")
        )
        await self.session.flush()

    async def points_of(self, product_id: int) -> list[PricePoint]:
        """Every point of a product, oldest first."""
        result = await self.session.execute(
            select(PricePoint)
            .where(PricePoint.product_id == product_id)
            .order_by(PricePoint.changed_at)
        )
        return list(result.scalars().all())

    async def last_point_before(self, moment: datetime) -> dict[int, Decimal]:
        """The last price each product had before a moment, by product.

        One query for the whole catalog rather than one per product: this feeds
        the month-on-month variation of every row of the prices screen (RF-24).
        """
        statement = (
            select(PricePoint.product_id, PricePoint.price)
            .where(PricePoint.changed_at < moment)
            .distinct(PricePoint.product_id)
            .order_by(PricePoint.product_id, PricePoint.changed_at.desc())
        )
        result = await self.session.execute(statement)
        return {row[0]: row[1] for row in result.all()}

    # --- The projected business parameters --------------------------------

    async def get_setting(self, key: str) -> Any | None:
        """Return the value this module last heard for a parameter, or None."""
        setting = await self.session.get(CatalogSetting, key)
        return None if setting is None else setting.value

    async def put_setting(self, key: str, value: Any) -> None:
        """Record the value the owner just set."""
        setting = await self.session.get(CatalogSetting, key)
        if setting is None:
            self.session.add(CatalogSetting(key=key, value=value))
        else:
            setting.value = value
        await self.session.flush()

    # --- Corrections a person made ----------------------------------------

    async def get_correction(self, correction_id: int) -> Correction | None:
        """Return one correction by id, whatever its state."""
        return await self.session.get(Correction, correction_id)

    async def correction_in_force(
        self, entity_type: str, entity_id: str, field: str
    ) -> Correction | None:
        """The correction that currently stands on a field, if there is one.

        `ACTIVE` and `CONFLICTED` both count: a conflict does not undo the
        correction, it flags it (RF-28). Only `REVERTED` stops standing.
        """
        result = await self.session.execute(
            select(Correction).where(
                Correction.entity_type == entity_type,
                Correction.entity_id == entity_id,
                Correction.field == field,
                Correction.status != CorrectionStatus.REVERTED,
            )
        )
        return result.scalar_one_or_none()

    async def corrections_in_force(self, entity_ids: Sequence[str]) -> list[Correction]:
        """Every correction standing on this set of entities.

        One query for a whole page of the prices screen rather than one per
        row: RF-26 marks every corrected value, so the listing would otherwise
        ask the same question two hundred times.
        """
        if not entity_ids:
            return []
        result = await self.session.execute(
            select(Correction).where(
                Correction.entity_id.in_(list(entity_ids)),
                Correction.status != CorrectionStatus.REVERTED,
            )
        )
        return list(result.scalars().all())

    async def add_correction(self, correction: Correction) -> Correction:
        """Store a correction and return it with its identifier."""
        self.session.add(correction)
        await self.session.flush()
        await self.session.refresh(correction)
        return correction

    # --- The rubros and their equivalences (008) -------------------------

    async def add_category(self, name: str) -> Category:
        """Create a rubro."""
        category = Category(name=name)
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def get_category(self, category_id: int) -> Category | None:
        """Return a rubro by id, or None."""
        return await self.session.get(Category, category_id)

    async def category_named(self, name: str) -> Category | None:
        """Return the rubro with this exact name, or None.

        Compared case-insensitively: the uniqueness in the database is exact,
        and two rubros that differ only in case are the loading mistake the
        service refuses before the constraint has to.
        """
        result = await self.session.execute(
            select(Category).where(func.lower(Category.name) == name.strip().lower())
        )
        return result.scalars().first()

    async def list_categories(self) -> list[Category]:
        """Every rubro, by name."""
        result = await self.session.execute(select(Category).order_by(Category.name))
        return list(result.scalars().all())

    async def delete_category(self, category: Category) -> None:
        """Remove a rubro. The service checks first that nothing points at it."""
        await self.session.delete(category)
        await self.session.flush()

    async def products_per_category(self) -> dict[int | None, int]:
        """How many products each rubro has, «sin rubro» included as `None`.

        The null key is not a special case handled later: it is the group RF-09
        asks for, and it comes out of the same `GROUP BY` as the rest.
        """
        result = await self.session.execute(
            select(Product.category_id, func.count())
            .where(Product.status == ProductStatus.ACTIVE)
            .group_by(Product.category_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def record_order_spend(self, lines: list[tuple[int, str | None, Decimal]]) -> None:
        """Write what a batch of purchase-order lines spent, idempotently.

        One row per staging line: reading the same order twice has to leave the
        same total. `ON CONFLICT` over the staging row updates it in place, so a
        correction to a line that was already read is reflected rather than
        added on top.
        """
        if not lines:
            return
        values = [
            {"staging_row_id": staging_row_id, "product_code": product_code, "amount": amount}
            for staging_row_id, product_code, amount in lines
        ]
        statement = insert(OrderSpend).values(values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[OrderSpend.staging_row_id],
                set_={
                    "product_code": statement.excluded.product_code,
                    "amount": statement.excluded.amount,
                },
            )
        )
        await self.session.flush()

    async def spend_by_category(self) -> tuple[dict[int, Decimal], Decimal, Decimal]:
        """What was spent on each rubro, plus «sin rubro» and the total (P7).

        The rubro of each line comes from joining its `product_code` against this
        module's own `product`: a line whose product has no rubro —or whose code
        matches no product at all— lands in the null group, which is the spend
        «sin rubro» the client sees as «pedazos sueltos». Nothing is estimated:
        every amount is one the portal printed on an order.
        """
        result = await self.session.execute(
            select(Product.category_id, func.sum(OrderSpend.amount))
            .select_from(OrderSpend)
            .outerjoin(Product, Product.code == OrderSpend.product_code)
            .group_by(Product.category_id)
        )
        per_category: dict[int, Decimal] = {}
        unclassified = Decimal(0)
        total = Decimal(0)
        for category_id, amount in result.all():
            spent = Decimal(amount or 0)
            total += spent
            if category_id is None:
                unclassified += spent
            else:
                per_category[int(category_id)] = spent
        return per_category, unclassified, total

    async def record_sale_revenue(
        self, lines: list[tuple[int, str | None, Decimal, date | None]]
    ) -> None:
        """Write what a batch of sales brought in, idempotently.

        El gemelo de `record_order_spend`: una fila por registro de `staging`,
        y `ON CONFLICT` sobre esa fila para que volver a leer el mismo día
        actualice en lugar de sumar encima.
        """
        if not lines:
            return
        values = [
            {
                "staging_row_id": staging_row_id,
                "product_code": product_code,
                "amount": amount,
                "sold_on": sold_on,
            }
            for staging_row_id, product_code, amount, sold_on in lines
        ]
        statement = insert(SaleRevenue).values(values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[SaleRevenue.staging_row_id],
                set_={
                    "product_code": statement.excluded.product_code,
                    "amount": statement.excluded.amount,
                    "sold_on": statement.excluded.sold_on,
                },
            )
        )
        await self.session.flush()

    async def drop_sale_revenue(self, staging_row_ids: list[int]) -> None:
        """Sacar de lo vendido las ventas que dejaron de contar."""
        if not staging_row_ids:
            return
        await self.session.execute(
            delete(SaleRevenue).where(SaleRevenue.staging_row_id.in_(staging_row_ids))
        )
        await self.session.flush()

    async def revenue_by_category(
        self, since: date | None = None, until: date | None = None
    ) -> tuple[dict[int, Decimal], Decimal, Decimal]:
        """What each rubro sold, plus «sin rubro» and the total.

        La misma consulta que `spend_by_category` sobre la otra tabla, y con una
        ventana: una venta tiene su día y mirar el mes que se está cerrando es
        la pregunta que se hace con esto. El gasto por rubro no la tiene porque
        una orden de compra no publica el suyo.
        """
        statement = (
            select(Product.category_id, func.sum(SaleRevenue.amount))
            .select_from(SaleRevenue)
            .outerjoin(Product, Product.code == SaleRevenue.product_code)
            .group_by(Product.category_id)
        )
        if since is not None:
            statement = statement.where(SaleRevenue.sold_on >= since)
        if until is not None:
            statement = statement.where(SaleRevenue.sold_on <= until)
        result = await self.session.execute(statement)
        per_category: dict[int, Decimal] = {}
        unclassified = Decimal(0)
        total = Decimal(0)
        for category_id, amount in result.all():
            sold = Decimal(amount or 0)
            total += sold
            if category_id is None:
                unclassified += sold
            else:
                per_category[int(category_id)] = sold
        return per_category, unclassified, total

    async def aliases(self) -> list[CategoryAlias]:
        """Every equivalence in force, newest last."""
        result = await self.session.execute(select(CategoryAlias).order_by(CategoryAlias.id))
        return list(result.scalars().all())

    async def alias_for(self, text_normalized: str) -> CategoryAlias | None:
        """The equivalence that resolves this written form, or None."""
        result = await self.session.execute(
            select(CategoryAlias).where(CategoryAlias.text_normalized == text_normalized)
        )
        return result.scalars().first()

    async def alias_by_rule(self, rule_id: int) -> CategoryAlias | None:
        """The equivalence a rule projects, or None."""
        result = await self.session.execute(
            select(CategoryAlias).where(CategoryAlias.rule_id == rule_id)
        )
        return result.scalars().first()

    async def put_alias(
        self,
        *,
        text_normalized: str,
        text_original: str,
        category_id: int,
        rule_id: int | None,
        source: AliasSource = AliasSource.LEARNED,
    ) -> CategoryAlias:
        """Record (or re-point) an equivalence in the projection.

        Only the handlers call this: the decision belongs to `triage`, and this
        table is the copy this module reads while it classifies a batch.
        """
        alias = await self.alias_for(text_normalized)
        if alias is None:
            alias = CategoryAlias(
                text_normalized=text_normalized,
                text_original=text_original,
                category_id=category_id,
                rule_id=rule_id,
                source=source,
            )
            self.session.add(alias)
        else:
            alias.category_id = category_id
            alias.rule_id = rule_id
            alias.text_original = text_original
        await self.session.flush()
        return alias

    async def drop_alias_by_rule(self, rule_id: int) -> None:
        """Take an equivalence out of the projection: its rule was revoked."""
        await self.session.execute(delete(CategoryAlias).where(CategoryAlias.rule_id == rule_id))
        await self.session.flush()

    async def unclassified(self, *, skip: int = 0, limit: int = 50) -> list[Product]:
        """The products with no rubro, oldest first: the queue somebody empties."""
        result = await self.session.execute(
            select(Product)
            .where(Product.category_id.is_(None), Product.status == ProductStatus.ACTIVE)
            .order_by(Product.id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_unclassified(self) -> int:
        """How many products are «sin rubro» (RF-11)."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.category_id.is_(None), Product.status == ProductStatus.ACTIVE)
        )
        return int(result.scalar_one())

    async def unclassified_written_forms(self) -> dict[str, int]:
        """The written forms the products with no rubro came with, and how many.

        Grouped by the text as it arrived, not by its normalized key: the
        service holds the only definition of what «the same written form»
        means (`collapse_written_form`), and a second one written in SQL is a
        second definition that drifts (RF-26).
        """
        result = await self.session.execute(
            select(Product.category_raw, func.count())
            .where(
                Product.category_id.is_(None),
                Product.status == ProductStatus.ACTIVE,
                Product.category_raw.is_not(None),
                Product.category_raw != "",
            )
            .group_by(Product.category_raw)
        )
        return {str(row[0]): int(row[1]) for row in result.all()}

    async def rubro_of_subcategory(self) -> dict[str, set[int]]:
        """Which rubros each subcategory resolves to, among what is classified.

        The proposal is derived from this and never stored: with no column to
        write it in, there is no "proposed but unconfirmed" state a product
        could sit in while counting as classified (RF-16).
        """
        result = await self.session.execute(
            select(Product.subcategory_raw, Product.category_id)
            .where(Product.subcategory_raw.is_not(None), Product.category_id.is_not(None))
            .group_by(Product.subcategory_raw, Product.category_id)
        )
        found: dict[str, set[int]] = {}
        for subcategory, category_id in result.all():
            found.setdefault(str(subcategory), set()).add(int(category_id))
        return found

    async def products_classified_by(self, rule_id: int) -> list[Product]:
        """Exactly what one equivalence classified, and nothing else.

        A product somebody classified by hand has this column null, does not
        depend on any equivalence, and is neither re-pointed nor sent back.
        """
        result = await self.session.execute(
            select(Product).where(Product.classified_by_rule_id == rule_id)
        )
        return list(result.scalars().all())

    async def add_stock_point(
        self, *, product_id: int, quantity: int, observed_on: date, batch_id: int | None
    ) -> None:
        """Record the stock of a product for one day, once.

        Re-running the same day's list leaves the day as it was: the conflict
        is decided by the unique key, not by a check that could race with it.
        """
        await self.session.execute(
            insert(StockPoint)
            .values(
                product_id=product_id,
                quantity=quantity,
                observed_on=observed_on,
                batch_id=batch_id,
            )
            .on_conflict_do_update(
                constraint="uq_stock_point_product_day",
                set_={"quantity": quantity, "batch_id": batch_id},
            )
        )

    # --- The cuts the dashboard reads (009) ------------------------------

    async def price_curve(
        self, *, since: date | None, until: date | None
    ) -> list[tuple[date, Decimal, int]]:
        """How the prices the supplier publishes moved, month by month (RF-42).

        The average of the points of the history, which is what the supplier
        actually reported: a curve built from the price in force today would
        redraw the past every time a price changes.
        """
        month = func.date_trunc("month", PricePoint.changed_at)
        statement = select(month, func.avg(PricePoint.price), func.count())
        if since is not None:
            statement = statement.where(PricePoint.changed_at >= since)
        if until is not None:
            statement = statement.where(PricePoint.changed_at <= until)
        result = await self.session.execute(statement.group_by(month).order_by(month))
        return [(row[0].date(), Decimal(row[1] or 0), int(row[2])) for row in result.all()]

    async def stock_at(self, moment: date, *, latest: bool) -> dict[int, int]:
        """The stock of every product on the nearest day up to (or from) a date.

        The photograph closest to the edge of the window, not the one exactly on
        it: the list is published on the days it is published, and demanding an
        exact date would leave the cut empty whenever the window starts on a
        Sunday.
        """
        ordering = StockPoint.observed_on.desc() if latest else StockPoint.observed_on.asc()
        comparison = (
            StockPoint.observed_on <= moment if latest else StockPoint.observed_on >= moment
        )
        result = await self.session.execute(
            select(StockPoint.product_id, StockPoint.quantity, StockPoint.observed_on)
            .where(comparison)
            .order_by(StockPoint.product_id, ordering)
        )
        found: dict[int, int] = {}
        for product_id, quantity, _ in result.all():
            found.setdefault(int(product_id), int(quantity))
        return found

    async def products_without_a_price_in(self, since: date | None, until: date | None) -> int:
        """Active products with no published price inside the window (RF-46 of 009).

        They are what the price curve leaves out: the average of a month is the
        average of the points there are, and a product the supplier did not
        price in the whole window contributes nothing to any of them. Saying how
        many is the difference between a curve and a curve you can trust.
        """
        priced = select(PricePoint.product_id)
        if since is not None:
            priced = priced.where(PricePoint.changed_at >= since)
        if until is not None:
            priced = priced.where(PricePoint.changed_at <= until)
        result = await self.session.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.status == ProductStatus.ACTIVE, Product.id.not_in(priced))
        )
        return int(result.scalar_one())

    async def products_first_seen_between(
        self, since: date | None, until: date | None
    ) -> list[Product]:
        """The products the catalog started to know inside a window (RF-45)."""
        statement = select(Product)
        if since is not None:
            statement = statement.where(Product.first_seen_at >= since)
        if until is not None:
            statement = statement.where(Product.first_seen_at <= until)
        result = await self.session.execute(statement.order_by(Product.first_seen_at))
        return list(result.scalars().all())
