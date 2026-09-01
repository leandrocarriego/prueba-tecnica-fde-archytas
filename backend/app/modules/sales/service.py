"""Sales business logic: count what can be counted, hold what cannot, say which.

The client asked for this in one sentence — *"que se nos avise cuáles son, no
que se sumen como si fueran válidas"* — and the whole module is that sentence:

* a record that repeats another **identically** is counted once, and how many
  were merged is reported (RF-11, RF-12);
* one that repeats another with a **different** datum is held until a person
  decides which is valid (RF-13);
* one that is broken — no date, an impossible date, no total, a negative
  quantity, a product that does not exist, an amount wildly out of line — is
  held with its reason (RF-16 to RF-23);
* nothing is ever completed by assumption (RF-24), and every indicator says how
  many records it left out of itself (RF-25, RF-27).
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.sales.models import Sale, SaleState
from app.modules.sales.repository import SalesRepository
from app.modules.sales.schemas import (
    Indicator,
    MonthTotal,
    ResolvedGroup,
    ReviewQueue,
    SaleGroup,
    SaleList,
    SaleRead,
    SalesDashboard,
)
from app.shared.errors import ConflictError, NotFoundError, ValidationError
from app.shared.events import (
    CountedSale,
    HeldSale,
    NormalizedSale,
    PendingItem,
    QuarantinedSourceReopened,
    QuarantinedSourceResolved,
    SalesCounted,
    SalesHeld,
    events,
)
from app.shared.parameters import initial_value
from app.shared.sections import BusinessSection

logger = get_logger(__name__)

OUTLIER_KEY = "sales.outlier_threshold_pct"

# What a person reads next to a held record (RF-23), in Spanish like every
# user-facing string.
UNKNOWN_PRODUCT = "La venta apunta a un producto que no existe"
OUTLIER_TOTAL = "El total se aleja de lo habitual para ese producto"
DUPLICATE_WITH_DIFFERENCES = "Hay otra venta con el mismo código y datos distintos"
DUPLICATE_IDENTICAL = "Repetida idéntica: se cuenta una sola vez"
# Why a version was set aside when a **person** chose another one. It is not
# `DUPLICATE_IDENTICAL`: these versions were not identical — that is precisely
# why somebody had to decide — and telling the person who decided that the
# system unified them is telling them something that did not happen.
DISCARDED_BY_DECISION = "Se descartó al elegir otra versión de esta venta"

# What 011 needs said out loud when a held record stops being held. The kind is
# `triage`'s word for the case an unreadable sales row opens, and the key is the
# `staging` row it was opened with: rebuilding it any other way would close a
# case nobody resolved.
UNREADABLE_SALE_ROW = "unreadable_sale_row"
# Where the work happens, for the person who reads the closed case later.
# It used to say «la pantalla de ventas», and that stopped being true when
# the deciding moved into the queue: `/ventas` is a list now, and a case
# that names a screen where nothing can be decided sends somebody nowhere.
RESOLVED_IN_REVIEW = "la cola de pendientes"
REOPENED_IN_REVIEW = "la cola de pendientes"

# The two kinds of case a record that made it into `core` opens, and that
# `triage` shows in the one list of what is pending. They are `triage`'s words
# for them, like `UNREADABLE_SALE_ROW` above: this module names them so it can
# say out loud what it set aside, and it still never touches `triage`.
REPEATED_SALE = "repeated_sale"
BROKEN_SALE = "broken_sale"
# Where a broken record's case went when a twin turned it into a group. It is
# not a person's doing, and the closed case says so rather than crediting one.
GROUPED_WITH_A_TWIN = "la cola, al aparecer otra venta con el mismo código"
# Lo que se lee cuando un registro quedó apartado sin motivo escrito. No
# debería pasar —todo lo que se aparta se aparta por algo— y si pasa, la cola
# lo dice así en vez de mostrar un renglón en blanco.
NO_REASON_GIVEN = "Apartada sin motivo registrado"

NO_SUCH_SALE = "No encontramos esa venta"
NOT_HELD = "Esa venta no está apartada"
NOTHING_TO_UNDO = "Esa venta no tiene una resolución que deshacer"

# The fields that decide whether two records with the same code are the same
# sale. The code itself is not among them: it is what grouped them.
COMPARED = ("sold_on", "product_code", "quantity", "total")

HUNDRED = Decimal(100)


class SalesService:
    """Registers sales records, holds what cannot be added, and answers the dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sales = SalesRepository(session)

    # --- Registering what the sales screen brought -----------------------

    async def register_sales(self, *, batch_id: int, sales: tuple[NormalizedSale, ...]) -> None:
        """Bring a batch of sales records in, counting only what may be counted.

        Three outcomes, and none of them is «dropped». A record the parser could
        not read whole is **held with its reason**; one that repeats another
        identically is counted once and its copy kept; one that repeats another
        with something different holds both until a person decides.
        """
        known = await self.sales.known_products()
        threshold = Decimal(str(await self._setting(OUTLIER_KEY)))
        merged = held = counted = 0
        # What this batch left waiting for a person, to be said out loud once
        # the rows have their ids. Collected instead of announced row by row
        # because a repeated sale is **one** thing to decide, however many
        # versions of it arrived in the same batch.
        waiting: list[Sale] = []
        # Y las dos mitades de «esto suma»: lo que empieza a contar y lo que
        # dejó de hacerlo porque llegó su repetida.
        adding: list[CountedSale] = []
        dropped: list[int] = []

        for row in sales:
            if row.reason is not None:
                # The parser could not read this record whole. It is held with
                # the reason it arrived with (RF-16 to RF-19, RF-23) and it is
                # **not compared against anything**: a record missing its code
                # has no code to group by, and one missing its date or its total
                # is not a repetition of anybody until a person completes it.
                # Correcting it is `correct_sale`, and from there it counts.
                waiting.append(
                    await self.sales.add(
                        self._sale_of(row, state=SaleState.HELD, reason=row.reason)
                    )
                )
                held += 1
                continue

            reason = await self._why_not_countable(row, known=known, threshold=threshold)
            siblings = await self.sales.with_code_key(row.code_key)
            twin = self._identical_among(siblings, row)

            if twin is not None:
                # The same sale arriving twice with nothing different about it.
                # It is counted once and kept, so what was merged can be seen.
                await self.sales.add(
                    self._sale_of(row, state=SaleState.DISCARDED, reason=DUPLICATE_IDENTICAL)
                )
                merged += 1
                continue

            if siblings and reason is None:
                # Same code, something different: neither of them is added up
                # until somebody says which is valid (RF-13, RF-15).
                reason = DUPLICATE_WITH_DIFFERENCES
                for sibling in siblings:
                    if sibling.state is SaleState.COUNTED:
                        sibling.state = SaleState.HELD
                        sibling.reason = DUPLICATE_WITH_DIFFERENCES
                        # Contaba y dejó de contar. Quien tenga una proyección
                        # de lo vendido tiene que enterarse de la baja igual que
                        # de las altas, o sigue sumando plata que esta pantalla
                        # ya no suma.
                        if sibling.staging_row_id is not None:
                            dropped.append(sibling.staging_row_id)

            sale = await self.sales.add(
                self._sale_of(
                    row,
                    state=SaleState.COUNTED if reason is None else SaleState.HELD,
                    reason=reason,
                )
            )
            counted += int(sale.state is SaleState.COUNTED)
            held += int(sale.state is SaleState.HELD)
            if sale.state is SaleState.HELD:
                waiting.append(sale)
            elif sale.staging_row_id is not None and sale.total is not None:
                adding.append(
                    CountedSale(
                        staging_row_id=sale.staging_row_id,
                        product_code=sale.product_code,
                        total=sale.total,
                        sold_on=sale.sold_on,
                    )
                )

        await self.session.flush()
        await self._announce_held(batch_id=batch_id, records=waiting)
        # Y lo que cuenta, que es la otra mitad. Se publica siempre, también
        # vacío: quien mantiene una proyección de lo vendido necesita las bajas
        # aunque no haya altas.
        # Las dos listas tienen que ser disjuntas, y no lo son solas: una venta
        # que este mismo lote contó y después apartó —porque más abajo llegó su
        # repetida— está en las dos. Quien las reciba aplicaría el alta y la
        # baja en algún orden, y el orden decidiría el total.
        leaving = set(dropped)
        await events.publish(
            SalesCounted(
                batch_id=batch_id,
                counted=tuple(one for one in adding if one.staging_row_id not in leaving),
                no_longer_counted=tuple(leaving),
            ),
            self.session,
        )
        logger.info(
            "Sales registered",
            extra={"batch_id": batch_id, "counted": counted, "held": held, "merged": merged},
        )

    async def _announce_held(self, *, batch_id: int, records: Sequence[Sale]) -> None:
        """Say what came in and is waiting for a person (RF-06 of 011).

        Announced and not called, like every other thing this module tells the
        rest of the platform: `sales` may not touch `triage` (Artículo IV), so
        what leaves here is identifiers and a label and whoever cares listens.

        **What travels is one case per decision, not one per row.** Two versions
        of the same sale are a single question — *which of these is the valid
        one* — and sending two would put the same decision in front of a person
        twice. So the records of this batch are grouped the way the review queue
        groups them: by `code_key` when there is one and a twin to go with it,
        on their own otherwise.

        The grouping is asked of the database rather than of the batch, because
        the twin may have arrived a week ago: a record held alone in March and
        repeated in April is a group in April, and the case it opened when it
        was alone stops being true right then. That one is closed here, and
        `GROUPED_WITH_A_TWIN` says it was the queue and not a person who closed
        it.
        """
        if not records:
            return

        cases: list[HeldSale] = []
        alone: list[Sale] = []
        seen: set[str] = set()

        for record in records:
            if not record.code_key:
                # No code is no group, however many of them arrive: they would
                # all share the empty key and the screen would ask somebody
                # which of a pile of unrelated records «is the valid one».
                alone.append(record)
                continue
            if record.code_key in seen:
                continue
            seen.add(record.code_key)

            siblings = [
                sale
                for sale in await self.sales.with_code_key(record.code_key)
                if sale.state is SaleState.HELD
            ]
            if len(siblings) < 2:
                alone.append(record)
                continue

            cases.append(
                HeldSale(
                    kind=REPEATED_SALE,
                    key=record.code_key,
                    code=record.code,
                    reason=DUPLICATE_WITH_DIFFERENCES,
                    versions=len(siblings),
                )
            )
            for sibling in siblings:
                await events.publish(
                    QuarantinedSourceResolved(
                        kind=BROKEN_SALE,
                        key=str(sibling.id),
                        resolved_where=GROUPED_WITH_A_TWIN,
                    ),
                    self.session,
                )

        cases.extend(
            HeldSale(
                kind=BROKEN_SALE,
                key=str(record.id),
                code=record.code,
                reason=record.reason or "",
                versions=1,
            )
            for record in alone
        )

        await events.publish(SalesHeld(batch_id=batch_id, cases=tuple(cases)), self.session)

    @staticmethod
    def _sale_of(row: NormalizedSale, *, state: SaleState, reason: str | None) -> Sale:
        """Build the record, keeping what the portal said about it (RF-41)."""
        return Sale(
            code=row.code,
            code_key=row.code_key,
            sold_on=row.sold_on,
            product_code=row.product_code,
            quantity=row.quantity,
            total=row.total,
            state=state,
            reason=reason,
            portal_values={
                "sold_on": row.sold_on.isoformat() if row.sold_on else None,
                "product_code": row.product_code,
                "quantity": row.quantity,
                "total": str(row.total) if row.total is not None else None,
            },
            staging_row_id=row.staging_row_id,
        )

    async def _why_not_countable(
        self, row: NormalizedSale, *, known: set[str], threshold: Decimal
    ) -> str | None:
        """Why this record may not be added up, or nothing.

        Only reached by a record that **read whole**: the parser already named
        what it could not read — no date, a date that does not exist, no total,
        a negative quantity — and `register_sales` holds those with that reason
        without ever asking this. What is decided here is what needs the rest of
        the platform to answer: whether the product exists, and whether the
        amount is wildly out of line for it.
        """
        if row.product_code and row.product_code not in known:
            return UNKNOWN_PRODUCT
        if row.product_code and row.total is not None:
            usual = await self.sales.average_total_for(row.product_code)
            if usual is not None and usual > 0:
                drift = abs(row.total - usual) / usual * HUNDRED
                if drift > threshold:
                    return OUTLIER_TOTAL
        return None

    @staticmethod
    def _identical_among(siblings: list[Sale], row: NormalizedSale) -> Sale | None:
        """A record already stored that this one repeats with nothing different."""
        for sibling in siblings:
            if all(getattr(sibling, field) == getattr(row, field) for field in COMPARED):
                return sibling
        return None

    async def _setting(self, key: str) -> Any:
        """A business parameter, from this module's projection or its initial value."""
        stored = await self.sales.setting(key)
        return initial_value(key) if stored is None else stored

    async def remember_setting(self, key: str, value: Any) -> None:
        """Keep a business parameter this module reads."""
        await self.sales.put_setting(key, value)

    async def remember_product(self, product_code: str) -> None:
        """Keep a product the catalog started to know (RF-20)."""
        await self.sales.put_product(product_code)

    # --- Reading -----------------------------------------------------------

    async def list_sales(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        state: SaleState | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> SaleList:
        """The sales records, filtered the way the screen filters them."""
        records = await self.sales.list_sales(
            skip=skip, limit=limit, state=state, since=since, until=until
        )
        return SaleList(
            items=[SaleRead.model_validate(sale) for sale in records],
            total=await self.sales.count_sales(state=state, since=since, until=until),
            skip=skip,
            limit=limit,
        )

    async def review_queue(self) -> ReviewQueue:
        """What is waiting for a person: the repeated ones and the broken ones.

        A group is shown with its versions face to face and the fields they
        disagree on named (RF-30), which is what turns "these two are different"
        into a decision somebody can take in a second.
        """
        grouped = await self.sales.held_groups()
        groups: list[SaleGroup] = []
        broken: list[SaleRead] = []
        for code_key, records in grouped.items():
            # A record that arrived **without a code** is not part of any group,
            # however many of them there are. They all share the empty
            # `code_key`, so grouping them the way the rest is grouped would
            # build one bogus «repeated sale» out of records that have nothing
            # to do with each other — and the screen would ask a person to
            # choose which of them «is the valid one».
            if not code_key or len(records) < 2:
                broken.extend(SaleRead.model_validate(sale) for sale in records)
                continue
            groups.append(
                SaleGroup(
                    code_key=code_key,
                    versions=[SaleRead.model_validate(sale) for sale in records],
                    differences=self._differences_among(records),
                )
            )
        return ReviewQueue(
            groups=groups,
            broken=broken,
            pending_groups=len(groups),
            held=sum(len(records) for records in grouped.values()),
        )

    async def pending_work(self) -> tuple[PendingItem, ...]:
        """Todo lo que ventas tiene esperando a una persona, como lista completa.

        La respuesta a la pregunta que alguien hace en público cada tanto. Es
        **completa a propósito**: quien la escucha la usa para abrir lo que falta
        y cerrar lo que sobra, y una lista parcial le haría cerrar casos que
        siguen vivos.

        Sale de la misma cola que mira la pantalla —`review_queue`— y no de una
        consulta propia, para que no puedan discrepar: si un día la pantalla
        agrupa distinto, el informe agrupa igual, porque es el mismo código.
        """
        queue = await self.review_queue()
        items = [
            PendingItem(
                kind=REPEATED_SALE,
                key=group.code_key,
                reason=DUPLICATE_WITH_DIFFERENCES,
                section=BusinessSection.SALES.value,
                detail=(
                    ("code", group.versions[0].code if group.versions else group.code_key),
                    ("versions", str(len(group.versions))),
                ),
            )
            for group in queue.groups
        ]
        items.extend(
            PendingItem(
                kind=BROKEN_SALE,
                key=str(sale.id),
                reason=sale.reason or NO_REASON_GIVEN,
                section=BusinessSection.SALES.value,
                detail=(("code", sale.code),),
            )
            for sale in queue.broken
        )
        return tuple(items)

    async def resolved_groups(self, *, limit: int = 50) -> list[ResolvedGroup]:
        """The cases a person already decided (RF-34, RF-35, RF-36 of 009).

        The counterpart of `review_queue`, and it exists because that one
        answers a different question. A decided case leaves the queue on
        purpose — RF-37 asks for one less pending — and until now it left the
        screen with it, taking three signed requirements along: nobody could see
        the discarded version beside the chosen one, nobody could read what was
        decided and by whom, and the undo RF-35 promises had no place to be
        offered.
        """
        grouped = await self.sales.resolved_groups(limit=limit)
        resolved: list[ResolvedGroup] = []
        for code_key, records in grouped.items():
            # Every version of a group carries the same decision: `resolve_group`
            # stamps all of them, so any one of them can be asked.
            decision = next((sale.decision for sale in records if sale.decision), {})
            resolved.append(
                ResolvedGroup(
                    code_key=code_key,
                    versions=[SaleRead.model_validate(sale) for sale in records],
                    action=str(decision.get("action", "")),
                    kept_sale_id=decision.get("sale_id"),
                    resolved_at=next(
                        (sale.resolved_at for sale in records if sale.resolved_at), None
                    ),
                    resolved_by_user_id=next(
                        (sale.resolved_by_user_id for sale in records if sale.resolved_by_user_id),
                        None,
                    ),
                )
            )
        return resolved

    @staticmethod
    def _differences_among(records: list[Sale]) -> list[str]:
        """The fields on which the versions of a sale disagree."""
        return [field for field in COMPARED if len({getattr(sale, field) for sale in records}) > 1]

    async def dashboard(
        self, *, since: date | None = None, until: date | None = None
    ) -> SalesDashboard:
        """The commercial dashboard over one window.

        Every indicator carries how many records it left out, **including when
        it left out none** (RF-25, RF-27), and says whether any value behind it
        was estimated by a person rather than reported (RF-40).
        """
        invoiced, counted = await self.sales.totals(since=since, until=until)
        held = await self.sales.count_sales(state=SaleState.HELD, since=since, until=until)
        discarded = await self.sales.count_sales(
            state=SaleState.DISCARDED, since=since, until=until
        )
        queue = await self.review_queue()
        return SalesDashboard(
            since=since,
            until=until,
            invoiced=Indicator(
                value=invoiced,
                sales=counted,
                excluded=held + discarded,
                # Of everything left out, how much the platform unified on its
                # own (RF-12). It is reported apart from the rest because they
                # are different facts: nobody decided the merged ones, and a
                # person decided every other discarded one.
                merged=await self.sales.count_merged(since=since, until=until),
                has_estimates=await self.sales.has_estimates(since=since, until=until),
            ),
            by_month=[
                MonthTotal(month=month, total=total, sales=count)
                for month, total, count in await self.sales.monthly_totals(since=since, until=until)
            ],
            held_total=await self.sales.count_sales(state=SaleState.HELD),
            pending_groups=queue.pending_groups,
            # Las dos formas en que una venta espera a alguien, sumadas: un
            # grupo de repetidas es **una** decisión aunque tenga cuatro
            # versiones, y una apartada suelta es otra. Es exactamente lo que
            # muestra `/revision?area=SALES`, que es adonde lleva el aviso.
            pending_decisions=queue.pending_groups + len(queue.broken),
        )

    # --- Deciding ----------------------------------------------------------

    async def resolve_group(
        self, code_key: str, *, action: str, sale_id: int | None, actor_user_id: int
    ) -> list[SaleRead]:
        """Decide about a repeated sale (RF-31 to RF-34, RF-36, RF-37 of 009).

        Choosing a version counts that one and keeps the others visible beside
        it, discarded but never deleted. Declaring them different sales counts
        all of them: they were never the same sale, and the code they share is
        the mistake.
        """
        records = await self.sales.with_code_key(code_key)
        if not records:
            raise NotFoundError(NO_SUCH_SALE, details={"code_key": code_key})

        now = datetime.now(UTC)
        decision = {"action": action, "sale_id": sale_id}
        for sale in records:
            if action == "distinct":
                sale.state = SaleState.COUNTED
                sale.duplicate_of_sale_id = None
            else:
                chosen = sale.id == sale_id
                sale.state = SaleState.COUNTED if chosen else SaleState.DISCARDED
                sale.duplicate_of_sale_id = None if chosen else sale_id
            sale.reason = None if sale.state is SaleState.COUNTED else DISCARDED_BY_DECISION
            sale.decision = decision
            sale.resolved_by_user_id = actor_user_id
            sale.resolved_at = now
        await self.session.flush()
        await self._announce_resolved(records)
        # And the case the group itself opened. It is keyed by the `code_key`
        # and not by a row, because that is what was decided: one question about
        # however many versions there were.
        await events.publish(
            QuarantinedSourceResolved(
                kind=REPEATED_SALE, key=code_key, resolved_where=RESOLVED_IN_REVIEW
            ),
            self.session,
        )
        await self.session.commit()
        logger.info("Sales group resolved", extra={"code_key": code_key, "action": action})
        return [SaleRead.model_validate(sale) for sale in records]

    async def _announce_resolved(self, records: Sequence[Sale]) -> None:
        """Say that a reading nobody could type has been dealt with (RF-20 of 011).

        Until 011 an unreadable sales row went to quarantine and opened no case
        anywhere; now it opens one, and a case a person then resolves *on this
        screen* has to stop counting as pending — asking them to close it again
        in the review queue is the same work twice, and the day they forget, the
        list of pending things is lying.

        It is announced and not called. `sales` may not touch `triage`
        (Artículo IV), so what happens here is a fact stated in public —
        identifiers and a label, never the record — and whoever cares listens.
        Most of these close nothing, because most sales never had a case, and
        that is the ordinary outcome rather than an error.

        Only records that came from a reading are announced: one somebody typed
        has no `staging_row_id` and never had a case to close.
        """
        for sale in records:
            if sale.staging_row_id is None:
                continue
            await events.publish(
                QuarantinedSourceResolved(
                    kind=UNREADABLE_SALE_ROW,
                    key=str(sale.staging_row_id),
                    resolved_where=RESOLVED_IN_REVIEW,
                ),
                self.session,
            )

    async def undo_resolution(self, code_key: str) -> list[SaleRead]:
        """Put a resolved group back in the queue and recalculate (RF-35 of 009)."""
        records = await self.sales.with_code_key(code_key)
        if not records:
            raise NotFoundError(NO_SUCH_SALE, details={"code_key": code_key})
        if not any(sale.decision for sale in records):
            raise ConflictError(NOTHING_TO_UNDO, details={"code_key": code_key})
        for sale in records:
            sale.state = SaleState.HELD
            sale.reason = DUPLICATE_WITH_DIFFERENCES
            sale.decision = None
            sale.duplicate_of_sale_id = None
            sale.resolved_by_user_id = None
            sale.resolved_at = None
        await self.session.flush()
        await self._announce_reopened(records)
        # The mirror of the line in `resolve_group`, and it is here for the rule
        # that made its sibling exist: *hay una sola verdad sobre si algo sigue
        # pendiente*, and it has to hold in both directions.
        await events.publish(
            QuarantinedSourceReopened(
                kind=REPEATED_SALE, key=code_key, reopened_where=REOPENED_IN_REVIEW
            ),
            self.session,
        )
        await self.session.commit()
        return [SaleRead.model_validate(sale) for sale in records]

    async def _announce_reopened(self, records: Sequence[Sale]) -> None:
        """Say that a reading that had been dealt with is waiting again (RF-24).

        The mirror of `_announce_resolved`, and it is here for the reason the
        signed rule gives: *hay una sola verdad sobre si algo sigue pendiente*,
        and it has to hold in both directions. This screen lets somebody undo a
        resolution — 009 promised that (RF-35) — and until 011 the case that had
        closed itself stayed closed, so the queue said there was nothing to
        review about a record that was, right then, back under review.

        Announced and not called, like its mirror: `sales` may not touch
        `triage` (Artículo IV). Only records that came from a reading are
        announced, because only those ever had a case.
        """
        for sale in records:
            if sale.staging_row_id is None:
                continue
            await events.publish(
                QuarantinedSourceReopened(
                    kind=UNREADABLE_SALE_ROW,
                    key=str(sale.staging_row_id),
                    reopened_where=REOPENED_IN_REVIEW,
                ),
                self.session,
            )

    async def correct_sale(
        self,
        sale_id: int,
        *,
        values: dict[str, Any],
        is_estimated: bool,
        actor_user_id: int,
    ) -> SaleRead:
        """Correct a held record, keeping what the portal said (RF-38, RF-39, RF-41).

        A record that becomes readable is counted from here on; one that still
        is not stays held with the reason it already had. The platform does not
        pretend a correction fixed something it did not.
        """
        sale = await self.sales.sale(sale_id)
        if sale is None:
            raise NotFoundError(NO_SUCH_SALE, details={"sale_id": sale_id})
        if sale.state is not SaleState.HELD:
            raise ConflictError(NOT_HELD, details={"sale_id": sale_id})

        for field, value in values.items():
            if value is not None:
                setattr(sale, field, value)
        sale.is_estimated = sale.is_estimated or is_estimated
        sale.resolved_by_user_id = actor_user_id
        sale.resolved_at = datetime.now(UTC)

        if sale.sold_on is None or sale.total is None:
            raise ValidationError(
                "La venta sigue sin fecha o sin total", details={"sale_id": sale_id}
            )
        known = await self.sales.known_products()
        if sale.product_code and sale.product_code not in known:
            sale.reason = UNKNOWN_PRODUCT
        else:
            sale.state = SaleState.COUNTED
            sale.reason = None
        await self.session.flush()
        await self._announce_resolved([sale])
        # **Only if the correction actually fixed it.** A record whose product
        # still does not exist stays held, so its case stays open: closing it
        # here would empty the queue of something nobody resolved, which is the
        # one thing the queue exists not to do (Artículo II).
        if sale.state is SaleState.COUNTED:
            await events.publish(
                QuarantinedSourceResolved(
                    kind=BROKEN_SALE, key=str(sale.id), resolved_where=RESOLVED_IN_REVIEW
                ),
                self.session,
            )
        await self.session.commit()
        return SaleRead.model_validate(sale)
