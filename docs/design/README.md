# `docs/design/` — El sistema de diseño

Acá vive **qué significa** cada señal visual de la Plataforma Cordillera. Es material de producto:
se mira antes de dibujar una pantalla y se discute con el cliente, igual que una spec.

La dirección visual acordada se llama **"taller ordenado"**: densidad de herramienta de trabajo, no
de tablero de marketing. Papel cálido, tinta grafito, y un único acento naranja reservado para lo
urgente y para la acción principal. Nada decorativo: **el color aparece cuando algo requiere una
decisión**.

## Los tres archivos

| Archivo | Qué es | Cuándo se abre |
|---|---|---|
| `style-guide-cordillera.html` | Los fundamentos: paleta, colores de estado, tipografía, componentes, espaciado y los cuatro principios | Siempre que se toque una pantalla |
| `ui-cordillera.html` | Las pantallas de alta fidelidad: tablero, ficha de proveedor, bandeja de revisión, calendario, facturas, pagos y recibos | Al construir o rehacer esa pantalla |
| `wireframes-cordillera.html` | La estructura previa, sin color: qué información lleva cada pantalla y en qué orden | Al discutir el contenido de una pantalla, no su aspecto |

Son exportaciones de un lienzo de diseño y **se abren en el navegador**
(`open docs/design/ui-cordillera.html`). El `<script src="./support.js">` de la cabecera no está en
el repositorio y no hace falta: el contenido es HTML y CSS en línea, y se ve igual sin él.

## Qué es fuente de qué

El sistema tiene dos capas, y no se contradicen:

- **Esta carpeta** dice qué *significa* cada señal: por qué el ámbar es "requiere decisión" y el
  naranja es "decidí acá". Es la capa que se acuerda con el cliente.
- **`frontend/app/globals.css`** es la *implementación*: los tokens (`--brand`, `--warn-surface`,
  `--ok`, …) y las clases compartidas (`.pill`, `.amount`, `.section-label`). Cambiar la paleta es
  editar ese archivo, y nada más.

Encima de esa base hay tres primitivas que existen para que un mismo estado no se dibuje dos veces
distinto: `components/ui/badge.tsx` (la píldora), `components/ui/notice.tsx` (el aviso con su
acción) y `components/ui/button.tsx` (donde `variant="brand"` es el único naranja).

## Cómo se hace cumplir

No con disciplina: con reglas y con un test.

- Las reglas son `CONVENTIONS.md` → **`UI-01` a `UI-10`**, cada una con su severidad.
- `UI-01` (ningún color escrito a mano) y `UI-02` (ninguna clase de la paleta por defecto de
  Tailwind) **las verifica `frontend/tests/design-system.test.ts`, que rompe el build**. Es un
  chequeo estático de texto, así que alcanza también a las pantallas que ningún test renderiza.
- El `Code-Reviewer` recorre los `UI-*` restantes en el gate de calidad
  (`agents/skills/review_feature.md`), y el `Developer` los aplica siguiendo el paso 5 de
  `agents/skills/add_frontend_feature.md`.

**Por qué tanto andamiaje para algo que parece estética.** El producto promete avisar cuando algo
no se puede resolver solo (`CONSTITUTION.md`, Artículo II). Un aviso sólo cumple esa promesa si se
distingue de un adorno de un vistazo, y eso deja de ser cierto apenas el color se usa para decorar.
El color es, entonces, un recurso escaso y administrado. Cuando todo puede ser importante, nada lo
es.

## Si falta una señal

No se improvisa en el componente. Se agrega el **token** en `globals.css` y su **significado** acá,
y esa decisión es del `Frontend-Architect` (`agents/roles/frontend_architect.md`). Si el cambio
altera lo que una señal significa para el cliente, vuelve al `Solution-Designer`.

## Estado de la aplicación

La adopción del sistema sobre las pantallas existentes es la feature
[`012-design-system`](../specs/012-design-system/spec.md).
