"""Deriva los dos fixtures del portal que el relevamiento midió y no capturó.

`/mensajes` y `/ventas` no tienen captura: el relevamiento contó lo que hay en
cada una —64 mensajes y 588 ventas, con sus desgloses— pero no se guardó el DOM.
Este script arma dos archivos que **reproducen exactamente esos números** y las
anomalías que la spec de 009 enumera, con la misma estructura de tabla que sí se
capturó en las otras cuatro pantallas (`table.datos`, encabezado en `thead`,
fechas ISO, montos con `$` y separador de miles).

Es el mismo precedente que `price-list-broken-2026-08-28.xlsx`: un fixture
derivado a mano, declarado como tal, para poder afirmar en un test por qué se
apartó cada fila.

**Lo que esto no es.** No es la pantalla del portal. Las columnas son las que se
dedujeron del relevamiento, y el día que alguien capture las de verdad hay que
recapturar y volver a correr los tests de los parsers. Está anotado en el README
de los fixtures.

    uv run python ../scripts/fixtures/derive_portal_fixtures.py
"""

import random
from datetime import date, timedelta
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[2] / "backend" / "tests" / "fixtures" / "portal"

# La semilla fija hace que dos corridas den byte a byte lo mismo: un fixture que
# cambia solo es un fixture que no se puede versionar.
SEED = 20260829

HEAD = (
    "<html><head><meta charset='utf-8'><title>SIGProv — {title}</title></head><body>"
    "<h1>{title}</h1>"
)
TAIL = "</body></html>"

SUPPLIERS = [
    "Aceros Belgrano SA",
    "Cañerias del Litoral SA",
    "Distribuidora Metalica Sur",
    "Electrical Supply Argentina",
    "Ferretera del Norte SRL",
    "Herramientas Cuyo SRL",
    "Insumos Industriales Bahia",
    "Pinturerias Reunidas SA",
]

# Los tres tipos medidos, con sus conteos: 27 + 21 + 16 = 64.
MESSAGE_KINDS = [("Vencimiento proximo", 27), ("Reclamo de pago", 21), ("Stock bajo", 16)]
UNREAD = 30

SUBJECTS = {
    "Vencimiento proximo": "La factura {ref} vence el {when}",
    "Reclamo de pago": "Reclamo por la factura {ref}, impaga",
    "Stock bajo": "Stock bajo de {ref} en su ultimo pedido",
}


def _rows(rows: list[list[str]], headers: list[str]) -> str:
    """Una tabla `datos` con su encabezado, como las que publica el portal."""
    head = "".join(f"<th>{name}</th>" for name in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table class='datos'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def messages_page() -> str:
    """La bandeja: 64 mensajes, 27 de vencimiento, 21 reclamos, 16 de stock, 30 sin leer."""
    random.seed(SEED)
    start = date(2026, 6, 1)
    rows: list[list[str]] = []
    index = 0
    for kind, count in MESSAGE_KINDS:
        for _ in range(count):
            index += 1
            supplier = SUPPLIERS[index % len(SUPPLIERS)]
            reference = f"F-{random.randint(1000, 9999)}"
            when = (start + timedelta(days=index)).isoformat()
            rows.append(
                [
                    f"MSG-{index:04d}",
                    (start + timedelta(days=index % 80)).isoformat(),
                    supplier,
                    kind,
                    SUBJECTS[kind].format(ref=reference, when=when),
                    f"{supplier} informa: {SUBJECTS[kind].format(ref=reference, when=when)}.",
                    "No leido" if index <= UNREAD else "Leido",
                ]
            )
    headers = ["Id", "Fecha", "Remitente", "Tipo", "Asunto", "Mensaje", "Estado"]
    return (
        HEAD.format(title="Bandeja de mensajes")
        + _rows(rows, headers)
        + TAIL
    )


def sales_page() -> str:
    """Las ventas: 588 registros con las anomalías exactas que midió el relevamiento.

    588 filas en total: **17 grupos repetidos comparando el código tal cual y 27
    si primero se normaliza** —6 de ellos con datos en conflicto—, 3 sin fecha,
    3 con una fecha que no existe, 3 sin total, 3 con cantidad negativa, 2 con
    el total inflado diez veces y 1 apuntando a un producto que no existe.

    La diferencia entre 17 y 27 es el punto de RF-10: diez de esas repeticiones
    sólo se ven si el código se compara sin sus diferencias de escritura.
    """
    random.seed(SEED)
    start = date(2023, 1, 5)
    rows: list[list[str]] = []

    def sale(code: str, day: int, product: int, quantity: int, total: int) -> list[str]:
        return [
            code,
            (start + timedelta(days=day)).isoformat(),
            f"COR-{product:04d} - Articulo {product}",
            str(quantity),
            f"${total:,}".replace(",", "."),
        ]

    # 546 ventas limpias y distintas. Con las 27 repetidas y las 15 anómalas de
    # más abajo, el archivo cierra en las 588 filas que midió el relevamiento.
    for index in range(1, 547):
        rows.append(
            sale(
                f"V-{index:05d}",
                index * 2,
                (index % 100) + 1,
                random.randint(1, 40),
                random.randint(12_000, 900_000),
            )
        )

    # 27 repetidas, en dos mitades que existen para separar RF-09 de RF-10:
    # 17 repiten el código **tal cual** —se ven sin normalizar nada— y 10 sólo
    # coinciden después de sacarle al código las diferencias de escritura.
    # De las 27, 6 traen además un dato distinto: son las que necesitan que
    # alguien decida, y las otras 21 se cuentan una sola vez sin preguntar.
    for offset in range(17):
        original = rows[offset]
        repeated = list(original)
        if offset < 3:
            repeated[3] = str(int(original[3]) + 7)
        rows.append(repeated)
    for offset in range(17, 27):
        original = rows[offset]
        variant = list(original)
        variant[0] = f" {original[0].lower().replace('-', '')} "
        if offset < 20:
            variant[3] = str(int(original[3]) + 7)
        rows.append(variant)

    # Las rotas, una anomalía por fila para que un test pueda afirmar el motivo.
    for index in range(3):
        broken = sale(f"V-9{index:04d}", index, 5, 3, 45_000)
        broken[1] = ""
        rows.append(broken)
    for index in range(3):
        broken = sale(f"V-8{index:04d}", index, 5, 3, 45_000)
        broken[1] = "2025-02-31"
        rows.append(broken)
    for index in range(3):
        broken = sale(f"V-7{index:04d}", index, 5, 3, 45_000)
        broken[4] = ""
        rows.append(broken)
    for index in range(3):
        broken = sale(f"V-6{index:04d}", index, 5, -4, 45_000)
        rows.append(broken)
    for index in range(2):
        # El total inflado diez veces: se lee bien y lo aparta el umbral de
        # monto atípico, no el parser.
        rows.append(sale(f"V-5{index:04d}", index, 7, 2, 4_500_000))
    rows.append(sale("V-40000", 10, 999, 1, 61_000))

    headers = ["Codigo", "Fecha", "Producto", "Cantidad", "Total"]
    return HEAD.format(title="Ventas") + _rows(rows, headers) + TAIL


def main() -> None:
    """Escribe los dos archivos, sobrescribiendo lo que hubiera."""
    for name, content in (
        ("messages-page-2026-08-29.html", messages_page()),
        ("sales-page-2026-08-29.html", sales_page()),
    ):
        path = FIXTURES / name
        path.write_text(content, encoding="utf-8")
        print(f"{path.name}: {len(content):,} bytes")


if __name__ == "__main__":
    main()
