# Fixtures del portal SIGProv

Lo que la suite usa en lugar del portal. `TEST-03` es **Blocker**: los parsers se testean contra
esto, nunca contra SIGProv en vivo, y el corolario es que **la suite completa corre con el portal
apagado**. Por eso estos archivos se versionan.

| Archivo | Qué es | Para qué |
|---|---|---|
| `price-list-2026-08-28.xlsx` | El archivo del día, tal como lo descargó el portal | El parser de la lista |
| `price-list-broken-2026-08-28.xlsx` | **Derivado a mano** del anterior | La cuarentena |
| `price-list-page-2026-08-28.html` | La sección de precios renderizada | La navegación: encontrar el botón de descarga |
| `price-history-page-2026-08-28.html` | La pantalla de historial de un producto | El parser del historial publicado (RF-38) |

## El archivo del día

Una hoja, `Precios`. Fila 1 de encabezados y 100 de productos. Seis columnas: `Codigo`,
`Descripcion`, `Categoria`, `Subcategoria`, `Precio`, `Stock`.

Dos hechos que el parser puede dar por ciertos, y que conviene no volver a averiguar:

- **`Precio` viene como entero**, no como texto. En la pantalla se ve `$48.210` y en el archivo es
  `48210`: el punto de la pantalla es separador de miles, no decimal. No hay centavos en ninguna de
  las cien filas.
- **`Categoria` y `Subcategoria` vienen sucias** —`PINTURAS Y ADHESIVOS`, `Pinturas/Adhesivos` y
  `Pinturas y Adhesivos` son el mismo rubro—. P1 **no las interpreta**: las guarda tal cual.
  Unificarlas es P7.

## El archivo roto

**No existe en el portal: se derivó del archivo real.** Se rompe **una sola celda por fila**, para
que el test pueda afirmar por qué se apartó cada una sin ambigüedad. El resto de las filas quedó
intacto, que es justamente lo que RF-06 exige comprobar: una fila rota no frena a las demás.

| Fila | Código | Qué tiene | Requisito |
|---|---|---|---|
| 8 | `COR-0007` | `Precio` = `"CONSULTAR"` — texto donde va un número | RF-06 |
| 14 | `COR-0013` | `Precio` vacío | RF-06 |
| 22 | `COR-0021` | `Precio` = `-5000` — negativo | RF-06 |
| 35 | `COR-0034` | `Precio` = `"48.210"` — número **como texto**, con separador de miles | RF-06 |
| 51 | *(vacío)* | `Codigo` vacío | RF-06 |
| 67 | `COR-0065` | `Codigo` duplicado: repite el de la fila 66 | RF-06 |
| 102 | `COR-0999` | Formato **válido**, producto que el sistema no conoce | RF-07 |

**Los totales que un test puede afirmar:** 101 filas de datos → **94 válidas de productos conocidos,
6 apartadas por formato, 1 apartada por desconocida**.

La última no es una fila rota y no se comporta como tal: en la **primera** corrida se registra como
producto conocido junto con el resto (RF-02), y sólo a partir de la **segunda** queda apartada
(RF-07). Es la diferencia de comportamiento entre dos corridas consecutivas, y es lo más fácil de
romper sin darse cuenta.

## Recapturar

Los `.html` se capturan con el DOM renderizado —`copy(document.documentElement.outerHTML)` en la
consola, o `page.content()` en Playwright—, **no** con "Guardar página como": eso reescribe las rutas
y arrastra una carpeta de bundles del proveedor que acá no sirve para nada.

Antes de commitear un `.html` recapturado, dos chequeos:

```bash
file -I price-list-page-*.html          # tiene que decir charset=utf-8
grep -iE 'csrf|session|token|usuario'   # el Artículo VII: nada de credenciales acá
```

Un fixture con los bytes mal es peor que no tenerlo: hace que alguien "arregle" el parser para
tolerar una corrupción que en producción no existe.
