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
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.catalog.models import (
    Category,
    Correction,
    CorrectionStatus,
    PriceSource,
    Product,
    ProductPrice,
    ProductStatus,
)
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import (
    CatalogDashboard,
    CategoryAliasRead,
    CategoryList,
    CategoryRead,
    CorrectionMark,
    CorrectionRead,
    NewProductRead,
    PriceCurvePoint,
    PriceHistoryRead,
    PriceList,
    PricePointRead,
    PriceRead,
    StockCut,
    UnclassifiedList,
    UnclassifiedProduct,
)
from app.shared.corrections import CorrectionReason
from app.shared.errors import ConflictError, NotFoundError, ValidationError
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
    UnknownCategory,
    UnknownCategoryObserved,
    UnknownProduct,
    UnknownProductsObserved,
    events,
)
from app.shared.sections import BusinessSection
from app.shared.text import collapse_written_form, normalize
from app.shared.time import BUSINESS_TIME_ZONE

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
# The kind 008 adds to the same generic queue. A written form of a category
# nobody has decided about is a case, exactly like a product nobody knows.
UNKNOWN_CATEGORY = "unknown_category"

CATEGORY_ENTITY = "catalog.product_category"
CATEGORY_FIELD = "category_id"

NO_SUCH_CATEGORY = "No encontramos ese rubro"
CATEGORY_ALREADY_EXISTS = "Ya hay un rubro con ese nombre"
CATEGORY_HAS_PRODUCTS = "El rubro tiene productos asignados y por eso no se puede eliminar"

# How many unclassified products one decision reaches in a single pass. The
# catalog is a hundred products today and the whole queue fits well inside
# this; the bound is here so a decision can never turn into an unbounded scan.
MAX_RECLASSIFIED = 5000

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
        # Classifying a batch is a lookup against the table of equivalences,
        # not a call to anybody: the rules belong to `triage` and this module
        # reads its own projection of them (Artículo IV).
        equivalences = {
            alias.text_normalized: (alias.category_id, alias.rule_id)
            for alias in await self.catalog.aliases()
        }
        unresolved: dict[str, list[str]] = defaultdict(list)
        observed_on = now.astimezone(BUSINESS_TIME_ZONE).date()
        updated = unchanged = highlighted = 0
        # Every correction the list could contradict, read once. A product the
        # catalog does not know yet cannot have one, so only what came back
        # from `products_by_code` is asked about — and asking per row turned
        # the cheapest part of a run into a query per product of the catalogue.
        standing = await self._standing_corrections(product.id for product in known.values())

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

            corrections = standing.get(product.id, {})
            corrected_description = corrections.get(DESCRIPTION_FIELD)
            if corrected_description is not None and row.description.strip():
                # RF-28 is written about *a datum corrected by hand*, and the
                # description is one of the three (RF-23). It is checked here
                # and not inside `_register_price` because a run never rewrites
                # a known product's description: without this line the one
                # field the pipeline cannot overwrite would also be the one
                # that never gets flagged, and the owner would never hear that
                # the portal started calling the product something else.
                #
                # A row that carries no description at all is not the portal
                # calling the product something else, it is the portal not
                # saying — and a conflict raised over it would put the owner in
                # front of a case with nothing to decide (RF-29), which is how
                # an alert stops being read.
                await self._check_conflict(
                    corrected_description,
                    incoming=row.description,
                    against=corrected_description.portal_value,
                    moment=now,
                )

            changed, was_highlighted = await self._register_price(
                product=product,
                price=row.price,
                currency=row.currency,
                moment=now,
                threshold=threshold,
                batch_id=batch_id,
                source=PriceSource.PORTAL,
                corrections=corrections,
            )
            updated += int(changed)
            unchanged += int(not changed)
            highlighted += int(was_highlighted)

            self._classify(product, row, equivalences, unresolved)
            if row.stock is not None:
                await self.catalog.add_stock_point(
                    product_id=product.id,
                    quantity=row.stock,
                    observed_on=observed_on,
                    batch_id=batch_id,
                )

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
        if unresolved:
            # One case per written form, never one per product: a hundred rows
            # spelled the same way are one question (RF-21, RF-22 of 008).
            await events.publish(
                UnknownCategoryObserved(
                    batch_id=batch_id,
                    cases=tuple(
                        UnknownCategory(category_text=text, product_codes=tuple(codes))
                        for text, codes in sorted(unresolved.items())
                    ),
                ),
                self.session,
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
                "unresolved_categories": len(unresolved),
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
        actor_user_id: int | None = None,
        decided_at: datetime | None = None,
    ) -> None:
        """Add a product a person decided to incorporate (RF-30).

        `actor_user_id` and `decided_at` are who asked for it and when, and
        they are what turns this into a line of the log: incorporating a
        product from the review queue is the platform's one way of **loading**
        a datum by hand, and RF-09 covers loading with the same words it covers
        modifying.
        """
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
                # Empty and not looked up: a product that did not exist a line
                # ago cannot carry a correction against it.
                corrections={},
            )
        # **One decision, one line.** The line names the **product**, and its
        # description, because that is the datum a person loaded: the product
        # page links its history by `catalog.product` and the product's id
        # (RF-15), so this is where somebody asking "who put this here?" is
        # already looking. `old_value` stays empty, and truthfully — there was
        # no product to say anything about before this one. The amount
        # underneath is the row's own number as often as the person's, and
        # `source` on the price row is what says which.
        #
        # The asymmetry that leaves, written down so the next reader finds it
        # instead of rediscovering it: when the amount is the person's
        # (`price_source is PriceSource.SYSTEM`), the same act through the
        # other door — `set_price_by_code`, for a row nobody could read — does
        # leave a second line under `catalog.product_price`, and this one does
        # not. So the product page's «Historial de cambios del precio» comes
        # back empty for a product loaded here. It is deliberate: there the
        # price is the only datum that came into being, and here it arrives
        # inside the birth of the product, which is the datum the person
        # actually decided about. Two lines for one decision would say twice
        # what happened once, and the second would be filed under a screen
        # nobody reached that morning. If RF-09's «sin excepciones» is ever
        # read as covering the amount on its own, this is the line to add —
        # the fact needed to decide it is already on the row (`source`).
        await self._record_manual_load(
            entity_type=PRODUCT_ENTITY,
            entity_id=str(product.id),
            field=DESCRIPTION_FIELD,
            old_value=None,
            new_value=description,
            actor_user_id=actor_user_id,
            moment=decided_at,
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
        self,
        *,
        product_code: str,
        price: Decimal,
        currency: str = "ARS",
        actor_user_id: int | None = None,
        decided_at: datetime | None = None,
    ) -> None:
        """Register the price a person indicated for a known product (RF-29).

        The second way a datum gets loaded by hand, and so the second one that
        leaves a line behind (RF-09): the portal's row could not be read, and
        the amount in force from here on is one a person typed.
        """
        product = await self.catalog.get_by_code(product_code)
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_code": product_code})
        current = await self.catalog.get_price(product.id)
        previous = None if current is None else current.price
        # Read here and handed down, because the answer is needed twice: to
        # write the row, and to know afterwards whether the write reached it.
        standing = (await self._standing_corrections([product.id])).get(product.id, {})
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
            corrections=standing,
        )
        if PRICE_FIELD not in standing:
            # Recorded whether or not the number moved: somebody confirming the
            # amount already in force took a manual decision like any other, and
            # it is recorded like any other (RF-09) — the same answer
            # `apply_correction` gives to a correction back to the value a datum
            # already had. The one case that leaves no line is the one where
            # nothing was loaded: a standing correction holds this amount back on
            # purpose, and writing «cargó 1500» over a value the screen never
            # showed would be a line of the log that contradicts the screen it
            # explains.
            await self._record_manual_load(
                entity_type=PRICE_ENTITY,
                entity_id=str(product.id),
                field=PRICE_FIELD,
                old_value=previous,
                new_value=price,
                actor_user_id=actor_user_id,
                moment=decided_at,
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

    async def _record_manual_load(
        self,
        *,
        entity_type: str,
        entity_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        actor_user_id: int | None,
        moment: datetime | None,
    ) -> None:
        """Send a datum somebody loaded by hand to the one log of the platform (RF-09).

        `CREATED` and not `CORRECTED`: nobody is disagreeing with the portal
        here. The portal reported nothing — that is exactly why a person had to
        type it — so there is no original for the value to be measured against
        and no correction row underneath it (RF-33).

        **No reason is asked for, and that is deliberate.** RF-11 demands one
        when somebody modifies a datum *that already existed*; a load brings
        into being a datum that did not, and there is nothing for the reason to
        be about. Verified against the signed text on 2026-08-30.

        The moment is the one the decision carried and not `now()`: what the
        history has to say is when the person decided, and the two differ by
        however long the queue behind them took.
        """
        if actor_user_id is None:
            # Nothing manual happened, so there is nothing to record about who
            # did it. Inventing an author would put a name on the platform's
            # own work, which is worse than the silence.
            return
        await events.publish(
            ManualChangeRecorded(
                entity_type=entity_type,
                entity_id=entity_id,
                field=field,
                action=AuditAction.CREATED,
                actor_user_id=actor_user_id,
                section=CATALOG_SECTION,
                old_value=self._jsonable(old_value),
                new_value=self._jsonable(new_value),
                occurred_at=moment or datetime.now(UTC),
            ),
            self.session,
        )

    # --- The rubros of the catalog (008) ----------------------------------

    @staticmethod
    def _classify(
        product: Product,
        row: NormalizedPriceRow,
        equivalences: dict[str, tuple[int, int | None]],
        unresolved: dict[str, list[str]],
    ) -> None:
        """Give a product its rubro, or leave it for a person. Never guess.

        Three outcomes, and they are the whole of H4 of the spec:

        * the written form has an equivalence → the rubro of that equivalence,
          stamped with the rule that decided it (RF-02, RF-25);
        * it has none → the product stays «sin rubro» and the written form is
          collected so one case is opened for it (RF-21, RF-22);
        * the row brought no category at all → «sin rubro», and it waits in the
          queue of unclassified with the proposal derived from its subcategory
          (RF-09 to RF-12).

        What somebody decided by hand is never overwritten by an equivalence: a
        product with `classified_by_user_id` is a decision, not a match.
        """
        product.category_raw = row.category_raw
        product.subcategory_raw = row.subcategory_raw
        if row.category_raw is None or not row.category_raw.strip():
            return
        if product.classified_by_user_id is not None:
            return

        found = equivalences.get(collapse_written_form(row.category_raw))
        if found is None:
            unresolved[row.category_raw.strip()].append(product.code)
            return
        category_id, rule_id = found
        product.category_id = category_id
        product.classified_by_rule_id = rule_id

    async def list_categories(self) -> CategoryList:
        """The rubros with their count and their written forms (RF-01, RF-03, RF-04).

        «Sin rubro» travels beside the list rather than inside it, because it
        is not a row of `core.category` — but it is reported, so the cuts add
        up to the total the screen shows (RF-09, RF-10, RF-11).
        """
        categories = await self.catalog.list_categories()
        counts = await self.catalog.products_per_category()
        aliases: dict[int, list[CategoryAliasRead]] = defaultdict(list)
        for alias in await self.catalog.aliases():
            aliases[alias.category_id].append(CategoryAliasRead.model_validate(alias))
        return CategoryList(
            items=[
                CategoryRead(
                    id=category.id,
                    name=category.name,
                    product_count=counts.get(category.id, 0),
                    aliases=aliases.get(category.id, []),
                )
                for category in categories
            ],
            unclassified_count=counts.get(None, 0),
            total_products=sum(counts.values()),
        )

    async def create_category(self, *, name: str, actor_user_id: int) -> CategoryRead:
        """Add a rubro to the list (RF-05)."""
        clean = name.strip()
        if await self.catalog.category_named(clean) is not None:
            raise ConflictError(CATEGORY_ALREADY_EXISTS, details={"name": clean})
        category = await self.catalog.add_category(clean)
        await self._record_category_change(
            category, AuditAction.CREATED, actor_user_id, old_value=None, new_value=clean
        )
        await self.session.commit()
        logger.info("Category created", extra={"category_id": category.id})
        return CategoryRead(id=category.id, name=category.name, product_count=0, aliases=[])

    async def rename_category(
        self, category_id: int, *, name: str, actor_user_id: int
    ) -> CategoryRead:
        """Change the name of a rubro (RF-06)."""
        category = await self._require_category(category_id)
        clean = name.strip()
        existing = await self.catalog.category_named(clean)
        if existing is not None and existing.id != category.id:
            raise ConflictError(CATEGORY_ALREADY_EXISTS, details={"name": clean})
        previous, category.name = category.name, clean
        await self.session.flush()
        await self._record_category_change(
            category, AuditAction.UPDATED, actor_user_id, old_value=previous, new_value=clean
        )
        await self.session.commit()
        counts = await self.catalog.products_per_category()
        return CategoryRead(
            id=category.id,
            name=category.name,
            product_count=counts.get(category.id, 0),
            aliases=[
                CategoryAliasRead.model_validate(alias)
                for alias in await self.catalog.aliases()
                if alias.category_id == category.id
            ],
        )

    async def delete_category(self, category_id: int, *, actor_user_id: int) -> None:
        """Remove a rubro, unless something still points at it (RF-07).

        The check is here and not left to the foreign key on purpose: the
        system has to be able to say *why* it refuses, and an integrity error
        of PostgreSQL is not a sentence a person reads.
        """
        category = await self._require_category(category_id)
        counts = await self.catalog.products_per_category()
        in_use = counts.get(category.id, 0)
        if in_use:
            raise ConflictError(
                CATEGORY_HAS_PRODUCTS, details={"category_id": category_id, "products": in_use}
            )
        aliases = [
            alias for alias in await self.catalog.aliases() if alias.category_id == category.id
        ]
        if aliases:
            raise ConflictError(
                "El rubro todavía tiene formas escritas asignadas",
                details={"category_id": category_id, "aliases": len(aliases)},
            )
        name = category.name
        await self._record_category_change(
            category, AuditAction.UPDATED, actor_user_id, old_value=name, new_value=None
        )
        await self.catalog.delete_category(category)
        await self.session.commit()
        logger.info("Category deleted", extra={"category_id": category_id})

    async def unclassified(self, *, skip: int = 0, limit: int = 50) -> UnclassifiedList:
        """The queue of products with no rubro, each with its proposal or none.

        The proposal is derived here and stored nowhere (RF-16). A subcategory
        that resolves to **exactly one** rubro among what is already classified
        proposes it (RF-14); zero or more than one proposes nothing (RF-17) —
        breaking a tie would be the system deciding, which is the one thing
        this feature does not do.
        """
        products = await self.catalog.unclassified(skip=skip, limit=limit)
        total = await self.catalog.count_unclassified()
        by_subcategory = await self.catalog.rubro_of_subcategory()
        names = {category.id: category.name for category in await self.catalog.list_categories()}

        items: list[UnclassifiedProduct] = []
        for product in products:
            rubros = by_subcategory.get(product.subcategory_raw or "", set())
            proposed = next(iter(rubros)) if len(rubros) == 1 else None
            items.append(
                UnclassifiedProduct(
                    product_id=product.id,
                    code=product.code,
                    description=product.description,
                    category_raw=product.category_raw,
                    subcategory_raw=product.subcategory_raw,
                    proposed_category_id=proposed,
                    proposed_category_name=names.get(proposed) if proposed else None,
                )
            )
        return UnclassifiedList(items=items, total=total, skip=skip, limit=limit)

    async def set_product_category(
        self, product_id: int, *, category_id: int, actor_user_id: int
    ) -> UnclassifiedProduct:
        """Assign — or change — the rubro of a product (RF-13, RF-15, RF-20).

        Confirming a proposal and correcting it are the same write: only the
        rubro that travels differs, and the system has no reason to tell them
        apart. Who decided and when is recorded on the product (RF-18) and
        published as a manual change, so it reaches the one log of the platform
        without this module learning that the log exists.
        """
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError(NO_SUCH_PRODUCT, details={"product_id": product_id})
        category = await self._require_category(category_id)

        previous = product.category_id
        product.category_id = category.id
        product.classified_by_user_id = actor_user_id
        product.classified_at = datetime.now(UTC)
        # A decision by hand does not belong to any equivalence: revoking one
        # must not take this product with it.
        product.classified_by_rule_id = None
        await self.session.flush()

        await events.publish(
            ManualChangeRecorded(
                entity_type=PRODUCT_ENTITY,
                entity_id=str(product.id),
                action=AuditAction.UPDATED,
                actor_user_id=actor_user_id,
                section=CATALOG_SECTION,
                field=CATEGORY_FIELD,
                old_value=previous,
                new_value=category.id,
            ),
            self.session,
        )
        await self.session.commit()
        logger.info(
            "Product classified", extra={"product_id": product.id, "category_id": category.id}
        )
        return UnclassifiedProduct(
            product_id=product.id,
            code=product.code,
            description=product.description,
            category_raw=product.category_raw,
            subcategory_raw=product.subcategory_raw,
            proposed_category_id=category.id,
            proposed_category_name=category.name,
        )

    async def list_aliases(self) -> list[CategoryAliasRead]:
        """Every equivalence in force (RF-27).

        Who decided each one and when lives in `triage`, with the rule: the
        screen reads both and joins them by `rule_id`, and this module never
        touches somebody else's table to say a name.
        """
        return [CategoryAliasRead.model_validate(alias) for alias in await self.catalog.aliases()]

    async def learn_category_alias(
        self, *, rule_id: int | None, category_text: str, category_id: int
    ) -> None:
        """Project a decision about a written form, and apply it (RF-24, RF-25).

        Applying it here and not waiting for the next list is what makes the
        decision retroactive: the products that were left «sin rubro» by that
        written form get their rubro the moment somebody decides.
        """
        if await self.catalog.get_category(category_id) is None:
            logger.warning(
                "A decision named a rubro that does not exist", extra={"rule_id": rule_id}
            )
            return
        normalized = collapse_written_form(category_text)
        await self.catalog.put_alias(
            text_normalized=normalized,
            text_original=category_text.strip(),
            category_id=category_id,
            rule_id=rule_id,
        )
        classified = 0
        for product in await self.catalog.unclassified(limit=MAX_RECLASSIFIED):
            if product.category_raw and collapse_written_form(product.category_raw) == normalized:
                product.category_id = category_id
                product.classified_by_rule_id = rule_id
                classified += 1
        await self.session.flush()
        logger.info(
            "Category equivalence learned",
            extra={"rule_id": rule_id, "category_id": category_id, "classified": classified},
        )

    async def repoint_category_alias(self, *, rule_id: int, category_id: int) -> None:
        """Point an equivalence at another rubro and move what it had classified.

        RF-28 and RF-29, and the line that separates them from revoking:
        **nothing goes back to the queue**. The scope is exact —
        `classified_by_rule_id = rule_id` — so a product somebody classified by
        hand does not move, because it never depended on this equivalence.
        """
        alias = await self.catalog.alias_by_rule(rule_id)
        if alias is None or await self.catalog.get_category(category_id) is None:
            return
        alias.category_id = category_id
        moved = await self.catalog.products_classified_by(rule_id)
        for product in moved:
            product.category_id = category_id
        await self.session.flush()
        logger.info(
            "Category equivalence re-pointed",
            extra={"rule_id": rule_id, "category_id": category_id, "products": len(moved)},
        )

    async def forget_category_alias(self, rule_id: int) -> None:
        """Drop an equivalence and send back what it was resolving (RF-30, RF-31).

        The products are unclassified and go through the **same** step a batch
        goes through, so they end up as an `UnknownCategoryObserved` and the
        queue opens their case: one path, not a special branch for revocation.
        """
        alias = await self.catalog.alias_by_rule(rule_id)
        if alias is None:
            return
        affected = await self.catalog.products_classified_by(rule_id)
        text = alias.text_original
        await self.catalog.drop_alias_by_rule(rule_id)
        for product in affected:
            product.category_id = None
            product.classified_by_rule_id = None
        await self.session.flush()
        if affected:
            await events.publish(
                UnknownCategoryObserved(
                    batch_id=0,
                    cases=(
                        UnknownCategory(
                            category_text=text,
                            product_codes=tuple(product.code for product in affected),
                        ),
                    ),
                ),
                self.session,
            )
        logger.info(
            "Category equivalence forgotten",
            extra={"rule_id": rule_id, "products": len(affected)},
        )

    async def _require_category(self, category_id: int) -> Category:
        """Return the rubro, or say plainly that it is not there."""
        category = await self.catalog.get_category(category_id)
        if category is None:
            raise NotFoundError(NO_SUCH_CATEGORY, details={"category_id": category_id})
        return category

    async def _record_category_change(
        self,
        category: Category,
        action: AuditAction,
        actor_user_id: int,
        *,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Send a change of the rubro list to the one log of the platform."""
        await events.publish(
            ManualChangeRecorded(
                entity_type=CATEGORY_ENTITY,
                entity_id=str(category.id),
                action=action,
                actor_user_id=actor_user_id,
                section=CATALOG_SECTION,
                field="name",
                old_value=old_value,
                new_value=new_value,
            ),
            self.session,
        )

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
        # After the handlers, never before: a log line that could not be written
        # has to take the correction down with it (`GEN-09`), and committing
        # first would leave the value changed and the reason for it lost.
        await self.session.commit()
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
        await self.session.commit()
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

    async def _standing_corrections(
        self, product_ids: Iterable[int]
    ) -> dict[int, dict[str, Correction]]:
        """The corrections in force on these products, by product and by field.

        One query for a whole daily list rather than one per row: the list
        carries the entire catalogue, and the corrections it could contradict
        are a handful.

        Keyed by field and not by entity because a field belongs to exactly one
        entity — `CORRECTABLE_FIELDS` is what says so — and both entities are
        filed under the same `entity_id`, the product's. A product and its
        price in force cannot collide as long as they share no field name.
        """
        by_product: dict[int, dict[str, Correction]] = defaultdict(dict)
        entity_ids = [str(product_id) for product_id in product_ids]
        for correction in await self.catalog.corrections_in_force(entity_ids):
            by_product[int(correction.entity_id)][correction.field] = correction
        return by_product

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

        Text is compared normalised, for the same reason one step further out:
        «TORNILLO HEX.» and «Tornillo hex.» are one description written twice,
        and a list that changed the shift key is not the portal contradicting
        anybody. Flagging that as a conflict would put the owner in front of a
        case with nothing to decide (RF-28, RF-29), which is how an alert stops
        being read.

        `normalize` and not a comparison written here: it is the platform's one
        answer to "is this the same text?", the same one entity resolution
        asks, and two ways of comparing the same text in one repository is a
        disagreement waiting for the morning nobody remembers both.
        """
        _, numeric = cls._correctable(field)
        if numeric:
            return cls._as_number(left, field) == cls._as_number(right, field)
        return normalize(str(left)) == normalize(str(right))

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
        corrections: dict[str, Correction],
    ) -> tuple[bool, bool]:
        """Write the price in force. Returns (it changed, it is highlighted).

        A price that did not change adds no point to the history (RF-22) and
        keeps the date on which it was registered: that date is what the screen
        shows next to a product that did not come in today's list (RF-08).

        `source` is who is writing — a list the portal published, or this
        platform on somebody's decision. It is stamped on the row even when the
        amount did not move, because a list repeating a number a person typed
        is still the portal reporting that number (RF-33).

        `corrections` is what already stands on this product, by field, and
        the caller always brings it already read: a whole list reads the lot in
        one query, a price written onto a known product reads that product's,
        and a product being created passes `{}` because a product that did not
        exist a line ago cannot be contradicting anything.

        There is no default and no lookup down here on purpose. The query
        belongs where the caller can amortise it — re-asking from in here is
        what put one query per row into a run that carries the whole
        catalogue — and a required argument is what keeps the next caller from
        getting the cheap-looking version by saying nothing.
        """
        product.last_seen_at = moment

        # A corrected value is not overwritten by a later list (RF-28), and
        # `price` and `currency` are guarded one by one: both are correctable
        # fields of this row (RF-23), so a correction on either has to hold.
        # The comparison is local — the corrections live in this module
        # precisely so that these lines do not have to ask anybody anything.
        standing = corrections
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

    # --- The cuts of the dashboard that come from the catalog (009) -------

    async def dashboard(
        self, *, since: date | None = None, until: date | None = None
    ) -> CatalogDashboard:
        """What the supplier charged, what the stock did, and what is new.

        Three cuts of 009 that are about the catalog rather than about sales,
        and they live here for the reason the boundary exists: the prices, the
        stock and the products are this module's, and the dashboard reads them
        through its own endpoint rather than by another module reaching in.

        Each cut reports what it left out, **including when it left out
        nothing** (RF-46, RF-27): a product with no photograph at one end of the
        window is not counted as a zero, it is counted as excluded.
        """
        curve = await self.catalog.price_curve(since=since, until=until)
        opening = {} if since is None else await self.catalog.stock_at(since, latest=False)
        closing = {} if until is None else await self.catalog.stock_at(until, latest=True)
        products = await self.catalog.active_products()

        cuts: list[StockCut] = []
        excluded = 0
        for product in products:
            first, last = opening.get(product.id), closing.get(product.id)
            if first is None and last is None:
                # No photograph at either end: this product cannot be part of
                # this cut, and saying zero would be inventing a stock.
                excluded += 1
                continue
            cuts.append(
                StockCut(
                    product_id=product.id,
                    code=product.code,
                    description=product.description,
                    opening=first,
                    closing=last,
                    ran_out=last == 0,
                )
            )

        return CatalogDashboard(
            since=since,
            until=until,
            price_curve=[
                PriceCurvePoint(month=month, average_price=average, changes=changes)
                for month, average, changes in curve
            ],
            price_curve_excluded=0,
            stock=cuts,
            stock_excluded=excluded,
            new_products=[
                NewProductRead(
                    product_id=product.id,
                    code=product.code,
                    description=product.description,
                    first_seen_at=product.first_seen_at,
                )
                for product in await self.catalog.products_first_seen_between(since, until)
            ],
        )
