"""The way from a datum to its history, and from the history back to the undo.

Two rules of 003 that live entirely in the frontend, and that the converge of
the feature found half-built:

**One. From any datum changed by hand, its history (RF-15).** The log names the
kinds of datum it knows in `lib/operations/audit.ts` — `ENTITIES` — and
`entityHref` says which of them have a screen of their own. Whichever does has
to carry the link *the other way* too: `/historial?entidad=<kind>&id=<id>`.
Prices had it from the first commit and parameters did not, so a value the owner
changed named the log in prose and offered no way into it.

The rule is written over the vocabulary rather than over a list of files, so the
next feature that teaches the log a kind of datum with a screen inherits it.
What it does **not** check is that the link sits on the screen that shows the
datum: it asks the app whether the link exists at all, because which file renders
a row of a page is not something a regular expression should be deciding.

**Two. From the history, the undo (RF-30).** The acceptance criterion of the
signed spec puts it there in as many words — «El dueño deja sin efecto una
corrección desde el historial» — and until this was written the log only linked
away to the screen that had the button. So the table renders the very same
button the product page renders, and the screen asks for the ids behind a gate
that is the matrix's and not a second opinion about who the owner is.

Why a Python test for TypeScript: the frontend has no test runner, and adding
one to hold three static rules is a bigger change than they deserve — the same
reasoning as `test_manual_actions.py`, `test_screen_reads.py` and
`test_auth_pages.py`. If a frontend suite ever exists, this belongs there.
"""

import re
from pathlib import Path

import pytest

import app
from app.modules.identity.models import UserRole
from app.modules.identity.permissions import Level, Section, level_for

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[2]
FRONTEND = REPOSITORY_ROOT / "frontend"
VOCABULARY = FRONTEND / "lib" / "operations" / "audit.ts"
TABLE = FRONTEND / "components" / "operations" / "AuditTable.tsx"
HISTORY = FRONTEND / "app" / "(private)" / "historial" / "page.tsx"
PRODUCT_BUTTON = FRONTEND / "components" / "catalog" / "RevertCorrectionButton.tsx"

# `['catalog.product', 'Producto']` — one line of the map the log reads a kind
# of datum with.
NAMED_KIND = re.compile(r"\[\s*'(?P<kind>[\w.]+)'\s*,\s*'[^']+'\s*\]")
# The kinds `entityHref` answers a screen for: the ones a person can stand on.
HAS_A_SCREEN = re.compile(r"entry\.entity_type === '(?P<kind>[\w.]+)'")
# What the section the screen gates the undo with is called, read from the
# screen rather than assumed, and checked against the enum below.
GATE = re.compile(r"canEdit\(session\.permissions, '(?P<section>[A-Z_]+)'\)")

# Where the frontend may write the link into the log. A page, a component or a
# helper are all fair: the rule is that the way in exists, not who renders it.
SOURCES = sorted(
    path
    for folder in ("app", "components", "lib")
    for path in (FRONTEND / folder).rglob("*.ts*")
    if "node_modules" not in path.parts
)


def source_of(path: Path) -> str:
    """The file, read the way the bundler reads it."""
    return path.read_text(encoding="utf-8")


def named_kinds() -> set[str]:
    """Every kind of datum the log has a word for."""
    block = source_of(VOCABULARY)
    start = block.index("const ENTITIES")
    return {
        match["kind"] for match in NAMED_KIND.finditer(block[start : block.index("\n]", start)])
    }


def kinds_with_a_screen() -> set[str]:
    """The kinds `entityHref` sends somewhere: the data a person can stand on.

    A kind without one is not exempt by oversight — `purchases.supplier` is
    named by the log and has no screen yet — and a link to a page that does not
    exist would be worse than no link at all.
    """
    source = source_of(VOCABULARY)
    start = source.index("export function entityHref")
    return {match["kind"] for match in HAS_A_SCREEN.finditer(source[start:])}


def links_to_the_log() -> set[str]:
    """Every kind of datum some screen sends to the log, wherever it is written."""
    found: set[str] = set()
    for path in SOURCES:
        found.update(re.findall(r"/historial\?entidad=([\w.]+)", source_of(path)))
    return found


class TestFromTheDatumToItsHistory:
    """RF-15, over the vocabulary the log itself declares."""

    def test_the_log_names_the_kinds_this_feature_brought(self) -> None:
        """A guard on the reading above: an empty set would pass everything."""
        assert {"catalog.product", "catalog.product_price", "operations.parameter"} <= named_kinds()

    def test_every_kind_with_a_screen_of_its_own_leads_back_to_the_log(self) -> None:
        """Standing on a datum, its history is a link and not a search."""
        # Arrange
        reachable = kinds_with_a_screen()
        assert reachable, "entityHref stopped naming any kind: the reading below is broken"

        # Act
        linked = links_to_the_log()

        # Assert
        assert reachable <= linked, (
            "these data have a screen and no way from it into the log: "
            f"{sorted(reachable - linked)}"
        )

    def test_a_parameter_is_one_of_them(self) -> None:
        """The gap the converge found, pinned by name so it cannot come back."""
        assert "operations.parameter" in links_to_the_log()


class TestFromTheHistoryToTheUndo:
    """RF-30, whose acceptance criterion names this screen."""

    def test_the_log_renders_the_undo_itself(self) -> None:
        """Not a link to the screen that has the button: the button."""
        assert "<RevertCorrectionButton" in source_of(TABLE)

    def test_it_is_the_same_button_the_product_page_renders(self) -> None:
        """One component, so the rule that governs a manual action keeps holding.

        `test_manual_actions.py` demands that whoever runs a manual action learns
        whether it applied (RF-22), and it discovers the components that import
        an action of 003. A second button written for this screen would be a
        second place for that rule to be forgotten in.
        """
        assert "export function RevertCorrectionButton" in source_of(PRODUCT_BUTTON)
        assert "@/components/catalog/RevertCorrectionButton" in source_of(TABLE)

    def test_the_offer_goes_on_a_line_that_corrected_something(self) -> None:
        """And not on every line about the datum, the reversal's included.

        A datum collects several lines over its life — corrected, undone,
        corrected again — and only one correction stands on it at a time. An
        offer keyed on the datum alone would sit on all three, «Deshizo una
        corrección» included, with the three of them undoing the same row.
        """
        # Act
        table = source_of(TABLE)

        # Assert
        assert "entry.action !== 'CORRECTED'" in table
        # One line per datum: the first seen, which is the newest of a log that
        # arrives newest first.
        assert "decided.has(key)" in table

    def test_the_screen_asks_for_what_it_needs_to_offer_the_undo(self) -> None:
        """The ids come from the route that keeps them, in one question."""
        assert "/catalog/corrections?" in source_of(HISTORY)

    def test_the_gate_it_uses_is_a_section_the_matrix_knows(self) -> None:
        """A section nobody defines reads as `NONE` and hides the offer from everybody."""
        # Act
        gates = {match["section"] for match in GATE.finditer(source_of(HISTORY))}

        # Assert
        assert gates, "the log stopped gating the undo on a section"
        assert gates <= {section.value for section in Section}

    def test_that_section_is_the_owner_s_alone(self) -> None:
        """RF-30 says the owner, and the matrix is what says it in code."""
        # Arrange
        gates = {match["section"] for match in GATE.finditer(source_of(HISTORY))}

        # Act
        reach = {
            role.value: max(level_for(role.value, Section(name)) for name in gates)
            for role in UserRole
        }

        # Assert
        assert reach[UserRole.OWNER.value] >= Level.WRITE
        assert reach[UserRole.PURCHASING.value] is Level.NONE
        assert reach[UserRole.SALES.value] is Level.NONE
