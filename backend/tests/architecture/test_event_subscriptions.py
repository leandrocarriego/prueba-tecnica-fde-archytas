"""Every process that publishes an event has somebody listening.

> Un módulo nunca importa otro módulo. Se comunican publicando **eventos de
> dominio**.

`CONSTITUTION.md`, Artículo IV. The bus that carries them is in-process, and
that is the part which does not survive a fork or a second entry point: a
subscription registered in the API says nothing about the Celery worker, and
`publish` on an empty bus is legal and silent by design.

This was found in production, not here, and it could not have been found here:
the suite's `conftest` imports `app.main`, so handlers are always registered by
the time any test runs. Every test passed while the deployed worker ran the
nightly extraction, published what it found and reached nobody — the pipeline
stopping at `raw` with nothing to say so.

So the entry points are booted in **subprocesses**, one per test, each starting
from the empty bus a real process starts from.
"""

import subprocess
import sys
from pathlib import Path

import pytest

import app

BACKEND_ROOT = Path(app.__file__).resolve().parents[1]

# Counting through the catalog rather than the bus's own dict: the catalog is
# the shared vocabulary, and reaching into `_handlers` would tie this test to
# the bus's internals instead of to the rule.
COUNT_SUBSCRIPTIONS = """
from app.shared.events import events
from app.shared.events.catalog import DomainEvent
import app.shared.events.catalog as catalog

total = sum(
    len(events.handlers_for(member))
    for member in vars(catalog).values()
    if isinstance(member, type) and issubclass(member, DomainEvent) and member is not DomainEvent
)
print(total)
"""


def _subscriptions_after(boot: str) -> int:
    """Boot one entry point in a fresh process and count what it subscribed."""
    completed = subprocess.run(
        [sys.executable, "-c", boot + COUNT_SUBSCRIPTIONS],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return int(completed.stdout.strip().splitlines()[-1])


@pytest.mark.unit
class TestEveryPublisherHasSubscribers:
    """The three processes this product runs as."""

    def test_the_api_registers_on_import(self) -> None:
        """`app.main` is the composition root, and this is what it composes."""
        assert _subscriptions_after("import app.main\n") > 0

    def test_the_worker_registers_when_it_boots(self) -> None:
        """The signal has to fire, not merely be connected.

        This is the one that was broken: the tasks were discovered and the
        handlers were not, so an extraction published `PriceListExtracted` into
        an empty bus and nothing was ever normalised.
        """
        boot = (
            "from celery.signals import worker_process_init\n"
            # `app.worker` re-exports the Celery instance under this very
            # name, so the attribute shadows the submodule: import the object.
            "from app.worker.celery_app import celery_app\n"
            "celery_app.loader.import_default_modules()\n"
            "worker_process_init.send(sender=None)\n"
        )
        assert _subscriptions_after(boot) > 0

    def test_the_bootstrap_command_registers_before_it_invites(self) -> None:
        """It creates the owner and publishes `AccessInvited` in its own process.

        Run with no owner in the environment, so it stops at its own guard
        without touching the database: discovery happens before that guard
        precisely so the command cannot claim an invitation it never sent.
        """
        boot = (
            "import asyncio\n"
            "from app.config import settings\n"
            "settings.OWNER_EMAIL = ''\n"
            "from app.modules.identity.bootstrap import create_first_owner\n"
            "asyncio.run(create_first_owner())\n"
        )
        assert _subscriptions_after(boot) > 0
