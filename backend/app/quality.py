"""What the suite measured, for the screen that shows it.

`quality.json` is written by `scripts/quality_snapshot.py` from the artefacts of
a real run, and CI fails when the committed file disagrees with what the suite
just did. That check is the only reason this is worth showing: two numbers on a
public page are a claim, and a claim nobody verifies drifts into a lie that
looks exactly like the truth.

It is read once. The file is baked into the image at build time and cannot
change while the process runs, so re-reading it on every `/health` would be a
syscall per healthcheck for a value that is a constant.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from app.logging import get_logger

logger = get_logger(__name__)

SNAPSHOT = Path(__file__).resolve().parent / "quality.json"


class Quality(BaseModel):
    """How many tests passed, and how much of the code they covered."""

    tests: int
    coverage: float


@lru_cache
def get_quality() -> Quality | None:
    """The snapshot, or nothing at all.

    Missing or unreadable is not an error worth failing a health check over:
    the API serves requests perfectly well without knowing its own coverage.
    The screen simply says nothing, which is the honest answer to "we do not
    know" — the one thing it must never do is show a number it made up.
    """
    try:
        return Quality.model_validate_json(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("No quality snapshot to report", extra={"path": str(SNAPSHOT)})
        return None
