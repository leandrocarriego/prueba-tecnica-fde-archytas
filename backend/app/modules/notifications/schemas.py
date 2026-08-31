"""Notifications schemas: who the owner wants each kind of alert to reach."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.models import AlertKind


class RouteRead(BaseModel):
    """Which role receives one kind of alert (RF-37 of 007)."""

    model_config = ConfigDict(from_attributes=True)

    kind: AlertKind
    role: str
    updated_by_user_id: int | None = None
    updated_at: datetime | None = None
    # How many people hold that role and still have access. Shown because a
    # route pointing at a role nobody holds is a route that delivers nothing,
    # and the owner should see that before an alert fails to arrive.
    recipients: int = 0


class RouteWrite(BaseModel):
    """The role the owner wants a kind of alert to reach."""

    role: str
