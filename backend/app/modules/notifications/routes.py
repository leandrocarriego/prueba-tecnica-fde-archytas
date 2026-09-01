"""HTTP routes for the notifications module.

The owner's alone: deciding who gets told what is a decision about the team, and
`SYSTEM_PARAMETERS` is the section that already means "the settings of the
platform itself".
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.logging import get_logger
from app.modules.identity.dependencies import CurrentUser, Level, Section, require_section
from app.modules.notifications import tasks
from app.modules.notifications.delivery import AlertRouter
from app.modules.notifications.models import AlertKind
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.schemas import RouteRead, RouteTested, RouteWrite
from app.modules.notifications.service import DEFAULT_ROUTES, test_message
from app.shared.errors import ConflictError

logger = get_logger(__name__)

Session = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Un aviso configurado que no tiene a quién llegarle. Nombra el rol porque es el
# dato con el que se arregla: o se le da ese rol a alguien, o se apunta el aviso
# a otro. El propio `AlertRouter` ya intentó caer en el dueño antes de esto, así
# que llegar acá significa que tampoco el dueño tiene teléfono cargado.
NOBODY_TO_TELL = (
    "No hay a quién mandarlo: nadie con el rol {role} tiene un teléfono cargado y activo."
)


@router.get(
    "/routes",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.READ)],
    summary="Who receives each kind of alert",
)
async def list_routes(session: Session) -> list[RouteRead]:
    """The owner (RF-37 of 007).

    Every kind is listed, including the ones nobody has configured: those show
    the value that was signed, which is what the platform is actually obeying.
    """
    repository = NotificationsRepository(session)
    stored = await repository.routes()
    return [
        RouteRead(
            kind=kind,
            role=stored.get(kind, DEFAULT_ROUTES[kind.value]),
            recipients=len(
                await repository.active_with_role(stored.get(kind, DEFAULT_ROUTES[kind.value]))
            ),
        )
        for kind in AlertKind
    ]


@router.post(
    "/routes/{kind}/test",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.WRITE)],
    summary="Mandar un aviso de prueba de este tipo",
)
async def test_route(kind: AlertKind, session: Session) -> RouteTested:
    """El dueño: probar un aviso es mandarle un WhatsApp a alguien.

    **Por qué existe.** Un aviso se configura una vez y se comprueba el día que
    hace falta, que es el peor día para descubrir que no llega: la sesión de
    WhatsApp se desvinculó, el rol quedó sin nadie, alguien se dio de baja y
    era el único con teléfono. Nada de eso falla ruidosamente — el aviso
    simplemente no aparece, y del otro lado nadie sabe que tenía que aparecer.

    **Sale a los destinatarios de verdad, no a quien aprieta el botón.** Es la
    única forma de probar lo que se quiere probar: que el camino entero —el
    tipo de aviso, el rol al que apunta, quién tiene ese rol, su teléfono y la
    sesión de WhatsApp— termina en un teléfono encendido. Mandárselo a uno
    mismo probaría el último tramo y ninguno de los anteriores. Por eso el
    mensaje se identifica como prueba en su primera línea.

    **Sale ahora, sin esperar la ventana horaria** (RF-42, RF-43). La ventana
    existe para que un aviso automático no despierte a nadie a las tres de la
    mañana; éste lo pidió una persona que está mirando la pantalla, y hacerlo
    esperar al lunes sería no contestar la pregunta que hizo.

    Sin nadie a quien mandárselo no se encola nada y se contesta por qué: es la
    falla más común de las que esto viene a encontrar, y es la única que se
    puede afirmar antes de intentar la entrega.
    """
    router_ = AlertRouter(session)
    stored = await NotificationsRepository(session).routes()
    role = stored.get(kind, DEFAULT_ROUTES[kind.value])
    phones = await router_.phones_for(kind)
    if not phones:
        raise ConflictError(
            NOBODY_TO_TELL.format(role=role),
            details={"kind": kind.value, "role": role},
        )

    message = test_message(kind.value)
    for phone in phones:
        # Sin `message_id`: no hay ningún mensaje del portal detrás de esto. Y
        # sin `countdown`, que es lo que lo distingue de un aviso automático.
        tasks.send_alert.apply_async(args=[phone, message, kind.value, None])
    logger.info("Test alert queued", extra={"kind": kind.value, "recipients": len(phones)})
    return RouteTested(kind=kind, role=role, sent_to=[_last_digits(phone) for phone in phones])


def _last_digits(phone: str) -> str:
    """Los últimos cuatro dígitos, que alcanzan para reconocer un teléfono propio.

    El número entero no vuelve en la respuesta: es el dato de contacto de una
    persona, y para contestar «¿salió al teléfono correcto?» no hace falta
    repetirlo completo.
    """
    return f"…{phone[-4:]}" if len(phone) > 4 else phone


@router.put(
    "/routes/{kind}",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.WRITE)],
    summary="Say who receives one kind of alert",
)
async def set_route(
    kind: AlertKind, payload: RouteWrite, current_user: CurrentUser, session: Session
) -> RouteRead:
    """The owner (RF-37 of 007)."""
    repository = NotificationsRepository(session)
    await repository.put_route(kind, payload.role, actor_user_id=current_user.id)
    await session.commit()
    return RouteRead(
        kind=kind,
        role=payload.role,
        updated_by_user_id=current_user.id,
        recipients=len(await repository.active_with_role(payload.role)),
    )
