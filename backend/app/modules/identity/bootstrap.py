"""Creating the first access, once, when the platform is installed.

Everything about the feature presupposes an owner: he hands out accesses, he
administers them, and nobody else can. Which leaves exactly one account that
cannot be created the normal way — his own.

So it is created here, from the environment, and **not from a route**. A route
that mints owners would be a way into the system that bypasses the three rules
this feature exists to enforce, and it would sit there for the life of the
product waiting to be found. A command runs when somebody installs the thing
and then is not part of the running system at all.

It is idempotent: running it twice leaves one owner, not two.

    uv run python -m app.modules.identity.bootstrap
"""

import asyncio

from app.config import settings
from app.database import SessionFactory
from app.logging import get_logger, setup_logging
from app.modules.identity.models import User, UserRole
from app.modules.identity.repository import UserRepository
from app.modules.identity.schemas import PHONE_MIN
from app.modules.identity.service import INVITE_NEW_ACCESS, IdentityService
from app.shared.events import discover_handlers

logger = get_logger(__name__)

MISSING_SETTINGS = (
    "Faltan OWNER_EMAIL, OWNER_NAME y OWNER_PHONE en el entorno: "
    "sin ellos no hay a quién darle el primer acceso."
)


async def create_first_owner() -> str:
    """Create the owner's access and invite him, unless there already is one.

    Returns a line describing what happened, for whoever ran the command.
    """
    # This command is its own process, so it starts with an empty bus. Without
    # this the owner is created, `AccessInvited` is published to nobody, and the
    # line printed below claims an invitation that never left.
    discover_handlers()

    if not (settings.OWNER_EMAIL and settings.OWNER_NAME and settings.OWNER_PHONE):
        return MISSING_SETTINGS
    if len(settings.OWNER_PHONE) < PHONE_MIN:
        return "OWNER_PHONE no parece un teléfono: la invitación no tendría dónde llegar."

    async with SessionFactory() as session:
        users = UserRepository(session)
        if await users.count_owners():
            return "Ya hay un dueño: no se creó ninguno."
        if await users.get_by_email(settings.OWNER_EMAIL) is not None:
            return f"Ya existe un acceso con {settings.OWNER_EMAIL}: no se creó ninguno."

        owner = User(
            email=settings.OWNER_EMAIL,
            name=settings.OWNER_NAME,
            phone=settings.OWNER_PHONE,
            role=UserRole.OWNER,
            is_active=True,
        )
        owner = await users.add(owner)
        # The same invitation as everybody else's: not even the person running
        # the installer gets to choose the owner's password.
        service = IdentityService(session)
        await service.invite(owner, INVITE_NEW_ACCESS)
        await session.commit()

    logger.info("First owner created", extra={"email": settings.OWNER_EMAIL})
    return (
        f"Dueño creado: {settings.OWNER_EMAIL}. "
        "La invitación para definir su clave salió a su WhatsApp."
    )


def main() -> None:
    """Entry point for `python -m app.modules.identity.bootstrap`."""
    setup_logging()
    print(asyncio.run(create_first_owner()))


if __name__ == "__main__":
    main()
