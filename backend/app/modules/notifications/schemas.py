"""Notifications schemas: who the owner wants each kind of alert to reach."""

from datetime import datetime
from typing import Literal

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
    """The role the owner wants a kind of alert to reach.

    **The two roles that may receive one, and not any string.** It used to take
    whatever it was given, which nobody could reach while the route had no
    screen; now that the owner picks from a control, a typo would point a kind
    of alert at a role nobody holds, and sales would be offerable — and RF-46
    says in as many words that sales does not reach the supplier inbox these
    alerts are about.

    Spelled as a `Literal` and not as the `UserRole` of `identity`, because a
    module never imports another (Artículo IV): what travels between them are
    the role strings the `UserRoleChanged` events already carry.
    """

    role: Literal["OWNER", "PURCHASING"]
