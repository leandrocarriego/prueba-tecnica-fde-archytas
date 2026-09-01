"""La cola de revisión: una sola lista, y una puerta que no la contradice.

Dos reglas de la 011 que viven enteras en el frontend, y que son RF-06 y RF-12
disfrazadas de detalle de UI. Las dos se rompen **en silencio** —no dan error,
no rompen el build, no se ven mirando la pantalla con el rol equivocado— y por
eso están escritas acá.

**Una. La puerta está abierta para los tres (RF-06).** La entrada `/revision` de
la barra pedía `PRICES`, que era cierto mientras en la cola sólo hubiera
precios. Desde que las ventas apartadas caen ahí dejó de serlo: le cerraba la
puerta a Julián, que es el dueño de esa mitad. La ruta ya no recorta por sección
y la pantalla recorta lo que *muestra*, así que la entrada del menú no puede
seguir declarando una. Si volviera a declararla, el backend seguiría
contestando bien y simplemente no habría por dónde entrar.

**Dos. Las reglas aprendidas se piden sólo si se alcanzan (RF-12).** Toda regla
aprendida es de precios y `/triage/rules` sigue pidiendo `PRICES`. La pantalla
pedía las reglas siempre, y con la cola abierta eso pasa a ser un 403 para quien
no alcanza esa sección — un 403 que `rules ?? []` convierte en una lista vacía.
Un error amortiguado por accidente no es un comportamiento: es uno que nadie
testea, y por eso este archivo lo testea.

Por qué un test de Python sobre TypeScript: el mismo motivo que
`test_manual_actions.py`, `test_history_is_reachable.py`, `test_screen_reads.py`
y `test_auth_pages.py`, que son los cuatro precedentes. Si alguna vez hay una
suite de frontend, esto pertenece ahí.
"""

import re
from pathlib import Path

import pytest

import app

pytestmark = pytest.mark.unit

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[2]
FRONTEND = REPOSITORY_ROOT / "frontend"
NAVIGATION = FRONTEND / "components" / "auth" / "Navigation.tsx"
SCREEN = FRONTEND / "app" / "(private)" / "revision" / "page.tsx"

# `{ href: '/revision', label: 'Revisar esto' }`, con o sin sección: el objeto
# entero, para poder preguntar si la declara. `[^{}]*` no puede salirse de las
# llaves que abrió, así que una entrada nunca se lee mezclada con la de al lado.
REVIEW_ENTRY = re.compile(r"\{[^{}]*href:\s*'/revision'[^{}]*\}")
# `section: 'PRICES'` dentro de esa entrada.
DECLARES_A_SECTION = re.compile(r"\bsection:\s*'[A-Z_]+'")
# Lo que la pantalla pide, y bajo qué condición.
ASKS_FOR_THE_RULES = re.compile(r"fetchFromApi<Rule\[\]>\('/triage/rules'\)")
GUARDS_ON_PRICES = re.compile(r"canEdit\(session\.permissions,\s*'PRICES'\)")


def source_of(path: Path) -> str:
    """El archivo, como lo lee el bundler."""
    return path.read_text(encoding="utf-8")


class TestTheDoorIsOpenToTheThreeOfThem:
    """RF-06: una lista sola a la que no todos llegan es otra vez un lugar más."""

    def test_the_menu_declares_the_entry(self) -> None:
        """Un archivo movido o una entrada renombrada no pueden pasar en silencio."""
        # Arrange / Act
        entry = REVIEW_ENTRY.search(source_of(NAVIGATION))

        # Assert
        assert entry is not None, (
            f"no hay ninguna entrada de menú que apunte a /revision en {NAVIGATION}"
        )

    def test_the_entry_declares_no_section(self) -> None:
        """Como `/acciones` y `/historial`: cualquier sesión la alcanza.

        La pantalla recorta por área lo que muestra, en vez de cerrarse. Declarar
        una sección acá le daría a alguien permiso sobre la mitad de la cola y
        ninguna puerta por donde entrar, y nada fallaría al hacerlo.
        """
        # Arrange
        entry = REVIEW_ENTRY.search(source_of(NAVIGATION))
        assert entry is not None

        # Act
        declared = DECLARES_A_SECTION.search(entry.group(0))

        # Assert
        assert declared is None, (
            "la entrada /revision volvió a declarar una sección "
            f"({declared.group(0) if declared else ''}): eso le cierra la puerta a un rol "
            "que sí tiene pendientes de su área en la cola"
        )


class TestTheRulesAreAskedForOnlyByWhoeverReachesThem:
    """RF-12: un 403 amortiguado por accidente no es un comportamiento."""

    def test_the_screen_asks_for_the_rules(self) -> None:
        """Si el pedido se fue de la pantalla, la regla de abajo no dice nada."""
        # Arrange / Act
        screen = source_of(SCREEN)

        # Assert
        assert ASKS_FOR_THE_RULES.search(screen) is not None, (
            f"{SCREEN} ya no pide /triage/rules: revisá si esta regla sigue teniendo sentido"
        )

    def test_it_asks_for_them_behind_the_permission_they_need(self) -> None:
        """El pedido está condicionado a alcanzar `PRICES`, que es lo que la ruta exige."""
        # Arrange
        screen = source_of(SCREEN)

        # Act
        guarded = GUARDS_ON_PRICES.search(screen)

        # Assert
        assert guarded is not None, (
            f"{SCREEN} pide /triage/rules sin preguntar antes si quien mira alcanza PRICES. "
            "Para quien no la alcanza eso es un 403 que `rules ?? []` disfraza de lista vacía"
        )
        # Y la condición está **antes** del pedido, que es la mitad que importa:
        # preguntarlo después lo convierte en un `if` decorativo sobre una
        # respuesta que ya vino con error.
        assert guarded.start() < ASKS_FOR_THE_RULES.search(screen).start()  # type: ignore[union-attr]
