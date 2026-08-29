"""Data access for the catalog module. Private to this module."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import (
    CatalogSetting,
    PricePoint,
    PriceSource,
    Product,
    ProductPrice,
    ProductStatus,
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
    ) -> list[tuple[Product, ProductPrice | None]]:
        """Return a page of products with their price in force."""
        statement = self._prices_query(query, highlighted)
        result = await self.session.execute(
            statement.order_by(Product.code).offset(skip).limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def count_prices(self, *, query: str | None = None, highlighted: bool = False) -> int:
        """How many products match the same filters as `list_prices`."""
        subquery = self._prices_query(query, highlighted).subquery()
        result = await self.session.execute(select(func.count()).select_from(subquery))
        return int(result.scalar_one())

    @staticmethod
    def _prices_query(query: str | None, highlighted: bool) -> Select[Any]:
        """The one statement behind the listing and its count."""
        statement = select(Product, ProductPrice).outerjoin(
            ProductPrice, ProductPrice.product_id == Product.id
        )
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(Product.code.ilike(pattern), Product.description.ilike(pattern))
            )
        if highlighted:
            statement = statement.where(ProductPrice.is_highlighted.is_(True))
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
