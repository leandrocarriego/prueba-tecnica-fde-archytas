"""Celery application.

Tasks live next to the module that owns them (`app/modules/<module>/tasks.py`)
and are discovered automatically, so adding a module never means editing this
file.
"""

import pkgutil
from importlib import import_module

from celery import Celery
from celery.signals import worker_shutdown

from app.config import settings
from app.worker.bridge import shutdown_loop


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

celery_app.autodiscover_tasks(packages=_module_packages(), force=True)


@worker_shutdown.connect
def _on_worker_shutdown(**_: object) -> None:
    """Close the worker's event loop when Celery shuts the process down."""
    shutdown_loop()
