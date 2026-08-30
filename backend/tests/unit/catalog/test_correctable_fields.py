"""What a person may correct on a product, and what they have to say to do it.

Pure rules, so they are checked without a database: which fields exist, where
each one lives, and that a correction without a legal reason is refused before
anything is written.
"""

from decimal import Decimal

import pytest

from app.modules.catalog.models import PriceSource, Product, ProductPrice
from app.modules.catalog.service import (
    CORRECTABLE_FIELDS,
    PRICE_ENTITY,
    PRODUCT_ENTITY,
    CatalogService,
)
from app.shared.corrections import CorrectionReason
from app.shared.errors import ValidationError


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
