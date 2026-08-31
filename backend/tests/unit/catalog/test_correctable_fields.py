"""What a person may correct on a product, and what they have to say to do it.

Pure rules, so they are checked without a database: which fields exist, where
each one lives, what a value has to be to land in a column, and that a
correction without a legal reason is refused before anything is written.
"""

import re
from decimal import Decimal
from pathlib import Path

import pytest

import app.modules.catalog.service as catalog_service
from app.modules.catalog.handlers import _price_of
from app.modules.catalog.models import PriceSource, Product, ProductPrice
from app.modules.catalog.service import (
    CORRECTABLE_FIELDS,
    DEFAULT_HIGHLIGHT_THRESHOLD,
    HIGHLIGHT_THRESHOLD_KEY,
    NEGATIVE_AMOUNT,
    PRICE_ENTITY,
    PRODUCT_ENTITY,
    CatalogService,
)
from app.shared.corrections import CorrectionReason
from app.shared.errors import ValidationError
from app.shared.parameters import initial_value


@pytest.mark.unit
class TestWhichFieldsCanBeCorrected:
    """RF-23 asks for any field of a datum the portal brought, not only amounts."""

    def test_a_field_that_is_not_an_amount_can_be_corrected(self) -> None:
        """The description is the case the acceptance criterion is about."""
        # Act
        entity_type, numeric = CatalogService._correctable("description")

        # Assert
        assert entity_type == PRODUCT_ENTITY
        assert numeric is False

    def test_the_price_lives_with_the_price_and_is_a_number(self) -> None:
        # Act
        entity_type, numeric = CatalogService._correctable("price")

        # Assert
        assert entity_type == PRICE_ENTITY
        assert numeric is True

    def test_the_supplier_code_is_not_correctable(self) -> None:
        """It is the key the daily list is matched by.

        "Correcting" it would quietly detach the product from every list that
        follows, which is not a correction but a different product.
        """
        # Assert
        assert "code" not in CORRECTABLE_FIELDS
        with pytest.raises(ValidationError):
            CatalogService._correctable("code")

    def test_an_unknown_field_says_which_ones_there_are(self) -> None:
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            CatalogService._correctable("descuento")

        assert refusal.value.details["correctable"] == sorted(CORRECTABLE_FIELDS)


@pytest.mark.unit
class TestTheReasonIsRequired:
    """RF-11: without a reason from the list, the correction does not happen."""

    def test_a_reason_from_the_list_is_accepted(self) -> None:
        # Assert
        assert (
            CatalogService._reason(CorrectionReason.MISREAD_FROM_DOCUMENT.value)
            is CorrectionReason.MISREAD_FROM_DOCUMENT
        )

    @pytest.mark.parametrize("code", ["", "porque sí", "OTHER_REASON"])
    def test_anything_else_is_refused(self, code: str) -> None:
        # Act / Assert
        with pytest.raises(ValidationError):
            CatalogService._reason(code)


@pytest.mark.unit
class TestWhatGoesIntoJsonb:
    """One pair of columns holds a price, a date and a description."""

    def test_a_decimal_travels_as_text(self) -> None:
        """So it comes back with its cents instead of as a float that lost them."""
        # Assert
        assert CatalogService._jsonable(Decimal("1234.50")) == "1234.50"

    def test_everything_else_travels_as_itself(self) -> None:
        # Assert
        assert CatalogService._jsonable("Tornillo") == "Tornillo"
        assert CatalogService._jsonable(None) is None


@pytest.mark.unit
class TestWhereTheDatumCameFrom:
    """RF-33: a datum loaded entirely by hand offers no way back to the portal.

    The question is asked of the row that holds the value, which is why both
    rows answer it: a description lives on the product and an amount lives on
    its price, and the two can have come from different places.
    """

    def test_a_description_the_list_brought_came_from_the_portal(self) -> None:
        # Arrange
        listed = Product(code="COR-1", description="x", source=PriceSource.PORTAL)

        # Assert
        assert CatalogService._came_from_the_portal(listed) is True

    def test_a_description_a_person_typed_did_not(self) -> None:
        # Arrange
        typed = Product(code="COR-2", description="x", source=PriceSource.SYSTEM)

        # Assert
        assert CatalogService._came_from_the_portal(typed) is False

    def test_a_price_is_asked_about_its_own_row_and_not_the_product(self) -> None:
        """The case the old flag could not tell apart, and RF-33 turns on it.

        A product a person incorporated by hand is re-priced by the next daily
        list: from that morning the amount is the portal's even though the
        product never was.
        """
        # Arrange
        typed = Product(code="COR-3", description="x", source=PriceSource.SYSTEM)
        repriced = ProductPrice(price=Decimal("1000"), source=PriceSource.PORTAL)

        # Assert
        assert CatalogService._came_from_the_portal(typed) is False
        assert CatalogService._came_from_the_portal(repriced) is True


@pytest.mark.unit
class TestWhatCountsAsAnAmount:
    """RF-23 lets a person correct a price; it does not let them write a hole.

    The value goes straight into `core.product_price.price` and into the
    correction that keeps it, so what is refused here is refused before any
    column holds it.
    """

    def test_an_amount_is_read_with_its_cents(self) -> None:
        # Act / Assert
        assert CatalogService._as_number("1234.50", "price") == Decimal("1234.50")

    def test_a_text_that_is_no_number_is_refused(self) -> None:
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            CatalogService._as_number("mil quinientos", "price")

        assert refusal.value.message == "«price» tiene que ser un número."

    @pytest.mark.parametrize("value", ["nan", "snan", "-nan", "inf", "-Infinity"])
    def test_a_value_that_is_not_finite_is_refused_like_any_other(self, value: str) -> None:
        """No spelling of "not a number" is a price, and no infinity either.

        A NaN in the column is the expensive one: it is equal to nothing, not
        even to itself, so every list that follows contradicts the correction
        and the owner is told about the same conflict every morning, forever
        (RF-28).
        """
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            CatalogService._as_number(value, "price")

        # The refusal has to be *this* one and not some later accident: the
        # message is what tells the person what to type instead.
        assert refusal.value.message == "«price» tiene que ser un número."
        assert refusal.value.details["field"] == "price"

    @pytest.mark.parametrize("value", ["-1", "-0.01", -1500])
    def test_an_amount_below_zero_is_refused_as_the_daily_list_already_is(
        self, value: str | int
    ) -> None:
        """The same rule from the other door.

        `ingestion` quarantines a row whose price is negative instead of
        writing it; a correction reaches the same column, so it cannot be the
        way that number gets in by hand.
        """
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            CatalogService._as_number(value, "price")

        assert refusal.value.message == NEGATIVE_AMOUNT

    def test_zero_is_a_price_and_is_accepted(self) -> None:
        """Free of charge is a number the portal may report; below zero is not."""
        # Act / Assert
        assert CatalogService._as_number("0", "price") == Decimal("0")


@pytest.mark.unit
class TestWhereTheStartingThresholdComesFrom:
    """A parameter nobody has changed still has a value (RF-04, RF-20 of 001).

    Which value is declared once, in the catalog of business parameters, and
    read from there. A copy in this module would be a second answer to the same
    question, and the day somebody moved the catalog the installation nobody
    configured would go on highlighting by the old one.
    """

    def test_it_is_read_from_the_catalog_and_not_written_here(self) -> None:
        """Read from the source, not compared against it.

        The obvious test — `initial_value(KEY) == DEFAULT_HIGHLIGHT_THRESHOLD` —
        cannot fail: it is the definition of the constant restated, so putting
        the literal `Decimal("10")` back would leave it green, and that literal
        is the whole regression this guards against. The constant is computed
        once at import, so no fixture can move the catalog underneath it either.

        What is left is to read the line that defines it, which is the shape of
        the question anyway: *is the value written here, or asked for?*
        """
        # Arrange
        source = Path(catalog_service.__file__).read_text(encoding="utf-8")

        # Act
        defined = re.search(r"^DEFAULT_HIGHLIGHT_THRESHOLD\s*=\s*(?P<value>.+)$", source, re.M)

        # Assert
        assert defined is not None, (
            "DEFAULT_HIGHLIGHT_THRESHOLD is no longer defined at the top level of "
            "catalog/service.py. If it moved, this rule moved with it."
        )
        assert "initial_value" in defined["value"], (
            f"DEFAULT_HIGHLIGHT_THRESHOLD is written as `{defined['value'].strip()}` instead "
            f"of being read from the catalog with `initial_value({HIGHLIGHT_THRESHOLD_KEY!r})`. "
            "A second copy is a second answer to the same question, and the day the "
            "catalog moves, the installation nobody configured keeps highlighting by the "
            "old number."
        )
        # And that asking for it still yields something usable as an amount.
        assert Decimal(str(initial_value(HIGHLIGHT_THRESHOLD_KEY))) == DEFAULT_HIGHLIGHT_THRESHOLD


@pytest.mark.unit
class TestThePriceSomebodyTypedResolvingACase:
    """The third door into the same column, and the one nobody was watching.

    A person resolving a case from the review queue types an amount, and it
    reaches `core.product_price.price` through `_price_of` — not through
    `CatalogService._as_number`, which is the guard everybody remembers. Two
    doors that disagree about what a price is are one door.
    """

    @pytest.mark.parametrize("value", ["nan", "snan", "inf", "-Infinity"])
    def test_a_price_that_is_not_finite_never_reaches_the_column(self, value: str) -> None:
        """And this one is not merely wrong, it is an outage.

        A `NaN` written here is compared against the highlight threshold by the
        next daily list, `Decimal` signals on that comparison, and the batch
        falls over — the whole list, not the row. Article II calls for
        quarantine; a crash is the opposite of it.
        """
        # Act / Assert
        assert _price_of({"price": value}) is None

    @pytest.mark.parametrize("value", ["-1", -1500])
    def test_a_negative_price_never_reaches_it_either(self, value: str | int) -> None:
        """`ingestion` already quarantines a negative price from the daily list.

        Resolving a case by hand must not be the way that number gets in.
        """
        # Act / Assert
        assert _price_of({"price": value}) is None

    def test_the_amount_a_person_actually_typed_gets_through(self) -> None:
        """The guard is a filter, not a wall: zero is a price and so is 1234.50."""
        # Act / Assert
        assert _price_of({"price": "1234.50"}) == Decimal("1234.50")
        assert _price_of({"price": 0}) == Decimal("0")
        assert _price_of({}) is None
