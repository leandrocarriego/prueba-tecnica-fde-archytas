"""No date is formatted outside `lib/time`.

A locale sets the format, not the timezone. `toLocaleString('es-AR')` renders
an instant in **the runtime's** zone, and the frontend container has no `TZ`:
the prices screen said `29/8/2026, 09:51:31` for an update that happened at
18:51 in the shop.

The three hours are the visible half. The other half is that a Server Component
rendered UTC while the browser would hydrate the same instant in the visitor's
zone — from Tokyo, the same value read `30/8/2026, 06:51:31`, a different day.
Two renders of one markup that disagree is a hydration mismatch waiting for the
first user outside Argentina.

So every formatter lives in `frontend/lib/time.ts`, which pins the zone once.
The rule is not "remember to pass timeZone": it is that nothing else formats a
date at all, which is the version a test can check.

Why a Python test for TypeScript: the frontend has no test runner, and the same
reasoning as `test_auth_pages.py` applies. If a frontend suite ever exists, this
belongs there.
"""

import re
from pathlib import Path

import pytest

import app

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[2]
FRONTEND = REPOSITORY_ROOT / "frontend"
SEARCHED = ("app", "components", "lib")

# The one file allowed to know how a date is written.
TIME = FRONTEND / "lib" / "time.ts"

# `toLocaleString`, `toLocaleDateString`, `toLocaleTimeString`, and building a
# formatter by hand. Every one of them takes its zone from the runtime unless
# told otherwise, and being told otherwise is exactly what gets forgotten.
FORMATS_A_DATE = re.compile(r"toLocale(?:Date|Time)?String\s*\(|new Intl\.DateTimeFormat\s*\(")


def sources() -> list[Path]:
    """Every TypeScript source of the frontend, minus its dependencies."""
    return sorted(
        path
        for directory in SEARCHED
        for path in (FRONTEND / directory).rglob("*.ts*")
        if "node_modules" not in path.parts and ".next" not in path.parts
    )


@pytest.mark.unit
class TestDatesAreWrittenInOnePlace:
    """One timezone, pinned once, for a business that only has one."""

    def test_there_are_sources_to_check(self) -> None:
        """A moved directory must not quietly pass this file."""
        assert sources(), f"no .ts/.tsx under {FRONTEND}"

    def test_the_one_place_exists_and_pins_the_zone(self) -> None:
        """The exemption is only worth granting because this is what is in it."""
        assert TIME.exists(), f"{TIME} is where the timezone lives"
        source = TIME.read_text(encoding="utf-8")
        assert "America/Argentina/Buenos_Aires" in source
        assert "hour12: false" in source, "12-hour is how 21:51 becomes an ambiguous 09:51"

    def test_nothing_else_formats_a_date(self) -> None:
        """Anywhere else, the zone is whatever the process happens to be in."""
        offenders = [
            f"{path.relative_to(FRONTEND)}:{number}"
            for path in sources()
            if path != TIME
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if FORMATS_A_DATE.search(line)
        ]
        assert not offenders, (
            "these format a date outside lib/time, so they render in whatever "
            f"timezone the runtime is in: {', '.join(offenders)}"
        )
