"""Role-based access control, over HTTP.

The business has three roles — OWNER, PURCHASING, SALES — and authorisation is
enforced per resource, not by hiding links in a menu. These tests call the real
endpoints with a real token for each role.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User, UserRole
from app.modules.ingestion.service import IngestionService
from tests.conftest import API_PREFIX, authorization_header
from tests.factories.portal_factory import (
    sales_page_bytes,
    supplier_ledger_with_a_broken_payment,
)
from tests.factories.user_factory import DEFAULT_PASSWORD, UserFactory

# No password: the owner hands out accesses, not credentials (RF-44). The phone
# is required, because that is where the invitation goes.
NEW_USER = {
    "email": "alta@example.com",
    "name": "Alta",
    "phone": "+5491144445555",
    "role": UserRole.SALES.value,
}
# A key of the catalog: since 003 the list is closed, so an invented key is
# refused before authorisation ever becomes the interesting part of the test.
PARAMETERS = {"items": [{"key": "price_update.interval_hours", "value": 24}]}


@pytest.mark.integration
@pytest.mark.database
class TestPurchasingRole:
    """What whoever handles purchasing can and cannot do."""

    async def test_cannot_create_a_user(self, purchasing_client: AsyncClient) -> None:
        """Handing out accounts and roles is the owner's decision."""
        # Act
        response = await purchasing_client.post(f"{API_PREFIX}/users", json=NEW_USER)

        # Assert
        assert response.status_code == 403

    async def test_cannot_update_the_business_parameters(
        self, purchasing_client: AsyncClient
    ) -> None:
        """These values decide how the platform behaves: owner only."""
        # Act
        response = await purchasing_client.put(
            f"{API_PREFIX}/operations/parameters", json=PARAMETERS
        )

        # Assert
        assert response.status_code == 403

    async def test_cannot_list_users(self, purchasing_client: AsyncClient) -> None:
        """RF-24: the access screens are the owner's, reading them included.

        This used to be allowed, on the argument that the team should know who
        its colleagues are. No requirement asks for it, and the list carries
        everybody's email, phone and role — so it went back behind the same
        door as the rest of the administration.
        """
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/users")

        # Assert
        assert response.status_code == 403

    async def test_can_read_the_job_history(self, purchasing_client: AsyncClient) -> None:
        """Whether last night's extraction ran is not privileged information."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/jobs")

        # Assert
        assert response.status_code == 200

    async def test_cannot_read_the_business_parameters(
        self, purchasing_client: AsyncClient
    ) -> None:
        """Reading the rules is as restricted as writing them."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/parameters")

        # Assert
        assert response.status_code == 403

    async def test_cannot_deactivate_a_user(
        self, purchasing_client: AsyncClient, sales_user: User
    ) -> None:
        """Disabling a colleague's account is an administrative act."""
        # Act
        response = await purchasing_client.post(f"{API_PREFIX}/users/{sales_user.id}/deactivate")

        # Assert
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.database
class TestSalesRole:
    """Sales has the same operational reach as purchasing."""

    async def test_cannot_create_a_user(self, sales_client: AsyncClient) -> None:
        """Administration is closed to the operational roles."""
        assert (await sales_client.post(f"{API_PREFIX}/users", json=NEW_USER)).status_code == 403

    async def test_can_read_its_own_account(self, sales_client: AsyncClient) -> None:
        """Every authenticated role can read itself."""
        # Act
        response = await sales_client.get(f"{API_PREFIX}/auth/me")

        # Assert
        assert response.status_code == 200
        assert response.json()["user"]["role"] == UserRole.SALES.value


@pytest.mark.integration
@pytest.mark.database
class TestOwnerRole:
    """The owner is admitted everywhere."""

    async def test_can_create_a_user(self, owner_client: AsyncClient) -> None:
        """The route the operational roles are refused."""
        # Act
        response = await owner_client.post(f"{API_PREFIX}/users", json=NEW_USER)

        # Assert
        assert response.status_code == 201
        assert response.json()["email"] == NEW_USER["email"]

    async def test_can_update_the_business_parameters(self, owner_client: AsyncClient) -> None:
        """Writing the rules is the owner's."""
        # Act
        response = await owner_client.put(f"{API_PREFIX}/operations/parameters", json=PARAMETERS)

        # Assert
        assert response.status_code == 200
        assert response.json()[0]["key"] == "price_update.interval_hours"
        assert response.json()[0]["value"] == 24

    async def test_can_list_users(self, owner_client: AsyncClient) -> None:
        """The only role that reaches the list at all."""
        assert (await owner_client.get(f"{API_PREFIX}/users")).status_code == 200

    async def test_can_change_a_role(self, owner_client: AsyncClient, sales_user: User) -> None:
        """Deciding who does what is the point of the role."""
        # Act
        response = await owner_client.patch(
            f"{API_PREFIX}/users/{sales_user.id}", json={"role": UserRole.PURCHASING.value}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.PURCHASING.value


@pytest.mark.integration
@pytest.mark.database
class TestAnonymousCallers:
    """No credentials, no answer."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", f"{API_PREFIX}/users"),
            ("GET", f"{API_PREFIX}/auth/me"),
            ("GET", f"{API_PREFIX}/operations/jobs"),
            ("GET", f"{API_PREFIX}/operations/parameters"),
        ],
    )
    async def test_a_protected_route_without_a_token_is_401(
        self, client: AsyncClient, method: str, path: str
    ) -> None:
        """A missing token is not a 403: the caller was never identified."""
        # Act
        response = await client.request(method, path)

        # Assert
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_an_invalid_token_is_401(self, client: AsyncClient) -> None:
        """A token that cannot be verified identifies nobody."""
        # Act
        response = await client.get(
            f"{API_PREFIX}/users", headers={"Authorization": "Bearer not-a-token"}
        )

        # Assert
        assert response.status_code == 401

    async def test_the_token_of_a_deactivated_user_is_401(
        self,
        client: AsyncClient,
        owner_client: AsyncClient,
        sales_user: User,
        session: AsyncSession,
    ) -> None:
        """Deactivating an account has to close the session it is holding."""
        # Arrange
        headers = await authorization_header(session, sales_user)
        assert (await client.get(f"{API_PREFIX}/auth/me", headers=headers)).status_code == 200

        # Act
        await owner_client.post(f"{API_PREFIX}/users/{sales_user.id}/deactivate")
        response = await client.get(f"{API_PREFIX}/auth/me", headers=headers)

        # Assert
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.database
class TestOwnAccountOnly:
    """Routes that act on the caller take the caller from the token."""

    async def test_change_password_cannot_be_pointed_at_another_account(
        self, sales_client: AsyncClient
    ) -> None:
        """The body carries passwords, never a user id.

        If the endpoint took a target user, a session would be enough to
        overwrite somebody else's credential.
        """
        # Act
        response = await sales_client.post(
            f"{API_PREFIX}/auth/password/change",
            json={
                "current_password": DEFAULT_PASSWORD,
                "new_password": "otra-clave-2026",
                # Ignored by the schema: there is no target field to abuse.
                "user_id": 1,
            },
        )

        # Assert
        assert response.status_code == 204

    async def test_a_wrong_current_password_is_401(self, sales_client: AsyncClient) -> None:
        """Holding the session is not enough to change the password."""
        # Act
        response = await sales_client.post(
            f"{API_PREFIX}/auth/password/change",
            json={"current_password": "incorrecta", "new_password": "otra-clave-2026"},
        )

        # Assert
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.database
class TestRolesInTheDatabase:
    """The three roles the business actually has."""

    @pytest.mark.parametrize("role", list(UserRole))
    async def test_every_role_can_authenticate(
        self, client: AsyncClient, session: AsyncSession, role: UserRole
    ) -> None:
        """No role is locked out of the platform it was given."""
        # Arrange
        user = await UserFactory.create(session, role=role)

        # Act
        response = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": user.email, "password": DEFAULT_PASSWORD},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["user"]["role"] == role.value


@pytest.mark.integration
@pytest.mark.database
class TestTheCommercialDashboardIsNotForPurchasing:
    """RF-08 y RF-29 de 009, **por comportamiento y no por construcción**.

    La matriz ya decía que compras no llega ni a las ventas ni al tablero, y el
    test que la recorre lo verificaba en la tabla. Lo que faltaba era una request
    de verdad: RF-08 dice que Marcela no llega «ni pegando su dirección», y eso
    sólo lo prueba pegando la dirección.
    """

    async def test_purchasing_cannot_read_the_dashboard(
        self, purchasing_client: AsyncClient
    ) -> None:
        """RF-08."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/dashboard/sales")

        # Assert
        assert response.status_code == 403

    async def test_purchasing_cannot_read_the_catalog_cuts(
        self, purchasing_client: AsyncClient
    ) -> None:
        """RF-08: los tres cortes del catálogo son del mismo tablero."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/dashboard/catalog")

        # Assert
        assert response.status_code == 403

    async def test_purchasing_cannot_list_the_sales(self, purchasing_client: AsyncClient) -> None:
        """RF-08."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/sales")

        # Assert
        assert response.status_code == 403

    async def test_purchasing_cannot_reach_the_review_queue(
        self, purchasing_client: AsyncClient
    ) -> None:
        """RF-29: resolver una venta apartada es de ventas y del dueño, y de nadie más."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/sales/review")

        # Assert
        assert response.status_code == 403

    async def test_purchasing_cannot_correct_a_sale(self, purchasing_client: AsyncClient) -> None:
        """RF-29: y la escritura también, no sólo la lectura de la cola."""
        # Act
        response = await purchasing_client.patch(f"{API_PREFIX}/sales/1", json={"quantity": 3})

        # Assert
        assert response.status_code == 403

    async def test_sales_reaches_the_dashboard_and_the_queue(
        self, sales_client: AsyncClient
    ) -> None:
        """La otra mitad: cerrarle la puerta a compras no puede cerrársela a ventas."""
        # Act
        board = await sales_client.get(f"{API_PREFIX}/dashboard/sales")
        queue = await sales_client.get(f"{API_PREFIX}/sales/review")

        # Assert
        assert board.status_code == 200
        assert queue.status_code == 200

    async def test_the_owner_reaches_them_too(self, owner_client: AsyncClient) -> None:
        """El dueño ve todo, y esta sección no es la excepción."""
        # Act
        board = await owner_client.get(f"{API_PREFIX}/dashboard/sales")
        queue = await owner_client.get(f"{API_PREFIX}/sales/review")

        # Assert
        assert board.status_code == 200
        assert queue.status_code == 200


@pytest.mark.integration
@pytest.mark.database
class TestTheOrdersAndTheInboxAreNotForSales:
    """RF-09 y RF-46 de 007, **por comportamiento**.

    Los dos requisitos dicen que Julián no llega «ni pegando su dirección», y eso
    sólo se prueba pegando la dirección. Hasta acá estaban probados por
    construcción: la matriz decía que no, y nadie lo había intentado.
    """

    async def test_sales_cannot_see_the_purchase_orders(self, sales_client: AsyncClient) -> None:
        """RF-09."""
        # Act
        response = await sales_client.get(f"{API_PREFIX}/purchase-orders")

        # Assert
        assert response.status_code == 403

    async def test_sales_cannot_resolve_a_held_order(self, sales_client: AsyncClient) -> None:
        """RF-53: resolver una orden apartada es del dueño y de compras."""
        # Act
        response = await sales_client.post(
            f"{API_PREFIX}/purchase-orders/1/resolution", json={"supplier_id": 1}
        )

        # Assert
        assert response.status_code == 403

    async def test_sales_cannot_open_the_inbox(self, sales_client: AsyncClient) -> None:
        """RF-46, que incluye los mensajes de stock bajo."""
        # Act
        response = await sales_client.get(f"{API_PREFIX}/messages")

        # Assert
        assert response.status_code == 403

    async def test_purchasing_reaches_both(self, purchasing_client: AsyncClient) -> None:
        """La otra mitad: cerrarle la puerta a ventas no puede cerrársela a compras."""
        # Act
        orders = await purchasing_client.get(f"{API_PREFIX}/purchase-orders")
        inbox = await purchasing_client.get(f"{API_PREFIX}/messages")

        # Assert
        assert orders.status_code == 200
        assert inbox.status_code == 200

    async def test_only_the_owner_decides_who_gets_told_what(
        self, purchasing_client: AsyncClient, owner_client: AsyncClient
    ) -> None:
        """RF-37: repartir los avisos es una decisión sobre el equipo."""
        # Act
        refused = await purchasing_client.get(f"{API_PREFIX}/alerts/routes")
        allowed = await owner_client.get(f"{API_PREFIX}/alerts/routes")

        # Assert
        assert refused.status_code == 403
        assert allowed.status_code == 200

    async def test_the_owner_changes_a_route_and_sales_is_not_offerable(
        self, owner_client: AsyncClient
    ) -> None:
        """RF-37, ahora que hay pantalla, y RF-46, que la limita.

        La ruta aceptaba cualquier string mientras nadie pudiera llamarla. Con
        un control en `/configuracion`, un rol que no existe apuntaría un tipo
        de aviso a nadie, y ventas sería elegible para los reclamos de la
        bandeja a la que ventas no entra.
        """
        # Act
        changed = await owner_client.put(
            f"{API_PREFIX}/alerts/routes/PAYMENT_CLAIM", json={"role": "OWNER"}
        )
        to_sales = await owner_client.put(
            f"{API_PREFIX}/alerts/routes/PAYMENT_CLAIM", json={"role": "SALES"}
        )

        # Assert
        assert changed.status_code == 200
        assert changed.json()["role"] == "OWNER"
        assert to_sales.status_code == 422

    async def test_purchasing_can_read_the_senders_it_filters_by(
        self, purchasing_client: AsyncClient, sales_client: AsyncClient
    ) -> None:
        """RF-26: el filtro por proveedor necesita saber por cuáles se filtra."""
        # Act
        allowed = await purchasing_client.get(f"{API_PREFIX}/messages/senders")
        refused = await sales_client.get(f"{API_PREFIX}/messages/senders")

        # Assert
        assert allowed.status_code == 200
        assert isinstance(allowed.json(), list)
        assert refused.status_code == 403


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.portal
class TestEachOneSeesTheirOwnPendingThings:
    """H3 de la 011: la cola de revisión es una sola y cada uno ve su parte.

    Es la clase de test que la feature más necesita, porque el modo de fallar es
    silencioso: hasta la 011 la puerta decía quién entraba, y ahora entra
    cualquiera con sesión y lo que recorta es el **servicio**. Una puerta cerrada
    se prueba sola —el 403 salta—; un filtro que se olvida no salta, sólo muestra
    de más.

    El reparto lo fijó el Lead el 2026-08-31 contra `PROJECT_BRIEF.md`: los siete
    `kind` que existían antes de la 011 nacen de la ingesta del portal y son de
    compras, los precios incluidos —el brief dice de Marcela que sobre los
    precios de lista «sí puede … resolver lo que el sistema haya apartado»—. El
    primero de ventas lo trae esta feature: las ventas que no se pudieron leer.
    """

    @staticmethod
    async def both_areas_have_something(session: AsyncSession) -> None:
        """Un pendiente de compras y otro de ventas, para que el filtro tenga qué filtrar."""
        service = IngestionService(session)
        await service.normalize_supplier_ledger(
            raw_document_id=1, content=supplier_ledger_with_a_broken_payment()
        )
        await service.normalize_sales(raw_document_id=2, content=sales_page_bytes())
        await session.commit()

    async def test_purchasing_sees_purchasing_and_not_sales(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """RF-12 de un lado."""
        # Arrange
        await self.both_areas_have_something(session)

        # Act
        body = (await purchasing_client.get(f"{API_PREFIX}/triage/cases?limit=200")).json()

        # Assert
        assert {item["section"] for item in body["items"]} == {"PURCHASING"}

    async def test_sales_sees_sales_and_not_purchasing(
        self, session: AsyncSession, sales_client: AsyncClient
    ) -> None:
        """RF-12 del otro. Es lo que la 011 le agrega a Julián: sus ventas apartadas."""
        # Arrange
        await self.both_areas_have_something(session)

        # Act
        body = (await sales_client.get(f"{API_PREFIX}/triage/cases?limit=200")).json()

        # Assert
        assert {item["section"] for item in body["items"]} == {"SALES"}

    async def test_the_owner_sees_both(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """RF-14."""
        # Arrange
        await self.both_areas_have_something(session)

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/triage/cases?limit=200")).json()

        # Assert
        assert {item["section"] for item in body["items"]} == {"PURCHASING", "SALES"}

    async def test_nobody_resolves_what_is_not_theirs(
        self, session: AsyncSession, sales_client: AsyncClient, owner_client: AsyncClient
    ) -> None:
        """RF-13, y con el id en la mano.

        No alcanza con que el listado no lo muestre: un id es adivinable, y una
        restricción que se apoya en que la pantalla omita algo no es una
        restricción.
        """
        # Arrange
        await self.both_areas_have_something(session)
        listed = (await owner_client.get(f"{API_PREFIX}/triage/cases?limit=200")).json()
        of_purchasing = next(item for item in listed["items"] if item["section"] == "PURCHASING")

        # Act
        response = await sales_client.post(
            f"{API_PREFIX}/triage/cases/{of_purchasing['id']}/resolution",
            json={"decision": {"action": "ignore"}, "remember": False},
        )

        # Assert
        assert response.status_code == 403

    async def test_the_owner_narrows_the_list_to_one_area(
        self, session: AsyncSession, owner_client: AsyncClient
    ) -> None:
        """RF-22: el filtro por área, que es del dueño porque es el único que ve dos."""
        # Arrange
        await self.both_areas_have_something(session)

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/triage/cases?limit=200&section=SALES")).json()

        # Assert
        assert {item["section"] for item in body["items"]} == {"SALES"}

    async def test_the_filter_narrows_and_never_widens(
        self, session: AsyncSession, sales_client: AsyncClient
    ) -> None:
        """RF-22 tiene un piso, y este es el test que lo pone.

        Se rechaza en vez de contestar una lista vacía: una lista vacía se lee
        como «no hay nada en compras», que es otra afirmación y es mentira.
        """
        # Arrange
        await self.both_areas_have_something(session)

        # Act
        response = await sales_client.get(f"{API_PREFIX}/triage/cases?section=PURCHASING")

        # Assert
        assert response.status_code == 403

    async def test_the_three_reach_the_screen(
        self,
        purchasing_client: AsyncClient,
        sales_client: AsyncClient,
        owner_client: AsyncClient,
    ) -> None:
        """RF-06: la puerta no es lo que recorta, y por eso está abierta para los tres.

        Con la cola vacía y sin nada que ver, los tres tienen que entrar igual.
        Que a alguno le responda 403 sería la 011 al revés: una lista sola a la
        que no todos llegan es otra vez un lugar más al que hay que acordarse de
        entrar.
        """
        # Act / Assert
        for client in (purchasing_client, sales_client, owner_client):
            assert (await client.get(f"{API_PREFIX}/triage/cases")).status_code == 200

    async def test_the_rules_stay_where_they_were(self, sales_client: AsyncClient) -> None:
        """Abrir la cola no abrió las reglas aprendidas, y es deliberado.

        Toda regla aprendida es de precios —las cuatro `kind` que la 011 agrega
        van con `remember=False` porque aprender quedó fuera de alcance—, así que
        `/triage/rules` sigue pidiendo `PRICES`. Es también lo que obliga a la
        pantalla a condicionar ese pedido: sin condición, para quien no alcanza
        `PRICES` es un 403 que `rules ?? []` disfraza de lista vacía.
        """
        # Act
        response = await sales_client.get(f"{API_PREFIX}/triage/rules")

        # Assert
        assert response.status_code == 403
