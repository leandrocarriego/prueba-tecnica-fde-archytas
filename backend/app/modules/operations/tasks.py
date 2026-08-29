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
from app.modules.operations.service import OperationsService
from app.shared.errors import ConflictError
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
