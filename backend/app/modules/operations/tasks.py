"""The heartbeat of the scheduled price update.

Beat runs one small task on a fixed tick, and that task reads how often the
owner wants the portal queried and decides whether the next query is due. It is
what makes RF-21 true — a new frequency applies from the following query,
without a redeploy and without rewriting the schedule from the database.

The task itself never extracts anything: it opens the run and hands the work to
the module that owns the portal, by task name.
"""

from datetime import timedelta
from typing import Any

from app.database import SessionFactory
from app.logging import get_logger
from app.modules.operations.service import SYNC_JOBS, OperationsService
from app.shared.errors import ConflictError
from app.shared.events import PendingWorkRequested, events
from app.worker.bridge import async_task
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

# How often the heartbeat wakes up. It is not the frequency of the update: that
# one is a business parameter and this only has to be fine enough that a change
# to it takes effect soon.
TICK_MINUTES = 15


@celery_app.task(name="operations.tick_price_update")
@async_task
async def tick_price_update() -> dict[str, Any]:
    """Ask for the price list if the configured interval has gone by (RF-01)."""
    async with SessionFactory() as session:
        service = OperationsService(session)
        # Before deciding anything: a run whose worker died is still RUNNING,
        # and while it is, nothing else can start — not the schedule and not a
        # person. The heartbeat is the only thing that wakes up on its own, so
        # it is where that gets noticed.
        abandoned = await service.close_abandoned_price_update()
        if not await service.due_for_update():
            return {"requested": False, "abandoned": abandoned}
        try:
            requested = await service.request_price_update()
        except ConflictError:
            # Somebody asked for one by hand in the meantime. One update at a
            # time is the rule, and this is the caller that gives way (RF-15).
            logger.info("Scheduled update skipped: one is already running")
            return {"requested": False}

    logger.info("Scheduled price update requested", extra={"job_run_id": requested.job_run_id})
    return {"requested": True, "job_run_id": requested.job_run_id, "abandoned": abandoned}


# Registered from the module that owns the task: `app/worker/celery_app.py` does
# not know about the modules, and adding one never means editing it.
celery_app.conf.beat_schedule["price-update-tick"] = {
    "task": "operations.tick_price_update",
    "schedule": timedelta(minutes=TICK_MINUTES),
}


@celery_app.task(name="operations.tick_extractions")
@async_task
async def tick_extractions() -> dict[str, Any]:
    """Ask the portal for whatever section is due, by its own parameter.

    One heartbeat for the five scheduled extractions of 004, 007 and 009,
    rather than five schedules to keep in step with the settings panel. Each
    one is decided independently and skipped in silence when it is not due or
    when one of its kind is already running.
    """
    requested: dict[str, int] = {}
    async with SessionFactory() as session:
        service = OperationsService(session)
        # First, whatever a dead worker left open. A section with a `RUNNING`
        # run is skipped by `request_sync`, so without this the heartbeat would
        # keep passing over it for ever — which is what it did.
        abandoned = await service.close_abandoned_syncs()
        for job in SYNC_JOBS:
            if not await service.due_for_sync(job):
                continue
            job_run_id = await service.request_sync(job)
            if job_run_id is not None:
                requested[job.key] = job_run_id

    if requested:
        logger.info("Scheduled extractions requested", extra={"jobs": sorted(requested)})
    return {"requested": requested, "abandoned": abandoned}


celery_app.conf.beat_schedule["extraction-tick"] = {
    "task": "operations.tick_extractions",
    "schedule": timedelta(minutes=TICK_MINUTES),
}


@celery_app.task(name="operations.tick_pending_work")
@async_task
async def tick_pending_work() -> dict[str, Any]:
    """Preguntar en público qué sigue esperando una decisión de una persona.

    El latido que mantiene honesta la cola de pendientes. Todo lo demás la
    alimenta **en el momento en que algo pasa**, lo cual es exacto para lo que
    pasa desde que existe el evento que lo cuenta y ciego para todo lo que ya
    estaba apartado antes: una factura en revisión desde marzo, un proveedor sin
    CUIT desde siempre, una venta repetida guardada antes de que `sales`
    aprendiera a anunciarlo. Nadie los publicó nunca, así que la cola decía que
    no había nada mientras el padrón y las facturas decían que sí.

    La pregunta no sabe quién contesta ni qué se hace con la respuesta —esto es
    `operations` preguntando, no `operations` sabiendo de ventas—, y por eso
    agregar un tercer módulo que tenga pendientes no se toca acá.

    Es barata y es idempotente: quien la escucha abre sólo lo que falta y cierra
    sólo lo que sobra, así que correrla de más no mueve nada.
    """
    async with SessionFactory() as session:
        await events.publish(PendingWorkRequested(), session)
        await session.commit()
    return {"asked": True}


celery_app.conf.beat_schedule["pending-work-tick"] = {
    "task": "operations.tick_pending_work",
    "schedule": timedelta(minutes=TICK_MINUTES),
}
