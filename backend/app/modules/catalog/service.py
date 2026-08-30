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

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.catalog.models import (
    Correction,
    CorrectionStatus,
    PriceSource,
    Product,
    ProductPrice,
    ProductStatus,
)
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import (
    CorrectionMark,
    CorrectionRead,
    PriceHistoryRead,
    PriceList,
    PricePointRead,
    PriceRead,
)
from app.shared.corrections import CorrectionReason
from app.shared.errors import NotFoundError, ValidationError
from app.shared.events import (
    AuditAction,
    CorrectionConflicted,
    KnownProductsMissing,
    ManualChangeRecorded,
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
from app.shared.sections import BusinessSection

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

# --- Correcting a value by hand -------------------------------------------
#
# What this module calls its own data when it talks about it to the rest of the
# platform. Strings, in this module's vocabulary: nobody else has to resolve
# them, they only have to be stable.
PRODUCT_ENTITY = "catalog.product"
PRICE_ENTITY = "catalog.product_price"

PRICE_FIELD = "price"
CURRENCY_FIELD = "currency"
DESCRIPTION_FIELD = "description"

# Which fields a person may correct, and where each one lives. RF-23 asks for
# *any* field of a datum brought from the portal, not only the amounts — which
# is why the description is here beside the price.
#
# `code` is deliberately absent. It is the supplier's own identifier, the key
# the daily list is matched by: "correcting" it would silently detach the
# product from every list that follows, which is not a correction but a
# different product.
CORRECTABLE_FIELDS: dict[str, tuple[str, bool]] = {
    DESCRIPTION_FIELD: (PRODUCT_ENTITY, False),
    PRICE_FIELD: (PRICE_ENTITY, True),
    CURRENCY_FIELD: (PRICE_ENTITY, False),
}

# Prices and the product catalog belong to sales in the map of roles, so that
# is the section every correction here is filed under. It is what decides who
# sees it in the history (RF-19).
CATALOG_SECTION = BusinessSection.SALES

NO_PRICE_YET = "El producto todavía no tiene un precio para corregir"
# What the person who ran the action reads when the product is not there
# (RF-22). In Spanish like every other refusal of this module: the envelope in
# `main.py` serves this string straight to the screen (Artículo VIII).
NO_SUCH_PRODUCT = "No encontramos ese producto"


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
                source=PriceSource.PORTAL,
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
        # Two questions, and only one of them is open. The **description** is
        # always the portal's: it is read from the row the case carried, and a
        # person resolving it decides whether to incorporate the product, not
        # what it is called. So the product keeps a portal value underneath,
        # correcting it opens a correction (RF-25) and that correction can be
        # undone (RF-30, RF-31).
        #
        # The **amount** is the one that may be nobody's but the person's:
        # `triage` prefers the price they wrote over the one the row carried,
        # and RF-33 says a value nobody reported offers no way back to the
        # portal's. A saved rule cannot type anything — it replays the row —
        # so what it incorporates stays the portal's word.
        #
        # It errs on the safe side when a person accepts the row without
        # changing the price: the platform refuses a reversal it could have
        # offered, instead of inventing a portal value that was never reported
        # (Artículo III). Tomorrow's list re-prices the row and settles it.
        price_source = PriceSource.PORTAL if rule_id is not None else PriceSource.SYSTEM
        product = await self.catalog.add_product(
            code=product_code,
            description=description,
            seen_at=now,
            registered_by_rule_id=rule_id,
        )
        product.source = PriceSource.PORTAL
        await self.session.flush()
        if price is not None:
            await self._register_price(
                product=product,
                price=price,
                currency=currency,
                moment=now,
                threshold=await self.highlight_threshold(),
                batch_id=None,
                source=price_source,
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
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_code": product_code})
        await self._register_price(
            product=product,
            price=price,
            currency=currency,
            moment=datetime.now(UTC),
            threshold=await self.highlight_threshold(),
            batch_id=None,
            # The number a person wrote while resolving an unreadable row:
            # `triage` takes it from their decision, never from the portal.
            source=PriceSource.SYSTEM,
        )

    async def discontinue(self, product_id: int) -> None:
        """Give a product up for discontinued (RF-31)."""
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_id": product_id})
        product.status = ProductStatus.DISCONTINUED
        await self.session.flush()
        logger.info("Product discontinued", extra={"product_id": product_id})

    async def keep_active(self, product_id: int) -> None:
        """Keep a product in force even though it stopped coming in the list (RF-31)."""
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_id": product_id})
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

    # --- Correcting a value by hand ---------------------------------------

    async def apply_correction(
        self,
        *,
        product_id: int,
        field: str,
        value: Any,
        reason_code: str,
        reason_detail: str | None,
        actor_user_id: int,
    ) -> CorrectionRead:
        """Put a person's value on top of a product's, without losing the old one.

        Two paths, and the difference is where the datum came from:

        * **It came from the portal.** A `Correction` row keeps what the portal
          said (RF-25) so the value can be given back later (RF-31), the screen
          can show both side by side (RF-27), and a later list that contradicts
          it is a conflict rather than an overwrite (RF-28).
        * **A person loaded it.** There is no portal value to keep, so there is
          no correction row and nothing to give back (RF-33). The change is
          still recorded with its reason, because RF-11 asks for one on *any*
          manual change to a datum that already existed.

        Either way the log line is written in this transaction: the handler of
        `ManualChangeRecorded` runs here, and if it fails so does this.
        """
        entity_type, numeric = self._correctable(field)
        reason = self._reason(reason_code)
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_id": product_id})

        target: Product | ProductPrice
        if entity_type == PRODUCT_ENTITY:
            target = product
        else:
            price = await self.catalog.get_price(product.id)
            if price is None:
                raise NotFoundError(NO_PRICE_YET, details={"product_id": product_id})
            target = price

        entity_id = str(product.id)
        previous = getattr(target, field)
        corrected = (
            self._as_number(value, field)
            if numeric
            else self._as_text(value, field, limit=self._length_of(target, field))
        )

        correction = await self._store_correction(
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            previous=previous,
            corrected=corrected,
            reason=reason,
            reason_detail=reason_detail,
            actor_user_id=actor_user_id,
            from_portal=self._came_from_the_portal(target),
        )

        setattr(target, field, corrected)
        await self.session.flush()

        await events.publish(
            ManualChangeRecorded(
                entity_type=entity_type,
                entity_id=entity_id,
                field=field,
                # A datum the portal never brought is *updated*, not corrected:
                # there is nothing it is being corrected against.
                action=AuditAction.CORRECTED if correction else AuditAction.UPDATED,
                actor_user_id=actor_user_id,
                section=CATALOG_SECTION,
                old_value=self._jsonable(previous),
                new_value=self._jsonable(corrected),
                reason_code=reason.value,
                reason_detail=reason_detail,
            ),
            self.session,
        )
        logger.info(
            "Value corrected by hand",
            extra={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "field": field,
                "actor_user_id": actor_user_id,
                "correction_id": None if correction is None else correction.id,
            },
        )
        return CorrectionRead(
            correction_id=None if correction is None else correction.id,
            product_id=product.id,
            entity_type=entity_type,
            field=field,
            portal_value=None if correction is None else correction.portal_value,
            value=self._jsonable(corrected),
            status=None if correction is None else correction.status,
        )

    async def revert_correction(self, correction_id: int, *, actor_user_id: int) -> CorrectionRead:
        """Give a datum back the value the portal reported (RF-30, RF-31).

        **The portal's value, not the previous one.** After two corrections in a
        row those are different numbers, and `portal_value` is the one that was
        never rewritten — which is the whole reason the column exists.

        The row is marked, never deleted (RF-32): who undid it and when are part
        of the record, and a history entry pointing at a row somebody removed
        would explain nothing.
        """
        correction = await self.catalog.get_correction(correction_id)
        if correction is None or correction.status is CorrectionStatus.REVERTED:
            # Also the answer for a datum the portal never brought: it has no
            # correction, so there is nothing to undo (RF-33).
            raise NotFoundError(
                "No hay una corrección vigente para deshacer",
                details={"correction_id": correction_id},
            )

        entity_type, numeric = self._correctable(correction.field)
        product = await self.catalog.get_product(int(correction.entity_id))
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_id": correction.entity_id})

        target: Product | ProductPrice
        if entity_type == PRODUCT_ENTITY:
            target = product
        else:
            price = await self.catalog.get_price(product.id)
            if price is None:
                raise NotFoundError(NO_PRICE_YET, details={"product_id": product.id})
            target = price

        restored = (
            self._as_number(correction.portal_value, correction.field)
            if numeric
            else str(correction.portal_value)
        )
        setattr(target, correction.field, restored)

        now = datetime.now(UTC)
        correction.status = CorrectionStatus.REVERTED
        correction.reverted_by_user_id = actor_user_id
        correction.reverted_at = now
        await self.session.flush()

        await events.publish(
            ManualChangeRecorded(
                entity_type=correction.entity_type,
                entity_id=correction.entity_id,
                field=correction.field,
                action=AuditAction.CORRECTION_REVERTED,
                actor_user_id=actor_user_id,
                section=CATALOG_SECTION,
                old_value=correction.corrected_value,
                new_value=correction.portal_value,
                # No reason is asked for: undoing a correction is its own named
                # action in the log, not a new opinion about the value.
            ),
            self.session,
        )
        logger.info(
            "Correction reverted",
            extra={"correction_id": correction.id, "actor_user_id": actor_user_id},
        )
        return CorrectionRead(
            correction_id=correction.id,
            product_id=product.id,
            entity_type=correction.entity_type,
            field=correction.field,
            portal_value=correction.portal_value,
            value=correction.portal_value,
            status=correction.status,
        )

    async def _store_correction(
        self,
        *,
        entity_type: str,
        entity_id: str,
        field: str,
        previous: Any,
        corrected: Any,
        reason: CorrectionReason,
        reason_detail: str | None,
        actor_user_id: int,
        from_portal: bool,
    ) -> Correction | None:
        """Open or refresh the correction standing on a field.

        Correcting an already corrected field **does not move `portal_value`**:
        it is what the portal said, once, and every reversal goes back to it.
        A correction made over a conflict closes the conflict — the spec says
        the case is settled where the datum lives, not in a queue somebody has
        to empty.

        `from_portal` decides whether a correction is **opened**, never whether
        one that already stands keeps up with the value. `source` says who
        wrote the row last, and it moves: somebody registering a price by hand
        does not un-report what the portal had said the day the correction was
        made (RF-25). A correction left behind while the value walks on is a
        mark that lies about what the screen shows (RF-27) and a reversal that
        gives back a value related to nothing (RF-31).
        """
        now = datetime.now(UTC)
        correction = await self.catalog.correction_in_force(entity_type, entity_id, field)
        if correction is None:
            if not from_portal:
                # Nothing the portal ever reported underneath this value: no
                # original to keep, and nothing to give back (RF-33).
                return None
            return await self.catalog.add_correction(
                Correction(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    field=field,
                    portal_value=self._jsonable(previous),
                    corrected_value=self._jsonable(corrected),
                    reason_code=reason.value,
                    reason_detail=reason_detail,
                    corrected_by_user_id=actor_user_id,
                    corrected_at=now,
                    status=CorrectionStatus.ACTIVE,
                )
            )

        correction.corrected_value = self._jsonable(corrected)
        correction.reason_code = reason.value
        correction.reason_detail = reason_detail
        correction.corrected_by_user_id = actor_user_id
        correction.corrected_at = now
        correction.status = CorrectionStatus.ACTIVE
        correction.conflict_value = None
        correction.conflict_detected_at = None
        await self.session.flush()
        return correction

    async def _corrections_on_the_price(self, product_id: int) -> dict[str, Correction]:
        """The corrections standing on a product's price row, by field.

        One query for the whole row rather than one per correctable field: a
        daily list walks this once per product it carries.
        """
        return {
            correction.field: correction
            for correction in await self.catalog.corrections_in_force([str(product_id)])
            if correction.entity_type == PRICE_ENTITY
        }

    async def _check_conflict(
        self, correction: Correction, *, incoming: Any, against: Any, moment: datetime
    ) -> None:
        """Compare what a list brings against a value a person corrected (RF-28).

        Three outcomes, and none of them touches the corrected value:

        * the portal said what `against` already says — nothing happened;
        * it said something else — the correction is flagged and the owner is
          told (RF-29);
        * it said the same something else again — already flagged, so no second
          warning and nothing rewritten.

        `against` is not the same column for every field, and that is the whole
        of it. An **amount** is measured against `portal_value`: the portal
        repeating its own number is not news. A **currency** is measured
        against what the person left, because the portal never reports a
        currency on its own — it reports "1500 pesos", and the unit rides along
        with every amount it publishes. Measured against `portal_value` a
        corrected currency could never be contradicted, since a supplier goes
        on quoting in the currency it always did: every later list would
        quietly disagree with the person and the owner would never hear of it.
        """
        if self._same(correction.field, incoming, against):
            return
        if (
            correction.status is CorrectionStatus.CONFLICTED
            and correction.conflict_value is not None
            and self._same(correction.field, correction.conflict_value, incoming)
        ):
            return

        correction.status = CorrectionStatus.CONFLICTED
        correction.conflict_value = self._jsonable(incoming)
        correction.conflict_detected_at = moment
        await self.session.flush()
        await events.publish(
            CorrectionConflicted(
                entity_type=correction.entity_type,
                entity_id=correction.entity_id,
                field=correction.field,
                correction_id=correction.id,
                original_value=correction.portal_value,
                corrected_value=correction.corrected_value,
                incoming_value=self._jsonable(incoming),
            ),
            self.session,
        )
        logger.warning(
            "The portal contradicted a correction",
            extra={
                "correction_id": correction.id,
                "entity_id": correction.entity_id,
                "field": correction.field,
            },
        )

    @staticmethod
    def _correctable(field: str) -> tuple[str, bool]:
        """Where a field lives and whether it holds a number, or refuse it."""
        target = CORRECTABLE_FIELDS.get(field)
        if target is None:
            raise ValidationError(
                f"«{field}» no es un campo que se pueda corregir.",
                details={"field": field, "correctable": sorted(CORRECTABLE_FIELDS)},
            )
        return target

    @staticmethod
    def _reason(reason_code: str) -> CorrectionReason:
        """The reason somebody picked, or refuse the correction (RF-11)."""
        try:
            return CorrectionReason(reason_code)
        except ValueError as error:
            raise ValidationError(
                "Elegí un motivo de la lista para poder corregir.",
                details={"reason_code": reason_code},
            ) from error

    @staticmethod
    def _as_number(value: Any, field: str) -> Decimal:
        """Read a value as the number its field holds."""
        try:
            return Decimal(str(value))
        except (InvalidOperation, ArithmeticError, ValueError) as error:
            raise ValidationError(
                f"«{field}» tiene que ser un número.", details={"field": field}
            ) from error

    @staticmethod
    def _as_text(value: Any, field: str, *, limit: int | None = None) -> str:
        """Read a value as the text its field holds, or refuse it.

        The type is demanded, not coerced, because `str()` accepts everything
        and writes it in the wrong language: `None` becomes «None», `True`
        becomes «True», a list becomes its Python repr. Every one of those is
        an English word or a piece of code landing in a field the client reads
        in Spanish (Artículo VIII), and each of them sails past an emptiness
        test. RF-23 lets a person correct a text the portal brought; it does
        not let them erase it, nor replace it with whatever their JSON carried.

        `limit` is the column's own length. A text longer than the field is a
        refusal the person can read, not a database error escaping the service
        as a 500 (ERR-06).
        """
        if not isinstance(value, str):
            raise ValidationError(f"«{field}» tiene que ser texto.", details={"field": field})
        text = value.strip()
        if not text:
            raise ValidationError(
                "El valor corregido no puede quedar vacío.", details={"field": field}
            )
        if limit is not None and len(text) > limit:
            raise ValidationError(
                f"«{field}» no puede superar los {limit} caracteres.",
                details={"field": field, "max_length": limit},
            )
        return text

    @staticmethod
    def _length_of(target: Product | ProductPrice, field: str) -> int | None:
        """How long the column behind a field is, when it says so.

        Asked of the table instead of copied beside it: two numbers that have
        to agree are one number too many, and the one that decides is the one
        the database enforces.
        """
        length = getattr(type(target).__table__.c[field].type, "length", None)
        return length if isinstance(length, int) else None

    @classmethod
    def _same(cls, field: str, left: Any, right: Any) -> bool:
        """Whether two values of a field are the same value.

        Amounts are compared as numbers and not as text: `portal_value` keeps a
        price as «1000.0000» and a list brings `Decimal("1000")`, which is one
        number written twice.
        """
        _, numeric = cls._correctable(field)
        if numeric:
            return cls._as_number(left, field) == cls._as_number(right, field)
        return str(left) == str(right)

    @staticmethod
    def _jsonable(value: Any) -> Any:
        """The shape a value takes inside JSONB.

        A `Decimal` goes in as text so it comes back with its cents instead of
        as a float that lost them.
        """
        return str(value) if isinstance(value, Decimal) else value

    @staticmethod
    def _came_from_the_portal(target: Product | ProductPrice) -> bool:
        """Whether there is a value the portal reported underneath this one.

        The question is asked of **the row that holds the value being
        corrected**, not of the product: a product a person typed into the
        review queue gets re-priced by the next daily list, and from that
        morning on the amount is the portal's even though the description
        beside it never was. RF-33 talks about a datum, and so does this flag.

        `registered_by_rule_id` used to answer this and could not: it says
        which learned rule incorporated a product (RF-37), which is neither the
        same question nor even close — a product that arrived in an ordinary
        daily list has no rule either.
        """
        return target.source is PriceSource.PORTAL

    @staticmethod
    def _marks(corrections: list[Correction]) -> list[CorrectionMark]:
        """Turn the corrections standing on a datum into what a screen shows."""
        return [
            CorrectionMark(
                correction_id=correction.id,
                field=correction.field,
                portal_value=correction.portal_value,
                corrected_value=correction.corrected_value,
                status=correction.status,
                conflict_value=correction.conflict_value,
            )
            for correction in corrections
        ]

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
        # One query for the page rather than one per row (RF-26).
        marks: dict[str, list[Correction]] = defaultdict(list)
        for correction in await self.catalog.corrections_in_force(
            [str(product.id) for product, _ in rows]
        ):
            marks[correction.entity_id].append(correction)
        items = [
            self._price_read(product, price, previous_month.get(product.id), marks[str(product.id)])
            for product, price in rows
        ]
        return PriceList(items=items, total=total, skip=skip, limit=limit)

    async def price_history(self, product_id: int) -> PriceHistoryRead:
        """How the price of one product evolved (RF-23)."""
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_id": product_id})
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
            corrections=self._marks(await self.catalog.corrections_in_force([str(product.id)])),
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
        source: PriceSource,
    ) -> tuple[bool, bool]:
        """Write the price in force. Returns (it changed, it is highlighted).

        A price that did not change adds no point to the history (RF-22) and
        keeps the date on which it was registered: that date is what the screen
        shows next to a product that did not come in today's list (RF-08).

        `source` is who is writing — a list the portal published, or this
        platform on somebody's decision. It is stamped on the row even when the
        amount did not move, because a list repeating a number a person typed
        is still the portal reporting that number (RF-33).
        """
        product.last_seen_at = moment

        # A corrected value is not overwritten by a later list (RF-28), and
        # `price` and `currency` are guarded one by one: both are correctable
        # fields of this row (RF-23), so a correction on either has to hold.
        # The comparison is local — the corrections live in this module
        # precisely so that these lines do not have to ask anybody anything.
        standing = await self._corrections_on_the_price(product.id)
        corrected_price = standing.get(PRICE_FIELD)
        corrected_currency = standing.get(CURRENCY_FIELD)
        # Only the portal can contradict a correction. This same method writes
        # the amount a person typed while resolving an unreadable row, and
        # telling the owner that the portal contradicted a correction about a
        # value the platform itself wrote would be an alert about nobody
        # (RF-29).
        from_the_portal = source is PriceSource.PORTAL

        if from_the_portal and corrected_currency is not None:
            # The unit is checked before anything is decided about the amount,
            # because what contradicts a corrected currency is the list naming
            # another one: whether the number beside it moved has nothing to do
            # with it. A daily list repeats yesterday's price most mornings, so
            # asking this only where a new amount gets written would report the
            # contradiction on the one morning the number happened to change,
            # and stay quiet every other day (RF-28, RF-29).
            await self._check_conflict(
                corrected_currency,
                incoming=currency,
                against=corrected_currency.corrected_value,
                moment=moment,
            )

        if corrected_price is not None:
            if from_the_portal:
                await self._check_conflict(
                    corrected_price,
                    incoming=price,
                    against=corrected_price.portal_value,
                    moment=moment,
                )
            else:
                # A person's number arriving through the review queue instead
                # of through the corrections door. It is not applied — the
                # correction is what the screen shows, and moving it takes a
                # reason (RF-11) — and it is said out loud instead of dropped
                # in silence (Artículo II).
                logger.info(
                    "A manual price was held back by a standing correction",
                    extra={"product_id": product.id, "correction_id": corrected_price.id},
                )
            # A correction on the amount freezes the whole row, currency
            # included, and that is deliberate: the unit belongs to the number,
            # and pinning a new one onto an amount the portal never reported
            # would silently change what the corrected value means.
            current = await self.catalog.get_price(product.id)
            if current is not None:
                # The product did come in the list, so it is not stale — and
                # there was no comparison to make, so nothing is highlighted.
                current.is_stale = False
                current.is_highlighted = False
                await self.session.flush()
            return False, False

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
                    source=source,
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
            current.source = source
            await self.session.flush()
            return False, False

        variation = self._variation(price, current.price)
        is_highlighted = variation is not None and variation > threshold
        current.previous_price = current.price
        current.price = price
        current.effective_at = moment
        current.is_highlighted = is_highlighted
        current.is_stale = False
        current.source = source
        # A unit a person ruled out is not written, whoever is writing (RF-28).
        # What the list said about it was already recorded on the correction,
        # and the owner already heard about it, up where that check runs on
        # every list rather than only on the ones that move the number.
        if corrected_currency is None:
            current.currency = currency
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
        self,
        product: Product,
        price: ProductPrice | None,
        previous_month: Decimal | None,
        corrections: list[Correction],
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
            corrections=self._marks(corrections),
        )
