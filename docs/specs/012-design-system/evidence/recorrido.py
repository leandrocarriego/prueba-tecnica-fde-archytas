"""Recorrido de la 012 con Playwright: olas 1, 2, 3 y el final.

Se corre contra el stack local (backend nativo en :8000, frontend en :3000) con
el sistema operativo **en modo oscuro** (`color_scheme='dark'`), que es lo que
RF-20 pide probar.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

# Por omisión, el build de producción: es lo que se despliega. El servidor de
# desarrollo agrega instrumentación propia que no existe en lo que ve el
# cliente —mide un componente que redirige y se queja de un tiempo negativo—, y
# un recorrido no debería anotar como defecto algo que el producto no tiene.
BASE = os.environ.get("RECORRIDO_BASE", "http://localhost:3100")
EVIDENCE = Path("/Users/leandrocarriego/Desktop/Archytas/docs/specs/012-design-system/evidence")

PAPEL = "rgb(244, 242, 237)"       # --background
NARANJA = "rgb(194, 75, 21)"       # --brand
AZUL = "rgb(31, 75, 153)"          # --link

OWNER = ("dueno@example.com", "Recorrido012!")
VENTAS = ("ventas@example.com", "Ventas012!")

# Las dieciséis secciones del menú, con la ruta que abre cada una.
SECCIONES = [
    ("Tablero", "/tablero"),
    ("Proveedores", "/proveedores"),
    ("Facturas", "/facturas"),
    ("Órdenes de compra", "/ordenes"),
    ("Calendario", "/calendario"),
    ("Mensajes", "/mensajes"),
    ("Ventas", "/ventas"),
    ("Catálogo y precios", "/precios"),
    ("Rubros", "/rubros"),
    ("Revisar esto", "/revision"),
    ("Acciones", "/acciones"),
    ("Historial", "/historial"),
    ("Accesos", "/accesos"),
    ("Actividad", "/accesos/actividad"),
    ("Parámetros", "/configuracion"),
    ("Salud", "/health"),
]

DECISION = [
    "/revision",
    "/calendario",
    "/facturas/revision",
    "/facturas/incidentes",
    "/ventas/revision",
    "/proveedores/grafias",
    "/rubros/sin-clasificar",
    "/rubros/equivalencias",
    "/acciones",
]

fallos: list[str] = []
notas: list[str] = []


def check(condition: bool, what: str) -> None:
    linea = ("✅ " if condition else "❌ ") + what
    (notas if condition else fallos).append(linea)
    print(linea, flush=True)


def invitacion_nueva(email: str) -> str:
    """Una invitación fresca, con el token en claro.

    La emite la aplicación y sólo guarda su hash —que es lo correcto—, así que
    el recorrido la emite acá para poder abrir  como lo
    abriría la persona invitada. El canal de WhatsApp está apagado en local.
    """
    import asyncio
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from app.database import SessionFactory
    from app.modules.identity import security

    token = security.generate_token()

    async def emitir() -> None:
        async with SessionFactory() as session:
            row = (await session.execute(text("select id from users where email = :e"), {"e": email})).first()
            assert row is not None, email
            await session.execute(
                text("""insert into credential_tokens (user_id, token_hash, purpose, expires_at)
                        values (:u, :h, 'INVITATION', :x)"""),
                {"u": row[0], "h": security.hash_token(token), "x": datetime.now(UTC) + timedelta(hours=1)},
            )
            await session.commit()

    asyncio.run(emitir())
    return token


def login(page: Page, email: str, password: str) -> None:
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click("button[type=submit]")
    # La cookie de sesión la escribe la acción del servidor: esperar «red
    # tranquila» no alcanza, hay que esperar a estar adentro.
    page.wait_for_url(f"{BASE}/tablero", timeout=15000)
    page.wait_for_load_state("networkidle")


def style(page: Page, selector: str, prop: str) -> str:
    return page.eval_on_selector(
        selector, "(el, p) => getComputedStyle(el).getPropertyValue(p)", prop
    )


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(EVIDENCE / name), full_page=False)


def naranjas(page: Page) -> list[str]:
    """El texto de cada control que se dibuja con el naranja de marca."""
    return page.evaluate(
        """() => [...document.querySelectorAll('button, a')]
             .filter(el => getComputedStyle(el).backgroundColor === 'rgb(194, 75, 21)')
             .map(el => el.textContent.trim())"""
    )


# Los verbos con los que la plataforma nombra una acción que **escribe**. El
# azul de dato no puede estar sobre ninguno de éstos (`RF-13`, `UI-06`).
ESCRIBEN = (
    "guardar", "corregir", "eliminar", "borrar", "mover", "confirmar", "resolver",
    "anular", "deshacer", "asignar", "registrar", "dejar sin efecto", "marcar",
    "dar de alta", "actualizar", "revertir", "desactivar", "reactivar", "cerrar el incidente",
    "emitir", "incorporar", "descartar", "definir",
)


def azules_que_actuan(page: Page) -> list[str]:
    """Botones en azul de dato que además **modifican** algo.

    No alcanza con listar todo lo que se dibuja en azul: abrir un día del
    calendario o mostrar más filas no cambia ningún dato, y el azul ahí es
    correcto —es información, no decisión—. Lo que `RF-13` prohíbe es el azul
    sobre lo que escribe, y eso se reconoce por el verbo con el que la pantalla
    lo nombra.
    """
    azules = page.evaluate(
        """() => [...document.querySelectorAll('button')]
             .filter(el => getComputedStyle(el).color === 'rgb(31, 75, 153)')
             .map(el => el.textContent.trim().toLowerCase())"""
    )
    return [texto for texto in azules if any(verbo in texto for verbo in ESCRIBEN)]


# --- Ola 1: el shell, la raíz y las cuatro pantallas de sesión ---------------


def ola_1(page: Page, invitacion: str) -> None:
    # RF-05 y RF-20: la pantalla de ingreso, con el sistema operativo en oscuro.
    page.goto(f"{BASE}/login", wait_until="networkidle")
    fondo = style(page, "body", "background-color")
    check(fondo == PAPEL, f"RF-20 · /login sigue clara con el SO en oscuro (body = {fondo})")
    check(page.locator("form button[type=submit]").count() == 1, "RF-11 · /login tiene una sola acción")
    entrar = style(page, "form button[type=submit]", "background-color")
    check(entrar == NARANJA, f"RF-11 · y esa acción es la de acento ({entrar})")
    shot(page, "rf05-ingreso.png")

    # La invitación: la pantalla que abre quien nunca entró.
    page.goto(f"{BASE}/invitacion/{invitacion}", wait_until="networkidle")
    check(style(page, "body", "background-color") == PAPEL, "RF-20 · la invitación también")
    check(page.get_by_text("Definí tu clave").count() > 0, "RF-05 · la invitación es la misma tarjeta")
    shot(page, "rf05-invitacion.png")

    # Se define la clave desde ahí: es el alta real del acceso de Ventas.
    page.fill("input[placeholder='Clave nueva']", VENTAS[1])
    page.fill("input[placeholder='Repetí la clave nueva']", VENTAS[1])
    page.click("button[type=submit]")
    page.wait_for_timeout(1500)
    check(page.get_by_text("Ir a la pantalla de ingreso").count() > 0, "RF-11 · después de guardar queda la salida")
    shot(page, "rf05-invitacion-guardada.png")

    page.goto(f"{BASE}/reset-password", wait_until="networkidle")
    check(page.get_by_text("Restablecer").count() > 0, "RF-05 · recuperar la clave, misma tarjeta")
    shot(page, "rf05-recuperar.png")

    # RF-24: al entrar se cae en el tablero, sin bienvenida en el medio.
    login(page, *OWNER)
    page.goto(f"{BASE}/", wait_until="networkidle")
    check(page.url.endswith("/tablero"), f"RF-24 · la raíz cae en el tablero (quedó en {page.url})")
    check(page.locator("aside nav a").count() == 16, "RF-03 · la barra lista las dieciséis secciones")
    shot(page, "rf24-la-raiz-cae-en-el-tablero.png")


# --- Ola 2: la plata -------------------------------------------------------


def pildora_vencida(page: Page) -> dict[str, str] | None:
    """El trío de colores de la píldora «Venció sin recibo», donde aparezca."""
    return page.evaluate(
        """() => {
             const el = [...document.querySelectorAll('.pill')]
               .find(p => p.textContent.trim() === 'Venció sin recibo')
             if (!el) return null
             const s = getComputedStyle(el)
             return { color: s.color, fondo: s.backgroundColor, borde: s.borderColor }
           }"""
    )


def ola_2(page: Page) -> None:
    # (1) La misma píldora roja en las tres pantallas.
    page.goto(f"{BASE}/facturas", wait_until="networkidle")
    en_facturas = pildora_vencida(page)
    shot(page, "rf06-facturas.png")

    page.goto(f"{BASE}/calendario", wait_until="networkidle")
    page.get_by_role("link", name="« Mes anterior").click()   # la vencida es de agosto
    page.wait_for_url("**/calendario?since=**", timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    en_calendario = pildora_vencida(page)
    shot(page, "rf06-calendario.png")

    page.goto(f"{BASE}/proveedores/9001", wait_until="networkidle")
    en_proveedor = pildora_vencida(page)
    shot(page, "rf06-ficha-del-proveedor.png")

    check(en_facturas is not None, "RF-06 · la píldora vencida aparece en /facturas")
    check(en_calendario is not None, "RF-06 · y en /calendario")
    check(en_proveedor is not None, "RF-06 · y en la ficha del proveedor")
    if en_facturas and en_calendario and en_proveedor:
        iguales = en_facturas == en_calendario == en_proveedor
        check(iguales, f"RF-06 · y las tres son idénticas ({json.dumps(en_facturas, ensure_ascii=False)})")

    # (2) Cuatro dígitos contra siete: las comas caen en la misma vertical.
    page.goto(f"{BASE}/facturas", wait_until="networkidle")
    columna = page.evaluate(
        """() => [...document.querySelectorAll('table tbody tr')]
             .map(fila => fila.querySelectorAll('td')[5])
             .filter(Boolean)
             .map(td => ({ texto: td.textContent.trim(),
                           derecha: Math.round(td.getBoundingClientRect().right),
                           fuente: getComputedStyle(td).fontFamily.split(',')[0] }))"""
    )
    largos = {len(c["texto"]) for c in columna}
    bordes = {c["derecha"] for c in columna}
    check(len(largos) > 1, f"RF-10 · la columna tiene cifras de distinto largo ({sorted(largos)})")
    check(len(bordes) == 1, f"RF-10 · y todas terminan en la misma vertical ({bordes})")
    check(all("Plex" in c["fuente"] for c in columna), f"RF-09 · en mono tabular ({columna[0]['fuente'] if columna else '—'})")

    # (3) Lo no confirmado se distingue sin leer la etiqueta.
    page.goto(f"{BASE}/proveedores/9001", wait_until="networkidle")
    grafias = page.evaluate(
        """() => [...document.querySelectorAll('.pill')]
             .filter(p => p.textContent.includes('METALURGICA') || p.textContent.includes('Metalurgica'))
             .map(p => ({ texto: p.textContent.trim(), borde: getComputedStyle(p).borderStyle }))"""
    )
    punteadas = [g for g in grafias if g["borde"] == "dashed"]
    check(len(grafias) >= 2, f"RF-08 · la ficha muestra las dos grafías ({len(grafias)})")
    check(len(punteadas) == 1, f"RF-08 · sólo la que reconoció el sistema va punteada ({punteadas})")
    shot(page, "rf08-lo-no-confirmado.png")

    # (4) Ningún botón que guarda, corrige o borra usa el color de enlace.
    for ruta in ("/facturas", "/facturas/9001", "/facturas/pagos", "/ordenes", "/proveedores/9001"):
        page.goto(f"{BASE}{ruta}", wait_until="networkidle")
        azules = azules_que_actuan(page)
        check(not azules, f"RF-13 · en {ruta} ningún botón usa el azul de dato ({azules})")


# --- Ola 3: las decisiones --------------------------------------------------


def ola_3(page: Page) -> None:
    for ruta in DECISION:
        page.goto(f"{BASE}{ruta}", wait_until="networkidle")
        page.wait_for_timeout(300)
        cuantos = naranjas(page)
        check(not cuantos, f"RF-21 · {ruta} no tiene ningún naranja ({cuantos})")
        azules = azules_que_actuan(page)
        check(not azules, f"RF-13 · {ruta} no usa el azul para actuar ({azules})")
    shot(page, "rf21-una-pantalla-de-decision.png")


# --- El recorrido final -----------------------------------------------------


def recorrido_del_dueno(page: Page) -> None:
    errores: list[str] = []
    page.on("pageerror", lambda e: errores.append(str(e)))

    for nombre, ruta in SECCIONES + [("Mi cuenta", "/mi-cuenta")]:
        page.goto(f"{BASE}{ruta}", wait_until="networkidle")
        page.wait_for_timeout(250)
        titulo = page.locator("h1").first
        check(titulo.count() > 0, f"RF-01 · {nombre} ({ruta}) renderiza")
        fondo = style(page, "body", "background-color")
        check(fondo == PAPEL, f"RF-02/RF-20 · {nombre} sobre el mismo papel ({fondo})")
        cuantos = naranjas(page)
        check(len(cuantos) <= 1, f"RF-11 · {nombre} usa como mucho un naranja ({cuantos})")
        if ruta in ("/tablero", "/facturas", "/revision"):
            shot(page, f"rf01-{ruta.strip('/').replace('/', '-')}.png")

    check(not errores, f"ninguna pantalla se rompió al renderizar ({errores})")


def recorrido_de_ventas(page: Page) -> None:
    login(page, *VENTAS)
    page.goto(f"{BASE}/tablero", wait_until="networkidle")
    entradas = page.evaluate("() => [...document.querySelectorAll('aside nav a')].map(a => a.textContent.trim())")
    check("Ventas" in entradas, f"RF-22 · Ventas ve su sección ({entradas})")
    for ajena in ("Facturas", "Órdenes de compra", "Accesos", "Parámetros"):
        check(ajena not in entradas, f"RF-17 · no ve {ajena}")
    # `RF-18` dicho como lo que es: **ningún título sin entradas debajo**.
    # Afirmar «Compras no aparece» era una suposición sobre los permisos que el
    # backend reparte, y es falsa: un acceso de Ventas alcanza el calendario, así
    # que el grupo Compras tiene una entrada y su título corresponde. El caso en
    # que un grupo queda entero afuera lo fija el test de render de la tarea 12,
    # que puede pedir el mapa de permisos que quiera.
    huerfanos = page.evaluate(
        """() => [...document.querySelectorAll('aside nav > div')]
             .filter(g => g.querySelector('p') && g.querySelectorAll('a').length === 0)
             .map(g => g.querySelector('p').textContent.trim())"""
    )
    check(not huerfanos, f"RF-18 · ningún título de grupo quedó sin entradas debajo ({huerfanos})")
    check(page.get_by_text("Julian Ventas").count() > 0, "RF-04 · el nombre de quien trabaja está a la vista")
    shot(page, "rf17-el-menu-de-ventas.png")


def main() -> int:
    invitacion = invitacion_nueva(VENTAS[0])
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        # El sistema operativo en modo oscuro: es lo que RF-20 pide probar.
        contexto = navegador.new_context(color_scheme="dark", viewport={"width": 1440, "height": 900})
        page = contexto.new_page()

        # Cada ola se anota entera aunque una falle: un recorrido que se corta
        # en el primer problema esconde los otros ocho.
        for nombre, paso in (
            ("ola 1", lambda: ola_1(page, invitacion)),
            ("ola 2", lambda: ola_2(page)),
            ("ola 3", lambda: ola_3(page)),
            ("recorrido del dueño", lambda: recorrido_del_dueno(page)),
        ):
            try:
                paso()
            except Exception as error:  # noqa: BLE001 — es un recorrido, no la suite
                check(False, f"{nombre} se cortó: {error}".split("Call log")[0])

        try:
            ventas = navegador.new_context(color_scheme="dark", viewport={"width": 1440, "height": 900})
            recorrido_de_ventas(ventas.new_page())
        except Exception as error:  # noqa: BLE001
            check(False, f"recorrido de Ventas se cortó: {error}".split("Call log")[0])

        navegador.close()

    if fallos:
        print("\n--- FALLOS ---")
        print("\n".join(fallos))
    print(f"\n{len(notas)} verificaciones en verde · {len(fallos)} en rojo")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
