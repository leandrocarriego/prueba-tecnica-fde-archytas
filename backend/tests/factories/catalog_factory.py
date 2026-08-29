"""Catalog factories: a product, its price in force and its history.

Written through the models rather than through `CatalogService`, so a test can
build the exact state it needs — a product whose history stops three months ago,
a price that rose exactly to the threshold — without going through the pipeline
it is about to exercise.
"""

import itertools
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import PricePoint, PriceSource, Product, ProductPrice

# Codes are unique per process: `core.product.code` is unique, and a test that
# does not care about the code should never collide with another.
_sequence = itertools.count(1)


class ProductFactory:
    """Builds products, with or without a price in force."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        code: str | None = None,
        description: str | None = None,
        price: Decimal | int | None = None,
        effective_at: datetime | None = None,
        previous_price: Decimal | int | None = None,
        is_highlighted: bool = False,
        is_stale: bool = False,
        **kwargs: Any,
    ) -> Product:
        """Create a product. `price=None` leaves it with no price in force."""
        index = next(_sequence)
        product = Product(
            code=code or f"TEST-{index:05d}",
            description=description or f"Producto de prueba {index}",
            **kwargs,
        )
        session.add(product)
        await session.flush()

        if price is not None:
            session.add(
                ProductPrice(
                    product_id=product.id,
                    price=Decimal(str(price)),
                    currency="ARS",
                    effective_at=effective_at or datetime.now(UTC),
                    previous_price=None if previous_price is None else Decimal(str(previous_price)),
                    is_highlighted=is_highlighted,
                    is_stale=is_stale,
                )
            )
            await session.flush()

        await session.refresh(product)
        return product

    @staticmethod
    async def add_point(
        session: AsyncSession,
        product: Product,
        *,
        price: Decimal | int,
        changed_at: datetime,
        source: PriceSource = PriceSource.SYSTEM,
        batch_id: int | None = None,
    ) -> PricePoint:
        """Add one point to a product's history."""
        point = PricePoint(
            product_id=product.id,
            price=Decimal(str(price)),
            changed_at=changed_at,
            source=source,
            batch_id=batch_id,
        )
        session.add(point)
        await session.flush()
        return point
