"""Data access for the notifications module. Private to this module."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    AlertKind,
    NotificationRecipient,
    NotificationRoute,
    NotificationSetting,
)


class NotificationsRepository:
    """Reads and writes who gets told what."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def put_recipient(
        self, *, user_id: int, role: str, phone: str, name: str = ""
    ) -> NotificationRecipient:
        """Record a person an alert can reach, or refresh what is known of them."""
        recipient = await self.session.get(NotificationRecipient, user_id)
        if recipient is None:
            recipient = NotificationRecipient(
                user_id=user_id, role=role, phone=phone, name=name, is_active=True
            )
            self.session.add(recipient)
        else:
            recipient.role = role
            recipient.is_active = True
            if phone:
                recipient.phone = phone
            if name:
                recipient.name = name
        await self.session.flush()
        return recipient

    async def set_active(self, user_id: int, *, active: bool) -> None:
        """Stop — or resume — sending alerts to somebody (RF-45 of 007)."""
        recipient = await self.session.get(NotificationRecipient, user_id)
        if recipient is None:
            return
        recipient.is_active = active
        await self.session.flush()

    async def set_role(self, user_id: int, role: str) -> None:
        """Follow a change of role: which alerts are theirs changed with it."""
        recipient = await self.session.get(NotificationRecipient, user_id)
        if recipient is None:
            return
        recipient.role = role
        await self.session.flush()

    async def active_with_role(self, role: str) -> list[NotificationRecipient]:
        """Everybody of this role who still has access."""
        result = await self.session.execute(
            select(NotificationRecipient).where(
                NotificationRecipient.role == role, NotificationRecipient.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def routes(self) -> dict[AlertKind, str]:
        """Which role receives each kind of alert, as the owner left it."""
        result = await self.session.execute(select(NotificationRoute))
        return {AlertKind(row.kind): row.role for row in result.scalars().all()}

    async def put_route(self, kind: AlertKind, role: str, *, actor_user_id: int) -> None:
        """Record who the owner wants to receive this kind of alert."""
        route = await self.session.get(NotificationRoute, kind)
        if route is None:
            self.session.add(
                NotificationRoute(kind=kind, role=role, updated_by_user_id=actor_user_id)
            )
        else:
            route.role = role
            route.updated_by_user_id = actor_user_id
        await self.session.flush()

    async def setting(self, key: str) -> Any | None:
        """The value of a parameter as this module last heard it, or None."""
        row = await self.session.get(NotificationSetting, key)
        return None if row is None else row.value

    async def put_setting(self, key: str, value: Any) -> None:
        """Record the value of a parameter the owner changed."""
        row = await self.session.get(NotificationSetting, key)
        if row is None:
            self.session.add(NotificationSetting(key=key, value=value))
        else:
            row.value = value
        await self.session.flush()
