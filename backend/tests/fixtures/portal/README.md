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
| `invoices-page-2026-08-29.html` | La sección `/facturas` renderizada, las 100 filas | La navegación y el parser de la tabla de facturas (004) |
| `invoice-F-8411-text.pdf` | Factura en PDF **con capa de texto** | El lector de PDF (004) |
| `invoice-F-9936-scanned.pdf` | Factura en PDF **escaneado**: un JPEG, sin texto | El OCR (004) |
| `invoice-F-7797.xlsx` | Factura en planilla, con el encabezado corrido | El lector de planillas (004) |
| `suppliers-ledger-page-2026-08-29.html` | `/estado-cuenta` con la primera fila **ya expandida** | El padrón: los ocho proveedores y su ficha (004) |
| `purchase-orders-page-2026-08-29.html` | La sección `/ordenes-compra` renderizada, las 40 filas | La navegación y el parser de órdenes de compra (007) |

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

## Las facturas (004)

Capturadas el **2026-08-29**. Cuatro hechos medidos sobre las 100 filas, que el parser puede dar por
ciertos:

- **La tabla ya trae los cuatro datos de cabecera** —`Proveedor`, `Nro. Factura`, `Fecha`, `Monto`—
  y **no hay una sola celda vacía** en ninguna columna. Las fechas vienen en ISO (`2026-05-03`) y los
  montos con `$` y separador de miles (`$223.376`), sin centavos.
- **Los formatos son tres**, en la columna `Tipo`: 46 `PDF (escaneado)`, 29 `Excel`, 25 `PDF`. No hay
  paginación: las 100 filas están en una sola pantalla.
- **24 grafías distintas de proveedor** para 8 proveedores reales, y **ningún** par
  (proveedor, número) repetido.
- **Dentro del archivo, la fecha viene en `dd/mm/aaaa`** —`03/05/2026`—, no en ISO como en la tabla.

Y una trampa que costó encontrar y no conviene volver a pisar:

> **El CUIT impreso en la factura es el de Cordillera, no el del proveedor.** Todas dicen
> `Cliente: Ferreteria Industrial Cordillera - CUIT 30-71234567-8`. Un parser que se quede con el
> primer CUIT que encuentre le asigna el mismo proveedor a las cien.

La planilla trae el encabezado **corrido a `A2`**, filas vacías intercaladas y una fila `TOTAL` al
pie: se lee buscando las etiquetas por nombre en toda la hoja, no por posición.

El escaneado es un único JPEG de 800×600 a 72 DPI sin capa de texto. La medición de OCR sobre doce
como éste está en `docs/specs/004-invoices-suppliers/research.md`.

## Las órdenes de compra (007)

Capturada el **2026-08-29** de `/ordenes-compra`. Siete columnas —`Nro. OC`, `Fecha`, `Proveedor`,
`Producto/insumo`, `Cantidad`, `Monto estimado`, `Estado`—, 40 filas, sin paginación. Cuatro hechos
medidos que el parser puede dar por ciertos:

- **Una orden es un producto.** Los 40 números de OC son distintos: no hay órdenes de varias líneas,
  y por lo tanto no hay pantalla de detalle que abrir.
- **El producto viene identificado con el código del catálogo** y enlazado a su ficha:
  `COR-0078 - Sujecion - Articulo 78` → `/precios/p78?de=ordenes`. El código de la celda es el mismo
  `COR-####` de la lista de precios, así que la orden se cruza con el catálogo sin adivinar por
  nombre.
- **Los cuatro estados son texto**, y sus conteos son los del relevamiento: 14 `Pendiente de envio`,
  5 `Enviada al proveedor`, 10 `Confirmada por proveedor`, 11 `Recibida`. 20 proveedores.
- **Hay una sola fecha por orden**, en ISO, y el monto viene con `$` y separador de miles, sin
  centavos — igual que en facturas.

Y dos hechos que **no** son del parser sino de la feature, y que conviene no volver a medir:

> **El portal no publica desde cuándo una orden está en su estado.** La única fecha es la de la
> orden. "Días en el mismo estado" no se puede leer del origen: se sabe recién cuando el sistema
> observa el cambio por sí mismo.

> **Ninguna de las 40 repite el par (proveedor, producto).** El caso que RF-15 tiene que detectar no
> existe en los datos reales: para testear la detección de pedido repetido hay que derivar un
> fixture a mano, como se hizo con `price-list-broken`.

## El padrón de proveedores (004)

**No hay una sección `/proveedores` en el portal.** El padrón es `/estado-cuenta`: ocho filas, una
por proveedor real, con el saldo y un control *Ver detalle*. Lo dice la propia pantalla —"cuenta
corriente agrupada por proveedor real"—, y es lo que hace de esas ocho razones sociales el padrón
canónico contra el que se resuelven las 24 grafías.

Dos cosas que el extractor tiene que saber:

- **El detalle se expande con un click y la URL no cambia.** No hay enlace que seguir: son ocho
  clicks en la misma pantalla. Por eso el fixture se capturó con una fila ya expandida.
- **Ahí, y sólo ahí, están el CUIT, el correo, el teléfono y la condición de pago** —`45 dias`, en
  texto—. Ninguna otra pantalla del portal publica un CUIT de proveedor: el único CUIT que aparece
  en `/configuracion` y en los archivos de factura es el de **Cordillera**, el cliente.

El detalle expandido trae además los movimientos de cuenta corriente —facturas y pagos con su
saldo—. Eso es **P5**, y la 004 no lo carga.

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
