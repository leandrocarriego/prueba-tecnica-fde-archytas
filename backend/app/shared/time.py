"""The clock this business runs on.

The ferretería is in Buenos Aires, the supplier publishes on that clock, and
the team reads a date standing in the shop. An instant stored with its offset
is unambiguous; a **date somebody typed** is not, and that is where this
matters: `desde 2026-08-30` means that day in Buenos Aires, not the day that
starts at midnight UTC — which is 21:00 of the day before, three hours of the
wrong day at one end and three missing at the other.

The frontend learned this the hard way and pinned the zone in
`frontend/lib/time.ts`, whose docstring tells the story. This is the same rule
on the server side, for the moment a filter reaches the database.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TIME_ZONE = ZoneInfo("America/Argentina/Buenos_Aires")
BUSINESS_TIME_ZONE_NAME = "America/Argentina/Buenos_Aires"


def as_business_time(value: datetime | None) -> datetime | None:
    """Give a naive instant the only timezone this business has.

    An instant that already carries an offset is left exactly as it is: the
    caller said what they meant, and reinterpreting it would be inventing a
    different moment. `None` stays `None`, because a filter nobody set is not a
    filter at midnight.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=BUSINESS_TIME_ZONE)
