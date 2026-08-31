"""What the screens of 003 say when the API does not hand them the data.

Why a Python test for TypeScript: the frontend has no test runner, and adding
one to hold three static rules is a bigger change than they deserve — the same
reasoning as `test_auth_pages.py`, `test_dates_have_a_timezone.py` and
`test_manual_actions.py`. If a frontend suite ever exists, this belongs there.

---

**One. A backend that is down is not a permission that is missing.**

`fetchFromApi` answered `null` to a 403, to a timeout and to a 500 alike, and
`/configuracion` read that `null` as "not for you": with the API unreachable
the screen told the owner «Tu acceso no llega a los parámetros del sistema … si
creés que es un error, pedíselo al dueño» — advice nobody can act on, about a
permission that was never missing, addressed to the person reading it.
`/precios/<id>` did the quiet version of the same thing: a failed read took the
correction half of the screen away without a word.

So `readFromApi` says which of the three it was, and a screen that renders a
refusal has to read it. `fetchFromApi` stays for the screens that have one
answer for every empty outcome, and is defined as `readFromApi` with the reason
dropped — one request path, so a screen that later needs the reason changes
which reader it calls and nothing else.

**Two. The correction is offered to whoever the route would admit.**

`GET /operations/corrections/reasons` is open to every authenticated role,
because it is what validates a `reason_code`. `POST
/catalog/products/{id}/corrections` demands `PRODUCT_CATALOG` in writing, which
purchasing does not have. Opening the correction form on the strength of the
first meant purchasing reached a product, saw «Corregir», pressed it and got a
403 — the route was right and the screen was lying.

The section and the level are not written down here: they are read from
`MANUAL_ACTIONS`, where the very same action already declares them for the
actions screen (`test_manual_actions.py`). Two copies of a rule are one rule
and one bug, so the detail screen is checked against the registry rather than
against a second opinion.

**Three. A page of the log says how much of the log it is.**

The history is append-only and grows forever. Showing fifty rows and nothing
else leaves whoever filtered and did not find what they were looking for unable
to tell "it did not happen" from "it is on row fifty-one" — so the answer's
`total` and `skip` are read, not thrown away with the envelope.
"""

import re
from pathlib import Path

import pytest

import app
from app.modules.identity.permissions import Section

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[2]
FRONTEND = REPOSITORY_ROOT / "frontend"
READER = FRONTEND / "lib" / "api" / "server.ts"
REGISTRY = FRONTEND / "lib" / "operations" / "actions.ts"
PRIVATE_PAGES = FRONTEND / "app" / "(private)"

# The screens 003 owns. Other features have screens of their own that read the
# API the same way; widening this list is their review, not this one.
SCREENS = {
    "configuracion": PRIVATE_PAGES / "configuracion" / "page.tsx",
    "historial": PRIVATE_PAGES / "historial" / "page.tsx",
    "precios/[productId]": PRIVATE_PAGES / "precios" / "[productId]" / "page.tsx",
    # Las seis de la 004, agregadas por el `/review-feature` de esa feature.
    # Las tres de arriba eran las de la 003, y la regla que fijaban dejaba
    # afuera a todas las demás: las seis de facturas y proveedores contestaban
    # `<NoPermission>` a un 403, a un timeout y a un 500 por igual, que es el
    # mismo defecto que este archivo existe para no repetir. Una lista que sólo
    # cubre la feature que la escribió es una regla que caduca en la siguiente.
    "facturas": PRIVATE_PAGES / "facturas" / "page.tsx",
    "facturas/[invoiceId]": PRIVATE_PAGES / "facturas" / "[invoiceId]" / "page.tsx",
    "facturas/revision": PRIVATE_PAGES / "facturas" / "revision" / "page.tsx",
    "proveedores": PRIVATE_PAGES / "proveedores" / "page.tsx",
    "proveedores/[supplierId]": PRIVATE_PAGES / "proveedores" / "[supplierId]" / "page.tsx",
    "proveedores/grafias": PRIVATE_PAGES / "proveedores" / "grafias" / "page.tsx",
}
HISTORY = SCREENS["historial"]
PRODUCT = SCREENS["precios/[productId]"]

# The reader that says why, and the one that drops the reason.
READS_THE_REASON = re.compile(r"export async function readFromApi\b")
DROPS_THE_REASON = re.compile(r"export async function fetchFromApi\b.*?\n\}", re.DOTALL)
OPENS_A_CONNECTION = re.compile(r"\bawait fetch\(")
# The house sentence for a read that did not come back, in the voice
# `/historial` already uses.
SAYS_IT_FAILED = re.compile(r"No pudimos traer")
RENDERS_A_REFUSAL = re.compile(r"<NoPermission\b")
READS_A_REFUSAL = re.compile(r"failure === 'unauthorized'")

# `id: 'correct-product'` and its two fields, read out of the registry's entry.
CORRECT_PRODUCT = re.compile(r"\{[^{}]*\bid:\s*'correct-product'[^{}]*\}", re.DOTALL)
SECTION_FIELD = re.compile(r"\bsection:\s*'(?P<value>[^']+)'")
WRITES_FIELD = re.compile(r"\bwrites:\s*(?P<value>true|false)")

# The gate that was there, and the one that was missing: a section opened on
# the strength of the reasons list alone.
OFFERED_ON_THE_REASONS = re.compile(r"\{\s*reasons\s*!==\s*null\s*&&\s*\(")
OFFERS_THE_FORM = re.compile(r"<CorrectionDialog\b")

# The envelope of a page of the log, and the shape that threw it away.
READS_THE_TOTAL = re.compile(r"\.total\b")
READS_THE_OFFSET = re.compile(r"\.skip\b")
KEEPS_ONLY_THE_ITEMS = re.compile(r"\)\?\.items\b")
ASKS_FOR_AN_OFFSET = re.compile(r"query\.set\('skip'")


def source(page: Path) -> str:
    return page.read_text(encoding="utf-8")


def screens_that_refuse() -> list[str]:
    """The screens of 003 that render a refusal at all.

    Read from the sources instead of listed here: a screen whose endpoint is
    open to every authenticated role has no refusal to render, and saying so in
    a list would go stale the day one of them gains a gate.
    """
    return sorted(name for name, page in SCREENS.items() if RENDERS_A_REFUSAL.search(source(page)))


@pytest.mark.unit
class TestAReadSaysWhyThereIsNoData:
    """The reader the screens below depend on."""

    def test_the_reader_exists(self) -> None:
        """A rename must fail here and not silently pass every test below."""
        assert READS_THE_REASON.search(source(READER)), (
            f"no `readFromApi` in {READER}: nothing left tells a refusal from an outage."
        )

    @pytest.mark.parametrize("outcome", ["unauthorized", "missing", "unavailable"])
    def test_it_names_the_outcome(self, outcome: str) -> None:
        """Three answers, because they are three different sentences on screen."""
        assert f"'{outcome}'" in source(READER), (
            f"`readFromApi` no longer names `{outcome}`: a screen cannot say what it "
            "does not receive."
        )

    def test_there_is_one_way_to_reach_the_api(self) -> None:
        """`fetchFromApi` is `readFromApi` with the reason dropped, not a second path.

        Two request paths drift: the timeout, the header and the cache policy
        get fixed on one of them, and a screen picks the wrong one.
        """
        dropping = DROPS_THE_REASON.search(source(READER))
        assert dropping is not None, f"no `fetchFromApi` in {READER}"
        assert "readFromApi" in dropping.group(0), (
            "`fetchFromApi` opens its own request instead of reading `readFromApi`."
        )
        opened = OPENS_A_CONNECTION.findall(source(READER))
        assert len(opened) == 1, (
            f"{len(opened)} calls to `fetch` in {READER}: one of them is a second path."
        )


@pytest.mark.unit
class TestTheScreensTellARefusalFromAFailure:
    """Each screen of 003, and the two sentences it has to keep apart."""

    @pytest.mark.parametrize("name", sorted(SCREENS))
    def test_the_screen_is_there_to_check(self, name: str) -> None:
        """A move that empties the list must not quietly pass this file."""
        assert SCREENS[name].is_file(), f"{SCREENS[name]} is not there"

    @pytest.mark.parametrize("name", sorted(SCREENS))
    def test_it_reads_the_reason(self, name: str) -> None:
        """`null` is not an answer these three may take."""
        text = source(SCREENS[name])
        assert "readFromApi" in text, (
            f"/{name} does not read `readFromApi`: whatever it renders on an empty "
            "read, it is guessing which of the three happened."
        )
        assert "fetchFromApi" not in text, (
            f"/{name} still calls `fetchFromApi`, which answers `null` to a 403 and "
            "to a timeout alike."
        )

    @pytest.mark.parametrize("name", sorted(SCREENS))
    def test_it_says_so_when_the_read_failed(self, name: str) -> None:
        """In the voice `/historial` already had, not a second one."""
        assert SAYS_IT_FAILED.search(source(SCREENS[name])), (
            f"/{name} has no «No pudimos traer …» for a read that did not come back: "
            "an outage is rendered as something else, and the something else is a lie."
        )

    def test_there_is_a_refusal_to_check(self) -> None:
        """A rewrite that drops every `NoPermission` must not quietly pass the next one."""
        assert screens_that_refuse(), (
            "no screen renders `NoPermission` any more: either the refusal moved "
            "or it stopped being told apart from an outage."
        )

    @pytest.mark.parametrize("name", screens_that_refuse())
    def test_a_refusal_is_decided_by_the_reason(self, name: str) -> None:
        """A screen only says «no tenés permiso» when that is what the API said."""
        assert READS_A_REFUSAL.search(source(SCREENS[name])), (
            f"/{name} renders `NoPermission` without reading `failure === "
            "'unauthorized'`: a backend that is down is announced as a permission "
            "that is missing, and it is the owner who is told to ask the owner."
        )


def registered_correction() -> tuple[str, bool]:
    """The section and level `MANUAL_ACTIONS` declares for `correct-product`."""
    entry = CORRECT_PRODUCT.search(source(REGISTRY))
    assert entry is not None, f"no `correct-product` entry in {REGISTRY}"
    section = SECTION_FIELD.search(entry.group(0))
    writes = WRITES_FIELD.search(entry.group(0))
    assert section is not None and writes is not None, (
        "the `correct-product` entry no longer declares a section and a level."
    )
    return section["value"], writes["value"] == "true"


@pytest.mark.unit
class TestTheCorrectionIsOfferedToWhoeverMayMakeIt:
    """The product screen, against the registry the actions screen already reads."""

    def test_the_registry_still_declares_it(self) -> None:
        """Read here rather than written here, so the two screens cannot disagree."""
        section, writes = registered_correction()
        assert section in {member.value for member in Section}, (
            f"`correct-product` names `{section}`, which is not a section of the business."
        )
        assert writes, (
            "`correct-product` no longer declares that it writes: "
            "`POST /catalog/products/{id}/corrections` demands the level to write."
        )

    def test_the_product_screen_demands_the_same_permission(self) -> None:
        """The gate the actions screen applies, applied where the form actually is."""
        section, writes = registered_correction()
        asking = "canEdit" if writes else "canSee"
        text = source(PRODUCT)
        gate = re.compile(rf"{asking}\(\s*session\.permissions\s*,\s*'{section}'\s*\)")
        assert gate.search(text), (
            f"the product screen does not ask `{asking}(session.permissions, "
            f"'{section}')`: it offers «Corregir» to somebody the route answers 403."
        )
        assert text.index(f"{asking}(session.permissions, '{section}')") < text.index(
            "<CorrectionDialog"
        ), "the permission is read after the form it is supposed to gate."

    def test_the_form_is_not_opened_on_the_reasons_alone(self) -> None:
        """The list of reasons is served to everybody: it authorises nothing.

        It comes from the same place that validates a `reason_code`, which is
        why it is served to every authenticated role — reading it as "this
        session may correct" is reading an answer to a question nobody asked.
        """
        text = source(PRODUCT)
        assert OFFERS_THE_FORM.search(text), "no `CorrectionDialog` left on the product screen"
        assert not OFFERED_ON_THE_REASONS.search(text), (
            "the correction section is opened by `reasons !== null`, which is true "
            "for purchasing too — and the route it leads to is not."
        )


@pytest.mark.unit
class TestThePageOfTheLogSaysHowMuchOfItThereIs:
    """`/historial`, and the fifty rows it used to show without saying so."""

    def test_it_reads_the_whole_answer(self) -> None:
        """`total` and `skip` come with the items and are part of the answer."""
        text = source(HISTORY)
        assert READS_THE_TOTAL.search(text), (
            "/historial does not read `total`: fifty rows on an append-only log, and "
            "no way to tell «no pasó» from «quedó en la fila 51»."
        )
        assert READS_THE_OFFSET.search(text), "/historial does not read `skip`."
        assert not KEEPS_ONLY_THE_ITEMS.search(text), (
            "/historial keeps `.items` and drops the envelope it came in."
        )

    def test_it_can_ask_for_the_next_page(self) -> None:
        """And the offset travels in the address bar, so the page stays a Server Component."""
        text = source(HISTORY)
        assert ASKS_FOR_AN_OFFSET.search(text), (
            "/historial never sends `skip`: there is no way to reach row 51."
        )
        assert text.count("pagina") >= 2, (
            "/historial does not both read and write the page in the query string: "
            "the link to the next page cannot be shared, or does not exist."
        )


# --- Lo que un indicador excluyó se puede ir a ver (RF-26 de 009) -----------
#
# El tablero decía cuántos registros dejó afuera y **no dejaba llegar a ellos**:
# el enlace aparecía sólo si había apartadas, y las que el sistema unificó solo
# no estaban en ninguna cola —`held_groups()` devuelve `HELD`, y ésas son
# `DISCARDED`—. Así que la mitad de lo excluido no se veía desde ningún lado, y
# RF-26 pide exactamente lo contrario.
#
# Va acá y no en el frontend por el mismo motivo que todo lo de este archivo: no
# hay runner de tests en el frontend, y estas dos reglas son estáticas.

DASHBOARD = FRONTEND / "app" / "(private)" / "tablero" / "page.tsx"
SALES_REVIEW = FRONTEND / "app" / "(private)" / "ventas" / "revision" / "page.tsx"


@pytest.mark.unit
class TestTheExcludedRecordsCanBeReached:
    """RF-26: desde el número excluido se llega a los registros que excluyó."""

    def test_the_excluded_count_is_a_link(self) -> None:
        """Un número que dice «excluí doce» y no lleva a los doce no se puede verificar."""
        assert "/ventas/revision" in source(DASHBOARD), (
            f"{DASHBOARD} ya no enlaza la revisión: el número excluido vuelve a ser "
            "un dato que nadie puede ir a comprobar (RF-26)."
        )

    def test_the_review_screen_also_asks_for_what_was_discarded(self) -> None:
        """Lo apartado espera una decisión; lo descartado, no — y las dos cosas se excluyen.

        Si esta lectura desaparece, la pantalla vuelve a mostrar sólo la mitad de
        lo que los indicadores dejaron afuera, y el enlace de arriba lleva a una
        respuesta incompleta sin decirlo.
        """
        assert "state=DISCARDED" in source(SALES_REVIEW), (
            f"{SALES_REVIEW} dejó de pedir las descartadas: la mitad de lo que el "
            "tablero excluye vuelve a no verse desde ninguna pantalla (RF-26)."
        )
