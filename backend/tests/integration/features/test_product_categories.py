"""Los rubros: clasificar sin adivinar, y corregir sin mandar nada a la cola.

Las cinco historias de `008-product-categories`, y en particular los cuatro
puntos que su propio plan marcó como los que se rompen de verdad:

* el **matcher** de una decisión sobre una forma escrita sale por el texto y no
  por el producto que la trajo — si sale por producto, RF-25 falla en silencio;
* cien productos con la misma forma escrita desconocida abren **un** caso;
* **corregir** una equivalencia reasigna y **no** manda nada a revisión, que es
  la línea entre RF-29 y RF-31;
* **revocar** sí la manda, y los totales de RF-10 siguen cerrando.

Todo contra la lista fijada en `tests/fixtures/portal/`, nunca contra el portal
(`TEST-03`).
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category, CategoryAlias, Product
from app.modules.catalog.service import UNKNOWN_CATEGORY, CatalogService
from app.modules.identity.models import User
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import TriageService
from app.shared.errors import ConflictError, NotFoundError, ValidationError
from app.shared.events import NormalizedPriceRow
from app.shared.sections import BusinessSection

pytestmark = [pytest.mark.integration, pytest.mark.database]


# Lo que el dueño alcanza, que es todo. Se escribe y no se da por sentado porque
# `resolve` no acepta un default: qué áreas puede tocar alguien es cosa de quien
# llama, y un default sería la cola creyéndole a cualquiera (RF-13 de 011).
EVERY_AREA = frozenset(BusinessSection)

API_PREFIX = "/api/v1"


def row(
    code: str,
    *,
    category: str | None = None,
    subcategory: str | None = None,
    stock: int | None = None,
) -> NormalizedPriceRow:
    """One normalised row of the daily list, as `ingestion` publishes it."""
    return NormalizedPriceRow(
        staging_row_id=0,
        product_code=code,
        description=f"Producto {code}",
        price=Decimal("1000"),
        currency="ARS",
        category_raw=category,
        subcategory_raw=subcategory,
        stock=stock,
    )


async def apply(
    session: AsyncSession, rows: list[NormalizedPriceRow], *, batch_id: int = 1
) -> None:
    """Run one batch through the catalog, seeding it if it is the first."""
    await CatalogService(session).apply_price_batch(batch_id=batch_id, rows=tuple(rows))
    await session.flush()


async def product(session: AsyncSession, code: str) -> Product:
    """The product with this code, as it ended up in `core`."""
    found = (await session.execute(select(Product).where(Product.code == code))).scalar_one()
    await session.refresh(found)
    return found


async def named(session: AsyncSession, name: str) -> Category:
    """The seeded rubro with this name."""
    return (await session.execute(select(Category).where(Category.name == name))).scalar_one()


async def pending_categories(session: AsyncSession) -> list[ExceptionCase]:
    """The cases waiting for somebody to say what rubro a written form means."""
    result = await session.execute(
        select(ExceptionCase).where(
            ExceptionCase.kind == UNKNOWN_CATEGORY, ExceptionCase.status == CaseStatus.PENDING
        )
    )
    return list(result.scalars().all())


class TestTheSignedTableIsAlreadyLoaded:
    """H1: the platform starts knowing the eighteen written forms it was given."""

    async def test_every_equivalence_has_a_rule_behind_it(self, session: AsyncSession) -> None:
        """The asymmetry the plan warned about: a seeded form must be correctable.

        If the eighteen forms of the factory had no rule they could neither be
        re-pointed nor revoked, and nothing would fail — RF-28 and RF-30 would
        simply not reach them. So every equivalence, seeded or learned, is
        checked to carry its rule.
        """
        # Act
        aliases = (await session.execute(select(CategoryAlias))).scalars().all()

        # Assert
        assert aliases
        assert all(alias.rule_id is not None for alias in aliases)

    async def test_a_rubro_shows_the_written_forms_that_have_a_row(
        self, session: AsyncSession
    ) -> None:
        """RF-03, and it fixes **what the system does**, not what was signed.

        The signed acceptance criterion says that opening «Pinturas y
        Adhesivos» shows the **three** written forms that reach it, and the
        screen shows **two**: `PINTURAS Y ADHESIVOS` and `Pinturas/Adhesivos`.
        The three still *resolve* — `Pinturas y Adhesivos` in title case has the
        same matching key as the first, and that is why it has no row of its
        own. So this test asserts two, deliberately, and it is the assertion
        that has to change if the human decides the agreement is what stands:
        it is point 13 of *Deriva* in `plan.md`, and until then this pins the
        behaviour so nobody changes it by accident.
        """
        # Act
        listing = await CatalogService(session).list_categories()

        # Assert
        paints = next(item for item in listing.items if item.name == "Pinturas y Adhesivos")
        assert [alias.text_original for alias in paints.aliases] == [
            "PINTURAS Y ADHESIVOS",
            "Pinturas/Adhesivos",
        ]

    async def test_the_seeded_forms_are_not_attributed_to_anybody(
        self, session: AsyncSession
    ) -> None:
        """An equivalence that came with the system was decided by nobody (RF-27)."""
        # Act
        rules = await TriageService(session).list_rules(kind=UNKNOWN_CATEGORY)

        # Assert
        assert rules
        assert all(rule.created_by_user_id is None for rule in rules)
        assert all(rule.created_by_name for rule in rules)

    async def test_a_written_form_that_only_differs_in_case_is_one_equivalence(
        self, session: AsyncSession
    ) -> None:
        """`ELECTRICIDAD` and `Electricidad` are the same key, and resolve the same.

        This is the pair the normalisation is allowed to collapse, and the only
        one: `Ferreteria Gral.` stays a row of its own.
        """
        # Act
        await apply(
            session,
            [
                row("CAT-0001", category="ELECTRICIDAD"),
                row("CAT-0002", category="Electricidad"),
                row("CAT-0003", category="Ferreteria Gral."),
            ],
        )

        # Assert
        electricity = await named(session, "Electricidad")
        hardware = await named(session, "Ferretería General")
        assert (await product(session, "CAT-0001")).category_id == electricity.id
        assert (await product(session, "CAT-0002")).category_id == electricity.id
        assert (await product(session, "CAT-0003")).category_id == hardware.id


class TestAFormNobodyDecidedAbout:
    """H4: what the system does not know goes to a person, never to a guess."""

    async def test_it_opens_one_case_for_a_hundred_products(self, session: AsyncSession) -> None:
        """RF-21, RF-22: one question per written form, not per product."""
        # Act
        await apply(
            session, [row(f"CAT-01{index:02d}", category="Bulones Varios") for index in range(100)]
        )

        # Assert
        cases = await pending_categories(session)
        assert len(cases) == 1
        assert cases[0].payload["category_text"] == "Bulones Varios"
        assert cases[0].payload["products"] == 100

    async def test_the_products_are_left_without_a_rubro(self, session: AsyncSession) -> None:
        """RF-22: not assigned to anything, and counted as «sin rubro»."""
        # Act
        await apply(session, [row("CAT-0200", category="Bulones Varios")])

        # Assert
        assert (await product(session, "CAT-0200")).category_id is None
        assert (await CatalogService(session).list_categories()).unclassified_count >= 1

    async def test_the_decision_matches_on_the_written_form(
        self, session: AsyncSession, owner: User
    ) -> None:
        """The first test the plan asks for, and the one that fails in silence.

        A decision about a category is about the **text**. If the matcher came
        out with `product_code`, the equivalence would apply to one product and
        the other ninety-nine would stay in the queue — with every other test
        still green.
        """
        # Arrange
        await apply(session, [row("CAT-0300", category="Bulones Varios")])
        case = (await pending_categories(session))[0]
        target = await named(session, "Ferretería General")

        # Act
        await TriageService(session).resolve(
            case.id, decision={"category_id": target.id}, user_id=owner.id, visible=EVERY_AREA
        )

        # Assert
        rule = (await TriageService(session).list_rules(kind=UNKNOWN_CATEGORY))[0]
        assert rule.matcher["category_text"] == "Bulones Varios"
        assert "product_code" not in rule.matcher

    async def test_deciding_classifies_what_was_already_set_aside(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-24, RF-25: the decision is retroactive and applies on its own after."""
        # Arrange — both products are registered by the first list; the second
        # one arrives without a category and waits in the unclassified queue.
        await apply(
            session,
            [row("CAT-0400", category="Bulones Varios"), row("CAT-0401", category=None)],
        )
        case = (await pending_categories(session))[0]
        target = await named(session, "Ferretería General")

        # Act
        await TriageService(session).resolve(
            case.id, decision={"category_id": target.id}, user_id=owner.id, visible=EVERY_AREA
        )

        # Assert — the one that was waiting is classified retroactively, and
        # the next list that spells it the same way needs nobody.
        assert (await product(session, "CAT-0400")).category_id == target.id
        await apply(session, [row("CAT-0401", category="Bulones Varios")], batch_id=2)
        assert (await product(session, "CAT-0401")).category_id == target.id
        assert not await pending_categories(session)


class TestCorrectingAnEquivalence:
    """H5: re-pointing is not revoking, and the difference is the whole test."""

    async def _an_equivalence(self, session: AsyncSession, owner: User) -> tuple[int, Category]:
        """A learned equivalence over `Bulones Varios`, with a product behind it."""
        await apply(session, [row("CAT-0500", category="Bulones Varios")])
        case = (await pending_categories(session))[0]
        first = await named(session, "Ferretería General")
        await TriageService(session).resolve(
            case.id, decision={"category_id": first.id}, user_id=owner.id, visible=EVERY_AREA
        )
        rule = (await TriageService(session).list_rules(kind=UNKNOWN_CATEGORY))[0]
        return rule.id, first

    async def test_it_reassigns_without_going_through_review(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-28, RF-29. If the product shows up in the queue, RF-31 was built here."""
        # Arrange
        rule_id, _ = await self._an_equivalence(session, owner)
        target = await named(session, "Herramientas")

        # Act
        await TriageService(session).redecide_rule(
            rule_id, decision={"category_id": target.id}, user_id=owner.id
        )

        # Assert
        assert (await product(session, "CAT-0500")).category_id == target.id
        assert not await pending_categories(session)

    async def test_it_reaches_a_seeded_equivalence_the_same_way(
        self, session: AsyncSession, owner: User
    ) -> None:
        """The eighteen of the factory are rules like any other, so this works on them."""
        # Arrange
        await apply(session, [row("CAT-0600", category="Herram.")])
        alias = (
            await session.execute(
                select(CategoryAlias).where(CategoryAlias.text_original == "Herram.")
            )
        ).scalar_one()
        target = await named(session, "Instrumental")

        # Act
        await TriageService(session).redecide_rule(
            alias.rule_id or 0, decision={"category_id": target.id}, user_id=owner.id
        )

        # Assert
        assert (await product(session, "CAT-0600")).category_id == target.id

    async def test_it_does_not_touch_what_somebody_classified_by_hand(
        self, session: AsyncSession, owner: User
    ) -> None:
        """A hand-made decision does not depend on any equivalence, and does not move."""
        # Arrange
        rule_id, _ = await self._an_equivalence(session, owner)
        by_hand = await named(session, "Sanitarios")
        await CatalogService(session).set_product_category(
            (await product(session, "CAT-0500")).id,
            category_id=by_hand.id,
            actor_user_id=owner.id,
        )
        target = await named(session, "Herramientas")

        # Act
        await TriageService(session).redecide_rule(
            rule_id, decision={"category_id": target.id}, user_id=owner.id
        )

        # Assert
        assert (await product(session, "CAT-0500")).category_id == by_hand.id

    async def test_a_revoked_equivalence_cannot_be_re_pointed(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Reviving what somebody switched off, with nobody deciding it, is refused."""
        # Arrange
        rule_id, _ = await self._an_equivalence(session, owner)
        await TriageService(session).revoke_rule(rule_id, user_id=owner.id)
        target = await named(session, "Herramientas")

        # Act / Assert
        with pytest.raises(ConflictError):
            await TriageService(session).redecide_rule(
                rule_id, decision={"category_id": target.id}, user_id=owner.id
            )


class TestRevokingAnEquivalence:
    """H5 from the other side: RF-30 and RF-31, with the totals still closing."""

    async def test_the_products_go_back_to_review(self, session: AsyncSession, owner: User) -> None:
        """RF-31: unclassified **and** back in the queue, by the ordinary path."""
        # Arrange
        await apply(session, [row("CAT-0700", category="Bulones Varios")])
        case = (await pending_categories(session))[0]
        target = await named(session, "Ferretería General")
        await TriageService(session).resolve(
            case.id, decision={"category_id": target.id}, user_id=owner.id, visible=EVERY_AREA
        )
        rule = (await TriageService(session).list_rules(kind=UNKNOWN_CATEGORY))[0]

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        assert (await product(session, "CAT-0700")).category_id is None
        assert [case.payload["category_text"] for case in await pending_categories(session)] == [
            "Bulones Varios"
        ]

    async def test_the_cuts_still_add_up_to_the_total(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-10: «sin rubro» counts, so a revocation cannot lose a product."""
        # Arrange
        await apply(
            session,
            [row("CAT-0800", category="Bulones Varios"), row("CAT-0801", category="SANITARIOS")],
        )
        case = (await pending_categories(session))[0]
        await TriageService(session).resolve(
            case.id,
            decision={"category_id": (await named(session, "Ferretería General")).id},
            user_id=owner.id,
            visible=EVERY_AREA,
        )
        rule = (await TriageService(session).list_rules(kind=UNKNOWN_CATEGORY))[0]

        # Act
        await TriageService(session).revoke_rule(rule.id, user_id=owner.id)

        # Assert
        listing = await CatalogService(session).list_categories()
        assert (
            sum(item.product_count for item in listing.items) + listing.unclassified_count
            == listing.total_products
        )


class TestTheQueueOfProductsWithoutARubro:
    """H2 and H3: what has no category at all, and what the system proposes."""

    async def test_a_known_subcategory_proposes_its_rubro(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-14: derived from what is already classified, never from a fixed table."""
        # Arrange — one classified product teaches the subcategory.
        await apply(
            session,
            [
                row("CAT-0900", category="SANITARIOS", subcategory="Griferia"),
                row("CAT-0901", category=None, subcategory="Griferia"),
            ],
        )

        # Act
        queue = await CatalogService(session).unclassified()

        # Assert
        waiting = next(item for item in queue.items if item.code == "CAT-0901")
        assert waiting.proposed_category_id == (await named(session, "Sanitarios")).id
        assert waiting.proposed_category_name == "Sanitarios"

    async def test_a_subcategory_that_points_at_two_rubros_proposes_nothing(
        self, session: AsyncSession
    ) -> None:
        """RF-17: «conocida» means one rubro. Breaking a tie would be deciding."""
        # Arrange
        await apply(
            session,
            [
                row("CAT-1000", category="SANITARIOS", subcategory="Mixta"),
                row("CAT-1001", category="HERRAMIENTAS", subcategory="Mixta"),
                row("CAT-1002", category=None, subcategory="Mixta"),
            ],
        )

        # Act
        queue = await CatalogService(session).unclassified()

        # Assert
        waiting = next(item for item in queue.items if item.code == "CAT-1002")
        assert waiting.proposed_category_id is None

    async def test_a_proposal_is_not_an_assignment(self, session: AsyncSession) -> None:
        """RF-16: until somebody confirms, the product **is** «sin rubro»."""
        # Arrange
        await apply(
            session,
            [
                row("CAT-1100", category="SANITARIOS", subcategory="Bachas"),
                row("CAT-1101", category=None, subcategory="Bachas"),
            ],
        )

        # Assert
        assert (await product(session, "CAT-1101")).category_id is None
        assert any(
            item.code == "CAT-1101" for item in (await CatalogService(session).unclassified()).items
        )

    async def test_confirming_takes_it_out_of_the_queue_and_says_who(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-18, RF-19: who decided and when, and it stops being listed."""
        # Arrange
        await apply(session, [row("CAT-1200", category=None, subcategory="Sueltos")])
        waiting = await product(session, "CAT-1200")
        target = await named(session, "Instrumental")

        # Act
        await CatalogService(session).set_product_category(
            waiting.id, category_id=target.id, actor_user_id=owner.id
        )

        # Assert
        classified = await product(session, "CAT-1200")
        assert classified.category_id == target.id
        assert classified.classified_by_user_id == owner.id
        assert classified.classified_at is not None
        assert not any(
            item.code == "CAT-1200" for item in (await CatalogService(session).unclassified()).items
        )


class TestKeepingTheRubroList:
    """H1 from the maintenance side: add, rename, and refuse to delete in use."""

    async def test_a_rubro_in_use_is_not_deleted_and_says_why(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-07: refused in the service, so the platform can give a reason."""
        # Arrange
        await apply(session, [row("CAT-1300", category="SANITARIOS")])
        in_use = await named(session, "Sanitarios")

        # Act / Assert
        with pytest.raises(ConflictError) as refused:
            await CatalogService(session).delete_category(in_use.id, actor_user_id=owner.id)
        assert refused.value.details["products"] == 1

    async def test_two_rubros_cannot_share_a_name(self, session: AsyncSession, owner: User) -> None:
        """A duplicate is a loading mistake, not a case of the business (RF-05)."""
        # Act / Assert
        with pytest.raises(ConflictError):
            await CatalogService(session).create_category(name="sanitarios", actor_user_id=owner.id)

    async def test_a_rubro_can_be_added_and_renamed(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-05, RF-06."""
        # Act
        created = await CatalogService(session).create_category(
            name="Jardinería", actor_user_id=owner.id
        )
        renamed = await CatalogService(session).rename_category(
            created.id, name="Parquización", actor_user_id=owner.id
        )

        # Assert
        assert renamed.name == "Parquización"
        assert any(
            item.name == "Parquización"
            for item in (await CatalogService(session).list_categories()).items
        )


class TestHowManyAreWaitingOnAReview:
    """RF-26, the requirement that had neither a line built nor a test.

    «Sin rubro» and «pendiente de revisión» are two different numbers over the
    same products, and the screen shows both because they are emptied in two
    different places: what arrived with no category at all is classified by
    hand (H2), and what arrived written in a way nobody decided about waits for
    a decision in the queue (H4). Counting them as one would say the review
    queue holds work it does not have.
    """

    async def test_the_count_is_what_the_queue_has_open(self, session: AsyncSession) -> None:
        """The three products behind the one open case, and the one that is not."""
        # Arrange
        before = await CatalogService(session).list_categories()

        # Act — three products with the same unknown written form, and a
        # fourth that came with no category at all.
        await apply(
            session,
            [row(f"CAT-06{index:02d}", category="Bulones Varios") for index in range(3)]
            + [row("CAT-0610", category=None)],
        )

        # Assert — all four are «sin rubro»; only the three that opened the
        # case are pending a review.
        listing = await CatalogService(session).list_categories()
        assert listing.unclassified_count == before.unclassified_count + 4
        assert listing.pending_review_count == before.pending_review_count + 3
        assert len(await pending_categories(session)) == 1

    async def test_deciding_the_written_form_empties_it(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Resolving the case takes its products out of the count, in one move."""
        # Arrange
        before = await CatalogService(session).list_categories()
        await apply(
            session, [row(f"CAT-06{index:02d}", category="Bulones Varios") for index in (3, 4)]
        )
        case = (await pending_categories(session))[0]
        target = await named(session, "Ferretería General")

        # Act
        await TriageService(session).resolve(
            case.id, decision={"category_id": target.id}, user_id=owner.id, visible=EVERY_AREA
        )

        # Assert — and the products left «sin rubro» too, because they got
        # their rubro: the two counts move together here, and only here.
        listing = await CatalogService(session).list_categories()
        assert listing.pending_review_count == before.pending_review_count
        assert listing.unclassified_count == before.unclassified_count


class TestADecisionThatCannotBeApplied:
    """Article II from the side nobody was watching: the case that resolves into nothing.

    `decision` is a free dict from the route, and every one of these used to
    return in silence **after** `triage` had marked the case RESOLVED and was
    about to commit: the question left the queue, no equivalence was written,
    no product was classified, and no exception was filed. Refusing aborts that
    transaction, which is the only thing that keeps the question.
    """

    async def _a_case(self, session: AsyncSession) -> int:
        """One open case over a written form nobody has decided about.

        The **id**, not the row: every test here rolls the refused decision
        back, and a rollback expires every object the session holds — reading
        an attribute off one afterwards is IO where no `await` can happen.
        """
        await apply(session, [row("CAT-0700", category="Bulones Varios")])
        # Committed on purpose: the rollback each test runs has to undo the
        # refused decision and nothing else. Without this it would also undo
        # the case, and every assertion here would pass over an empty queue.
        await session.commit()
        return (await pending_categories(session))[0].id

    async def test_a_rubro_that_does_not_exist_does_not_resolve_the_case(
        self, session: AsyncSession, owner: User
    ) -> None:
        """The decision names rubro 9999, and the case stays where it was."""
        # Arrange
        case_id = await self._a_case(session)

        # Act
        with pytest.raises(NotFoundError):
            await TriageService(session).resolve(
                case_id, decision={"category_id": 9999}, user_id=owner.id, visible=EVERY_AREA
            )
        await session.rollback()

        # Assert — still pending, and the product still waiting for it.
        assert [open_case.id for open_case in await pending_categories(session)] == [case_id]
        assert (await product(session, "CAT-0700")).category_id is None

    async def test_a_decision_that_names_no_rubro_is_refused(
        self, session: AsyncSession, owner: User
    ) -> None:
        """A decision with nothing in it used to resolve the case and do nothing."""
        # Arrange
        case_id = await self._a_case(session)

        # Act
        with pytest.raises(ValidationError):
            await TriageService(session).resolve(
                case_id, decision={"remember": True}, user_id=owner.id, visible=EVERY_AREA
            )
        await session.rollback()

        # Assert
        assert [open_case.id for open_case in await pending_categories(session)] == [case_id]

    async def test_a_rubro_that_is_not_a_number_is_refused(
        self, session: AsyncSession, owner: User
    ) -> None:
        """`decision` is a free dict, so «Ferretería» arrives here as a string."""
        # Arrange
        case_id = await self._a_case(session)

        # Act
        with pytest.raises(ValidationError):
            await TriageService(session).resolve(
                case_id,
                decision={"category_id": "Ferretería"},
                user_id=owner.id,
                visible=EVERY_AREA,
            )
        await session.rollback()

        # Assert
        assert [open_case.id for open_case in await pending_categories(session)] == [case_id]

    async def test_the_equivalence_is_not_written_either(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Nothing half-applied: no alias for a decision that was refused."""
        # Arrange
        case_id = await self._a_case(session)

        # Act
        with pytest.raises(NotFoundError):
            await TriageService(session).resolve(
                case_id, decision={"category_id": 9999}, user_id=owner.id, visible=EVERY_AREA
            )
        await session.rollback()

        # Assert
        aliases = (
            (
                await session.execute(
                    select(CategoryAlias).where(CategoryAlias.text_normalized == "bulones varios")
                )
            )
            .scalars()
            .all()
        )
        assert not aliases


class TestDecidingOneFromTheScreen:
    """The half of H4 the service-level tests never touched: the round trip.

    RF-24 and RF-25 were green because every test resolved the case by calling
    `TriageService` — the half that was built. What a person does is a request:
    open the queue, read the written form the product arrived with (RF-23),
    name a rubro, and see the count of what is pending come down (RF-26). Each
    of those is a route, and none of them was exercised.

    It runs as **compras**, which is the 010 talking: the rubros are maintained
    by whoever buys, so the person who meets this case is Marcela.
    """

    async def test_a_written_form_is_decided_and_applied_over_http(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """From the unknown written form to the classified products, by request only."""
        # Arrange — two products of the same list arrive written in a way the
        # signed table does not have.
        await apply(
            session,
            [
                row("CAT-0800", category="Bulones Varios"),
                row("CAT-0801", category="Bulones Varios"),
            ],
        )
        await session.commit()

        # Act — the queue shows one case, and it says how the category arrived
        # written (RF-23), which is the whole basis for deciding.
        queue = await purchasing_client.get(
            f"{API_PREFIX}/triage/cases", params={"kind": UNKNOWN_CATEGORY}
        )
        assert queue.status_code == 200
        case = queue.json()["items"][0]
        assert case["payload"]["category_text"] == "Bulones Varios"

        listing = await purchasing_client.get(f"{API_PREFIX}/categories")
        assert listing.json()["pending_review_count"] == 2
        rubro = next(
            item for item in listing.json()["items"] if item["name"] == "Ferretería General"
        )

        decided = await purchasing_client.post(
            f"{API_PREFIX}/triage/cases/{case['id']}/resolution",
            json={"decision": {"category_id": rubro["id"]}, "remember": True},
        )

        # Assert — the case is closed, both products carry the rubro, and the
        # screen that asked the question stops asking it.
        assert decided.status_code == 200
        after = (await purchasing_client.get(f"{API_PREFIX}/categories")).json()
        assert after["pending_review_count"] == 0
        assert next(item for item in after["items"] if item["id"] == rubro["id"])["aliases"]
        assert (await product(session, "CAT-0800")).category_id == rubro["id"]
        assert (await product(session, "CAT-0801")).category_id == rubro["id"]

    async def test_a_decision_that_names_no_rubro_is_refused_over_http(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """The silent resolution, from the door it can actually be reached through.

        `decision` is a free dict on the way in, so the empty one is a request
        anybody can send. It used to answer 200 over a case that left the queue
        having done nothing.
        """
        # Arrange
        await apply(session, [row("CAT-0810", category="Bulones Varios")])
        await session.commit()
        queue = await purchasing_client.get(
            f"{API_PREFIX}/triage/cases", params={"kind": UNKNOWN_CATEGORY}
        )
        case_id = queue.json()["items"][0]["id"]

        # Act
        refused = await purchasing_client.post(
            f"{API_PREFIX}/triage/cases/{case_id}/resolution",
            json={"decision": {}, "remember": True},
        )

        # Assert — refused, and the question is still there to be answered.
        assert refused.status_code == 422
        # The suite shares one session between the test and the request, so the
        # abort that closing a real request performs has to be asked for here:
        # without it the case would still carry the RESOLVED the service set
        # before the refusal, which is memory, not what the database holds.
        await session.rollback()
        still_open = await purchasing_client.get(
            f"{API_PREFIX}/triage/cases", params={"kind": UNKNOWN_CATEGORY}
        )
        assert [item["id"] for item in still_open.json()["items"]] == [case_id]
