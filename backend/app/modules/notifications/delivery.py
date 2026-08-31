"""Choosing who an alert goes to, and when it may go out.

Kept apart from `service.py`, which is the wording of the messages, because
this is a different question and it needs the database: which people hold the
role that receives this kind of alert, and whether the moment is inside the
window the owner allows.

**Nothing outside the window is dropped.** RF-42 of 007 says an immediate alert
whose cause happens outside the window goes out when the next one opens, so what
this computes is a delay, never a discard.
"""

from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.notifications.models import AlertKind
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.service import (
    DEFAULT_ROUTES,
    WINDOW_END_KEY,
    WINDOW_START_KEY,
    WORKING_DAYS,
)
from app.shared.parameters import initial_value
from app.shared.time import BUSINESS_TIME_ZONE

logger = get_logger(__name__)

DAYS_IN_A_WEEK = 7


class AlertRouter:
    """Says who an alert reaches, and how long it has to wait to go out."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notifications = NotificationsRepository(session)

    async def phones_for(self, kind: AlertKind) -> list[str]:
        """The numbers this kind of alert goes to (RF-37, RF-44, RF-45 of 007).

        Only people who still have access: somebody deactivated is not in the
        list, and that is not a rule anybody applies — it is what the recipients
        table already says.
        """
        routes = await self.notifications.routes()
        role = routes.get(kind, DEFAULT_ROUTES[kind.value])
        recipients = await self.notifications.active_with_role(role)
        if not recipients and role != "OWNER":
            # Nobody holds that role right now. The alert is not dropped: it
            # falls back to the owner, who reaches everything, rather than
            # disappearing because a role happens to be vacant.
            recipients = await self.notifications.active_with_role("OWNER")
        return [recipient.phone for recipient in recipients if recipient.phone]

    async def delay_until_window(self, moment: datetime | None = None) -> int:
        """Seconds to wait before an immediate alert may go out (RF-42, RF-43).

        Zero inside the window. Outside it, the number of seconds until the next
        window opens — the following morning, or Monday when it is the weekend.
        """
        now = (moment or datetime.now(UTC)).astimezone(BUSINESS_TIME_ZONE)
        start = self._time_of(await self.setting(WINDOW_START_KEY))
        end = self._time_of(await self.setting(WINDOW_END_KEY))

        if now.weekday() in WORKING_DAYS and start <= now.time() <= end:
            return 0

        opens = now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        if now.time() > start or now.weekday() not in WORKING_DAYS:
            opens += timedelta(days=1)
        for _ in range(DAYS_IN_A_WEEK):
            if opens.weekday() in WORKING_DAYS:
                break
            opens += timedelta(days=1)
        return max(int((opens - now).total_seconds()), 0)

    async def setting(self, key: str) -> Any:
        """A parameter, from what `operations` last published or its initial value."""
        stored = await self.notifications.setting(key)
        return initial_value(key) if stored is None else stored

    async def remember(self, key: str, value: Any) -> None:
        """Keep a parameter this router reads."""
        await self.notifications.put_setting(key, value)

    @staticmethod
    def _time_of(value: Any) -> time:
        """Read `HH:MM`, the shape a time-of-day parameter is stored in."""
        hours, _, minutes = str(value).partition(":")
        return time(hour=int(hours), minute=int(minutes or 0))
