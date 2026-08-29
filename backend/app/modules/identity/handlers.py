"""What `identity` does when something happens elsewhere.

One thing, for now: the three settings that govern how long a session lasts
and when an access gets locked belong to `operations`, and this module keeps
its own copy rather than reading somebody else's table.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.identity.service import IdentityService
from app.shared.events import BusinessParameterChanged, events

logger = get_logger(__name__)


@events.subscribe(BusinessParameterChanged)
async def project_access_setting(event: BusinessParameterChanged, session: AsyncSession) -> None:
    """Take in a parameter the owner changed, if it is one of ours.

    `operations` owns the parameters; this module keeps its own copy so it
    never has to read somebody else's table to know how long a session lasts.
    """
    await IdentityService(session).apply_setting(event.key, event.value)
