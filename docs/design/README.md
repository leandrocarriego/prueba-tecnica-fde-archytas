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

Encima de esa base hay seis piezas que existen para que un mismo estado no se dibuje dos veces
distinto:

| Pieza | Qué decide |
|---|---|
| `components/ui/badge.tsx` | La píldora de estado |
| `components/ui/notice.tsx` | El aviso, con la acción que lo resuelve |
| `components/ui/button.tsx` | Las variantes, donde `variant="brand"` es el único naranja |
| `components/ui/amount.tsx` | `<Money>`, `<Day>`, `<Code>` y `<Decimal>`: la plata, las fechas y los códigos en mono tabular, alineados cuando son celda |
| `components/ui/state.tsx` | `<Loading>`, `<ErrorState>` y `<Empty>`: las tres caras de una pantalla sin datos |
| `lib/ui/tone.ts` | **El** mapa de cada estado del negocio a uno de los cinco tonos, y qué cuenta como «todavía sin confirmar» |

La última es la que sostiene a las demás: mientras cada pantalla elija su color, «vencida» se
dibuja de tres maneras distintas y nadie se entera.

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

Los que se agregaron así, y qué quieren decir:

| Token | Significa | Dónde se ve |
|---|---|---|
| `--muted-ink` | El gris del **rótulo**: nombra un bloque sin competir con su título. Es más apagado que `--muted-foreground`, que es texto para leer; esto se recorre con la vista | `.section-label` |
| `--draft-border` | El borde del punteado de **"todavía sin confirmar"**: un paso más cálido que `--border`, para que el guion se vea sin gritar | `.pill-draft` |

Los dos existían como color escrito a mano dentro de `globals.css` —el único archivo donde el test
lo permite— y por eso no rompían nada; pero un color sin nombre no se puede reusar ni cambiar, que
es justamente lo que `UI-09` pide evitar.

Y una señal que no es un color sino un **relleno**:

| Clase | Significa | Dónde se ve |
|---|---|---|
| `.hatch-excluded` | El rayado de **"esto quedó afuera del número"**: una porción que existe, que se mide y que **no está sumada** en el dato de al lado | La composición del corte de stock, en el tablero |

Va rayada y no de un color liso a propósito: sobre una barra de composición, un liso más se lee
como una categoría más. La guía la dibuja así en `3b` —la barra de agosto del gráfico y el renglón
«sin rubro asignado»— y es la forma visual del Artículo II: lo que no se pudo interpretar se
muestra, no se descarta en silencio.

## Estado de la aplicación

**El sistema está adoptado en toda la plataforma.** Las dieciséis secciones del menú, Mi cuenta y
las cuatro pantallas de sesión usan los tokens, las primitivas y el mapa de tonos; el shell del área
privada pone el fondo y el ancho, y ninguna pantalla pone el suyo.

Lo hizo la feature [`012-design-system`](../specs/012-design-system/spec.md), que fue una
**migración y no una construcción**: la base ya existía y no la usaba nadie.

Lo que queda de eso, y que conviene saber antes de escribir una pantalla nueva:

- El estado de un dato sale de `lib/ui/tone.ts`. Si el estado que necesitás no está, se agrega ahí
  —una vez— y no en la pantalla.
- La plata, las fechas y los códigos pasan por `components/ui/amount.tsx`. `money()` y `day()` se
  usan sueltos **sólo** cuando hace falta el string y no el elemento (un `title`, un `aria-label`),
  y `frontend/tests/design-system.test.ts` lleva la lista de esos casos.
- El naranja es uno por pantalla, y ninguno en las nueve rutas donde se decide. Los dos chequeos
  recorren el árbol de imports de cada `page.tsx`, así que no alcanza con no ponerlo en la pantalla:
  cuenta también lo que traigan sus componentes.
