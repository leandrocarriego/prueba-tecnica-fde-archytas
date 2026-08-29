"""Celery application.

Tasks live next to the module that owns them (`app/modules/<module>/tasks.py`)
and are discovered automatically, so adding a module never means editing this
file.
"""

import pkgutil
from importlib import import_module

from celery import Celery
from celery.signals import worker_init, worker_process_init, worker_shutdown

from app.config import settings
from app.logging import get_logger
from app.shared.events import discover_handlers
from app.worker.bridge import shutdown_loop

logger = get_logger(__name__)


def _module_packages() -> list[str]:
    """Return the import path of every domain module, for task autodiscovery."""
    package = import_module("app.modules")
    return [f"app.modules.{info.name}" for info in pkgutil.iter_modules(package.__path__)]


celery_app = Celery(
    "cordillera",
    broker=settings.broker_url,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    result_expires=3600,
    task_send_sent_event=True,
    worker_send_task_events=True,
    # Extraction jobs are long and uneven; fetching one at a time keeps a slow
    # section from blocking the queue behind a prefetched batch.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # The schedule for periodic extraction is registered by the modules that own
    # the tasks, so this file does not need to know about them.
    beat_schedule={},
)

# Discovery is **lazy**: Celery imports every `tasks.py` when the application is
# finalised — which the worker and beat do on start — instead of at the moment
# this module is imported. Forcing it here would mean that any service asking
# for `celery_app` to dispatch a task by name imported its own module's tasks
# back, half-initialised, through this line.
celery_app.autodiscover_tasks(packages=_module_packages())


# Subscriptions are per process, and a task publishes events like any other
# caller. Without this the worker runs the nightly extraction, publishes what it
# found and reaches nobody: the pipeline stops at `raw` and nothing says so.
#
# It cannot go at import time — `handlers.py` imports the very `tasks.py` that
# Celery is in the middle of loading. On the signals it is safe, because by then
# every task module is imported and the application is finalised.
#
# Both signals on purpose: `worker_init` covers the parent (and the solo pool,
# where tasks run in it), `worker_process_init` each forked child. Imports are
# cached, so the second call is a no-op and never registers a handler twice.
@worker_init.connect
@worker_process_init.connect
def _on_worker_start(**_: object) -> None:
    """Register every module's subscriptions in the process that will publish."""
    logger.info("Handlers discovered", extra={"modules": len(discover_handlers())})


@worker_shutdown.connect
def _on_worker_shutdown(**_: object) -> None:
    """Close the worker's event loop when Celery shuts the process down."""
    shutdown_loop()
