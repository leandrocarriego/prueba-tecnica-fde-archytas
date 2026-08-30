"""Write down how many tests passed and how much of the code they covered.

The status page shows these two numbers, and a number on a screen is a claim.
The whole risk of this file is that the claim stops being true: a snapshot
written by hand, or committed once and never regenerated, keeps saying 546 while
the suite has 500 — and nobody notices, because a page that lies looks exactly
like a page that does not.

So three rules, in order of how much they matter:

1. **It is measured, never typed.** The numbers come from the artefacts the
   suite itself produced: `coverage.xml` from pytest-cov and a JUnit report from
   pytest.
2. **A red run writes nothing.** A coverage figure from a suite with failures
   describes code that does not work. Better no snapshot than that one.
3. **CI runs this with `--check`.** The committed file has to match what the
   suite just did, so a stale snapshot fails the build instead of reaching the
   page. That check is what makes the other two worth anything.

    uv run python scripts/quality_snapshot.py           # write it
    uv run python scripts/quality_snapshot.py --check   # verify it (CI)
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPOSITORY_ROOT / "backend"

COVERAGE = BACKEND / "coverage.xml"
JUNIT = BACKEND / ".pytest-report.xml"
# Inside the package because the Dockerfile copies `backend/` and the running
# API has to be able to read it. A build artefact that does not ship is not an
# artefact, it is a local file.
SNAPSHOT = BACKEND / "app" / "quality.json"

REGENERATE = "Regeneralo con `make quality` y commiteá el resultado."


class Missing(RuntimeError):
    """An artefact the suite should have produced is not there."""


def _read(path: Path) -> ElementTree.Element:
    if not path.exists():
        raise Missing(f"Falta {path.relative_to(REPOSITORY_ROOT)}: corré `make quality` primero.")
    return ElementTree.parse(path).getroot()


def coverage_percentage() -> float:
    """The share of lines the suite executed, as a percentage."""
    rate = _read(COVERAGE).get("line-rate")
    if rate is None:
        raise Missing("coverage.xml no trae `line-rate`.")
    return round(float(rate) * 100, 2)


def green_tests() -> int:
    """How many tests actually passed.

    Skipped ones are not green: they did not run, and counting them would
    inflate the number precisely when somebody disables a test to get past a
    gate — the one moment this figure should go down.
    """
    root = _read(JUNIT)
    # JUnit nests <testsuite> inside <testsuites>; pytest writes one suite.
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise Missing("El reporte JUnit no tiene ningún <testsuite>.")

    def count(name: str) -> int:
        return int(suite.get(name, "0"))

    failures, errors = count("failures"), count("errors")
    if failures or errors:
        raise Missing(
            f"La suite terminó con {failures} fallos y {errors} errores: "
            "una foto de una corrida en rojo describe código que no funciona."
        )
    return count("tests") - count("skipped")


def measure() -> dict[str, float | int]:
    """What the suite just did."""
    return {"tests": green_tests(), "coverage": coverage_percentage()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verificar que el archivo commiteado coincide con la corrida, sin escribirlo.",
    )
    arguments = parser.parse_args()

    try:
        measured = measure()
    except Missing as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if not arguments.check:
        SNAPSHOT.write_text(json.dumps(measured, indent=2) + "\n", encoding="utf-8")
        print(f"{measured['tests']} tests en verde, {measured['coverage']}% de cobertura.")
        return 0

    if not SNAPSHOT.exists():
        print(f"error: falta {SNAPSHOT.relative_to(REPOSITORY_ROOT)}. {REGENERATE}", file=sys.stderr)
        return 1

    committed = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if committed != measured:
        print(
            "error: la foto commiteada no coincide con lo que hizo la suite.\n"
            f"  commiteado: {committed}\n"
            f"  medido:     {measured}\n"
            f"{REGENERATE}",
            file=sys.stderr,
        )
        return 1

    print(f"La foto coincide: {measured['tests']} tests, {measured['coverage']}%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
