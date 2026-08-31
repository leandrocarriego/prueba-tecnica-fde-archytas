"""The permission matrix, checked against the spec instead of against itself.

The expected table below is **transcribed from `spec.md`**, not imported from
`app`. That is the whole point: a test that read the matrix out of the module
it is testing would agree with any mistake the module makes, including one that
opens a section to somebody the client said should never see it.

Sources, requirement by requirement: RF-08 the owner reaches everything · RF-09
purchasing sees no sales and no dashboard · RF-10 sales sees no suppliers, no
purchase invoices and no payments · RF-11 the three consult prices · RF-34 sales
consults the calendar and does not edit it · RF-35 only the owner and purchasing
act on prices · RF-24 and RF-31 the access screens are the owner's alone.
"""

import pytest

from app.modules.identity.permissions import MATRIX, Level, Section, level_for, permissions_for

OWNER, PURCHASING, SALES = "OWNER", "PURCHASING", "SALES"

# section -> role -> level, as the signed spec describes it.
EXPECTED: dict[str, dict[str, Level]] = {
    "PRICES": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.READ},
    "CALENDAR": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.READ},
    "SUPPLIERS": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.NONE},
    "PURCHASE_INVOICES": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.NONE},
    "PAYMENTS": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.NONE},
    "PURCHASE_ORDERS": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.NONE},
    "RECEIPTS": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.NONE},
    "SUPPLIER_MESSAGES": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.NONE},
    "SALES": {OWNER: Level.WRITE, PURCHASING: Level.NONE, SALES: Level.WRITE},
    "DASHBOARD": {OWNER: Level.READ, PURCHASING: Level.NONE, SALES: Level.READ},
    "STOCK": {OWNER: Level.WRITE, PURCHASING: Level.NONE, SALES: Level.WRITE},
    # La 010 los movió a compras: el rubro es la categoría con la que se compra.
    # Ventas conserva la consulta, como con los precios de lista.
    "PRODUCT_CATEGORIES": {OWNER: Level.WRITE, PURCHASING: Level.WRITE, SALES: Level.READ},
    "PRODUCT_CATALOG": {OWNER: Level.WRITE, PURCHASING: Level.NONE, SALES: Level.WRITE},
    "ACCESS_ADMIN": {OWNER: Level.WRITE, PURCHASING: Level.NONE, SALES: Level.NONE},
    "ACCESS_LOG": {OWNER: Level.READ, PURCHASING: Level.NONE, SALES: Level.NONE},
    "SYSTEM_PARAMETERS": {OWNER: Level.WRITE, PURCHASING: Level.NONE, SALES: Level.NONE},
    # Undoing a manual correction is the owner's alone, whatever section the
    # datum belongs to (003, RF-30). Correcting one is authorised by that
    # section instead, which is why this is not the same row as PRODUCT_CATALOG.
    "MANUAL_CORRECTIONS": {OWNER: Level.WRITE, PURCHASING: Level.NONE, SALES: Level.NONE},
}

EVERY_CELL = [
    (section, role, level) for section, roles in EXPECTED.items() for role, level in roles.items()
]


@pytest.mark.unit
class TestTheMatrixMatchesTheSpec:
    """Every cell, one at a time, so a failure names the one that moved."""

    @pytest.mark.parametrize(
        ("section", "role", "level"),
        EVERY_CELL,
        ids=[f"{section}-{role}" for section, role, _ in EVERY_CELL],
    )
    def test_a_role_reaches_exactly_as_far_as_the_spec_says(
        self, section: str, role: str, level: Level
    ) -> None:
        """48 cells: 16 sections by 3 roles."""
        assert level_for(role, Section(section)) is level

    def test_no_section_is_missing_from_the_matrix(self) -> None:
        """A section added without deciding its permission has to fail here.

        Not merely default to nothing: defaulting is what makes a forgotten
        decision look like a decision.
        """
        assert {section.value for section in Section} == set(EXPECTED)

    def test_every_section_declares_all_three_roles(self) -> None:
        """A half-filled row is a section that admits by omission."""
        incomplete = {
            section.value
            for section, roles in MATRIX.items()
            if set(roles) != {OWNER, PURCHASING, SALES}
        }
        assert not incomplete


@pytest.mark.unit
class TestLevels:
    """The order between levels is the feature, not a detail."""

    def test_writing_implies_reading(self) -> None:
        """`require_section(x, READ)` has to admit whoever holds WRITE."""
        assert Level.WRITE > Level.READ > Level.NONE

    def test_an_unknown_role_reaches_nothing(self) -> None:
        """A role that is not one of the three is not a role."""
        assert level_for("SUPERADMIN", Section.PRICES) is Level.NONE

    def test_the_map_of_a_role_covers_every_section(self) -> None:
        """It is what draws the menu, so a gap would hide a section by accident."""
        assert set(permissions_for(SALES)) == set(Section)


@pytest.mark.unit
class TestWhatTheClientAskedFor:
    """The four sentences the client said out loud, as assertions."""

    def test_marcela_does_not_see_the_sales_dashboard(self) -> None:
        """RF-09: *"no quiero que Marcela ande viendo las ventas"*."""
        assert level_for(PURCHASING, Section.SALES) is Level.NONE
        assert level_for(PURCHASING, Section.DASHBOARD) is Level.NONE

    def test_julian_does_not_reach_the_supplier_accounts(self) -> None:
        """RF-10: *"ni que Julián toque las cuentas de los proveedores"*."""
        assert level_for(SALES, Section.SUPPLIERS) is Level.NONE
        assert level_for(SALES, Section.PURCHASE_INVOICES) is Level.NONE
        assert level_for(SALES, Section.PAYMENTS) is Level.NONE

    def test_julian_sees_the_calendar_without_moving_it(self) -> None:
        """RF-34: the pair that the whole two-level design exists for."""
        assert level_for(SALES, Section.CALENDAR) is Level.READ

    def test_the_owner_reaches_every_section(self) -> None:
        """RF-08: *"y que yo sí pueda ver todo"*."""
        assert all(level_for(OWNER, section) is not Level.NONE for section in Section)
