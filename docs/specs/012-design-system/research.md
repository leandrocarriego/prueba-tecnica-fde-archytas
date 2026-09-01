# Sistema de diseño — Relevamiento previo

<!--
  ARTEFACTO INTERNO. Es el estado del terreno el día que se escribió el plan:
  qué de la 012 ya está construido, qué falta, y en qué archivo está cada cosa.
  El plan apunta acá para no llevar adentro una tabla de cuarenta filas.
-->

**Feature:** 012-design-system · **Fecha del relevamiento:** 2026-08-31

## Método

Se midió el árbol de `frontend/` con tres preguntas: qué primitivas del sistema de diseño
existen, quién las usa, y qué señal muestra hoy cada pantalla. Los números salen de contar
ocurrencias sobre el código, no de mirar pantallas.

## Lo que ya está construido (y no está commiteado)

La base del sistema de diseño existe en el árbol de trabajo, sobre la rama
`fix/extractions-were-wedged`, sin commitear:

| Pieza | Archivo | Estado |
|---|---|---|
| Tokens de la paleta, `.pill*`, `.amount`, `.section-label` | `frontend/app/globals.css` (245 líneas) | Completo |
| Píldora de estado | `frontend/components/ui/badge.tsx` | Completo |
| Aviso con su acción | `frontend/components/ui/notice.tsx` | Completo |
| Botones, con `variant="brand"` | `frontend/components/ui/button.tsx` | Completo |
| Tarjeta, campo | `frontend/components/ui/card.tsx`, `input.tsx` | Completo |
| Test que rompe el build (`UI-01`, `UI-02`) | `frontend/tests/design-system.test.ts` | Pasa: 3/3 |
| Corredor de tests | `vitest`, `@testing-library/*`, `jsdom` en `package.json` | Instalado |
| Las diez convenciones `UI-01` … `UI-10` | `CONVENTIONS.md` | Escritas |
| Qué significa cada señal | `docs/design/` + su `README.md` | Escrito |
| Barra lateral agrupada, con permisos y con quién trabaja | `frontend/components/auth/Navigation.tsx` | Completo salvo Ventas |

**Consecuencia para el plan:** esa base es una precondición de esta feature, no parte de su
trabajo. Tiene que viajar en la rama de la 012 (ver *Riesgos* en `plan.md`).

## Lo que falta: la adopción

Las primitivas existen y **no las usa nadie**. Contado sobre `app/` y `components/`:

| Primitiva | Usos hoy |
|---|---|
| `<Badge>` | **0** |
| `<Notice>` | **0** |
| `variant="brand"` | **0** |
| `.pill*` a mano (sin pasar por `Badge`) | 2 archivos: `app/(private)/accesos/actividad/page.tsx`, `components/access/AccessTable.tsx` |

Es decir: `RF-06`, `RF-07`, `RF-08`, `RF-11`, `RF-12`, `RF-14`, `RF-15`, `RF-16`, `RF-21` y
`RF-23` están **enteros por hacer**, y el trabajo es de adopción sobre pantallas que ya
funcionan, no de construcción.

## Lo que ya se cumple

| RF | Por qué ya se cumple | Dónde |
|---|---|---|
| `RF-01`, `RF-02` (parcial) | Ningún color literal ni clase de la paleta de Tailwind sobrevive en `app/`, `components/` ni `lib/`: el test pasa. Falta que cada pantalla use los tokens *bien*, no sólo que no use otros. | `tests/design-system.test.ts` |
| `RF-03` | Barra lateral fija, agrupada por área, con la sección actual marcada. | `Navigation.tsx` |
| `RF-04` | Nombre de quien trabaja y salida, siempre visibles, sin desplegable. | `Navigation.tsx` |
| `RF-17`, `RF-18` | El menú filtra por `canSee` y esconde el grupo que quedó vacío. | `Navigation.tsx` |
| `RF-20` | Cero ocurrencias de `dark:` y cero de `prefers-color-scheme` fuera del comentario de `globals.css`. | medido |

## Lo que falta, pantalla por pantalla

Señales medidas: **plata** = llamadas a `money`/`day`/`decimal`; **tabla** = etiquetas de tabla;
**estado** = menciones de estado de dominio; **botón** = botones.

### Las veintiocho pantallas privadas

| Pantalla | loc | plata | tabla | estado | botón | Qué necesita |
|---|---:|---:|---:|---:|---:|---|
| `tablero/page.tsx` | 212 | 7 | 2 | 0 | 0 | `RF-14`/`RF-16`/`RF-23`: hoy lo excluido va **debajo** del número, en `<p class="text-sm">`. Mono en los importes. |
| `historial/page.tsx` | 360 | 0 | 0 | 0 | 1 | Estados a píldora, códigos y fechas en mono, tres caras de pantalla. |
| `precios/[productId]/page.tsx` | 256 | 0 | 2 | 0 | 0 | Importes de la tabla en mono y alineados (`RF-10`). |
| `proveedores/[supplierId]/page.tsx` | 221 | 5 | 1 | 1 | 0 | Píldora de factura vencida igual que en el listado y el calendario (`RF-06`). |
| `revision/page.tsx` | 162 | 0 | 0 | 0 | 0 | `RF-21`: es lista de decisiones, ningún naranja. |
| `facturas/[invoiceId]/page.tsx` | 151 | 4 | 0 | 3 | 0 | Píldoras de estado, mono, una sola acción de acento. |
| `facturas/page.tsx` | 129 | 0 | 0 | 8 | 0 | Ocho menciones de estado sin píldora. |
| `mensajes/page.tsx` | 116 | 0 | 0 | 6 | 1 | Píldoras, y revisar de qué variante es el botón. |
| `ordenes/page.tsx` | 114 | 0 | 0 | 6 | 1 | Ídem. |
| `proveedores/page.tsx` | 101 | 1 | 2 | 0 | 0 | Mono en columnas, píldoras. |
| `calendario/page.tsx` | 99 | 1 | 0 | 0 | 0 | `RF-21`: ningún naranja; la señal del día vencido es la píldora. |
| `accesos/actividad/page.tsx` | 96 | 0 | 2 | 0 | 0 | Usa `.pill` a mano: pasa por `<Badge>`. |
| `facturas/pagos/page.tsx` | 94 | 0 | 0 | 0 | 0 | Mono en importes. |
| `configuracion/page.tsx` | 91 | 0 | 0 | 0 | 0 | Tarjeta, tres caras de pantalla. |
| `precios/page.tsx` | 90 | 0 | 0 | 1 | 0 | Píldora de estado del precio. |
| `health/page.tsx` | 84 | 0 | 0 | 0 | 0 | Sólo forma; `ApiStatusCard` ya usa tokens. |
| `facturas/incidentes/page.tsx` | 79 | 0 | 0 | 0 | 0 | `RF-21`. |
| `proveedores/grafias/page.tsx` | 69 | 0 | 0 | 0 | 0 | `RF-21`. |
| `facturas/revision/page.tsx` | 69 | 0 | 0 | 0 | 0 | `RF-21`. |
| `acciones/page.tsx` | 67 | 0 | 0 | 0 | 0 | Una sola acción de acento por acción listada: ninguna (`RF-21`). |
| `rubros/page.tsx` | 59 | 0 | 0 | 0 | 0 | Forma y píldoras. |
| `ventas/revision/page.tsx` | 56 | 0 | 0 | 1 | 0 | `RF-21`; es el destino de la entrada Ventas del menú. |
| `rubros/equivalencias/page.tsx` | 54 | 0 | 0 | 0 | 0 | `RF-21`. |
| `rubros/sin-clasificar/page.tsx` | 54 | 0 | 0 | 0 | 0 | `RF-21`. |
| `mi-cuenta/page.tsx` | 47 | 0 | 0 | 0 | 0 | Tarjeta y una acción de acento (guardar). |
| `page.tsx` (raíz privada) | 45 | 0 | 0 | 0 | 0 | **Es una pantalla de andamio**: `text-4xl`, `min-h-screen`, dos enlaces subrayados. No es ninguna de las dieciséis secciones. |
| `accesos/page.tsx` | 33 | 0 | 0 | 1 | 0 | Píldora del nivel de acceso. |
| `precios/configuracion/page.tsx` | 18 | 0 | 0 | 0 | 0 | Forma. |

### Las cuatro pantallas de sesión (`RF-05`)

`login`, `invitacion/[token]`, `recuperar/[token]` y `reset-password`, más
`components/auth/AuthLayout.tsx` (149 loc), `LoginForm.tsx` (189) y `ResetPasswordForm.tsx`
(389). Dependen de `lib/branding.ts`, que es una de las dos excepciones del test porque aplica
los colores **en línea**: es la única superficie donde el color no viene de una clase.

### Los componentes que llevan la plata y los estados

Los que más pesan, por trabajo esperado:

| Componente | loc | plata | tabla | botón |
|---|---:|---:|---:|---:|
| `purchases/CalendarGrid.tsx` | 536 | 7 | 0 | 10 |
| `triage/CaseCard.tsx` | 354 | 0 | 0 | 8 |
| `purchases/ReviewQueue.tsx` | 255 | 2 | 0 | 3 |
| `catalog/CorrectionDialog.tsx` | 237 | 0 | 0 | 3 |
| `sales/SalesReview.tsx` | 216 | 6 | 6 | 3 |
| `purchases/InvoicePanel.tsx` | 214 | 2 | 2 | 5 |
| `purchases/OrderTable.tsx` | 176 | 2 | 2 | 1 |
| `purchases/HeldVouchers.tsx` | 172 | 7 | 2 | 1 |
| `purchases/InvoiceTable.tsx` | 100 | 4 | 2 | 0 |
| `purchases/IncidentList.tsx` | 115 | 1 | 0 | 1 |

Catorce archivos importan de `@/lib/format`, y ninguno garantiza que el resultado salga en mono:
`money()` devuelve un string y quien lo escribe decide con qué tipografía. Esa es la razón
estructural de que `RF-09` y `RF-10` no se cumplan hoy, y por eso el plan la ataca con un
envoltorio y no con una revisión archivo por archivo.

## Lo que falta y no es una pantalla

- **La entrada de Ventas.** `Navigation.tsx` lista **quince** entradas; la spec habla de
  dieciséis secciones. La que falta es Ventas (`RF-22`), y la ruta `/ventas` **no existe**: sólo
  existe `/ventas/revision`.
- **Las tres caras de pantalla** (`RF-19`). No hay ni un `loading.tsx`, ni un `error.tsx`, ni un
  componente de lista vacía en todo `app/`. Cada pantalla resuelve sus tres caras a mano, o no
  las resuelve.
- **Dos colores literales dentro de `globals.css`**: `#8a8e93` en `.section-label` y `#c6c0b4` en
  `.pill-draft`. El test los permite —`globals.css` es una de sus dos excepciones— pero `UI-09`
  pide que un color viva en un token con nombre semántico.
