"""H5 de la 006: el canal en vivo, por debajo del evento de dominio.

`test_due_date_calendar.py` ya fija que un cambio **se anuncia**, y lo hace
sobre el evento de dominio a propósito: eso es lo que la feature promete, y por
dónde viaja es una decisión del plan. Lo que faltaba es la otra mitad — que el
transporte haga lo que el plan dice que hace—, y era justo la mitad sin ningún
test: `app/shared/live.py` quedaba al 50%, y las líneas sin cubrir eran el
mecanismo entero.

Lo que se sostiene acá, en el orden en que el traspaso de la feature lo pide:

1. **Una transacción que aborta no notifica a nadie.** Es el caso que va antes
   que ninguno: `pg_notify` es transaccional, y de eso depende que `GEN-09` se
   cumpla sin acoplar el movimiento de un vencimiento a la conexión de otro.
2. **El mensaje cruza de un proceso al otro**, que es la única razón por la que
   el bus es Postgres y no una lista en memoria: el despliegue corre con
   `--workers 2`, y una lista en memoria anda perfecto en la máquina de quien
   la escribe y falla la mitad de las veces en producción.
3. **Un lector lento pierde mensajes en vez de frenar el proceso.**
4. **La ruta del stream** contesta `text/event-stream`, y ventas la alcanza
   (RF-37) porque mirar el calendario en vivo es mirar el calendario.

Nada de esto necesita el portal: la feature no extrae nada.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.modules.purchases import routes

# `_dsn` es privada y se importa igual: la conexión que escucha tiene que
# apuntar **a la misma base y por la misma vía** que la que escucha en
# producción. Rehacer acá el `replace` del driver daría un test que pasa el día
# que el DSN de verdad se rompe, que es lo contrario de para qué está.
from app.shared.live import CHANNEL, QUEUE_LIMIT, LiveBus, _dsn, announce, bus
from tests.conftest import API_PREFIX

pytestmark = [pytest.mark.integration, pytest.mark.database]

# Lo que se espera a que llegue algo por la base. Generoso para que no parpadee
# en una máquina cargada, y corto para que un test roto no cuelgue la suite.
ARRIVES_IN = 5.0
# Lo que se espera para comprobar que **no** llega nada. Es un techo, no una
# medida: si el `NOTIFY` viajara igual, viajaría de inmediato al commit.
STAYS_QUIET_FOR = 0.75


@dataclass
class Escucha:
    """Lo que llegó por el canal, a una conexión que no es la que escribe."""

    received: asyncio.Queue[str]

    async def next_payload(self) -> str:
        return await asyncio.wait_for(self.received.get(), timeout=ARRIVES_IN)


@pytest.fixture
async def escucha() -> AsyncIterator[Escucha]:
    """Una conexión aparte, escuchando el canal como lo hace el otro worker."""
    connection = await asyncpg.connect(dsn=_dsn())
    received: asyncio.Queue[str] = asyncio.Queue()

    def anotar(_connection: object, _pid: int, _channel: str, payload: str) -> None:
        received.put_nowait(payload)

    await connection.add_listener(CHANNEL, anotar)
    try:
        yield Escucha(received)
    finally:
        # Cerrar sola alcanzaría; se lo saca igual porque un listener que
        # sobrevive a su test es la clase de fuga que aparece diez tests
        # después y en otro archivo.
        await connection.remove_listener(CHANNEL, anotar)
        await connection.close()


class TestWhatCrossesBetweenTwoProcesses:
    """`announce` viaja por Postgres, y sólo si la transacción llegó a buen puerto."""

    async def test_a_transaction_that_commits_reaches_the_other_process(
        self, engine: AsyncEngine, escucha: Escucha
    ) -> None:
        """RF-31: lo que una persona hace llega a la pantalla de la otra."""
        # Arrange — una sesión que **de verdad** commitea, y no la del resto de
        # la suite, que vive dentro de una transacción que siempre se revierte.
        async with AsyncSession(engine) as session:
            # Act
            await announce(session, "due_date", {"action": "moved", "id": 7})
            await session.commit()

        # Assert
        payload = await escucha.next_payload()
        assert json.loads(payload) == {
            "topic": "due_date",
            "data": {"action": "moved", "id": 7},
        }

    async def test_a_transaction_that_aborts_announces_nothing(
        self, engine: AsyncEngine, escucha: Escucha
    ) -> None:
        """Lo que hace que un handler pueda anunciar sin mentir (`GEN-09`).

        Si esto se rompiera, la pantalla de la otra persona se enteraría de un
        cambio que nunca ocurrió — y se enteraría **antes** de que la primera se
        entere de que no ocurrió.
        """
        # Arrange
        async with AsyncSession(engine) as session:
            # Act — se anuncia, y después la transacción se cae.
            await announce(session, "due_date", {"action": "moved", "id": 7})
            await session.rollback()

        # Assert
        await asyncio.sleep(STAYS_QUIET_FOR)
        assert escucha.received.empty()


async def subscribed(local: LiveBus, reader: AsyncIterator[str], expected: int) -> asyncio.Future:
    """Arranca un lector y espera a que quede suscripto **de verdad**.

    `read()` es un generador: su cuerpo no corre —y por lo tanto no se registra
    en `_subscribers`— hasta que alguien le pide el primer mensaje. Esperar un
    tick del loop y confiar alcanza a veces y falla otras, que es la peor clase
    de test; se espera al hecho, que es el contador de lectores.
    """
    pending = asyncio.ensure_future(anext(reader))
    async with asyncio.timeout(ARRIVES_IN):
        while local.readers < expected:
            await asyncio.sleep(0)
    return pending


class TestTheBusOfOneWorker:
    """`LiveBus` reparte a los navegadores pegados a *este* proceso."""

    async def test_every_reader_of_this_worker_gets_what_arrived(self) -> None:
        """RF-32: no es una persona la que se entera, son todas las que miran."""
        # Arrange
        local = LiveBus()
        first, second = local.read(), local.read()
        pending = [await subscribed(local, first, 1), await subscribed(local, second, 2)]

        # Act
        local._on_message(None, 0, CHANNEL, '{"topic":"due_date"}')

        # Assert
        got = await asyncio.wait_for(asyncio.gather(*pending), timeout=ARRIVES_IN)
        assert got == ['{"topic":"due_date"}'] * 2
        assert local.readers == 2

    async def test_a_reader_that_stopped_draining_loses_messages_and_holds_nobody(self) -> None:
        """Un navegador que se colgó no puede quedarse con el proceso.

        Pierde lo suyo y se pone al día cuando relee, que es lo que el plan
        decide a cambio de no sostener una cola por sesión.
        """
        # Arrange
        local = LiveBus()
        reader = local.read()
        pending = await subscribed(local, reader, 1)
        local._on_message(None, 0, CHANNEL, "arranque")
        assert await asyncio.wait_for(pending, timeout=ARRIVES_IN) == "arranque"

        # Act — el doble de lo que entra en la cola, y nadie leyendo.
        for index in range(QUEUE_LIMIT * 2):
            local._on_message(None, 0, CHANNEL, str(index))

        # Assert — no se cayó, no bloqueó, y el lector sigue vivo con lo que entró.
        assert local.readers == 1
        assert await asyncio.wait_for(anext(reader), timeout=ARRIVES_IN) == "0"

    async def test_a_reader_that_goes_away_stops_being_fed(self) -> None:
        """Cerrar la pantalla suelta la cola: nadie alimenta a quien no está."""
        # Arrange
        local = LiveBus()
        reader = local.read()
        pending = await subscribed(local, reader, 1)
        local._on_message(None, 0, CHANNEL, "hola")
        await asyncio.wait_for(pending, timeout=ARRIVES_IN)

        # Act
        await reader.aclose()

        # Assert
        assert local.readers == 0


class TestOpeningAndClosingTheChannel:
    """`start` y `stop`: la conexión dedicada que escucha, y soltarla."""

    async def test_starting_it_listens_and_starting_it_twice_changes_nothing(self) -> None:
        """Arrancar es idempotente: el `lifespan` no abre dos conexiones."""
        # Arrange
        local = LiveBus()

        # Act
        await local.start()
        assert local._started is True
        primera = local._connection
        await local.start()

        # Assert — la segunda no abrió nada nuevo.
        assert local._connection is primera
        await local.stop()

    async def test_a_channel_that_cannot_be_opened_is_not_fatal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Una plataforma que no arranca por esto es peor que una sin canal.

        Es una decisión escrita en el docstring de `start`, y una decisión que
        sólo vive en un docstring es la que alguien "arregla" seis meses después
        poniendo un `raise`: **el calendario se sigue viendo, sin actualizarse
        solo**, y quien mira se entera por el aviso de la pantalla.
        """
        # Arrange — un DSN que no resuelve.
        monkeypatch.setattr("app.shared.live._dsn", lambda: "postgresql://nadie@127.0.0.1:1/nada")
        local = LiveBus()

        # Act — no levanta.
        await local.start()

        # Assert — y lo dice quedándose apagado, no fingiendo que escucha.
        assert local._started is False
        assert local._connection is None

    async def test_stopping_lets_go_of_the_connection_and_of_every_reader(self) -> None:
        """Soltar la conexión suelta a los que lee: no quedan colas colgadas."""
        # Arrange
        local = LiveBus()
        await local.start()
        reader = local.read()
        await subscribed(local, reader, 1)

        # Act
        await local.stop()

        # Assert
        assert local._connection is None
        assert local._started is False
        assert local.readers == 0

    async def test_stopping_one_that_never_started_is_quiet(self) -> None:
        """El `lifespan` la llama siempre, arranque o no."""
        local = LiveBus()
        await local.stop()
        assert local._started is False


MENSAJE = '{"topic":"due_date","data":{"action":"moved","id":7}}'


class UnBusQueTermina:
    """Un bus que dice una cosa y se calla."""

    async def read(self) -> AsyncIterator[str]:
        yield MENSAJE


class TestTheStreamRoute:
    """`GET /calendar/stream`: la puerta por la que el navegador escucha."""

    async def test_sales_may_watch_the_calendar_live(
        self, sales_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RF-37: ventas mira el calendario, y mirarlo en vivo es mirarlo.

        El bus se reemplaza por uno que dice una cosa y se calla. El de verdad
        no termina nunca —es su trabajo—, y una respuesta que no termina no se
        puede leer entera desde un cliente en proceso. Lo que se prueba acá es
        lo que la **ruta** hace con lo que el bus le da, que es lo suyo: el
        encuadre SSE, y el comentario de apertura que le dice al navegador que
        ya está conectado en vez de dejarlo esperando a un proxy.
        """
        # Arrange
        monkeypatch.setattr(routes, "bus", UnBusQueTermina())

        # Act
        response = await sales_client.get(f"{API_PREFIX}/calendar/stream")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        # Sin buffering intermedio: un proxy que junte trozos convierte el canal
        # en vivo en un canal de a ratos.
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"
        assert response.text == f": conectado\n\ndata: {MENSAJE}\n\n"

    async def test_nobody_without_a_session_gets_the_stream(self, client: AsyncClient) -> None:
        """El canal lleva lo que se movió: no se escucha sin sesión."""
        # Act
        response = await client.get(f"{API_PREFIX}/calendar/stream")

        # Assert
        assert response.status_code in {401, 403}

    async def test_the_process_wide_bus_is_the_one_the_route_reads(self) -> None:
        """Uno por proceso, como el engine: dos listeners serían dos verdades."""
        assert isinstance(bus, LiveBus)
