"""Correcting a value without losing what it said.

Three things live here, and none of them belongs to a module:

* **`CorrectionStatus`** — the life of a correction: in force, contradicted by
  the portal, or undone.
* **`CorrectionReason`** — the short list a person picks from, with the words
  they read. It is here and not in the browser because the API is what
  validates the code, and a list that validates in one place and renders from
  another is two lists.
* **`CorrectionColumns`** — the shape of a corrections table, as a mixin.

The mixin, and not a table: **the correction is stored by the module that owns
the datum**. `catalog` has to know, while it is applying a new price, whether
that price has a correction on top and what the portal had originally said
(RF-28) — and asking `operations` for it would be reading another module's
table, which is the import the boundary forbids wearing a different hat. So
each module keeps its own table with the same columns, and `operations` hears
about every correction as an event, like everybody else.

What never changes is `portal_value`. It is what the portal said, it is what
comes back when the correction is undone (RF-31), and it is why two corrections
in a row still restore the portal's number and not the previous person's.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CorrectionStatus(enum.StrEnum):
    """Where a correction stands.

    `REVERTED` is a state and not a deletion: undoing a correction has to stay
    readable in the history, and a row that disappeared would leave the log
    pointing at nothing (Artículo II).
    """

    ACTIVE = "ACTIVE"
    CONFLICTED = "CONFLICTED"
    REVERTED = "REVERTED"


class CorrectionReason(enum.StrEnum):
    """Why somebody corrected a value (RF-11)."""

    PORTAL_WAS_WRONG = "PORTAL_WAS_WRONG"
    MISREAD_FROM_DOCUMENT = "MISREAD_FROM_DOCUMENT"
    TYPED_BY_MISTAKE = "TYPED_BY_MISTAKE"
    SUPPLIER_CORRECTED_IT = "SUPPLIER_CORRECTED_IT"
    OTHER = "OTHER"


# What each reason says, in the words the person picks it by (Artículo VIII).
#
# Five and not fifteen on purpose: the point of a list is being able to count
# how many corrections happened for the same reason, and a list long enough to
# cover every case is a list where everybody picks a different entry. The
# written detail beside it is always available for the odd one out.
REASON_LABELS: dict[CorrectionReason, str] = {
    CorrectionReason.PORTAL_WAS_WRONG: "El portal lo informó mal",
    CorrectionReason.MISREAD_FROM_DOCUMENT: "Se leyó mal del documento escaneado",
    CorrectionReason.TYPED_BY_MISTAKE: "Se cargó mal a mano",
    CorrectionReason.SUPPLIER_CORRECTED_IT: "El proveedor lo corrigió después",
    CorrectionReason.OTHER: "Otro",
}


def label_for(code: str | None) -> str | None:
    """The words behind a reason code, or None when there is no code.

    An unknown code answers itself rather than `None`: the history is
    append-only, so a reason that was legal when it was written stays readable
    even if the list changes later.
    """
    if code is None:
        return None
    try:
        return REASON_LABELS[CorrectionReason(code)]
    except ValueError:
        return code


class CorrectionColumns:
    """The columns every corrections table has, wherever it lives.

    A mixin rather than a base class: the table belongs to the module, and so
    does its name, its schema and its unique index over
    `(entity_type, entity_id, field)` among the ones still in force.

    The `correction_status` type is created without a schema so a second module
    in another schema reuses the same one instead of declaring a near-identical
    twin.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    field: Mapped[str] = mapped_column(String(100))
    # What the portal informed. Never written again after the first correction:
    # it is the evidence, and it is what a reversal restores (RF-25, RF-31).
    portal_value: Mapped[Any] = mapped_column(JSONB)
    corrected_value: Mapped[Any] = mapped_column(JSONB)
    reason_code: Mapped[str] = mapped_column(String(50))
    reason_detail: Mapped[str | None] = mapped_column(Text, default=None)
    corrected_by_user_id: Mapped[int] = mapped_column(Integer)
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[CorrectionStatus] = mapped_column(
        Enum(CorrectionStatus, name="correction_status"),
        default=CorrectionStatus.ACTIVE,
        server_default=CorrectionStatus.ACTIVE.value,
    )
    # What the portal came back with, when it contradicted the original (RF-28).
    conflict_value: Mapped[Any | None] = mapped_column(JSONB, default=None)
    conflict_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    reverted_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
