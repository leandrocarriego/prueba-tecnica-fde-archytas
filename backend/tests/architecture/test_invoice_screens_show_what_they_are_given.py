"""Las pantallas de la 004 muestran lo que la API les manda.

**Por qué existe este archivo.** El `/converge` de la 004 encontró seis veces el
mismo defecto, y las seis habían pasado un review: el backend guardaba el dato,
lo exponía en la respuesta, el plan daba el requisito por cumplido, y **ninguna
pantalla lo renderizaba**. El formato de la factura, las grafías en la ficha del
proveedor, quién resolvió una factura, quién asignó una grafía, el período de los
totales y la corrección del contacto. Cinco de esas seis no necesitaban una línea
de backend.

Es un defecto que no falla: la suite queda verde, el endpoint contesta bien, y
sólo se descubre abriendo el `.tsx`. Un requisito **no está cumplido porque el
backend lo devuelva**, y hasta ahora nada decía eso en voz alta.

Por qué un test de Python sobre TypeScript: el frontend no tiene runner, y
montar uno para sostener seis reglas estáticas es un cambio más grande que las
reglas — el mismo razonamiento de `test_auth_pages.py`,
`test_manual_actions.py` y `test_screen_reads.py`. Si algún día existe una suite
de frontend, esto pertenece ahí.

**Lo que estas reglas NO son.** No prueban que la pantalla se vea bien ni que el
dato sea el correcto: prueban que el campo se lee. Es el piso, no el techo, y es
exactamente el piso que faltaba.
"""

import re
from pathlib import Path

import pytest

import app

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[2]
FRONTEND = REPOSITORY_ROOT / "frontend"
PRIVATE_PAGES = FRONTEND / "app" / "(private)"
COMPONENTS = FRONTEND / "components" / "purchases"

# La pantalla que nombra cada requisito firmado, y lo que tiene que leer de la
# respuesta para cumplirlo. Una pantalla es su página más los componentes que
# rendericen su contenido: `page.tsx` compone y el componente imprime, así que
# leer sólo la página encontraría vacío lo que sí está.
INVOICE_LIST = (COMPONENTS / "InvoiceTable.tsx",)
INVOICE_CARD = (
    PRIVATE_PAGES / "facturas" / "[invoiceId]" / "page.tsx",
    COMPONENTS / "InvoicePanel.tsx",
)
SUPPLIER_CARD = (
    PRIVATE_PAGES / "proveedores" / "[supplierId]" / "page.tsx",
    COMPONENTS / "SupplierContact.tsx",
    COMPONENTS / "SupplierCorrection.tsx",
    COMPONENTS / "SupplierPeriod.tsx",
)
SPELLINGS = (COMPONENTS / "SpellingList.tsx",)
REVIEW_QUEUE = (COMPONENTS / "ReviewQueue.tsx",)


def text_of(paths: tuple[Path, ...]) -> str:
    """Everything the screen is made of, as one string."""
    for path in paths:
        assert path.exists(), f"{path} no existe: la pantalla se movió y esta regla quedó ciega"
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


# Cada fila es un requisito firmado, la pantalla que lo nombra, y la expresión
# que prueba que el dato se lee. `id` es el requisito, para que un fallo diga
# cuál se rompió y no «assert False».
RENDERED: list[tuple[str, tuple[Path, ...], str]] = [
    # RF-05: «la lista distingue a simple vista cuáles llegaron como imagen
    # escaneada». Se busca el campo, no la palabra: la etiqueta se traduce en
    # `labels.ts` y el texto en pantalla no es el nombre de la columna.
    ("RF-05", INVOICE_LIST, r"file_kind"),
    # RF-10: «al abrir un proveedor se ven todas las formas en que llegó escrito
    # su nombre». Vivían sólo en /proveedores/grafias, que es otra pregunta.
    ("RF-10", SUPPLIER_CARD, r"\.aliases"),
    # RF-16: «Marcela corrige el correo de un proveedor desde su ficha». El
    # `PATCH` y la server action existían y ningún componente la importaba.
    ("RF-16", SUPPLIER_CARD, r"correctSupplier"),
    # RF-22: «se pide el año en curso». La API aceptaba el período y la pantalla
    # llamaba a `/totals` sin parámetros.
    ("RF-22", SUPPLIER_CARD, r"since"),
    # RF-23: cuántas quedaron afuera **por estar en revisión**, contado aparte de
    # las que caen fuera del período.
    ("RF-23", SUPPLIER_CARD, r"excluded_in_review"),
    # RF-31: los tres datos de cabecera se confirman o se corrigen desde la cola.
    ("RF-31", REVIEW_QUEUE, r"HEADER_FIELDS"),
    # RF-04: se abre el archivo original.
    ("RF-04", INVOICE_CARD, r"/file"),
    # RF-32: «cada factura resuelta muestra qué se decidió, quién y cuándo».
    ("RF-32", INVOICE_CARD, r"resolved_by_name"),
    # RF-51: «cada una con quién y cuándo». La pantalla decía sólo cuándo.
    ("RF-51", SPELLINGS, r"created_by_name"),
]


@pytest.mark.parametrize(
    ("requirement", "screen", "pattern"),
    RENDERED,
    ids=[requirement for requirement, _, _ in RENDERED],
)
def test_the_screen_reads_what_the_requirement_needs(
    requirement: str, screen: tuple[Path, ...], pattern: str
) -> None:
    """El campo que ese requisito necesita se lee en la pantalla que lo nombra."""
    assert re.search(pattern, text_of(screen)), (
        f"{requirement}: la respuesta trae el dato y la pantalla no lo usa. "
        f"Es el defecto que el converge de la 004 encontró seis veces."
    )


def test_the_register_of_rules_covers_every_screen_of_the_feature() -> None:
    """Una regla que apunta a un archivo que ya no existe no prueba nada.

    `text_of` lo verifica archivo por archivo, así que esto es sólo la otra
    mitad: que ninguna pantalla de la feature quede sin una sola regla. Si
    mañana se agrega una, esta lista es donde se nota.
    """
    covered = {path for _, screen, _ in RENDERED for path in screen}
    for screen in (INVOICE_LIST, INVOICE_CARD, SUPPLIER_CARD, SPELLINGS, REVIEW_QUEUE):
        assert covered & set(screen), f"{screen[0].name} no tiene ninguna regla"
