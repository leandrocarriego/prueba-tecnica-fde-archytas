"""Which parts of the business each role reads the history of.

The translation from a role to a set of sections is the only one there is, and
it lives in the one file of `identity` another module may import. `operations`
filters its log with the answer without ever learning that `UserRole` exists.
"""

import pytest

from app.modules.identity.dependencies import visible_sections
from app.modules.identity.models import User, UserRole
from app.shared.sections import BusinessSection


def person(role: UserRole) -> User:
    """A user with nothing but the role. Nothing here touches a database."""
    return User(email="alguien@cordillera.test", name="Alguien", role=role)


@pytest.mark.unit
class TestVisibleSections:
    """RF-18 and RF-19, which are the same rule read from both ends."""

    def test_the_owner_reads_every_section(self) -> None:
        """RF-18: the owner sees the changes of the three people."""
        # Assert
        assert visible_sections(person(UserRole.OWNER)) == frozenset(BusinessSection)

    def test_purchasing_reads_purchasing(self) -> None:
        """RF-19: their section, and not the ones that are not theirs."""
        # Act
        sections = visible_sections(person(UserRole.PURCHASING))

        # Assert
        assert sections == frozenset({BusinessSection.PURCHASING})

    def test_sales_reads_sales(self) -> None:
        """The criterion of RF-19 by name: Julián does not see purchase invoices."""
        # Act
        sections = visible_sections(person(UserRole.SALES))

        # Assert
        assert sections == frozenset({BusinessSection.SALES})
        assert BusinessSection.PURCHASING not in sections

    def test_every_role_has_an_answer(self) -> None:
        """A role added without deciding what it reads would show nothing.

        Empty is the safe end of that mistake — it is the other end, showing
        somebody else's changes, that would be a leak.
        """
        # Assert
        assert all(visible_sections(person(role)) for role in UserRole)
