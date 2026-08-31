"""Una extracción cuyo worker no volvió no bloquea a su sección para siempre.

**De dónde sale este archivo.** El 2026-08-31, en producción, cinco extracciones
—facturas, padrón, órdenes, mensajes y ventas— quedaron `RUNNING` a las 07:14 y
no cerraron nunca. `request_sync` se niega a abrir una corrida mientras hay otra
de la misma clase corriendo, así que cada latido siguiente las salteó **en
silencio**: doce horas sin una sola factura, sin un error, sin una alerta y sin
nada que fuera a destrabarse solo.

La actualización de precios tenía `close_abandoned_price_update` desde la 001.
Las cinco secciones que vinieron después no tenían su equivalente, y la falta no
se notaba mientras nada muriera a mitad de camino.

Dos reglas, entonces, y las dos son sobre lo mismo: **que un fallo se pueda ver**.
"""

from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operations.models import JobStatus
from app.modules.operations.service import (
    ABANDONED,
    ABANDONED_AFTER,
    SYNC_JOBS,
    OperationsService,
)
from app.modules.operations import service as operations_service
from app.modules.portal import service as portal_service
from app.modules.portal import tasks as portal_tasks

pytestmark = [pytest.mark.integration, pytest.mark.database]

# El cuerpo async de la task, alcanzado por detrás del puente del worker, como
# hace `test_price_tasks.py` y por el mismo motivo.
extract_invoices = portal_tasks.extract_invoices.run.__wrapped__

INVOICES = SYNC_JOBS[0]


@pytest.fixture(autouse=True)
def no_broker(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record what would have been dispatched instead of dispatching it.

    `request_sync` hands the section to the worker over the broker, and the
    suite runs with RabbitMQ down — like it runs with the portal down
    (`TEST-03`). Without this the test passes on the machine that happens to
    have a broker up and fails in CI, which is the worst place to find out.
    """
    sent: list[str] = []

    def record(name: str, **_: Any) -> None:
        sent.append(name)

    monkeypatch.setattr(operations_service.celery_app, "send_task", record)
    return sent


@pytest.fixture
def service(session: AsyncSession) -> OperationsService:
    """The service under test, on the test's session."""
    return OperationsService(session)


async def run_started_ago(service: OperationsService, task_name: str, ago: timedelta) -> int:
    """A run of that task, opened `ago` in the past and never closed."""
    run = await service.start_run(task_name)
    stored = await service.runs.get(run.id)
    assert stored is not None
    await service.runs.update(stored, {"started_at": datetime.now(UTC) - ago})
    await service.session.commit()
    return run.id


class TestClosingWhatAWorkerLeftOpen:
    """`close_abandoned_syncs`: lo que el latido tiene que barrer antes de decidir."""

    async def test_a_run_past_the_limit_is_failed_with_its_reason(
        self, service: OperationsService
    ) -> None:
        """Se cierra como un fallo cualquiera, y la historia dice por qué."""
        # Arrange
        run_id = await run_started_ago(service, INVOICES.task_name, ABANDONED_AFTER * 2)

        # Act
        closed = await service.close_abandoned_syncs()

        # Assert
        assert closed == [run_id]
        stored = await service.runs.get(run_id)
        assert stored is not None
        assert stored.status is JobStatus.FAILED
        assert stored.error == ABANDONED
        assert stored.finished_at is not None

    async def test_a_run_still_inside_the_limit_is_left_alone(
        self, service: OperationsService
    ) -> None:
        """Una extracción que está tardando no es una extracción muerta."""
        # Arrange
        run_id = await run_started_ago(service, INVOICES.task_name, timedelta(minutes=1))

        # Act
        closed = await service.close_abandoned_syncs()

        # Assert
        assert closed == []
        stored = await service.runs.get(run_id)
        assert stored is not None
        assert stored.status is JobStatus.RUNNING

    async def test_the_section_can_be_requested_again_once_it_is_closed(
        self, service: OperationsService, no_broker: list[str]
    ) -> None:
        """El punto entero del arreglo: la sección se destraba.

        Sin esto la corrida abandonada gana para siempre — `request_sync`
        contesta `None` en cada latido y la sección no vuelve a pedirse nunca.
        """
        # Arrange
        await run_started_ago(service, INVOICES.task_name, ABANDONED_AFTER * 2)
        assert await service.request_sync(INVOICES) is None

        # Act
        await service.close_abandoned_syncs()

        # Assert
        assert await service.request_sync(INVOICES) is not None
        assert no_broker == [INVOICES.celery_task]

    async def test_every_scheduled_section_is_swept(self, service: OperationsService) -> None:
        """Las cinco, no sólo la que se rompió primero."""
        # Arrange
        expected = [
            await run_started_ago(service, job.task_name, ABANDONED_AFTER * 2) for job in SYNC_JOBS
        ]

        # Act
        closed = await service.close_abandoned_syncs()

        # Assert
        assert sorted(closed) == sorted(expected)


class _Handle:
    """An async context manager that lends the test's session and never closes it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


@pytest.fixture
def on_the_test_session(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the task open the session this test will roll back."""
    monkeypatch.setattr(portal_tasks, "SessionFactory", lambda: _Handle(session))


def celery_self() -> Any:
    """A stand-in for the bound task, with no attempts behind it."""

    class _Request:
        retries = 0

    class _Task:
        request = _Request()

        def retry(self, **_: Any) -> None:  # pragma: no cover - no debería llamarse
            raise AssertionError("un defecto no se reintenta")

    return _Task()


class TestAFailureThatIsNotThePortal:
    """Lo que dejó cinco secciones trabadas: morir sin decirlo."""

    async def test_it_is_recorded_instead_of_leaving_the_run_open(
        self,
        session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        on_the_test_session: None,
    ) -> None:
        """Un `UndefinedTableError` no es el portal negándose, y tiene que quedar escrito.

        Antes sólo se atrapaba `ExtractionError`: cualquier otra excepción salía
        de la task sin pasar por `_report_failure`, la corrida quedaba `RUNNING`
        para siempre y `request_sync` salteaba esa sección en cada latido.
        """
        # Arrange
        service = OperationsService(session)
        run = await service.start_run(INVOICES.task_name)
        await session.commit()

        async def boom(self: Any, **_: Any) -> int:
            raise RuntimeError("relation does not exist")

        monkeypatch.setattr(portal_service.PortalService, "extract_invoices", boom)

        # Act
        with pytest.raises(RuntimeError):
            await extract_invoices(celery_self(), job_run_id=run.id)

        # Assert
        failed = await OperationsService(session).get_run(run.id)
        assert failed.status is JobStatus.FAILED
        assert failed.error is not None
        assert "RuntimeError" in failed.error
