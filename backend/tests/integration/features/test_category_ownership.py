"""Quién mantiene los rubros (010): compras los cambia, ventas los consulta.

La 010 corrige una parte del acuerdo de accesos a la luz de lo que apareció al
construir los rubros: **el rubro es la categoría con la que se compra**, y quien
ve llegar la mercadería es quien está en condiciones de decir a cuál corresponde.

Lo que se fija acá es lo que no estaba probado **por comportamiento**: antes de
esta feature no existía ni una request real que verificara quién llega y quién
no. RF-11 lo pide con todas las letras — «si el rol ventas pide cambiar un rubro,
el sistema debe rechazar el pedido» — y esconder el botón nunca fue el mecanismo.
"""

import pytest
from httpx import AsyncClient

from app.modules.identity.permissions import MATRIX, Level, Section

API_PREFIX = "/api/v1"

pytestmark = [pytest.mark.integration, pytest.mark.database]

# Un nombre que la siembra firmada de la 008 no trae, para que el 201 sea
# sobre el permiso y no sobre el nombre.
A_RUBRO = {"name": "Rubro de prueba 010"}


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
