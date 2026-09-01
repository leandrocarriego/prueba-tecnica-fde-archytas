"""Quién mantiene los rubros (010): compras los cambia, ventas los consulta.

La 010 corrige una parte del acuerdo de accesos a la luz de lo que apareció al
construir los rubros: **el rubro es la categoría con la que se compra**, y quien
ve llegar la mercadería es quien está en condiciones de decir a cuál corresponde.

Lo que se fija acá es lo que no estaba probado **por comportamiento**: antes de
esta feature no existía ni una request real que verificara quién llega y quién
no. RF-11 lo pide con todas las letras — «si el rol ventas pide cambiar un rubro,
el sistema debe rechazar el pedido» — y esconder el botón nunca fue el mecanismo.
"""

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.service import CatalogService
from app.modules.identity.permissions import MATRIX, Level, Section
from app.shared.events import NormalizedPriceRow
from tests.factories.catalog_factory import ProductFactory

API_PREFIX = "/api/v1"

pytestmark = [pytest.mark.integration, pytest.mark.database]

# Un nombre que la siembra firmada de la 008 no trae, para que el 201 sea
# sobre el permiso y no sobre el nombre.
A_RUBRO = {"name": "Rubro de prueba 010"}

# Una forma escrita que ni la siembra de la 008 ni ningún otro test conocen: es
# lo que hace que el caso que se abre sea el de este test y no otro.
A_WRITTEN_FORM = "Rubro Nunca Visto 010"


def row(code: str, *, category: str | None = None) -> NormalizedPriceRow:
    """Una fila normalizada de la lista diaria, como la publica `ingestion`.

    Escrita acá y no importada de los tests de la 008: dos archivos de test que
    se importan entre sí se rompen juntos, y esta feature no depende de aquella.
    """
    return NormalizedPriceRow(
        staging_row_id=0,
        product_code=code,
        description=f"Producto {code}",
        price=Decimal("1000"),
        currency="ARS",
        category_raw=category,
        subcategory_raw=None,
        stock=None,
    )


async def rubro_named(client: AsyncClient, name: str) -> dict[str, Any]:
    """Un rubro que compras agrega, que es la única forma que tiene de existir."""
    created = await client.post(f"{API_PREFIX}/categories", json={"name": name})
    assert created.status_code == 201
    rubro: dict[str, Any] = created.json()
    return rubro


class TestPurchasingMaintainsTheRubros:
    """H1: Marcela los agrega, los renombra y los borra."""

    async def test_purchasing_can_add_a_rubro(self, purchasing_client: AsyncClient) -> None:
        """RF-01, que reemplaza a RF-05 de la 008."""
        # Act
        response = await purchasing_client.post(f"{API_PREFIX}/categories", json=A_RUBRO)

        # Assert
        assert response.status_code == 201

    async def test_purchasing_can_rename_one(self, purchasing_client: AsyncClient) -> None:
        """RF-02."""
        # Arrange
        created = await purchasing_client.post(
            f"{API_PREFIX}/categories", json={"name": "Para renombrar"}
        )
        rubro_id = created.json()["id"]

        # Act
        response = await purchasing_client.patch(
            f"{API_PREFIX}/categories/{rubro_id}", json={"name": "Renombrado"}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["name"] == "Renombrado"

    async def test_purchasing_can_delete_an_empty_one(self, purchasing_client: AsyncClient) -> None:
        """RF-03: uno vacío se borra; el motivo cuando no se puede es de la 008."""
        # Arrange
        created = await purchasing_client.post(
            f"{API_PREFIX}/categories", json={"name": "Para borrar"}
        )
        rubro_id = created.json()["id"]

        # Act
        response = await purchasing_client.delete(f"{API_PREFIX}/categories/{rubro_id}")

        # Assert
        assert response.status_code == 204

    async def test_purchasing_reaches_the_rubros_among_its_sections(self) -> None:
        """RF-09: los rubros aparecen entre las secciones a las que compras entra.

        El menú se dibuja filtrando por esto, así que verificar la matriz es
        verificar lo que Marcela ve al entrar.
        """
        # Assert
        assert MATRIX[Section.PRODUCT_CATEGORIES]["PURCHASING"] is Level.WRITE


class TestPurchasingClassifiesTheProducts:
    """H1 del otro lado: los productos sin rubro se movieron con los rubros.

    Es la primera de las cuatro decisiones que la spec puso sobre la mesa para
    confirmar al firmar, y la que más lejos llega: el acuerdo de los accesos
    había dejado «los productos sin rubro» entre las revisiones de ventas, y
    esta feature los mueve por la misma razón que mueve los rubros.

    Sin estos dos tests, de las **cuatro** escrituras de `catalog` sólo tres
    quedaban probadas por el lado que importa —que quien ahora es el dueño
    llegue—, y la que faltaba era justo la de clasificar.
    """

    async def test_purchasing_gives_a_rubro_to_a_product_that_had_none(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """RF-04, que reemplaza a RF-13 de la 008."""
        # Arrange
        waiting = await ProductFactory.create(session)
        rubro = await rubro_named(purchasing_client, "Para clasificar")

        # Act
        response = await purchasing_client.put(
            f"{API_PREFIX}/products/{waiting.id}/category", json={"category_id": rubro["id"]}
        )

        # Assert
        assert response.status_code == 200
        await session.refresh(waiting)
        assert waiting.category_id == rubro["id"]

    async def test_purchasing_moves_one_that_was_already_classified(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """RF-05, que reemplaza a RF-20 de la 008: reclasificar es la misma llamada."""
        # Arrange
        first = await rubro_named(purchasing_client, "Donde estaba")
        second = await rubro_named(purchasing_client, "Donde va")
        classified = await ProductFactory.create(session, category_id=first["id"])

        # Act
        response = await purchasing_client.put(
            f"{API_PREFIX}/products/{classified.id}/category", json={"category_id": second["id"]}
        )

        # Assert
        assert response.status_code == 200
        await session.refresh(classified)
        assert classified.category_id == second["id"]


class TestTheProposalIsPurchasings:
    """RF-13, que reemplaza a RF-15 de la 008: la propuesta cambia de destinatario.

    Aquel requisito le presentaba la propuesta a ventas para que la confirmara o
    la corrigiera. Como acá ventas deja de tener ninguna acción para clasificar,
    se quedaba sin nadie que lo cumpliera: es el mismo requisito con el actor
    cambiado, y por eso lo que se prueba es que **le llega a compras**.

    La 008 ya prueba de dónde sale una propuesta; lo que no probaba nadie es que
    Marcela la reciba y que confirmarla y corregirla sean la misma llamada.
    """

    async def test_the_proposal_reaches_purchasing(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """RF-13: la cola le trae a compras lo que el sistema propone para cada uno."""
        # Arrange — un producto ya clasificado le enseña la subcategoría.
        rubro = await rubro_named(purchasing_client, "Sanitarios de prueba")
        await ProductFactory.create(
            session, category_id=rubro["id"], subcategory_raw="Griferia 010"
        )
        waiting = await ProductFactory.create(session, subcategory_raw="Griferia 010")

        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/categories/unclassified?limit=200")

        # Assert
        assert response.status_code == 200
        item = next(each for each in response.json()["items"] if each["code"] == waiting.code)
        assert item["proposed_category_id"] == rubro["id"]
        assert item["proposed_category_name"] == "Sanitarios de prueba"

    async def test_confirming_and_correcting_are_the_same_call(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """RF-13: Marcela confirma una propuesta, corrige otra, y las dos se aplican."""
        # Arrange — los dos que esperan comparten la subcategoría, así que los
        # dos reciben la misma propuesta: lo que los distingue es la decisión.
        proposed = await rubro_named(purchasing_client, "Lo propuesto")
        another = await rubro_named(purchasing_client, "Lo corregido")
        await ProductFactory.create(
            session, category_id=proposed["id"], subcategory_raw="Bachas 010"
        )
        confirmed = await ProductFactory.create(session, subcategory_raw="Bachas 010")
        corrected = await ProductFactory.create(session, subcategory_raw="Bachas 010")

        # Act
        confirming = await purchasing_client.put(
            f"{API_PREFIX}/products/{confirmed.id}/category",
            json={"category_id": proposed["id"]},
        )
        correcting = await purchasing_client.put(
            f"{API_PREFIX}/products/{corrected.id}/category",
            json={"category_id": another["id"]},
        )

        # Assert
        assert (confirming.status_code, correcting.status_code) == (200, 200)
        await session.refresh(confirmed)
        await session.refresh(corrected)
        assert confirmed.category_id == proposed["id"]
        assert corrected.category_id == another["id"]


class TestTheCircuitOfANewWrittenForm:
    """RF-06 y RF-14: el circuito entero, por la cola y no por el servicio.

    Es lo que la spec promete en su objetivo —que el circuito de una forma
    escrita nueva lo pueda cerrar una sola persona— y lo que el plan marcó como
    el tramo que faltaba: los tests de la 008 llaman al `TriageService` y
    saltean la cola, así que RF-24 y RF-25 de aquella spec están verdes por la
    razón equivocada.

    Acá no se llama a ningún servicio. Llega la lista, Marcela pide su cola,
    resuelve el caso que encuentra, y se verifica lo que queda después.
    """

    async def test_purchasing_closes_it_from_the_review_queue(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """RF-06, RF-14, y la retroactividad de RF-25 de la 008.

        El batch va primero porque es el que siembra el catálogo: un producto no
        se agrega solo en una corrida posterior (RF-07 de la 008).
        """
        # Arrange — la lista trae una forma escrita que nadie decidió, en dos
        # productos, que es lo que hace que el caso sea uno y no dos.
        await CatalogService(session).apply_price_batch(
            batch_id=1,
            rows=(
                row("OWN-0001", category=A_WRITTEN_FORM),
                row("OWN-0002", category=A_WRITTEN_FORM),
            ),
        )
        await session.flush()
        rubro = await rubro_named(purchasing_client, "El que decide Marcela")

        # Act — el caso aparece en la cola de compras...
        queue = await purchasing_client.get(
            f"{API_PREFIX}/triage/cases?kind=unknown_category&limit=200"
        )
        case = next(
            each
            for each in queue.json()["items"]
            if each["payload"]["category_text"] == A_WRITTEN_FORM
        )
        # ...y se resuelve desde ahí, sin cambiar de sección, que es RF-14.
        decided = await purchasing_client.post(
            f"{API_PREFIX}/triage/cases/{case['id']}/resolution",
            json={"decision": {"category_id": rubro["id"]}, "remember": True},
        )

        # Assert
        assert queue.status_code == 200
        assert case["payload"]["products"] == 2
        assert decided.status_code == 200

        # La decisión queda guardada como equivalencia (RF-06).
        aliases = (await purchasing_client.get(f"{API_PREFIX}/categories/aliases")).json()
        assert any(
            alias["text_original"] == A_WRITTEN_FORM and alias["category_id"] == rubro["id"]
            for alias in aliases
        )

        # Y los dos productos que la esperaban quedan clasificados: la mitad
        # retroactiva del circuito, que es la que se rompe en silencio.
        waiting = (
            await purchasing_client.get(f"{API_PREFIX}/categories/unclassified?limit=200")
        ).json()
        assert not any(item["code"] in {"OWN-0001", "OWN-0002"} for item in waiting["items"])


class TestSalesSeesThemAndCannotChangeThem:
    """H2: Julián los consulta, y el sistema le rechaza el cambio igual."""

    @pytest.mark.parametrize(
        "path", ["/categories", "/categories/unclassified", "/categories/aliases"]
    )
    async def test_sales_still_reads_them(self, sales_client: AsyncClient, path: str) -> None:
        """RF-10: lo que pierde es cambiarlos, no verlos.

        El que se rompe sin ruido: al declarar `require_section` en las tres
        lecturas es fácil pedir `WRITE` por simetría con las escrituras y
        cerrarle la pantalla a ventas sin que nada se ponga rojo.
        """
        # Act
        response = await sales_client.get(f"{API_PREFIX}{path}")

        # Assert
        assert response.status_code == 200

    async def test_sales_cannot_add_a_rubro(self, sales_client: AsyncClient) -> None:
        """RF-11."""
        # Act
        response = await sales_client.post(f"{API_PREFIX}/categories", json=A_RUBRO)

        # Assert
        assert response.status_code == 403

    async def test_sales_cannot_rename_one(self, sales_client: AsyncClient) -> None:
        """RF-11."""
        # Act
        response = await sales_client.patch(f"{API_PREFIX}/categories/1", json=A_RUBRO)

        # Assert
        assert response.status_code == 403

    async def test_sales_cannot_delete_one(self, sales_client: AsyncClient) -> None:
        """RF-11."""
        # Act
        response = await sales_client.delete(f"{API_PREFIX}/categories/1")

        # Assert
        assert response.status_code == 403

    async def test_sales_cannot_classify_a_product(self, sales_client: AsyncClient) -> None:
        """RF-11: clasificar es cambiar, y confirmar una propuesta es clasificar."""
        # Act
        response = await sales_client.put(
            f"{API_PREFIX}/products/1/category", json={"category_id": 1}
        )

        # Assert
        assert response.status_code == 403

    async def test_the_owner_still_does_everything(self, owner_client: AsyncClient) -> None:
        """Ninguna sección se le cierra al dueño, y ésta tampoco."""
        # Act
        response = await owner_client.post(f"{API_PREFIX}/categories", json={"name": "Del dueño"})

        # Assert
        assert response.status_code == 201


class TestTheCatalogDidNotMoveWithThem:
    """La consecuencia deliberada que la spec declara: se mueven **sólo** los rubros."""

    async def test_the_product_catalog_is_still_sales(self) -> None:
        """Rubros y catálogo dejan de viajar juntos, y es a propósito.

        «Acompañar» el cambio moviendo también esta fila rompe el alcance de la
        spec sin que ningún otro test lo note: la 010 dice, en *Fuera de
        alcance*, que el catálogo y las correcciones de producto siguen siendo
        de ventas.
        """
        # Assert
        assert MATRIX[Section.PRODUCT_CATALOG]["SALES"] is Level.WRITE
        assert MATRIX[Section.PRODUCT_CATALOG]["PURCHASING"] is Level.NONE


class TestARubroChangeIsAPurchasingFact:
    """La decisión del humano del 2026-08-31, y el test que impide que se «limpie».

    Mover los rubros a compras sin mover la sección del cambio dejaba a Marcela
    sin ver en el historial lo que ella misma hace, y a Julián —que ya no puede
    hacerlo— viéndolo. Eso rompe **RF-19 de la 003**, que está firmada.
    """

    async def test_purchasing_sees_its_own_rubro_change_in_the_history(
        self, purchasing_client: AsyncClient
    ) -> None:
        """RF-19 de 003, sostenida después de mover el dueño de los rubros."""
        # Arrange — Marcela agrega un rubro.
        await purchasing_client.post(f"{API_PREFIX}/categories", json={"name": "Del historial"})

        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 200
        entries = response.json()["items"]
        assert any(entry["entity_type"] == "catalog.product_category" for entry in entries)

    async def test_sales_no_longer_sees_it(self, sales_client: AsyncClient) -> None:
        """La otra mitad: quien ya no puede cambiarlos tampoco los ve en su historial.

        No es una pérdida: es la consecuencia de que el hecho haya cambiado de
        área junto con quien lo decide.
        """
        # Act
        response = await sales_client.get(f"{API_PREFIX}/operations/audit")

        # Assert
        assert response.status_code == 200
        entries = response.json()["items"]
        assert all(entry["entity_type"] != "catalog.product_category" for entry in entries)
