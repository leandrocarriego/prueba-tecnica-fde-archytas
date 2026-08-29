# Investigación — Cómo se leen las facturas, y con qué (D1)

**Feature:** 004-invoices-suppliers · **Fecha:** 2026-08-29 · **Rol:** Backend-Architect

Cierra **D1** del relevamiento —*qué OCR y qué modelo*—, que era la última decisión transversal que
bloqueaba P2. Todo lo que sigue está **medido** contra el portal real el 2026-08-29, leyendo con
navegador y sin tocar sus endpoints internos (Artículo I). Los números son reproducibles con los
fixtures versionados en `backend/tests/fixtures/portal/`.

## 1. Lo que se midió en el origen

Sección `/facturas`, las 100 filas, sin paginación:

| Medición | Resultado |
|---|---|
| Columnas de la tabla renderizada | Proveedor · Nro. Factura · Fecha · Vencimiento · Recibo emitido · Producto/insumo · Monto · Pagado · Saldo · Estado de pago · Tipo · Archivo |
| Celdas vacías | **ninguna**, en ninguna columna de ninguna de las 100 filas |
| Formatos de archivo | 46 `PDF (escaneado)` · 29 `Excel` · 25 `PDF` |
| Grafías distintas de proveedor | 24 |
| Fechas fuera de formato ISO | 0 · Montos fuera de formato | 0 |
| Pares (proveedor, número) repetidos | 0 |

**El hallazgo que cambia el tamaño del problema:** los cuatro datos de cabecera —número, fecha,
proveedor y monto— **ya están en la pantalla renderizada de las 100 facturas**, completos y bien
formados. La lectura del archivo deja de ser la única vía posible para obtenerlos.

## 2. Lo que trae cada formato de archivo

Descargados desde el portal, uno por formato, más doce escaneados para la medición:

| Formato | Qué es en realidad | Cómo se lee | Resultado |
|---|---|---|---|
| `PDF` | PDF 1.7 con capa de texto | `pypdf` (BSD-3) | Texto exacto, con etiquetas (`Proveedor:`, `Numero:`, `Fecha:`, `Monto total:`) |
| `PDF (escaneado)` | Un único XObject JPEG de 800×600 a 72 DPI, **sin capa de texto** | OCR | Ver §3 |
| `Excel` | `.xlsx` real, una hoja `Factura` | `openpyxl` (MIT) | Encabezado **corrido a `A2`**, filas vacías intercaladas, `TOTAL` al pie |

Dos cosas que conviene no volver a averiguar:

- **El CUIT que aparece impreso en la factura es el de Cordillera, no el del proveedor.** Dice
  `Cliente: Ferreteria Industrial Cordillera - CUIT 30-71234567-8`. Un parser que busque "CUIT" y se
  quede con el primero que encuentre le asigna a **todas** las facturas el mismo proveedor. RF-11
  —identificar por CUIT— sólo aplica al CUIT **del emisor**, y en esta muestra no hay ninguno.
- **La planilla no necesita un modelo que la interprete.** La hipótesis del relevamiento era que la
  irregularidad —fila de títulos corrida, filas vacías— exigía un modelo. No: buscar las etiquetas
  por su nombre en toda la hoja resuelve el caso, y lo que no aparezca cae en revisión, que es lo
  que el Artículo II pide de todos modos.

## 3. La medición de OCR

Doce facturas escaneadas, cuatro campos cada una (48 datos), contra los valores de la tabla del
portal como verdad de referencia. Dos motores libres, los dos Apache-2.0:

| Motor | Aciertos | Por factura | Peso operativo |
|---|---|---|---|
| **Tesseract 5.5.3 + `spa`** | **48/48 (100%)** | **0,22 s** | Un binario del sistema (`apt-get install tesseract-ocr tesseract-ocr-spa`) + 2,2 MB de idioma |
| RapidOCR (PP-OCRv4, ONNX) | 48/48 (100%) | 1,04 s | Sólo `pip`, pero arrastra `onnxruntime` (~200 MB) y modelos |

Empatan en exactitud sobre esta muestra. Tesseract es **4,7× más rápido** y mucho más liviano; y
donde RapidOCR falla es en algo que importa: come los espacios (`Electrical SupplyArgentina`,
`Montotota1`), lo que ensucia justo el campo que después hay que unificar contra el padrón.

## 4. La decisión

**Sin costo por documento y sin modelo de lenguaje.** Cuatro piezas libres, ninguna con costo de
licencia ni por uso:

| Para | Herramienta | Licencia |
|---|---|---|
| PDF con texto | `pypdf` | BSD-3 |
| PDF escaneado | **Tesseract 5 + `spa`**, invocado desde el worker | Apache-2.0 |
| Planilla | `openpyxl` | MIT |
| Unificar la grafía del proveedor contra el padrón | `rapidfuzz` *(ya es dependencia del proyecto)* | MIT |

**Ningún LLM, ni pago ni local.** No hay nada en esta muestra que un modelo resuelva y estas cuatro
piezas no: los formatos son tres, están etiquetados, y lo ambiguo tiene que ir a una persona por
Artículo II, no a un modelo que adivine mejor.

### La doble lectura, que sale gratis

Como los cuatro datos están **en la tabla y en el archivo**, se leen los dos y se comparan. Eso da,
sin trabajo extra, exactamente la señal que pide RF-27 —*si un dato se obtuvo con certeza o quedó en
duda*—:

- **Coinciden** → el dato es certeza, la factura entra sin molestar a nadie.
- **No coinciden, o el archivo no se pudo leer** → la factura va a revisión con el recorte del
  archivo a la vista (RF-29, RF-30).

El archivo sigue siendo la evidencia que se le muestra a la persona, y el origen del dato cuando la
tabla no lo tenga.

## 5. Lo que se descartó, y por qué

| Alternativa | Por qué no |
|---|---|
| Un servicio pago de OCR (Textract, Document AI, Vision) | El cliente respondió que **no** acepta costo por documento (brief 1.2.0). Además: son 46 documentos, no 46.000 |
| Un LLM por API para interpretar planillas | Mismo costo recurrente, y la medición muestra que no hace falta |
| Un LLM local (Qwen2.5-VL, MiniCPM-V por Ollama) | Gratis de licencia, carísimo de operación: GPU o minutos de CPU por factura, contra los 0,22 s de Tesseract. Se paga hardware para resolver un problema que ya está resuelto |
| RapidOCR / PaddleOCR / EasyOCR / docTR | Empatan o pierden en exactitud acá, y pesan entre 200 MB y 2 GB de dependencias |
| PyMuPDF para el texto de los PDF | **AGPL**: contamina un producto propietario del cliente. `pypdf` hace lo mismo con licencia BSD |
| La visión de macOS (`VNRecognizeTextRequest`) | Excelente y gratis, pero no existe en el Linux donde esto se despliega |
| Leer sólo la tabla del portal y no abrir los archivos | Tienta, porque la tabla está completa. Pero el archivo es la evidencia que la revisión muestra (RF-30) y la única fuente si el portal deja de publicar una columna. Se leen los dos |

## 6. Lo que esta medición no prueba

- **La muestra es sintética.** Las 46 "escaneadas" son renders limpios, monoespaciados, sin ruido ni
  inclinación: el mejor caso posible para cualquier OCR. Una foto real de una factura arrugada no se
  parece a esto, y el 100% de arriba **no se puede prometer** sobre facturas reales.
- **Qué protege ese riesgo:** que `raw` sea inmutable (Artículo III). Si mañana entran fotos de
  verdad y Tesseract no alcanza, se cambia el motor y se reprocesan los cien archivos guardados sin
  pedirle nada al portal. El motor es reemplazable; la evidencia guardada, no.
- **El umbral de confianza por dato** —cuándo un OCR "dudoso" manda la factura a revisión— no se
  fija acá: se calibra en el `plan.md` con la doble lectura de §4 como primera regla.

## 7. Qué falta hacer con esto

- Las dependencias **todavía no se agregaron** a `pyproject.toml`: entran en `/implement` de esta
  feature, con `uv add` y su lockfile en el mismo commit (Artículo IX).
- El `Dockerfile` del worker suma `tesseract-ocr` y `tesseract-ocr-spa`.
- Este documento es insumo del `plan.md`, que es donde la decisión pasa a ser obligatoria.
