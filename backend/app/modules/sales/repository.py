"""Data access for the sales module. Private to this module."""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales.models import Sale, SalesProduct, SalesSetting, SaleState


class SalesRepository:
    """Reads and writes the sales records and the two projections they need."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sale(self, sale_id: int) -> Sale | None:
        """Return a sales record by id, or None."""
        return await self.session.get(Sale, sale_id)

    async def add(self, sale: Sale) -> Sale:
        """Store a record and give it its id."""
        self.session.add(sale)
        await self.session.flush()
        return sale

    async def with_code_key(self, code_key: str) -> list[Sale]:
        """Every record that is the same sale as this one, by its code."""
        result = await self.session.execute(
            select(Sale).where(Sale.code_key == code_key).order_by(Sale.id)
        )
        return list(result.scalars().all())

    async def list_sales(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        state: SaleState | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[Sale]:
        """A page of records, newest first."""
        statement = self._filtered(select(Sale), state, since, until)
        result = await self.session.execute(
            statement.order_by(Sale.sold_on.desc().nullslast(), Sale.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_sales(
        self,
        *,
        state: SaleState | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> int:
        """How many records match the same filters as the listing."""
        result = await self.session.execute(
            self._filtered(select(func.count()).select_from(Sale), state, since, until)
        )
        return int(result.scalar_one())

    @staticmethod
    def _filtered(
        statement: Select[Any], state: SaleState | None, since: date | None, until: date | None
    ) -> Select[Any]:
        """The filters the listing, the counts and the indicators share."""
        if state is not None:
            statement = statement.where(Sale.state == state)
        if since is not None:
            statement = statement.where(Sale.sold_on >= since)
        if until is not None:
            statement = statement.where(Sale.sold_on <= until)
        return statement

    async def monthly_totals(
        self, *, since: date | None, until: date | None
    ) -> list[tuple[date, Decimal, int]]:
        """What was invoiced per month, from the records that count (RF-03).

        Only `COUNTED`: a record that is held or that was found to duplicate
        another never reaches an indicator, and that is RF-04 and RF-15.
        """
        month = func.date_trunc("month", Sale.sold_on)
        statement = self._filtered(
            select(month, func.sum(Sale.total), func.count()), SaleState.COUNTED, since, until
        )
        result = await self.session.execute(statement.group_by(month).order_by(month))
        return [(row[0].date(), Decimal(row[1] or 0), int(row[2])) for row in result.all()]

    async def totals(self, *, since: date | None, until: date | None) -> tuple[Decimal, int]:
        """What was invoiced in a window and over how many records (RF-06, RF-07)."""
        result = await self.session.execute(
            self._filtered(
                select(func.coalesce(func.sum(Sale.total), 0), func.count()),
                SaleState.COUNTED,
                since,
                until,
            )
        )
        row = result.one()
        return Decimal(row[0]), int(row[1])

    async def has_estimates(self, *, since: date | None, until: date | None) -> bool:
        """Whether any record behind an indicator carries an estimated value (RF-40)."""
        result = await self.session.execute(
            self._filtered(select(Sale.id), SaleState.COUNTED, since, until)
            .where(Sale.is_estimated.is_(True))
            .limit(1)
        )
        return result.scalars().first() is not None

    async def average_total_for(self, product_code: str) -> Decimal | None:
        """What is usual for this product, from the records that count (RF-21).

        Derived from what is already counted rather than from a stored figure:
        a typical amount that has to be maintained is a second truth about the
        same sales, and it goes stale the moment one is corrected.
        """
        result = await self.session.execute(
            select(func.avg(Sale.total)).where(
                Sale.product_code == product_code,
                Sale.state == SaleState.COUNTED,
                Sale.total.is_not(None),
            )
        )
        value = result.scalar_one_or_none()
        return None if value is None else Decimal(value)

    async def held_groups(self) -> dict[str, list[Sale]]:
        """The records waiting for a person, grouped by the sale they are (RF-14)."""
        result = await self.session.execute(
            select(Sale).where(Sale.state == SaleState.HELD).order_by(Sale.code_key, Sale.id)
        )
        grouped: dict[str, list[Sale]] = {}
        for sale in result.scalars().all():
            grouped.setdefault(sale.code_key, []).append(sale)
        return grouped

    # --- The projections ---------------------------------------------------

    async def known_products(self) -> set[str]:
        """Every product code the catalog knows, as this module heard it."""
        result = await self.session.execute(select(SalesProduct.product_code))
        return {str(code) for code in result.scalars().all()}

    async def put_product(self, product_code: str) -> None:
        """Record a product the catalog started to know."""
        if await self.session.get(SalesProduct, product_code) is None:
            self.session.add(SalesProduct(product_code=product_code))
            await self.session.flush()

    async def setting(self, key: str) -> Any | None:
        """The value of a parameter as this module last heard it, or None."""
        row = await self.session.get(SalesSetting, key)
        return None if row is None else row.value

    async def put_setting(self, key: str, value: Any) -> None:
        """Record the value of a parameter the owner changed."""
        row = await self.session.get(SalesSetting, key)
        if row is None:
            self.session.add(SalesSetting(key=key, value=value))
        else:
            row.value = value
        await self.session.flush()
