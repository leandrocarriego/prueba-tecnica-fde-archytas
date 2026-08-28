# Convención de diagramas (Mermaid)

Cada feature lleva **diagramas de flujo** como parte de su spec: flujos por actor, un flujo
cross-actor de punta a punta, y la máquina de estados de la entidad. Existen para que la spec
y su alcance sean **fáciles de entender y de compartir con el cliente**.

## Por qué Mermaid (y no BPMN)

La palanca de confiabilidad es **derivar el diagrama de los artefactos autoritativos**
(escenarios de `spec.md`, máquina de estados de `data-model.md`, endpoints y eventos de
`contracts/`) — nunca dibujar a mano una fuente paralela que después se desincroniza. Dado
eso, el formato se elige por **generación confiable + diffeabilidad + cero fricción para
verlo**:

- **Mermaid** — texto plano (versionable, diffeable), se renderiza nativamente en GitHub y en
  VS Code, el agente lo genera de forma confiable, y exporta a PNG/PDF/SVG para el cliente.
  **Es el formato por defecto.**
- **BPMN 2.0** — la notación más formal, pero es XML con coordenadas de layout que los LLMs
  generan mal, necesita una app modeladora para verlo (no sirve para mandar por mail) y acá no
  agrega valor porque no hay un motor BPMN ejecutando nada. Reservar BPMN sólo si un
  stakeholder pide explícitamente entregables BPMN.
- **PlantUML** — sólo si un flujo necesita swimlanes formales de verdad (las soporta mejor que
  Mermaid), al costo de un paso de render. Mermaid cubre ~90% de los casos.

## Layout (por feature)

```
docs/specs/<NNN-feature>/diagrams/       ← fuentes, se versionan
  flujo-general.mmd        # sequenceDiagram — cross-actor de punta a punta (el flujo estrella)
  flujo-<rol>.mmd          # flowchart TD  — uno por actor/rol
  estados-<entidad>.mmd    # stateDiagram-v2 — ciclo de vida (derivado de data-model.md)
  README.md                # GENERADO pero versionado: se renderiza al abrir la carpeta en GitHub

dist/diagramas/<NNN-feature>/            ← salida binaria, gitignorada
  <nombre>.{png,pdf,svg}   # GENERADO: para adjuntar o pegar en un documento
```

- **La fuente canónica son los archivos `.mmd`.** Un diagrama por archivo.
- Ambos los **genera** `scripts/diagrams/export.sh` (`make diagrams`) y **ninguno se edita a
  mano**.
- **Todo lo binario y regenerable vive en `dist/`**, nunca dentro de `docs/`: una sola raíz de
  salida, y `docs/` con fuentes solamente. La excepción es el `README.md` de cada carpeta, que
  se versiona a propósito porque es el canal para ver los diagramas en GitHub sin descargar
  nada.

## Idioma

**Todos los diagramas van en español**, igual que el resto de la documentación.

Los diagramas que acompañan a `spec.md` son además **cara al cliente**: etiquetas, actores y
pasos a nivel de negocio, sin detalle técnico (nada de endpoints, tablas ni rutas de archivo).
Los diagramas puramente internos y técnicos (por ejemplo, una secuencia a nivel de endpoint
derivada de `contracts/`) viven junto a `plan.md`/`contracts/`.

## Reglas de autoría (confiabilidad)

1. **Derivar de la spec.** Los actores y los pasos salen de las user stories de `spec.md`; los
   estados y las transiciones salen de `data-model.md` (o de la lista de RF). El diagrama es
   una *vista*, no una fuente de verdad nueva — si cambia la spec, se regenera.
2. **Validado en CI y en el pre-commit.** Cada `.mmd` se compila con `make diagrams-check`
   (mermaid-cli). Un diagrama roto no llega a commitearse —lo frena el hook `diagrams`— ni a
   mergearse: `.github/workflows/ci.yml` lo corre en cada PR. Y `make diagrams` nunca exporta
   algo que no haya compilado, porque depende de la validación.
3. **Nodos entrecomillados** en los flowcharts (`A["texto: con puntuación"]`) y sin paréntesis
   dentro de las etiquetas (son sintaxis de forma) — evita que se rompa el parser.
4. **Un diagrama = una preocupación.** No meter todo el sistema en un solo gráfico.

## Comandos y tooling

- `/diagram` (skill `add_diagrams`) — genera/actualiza los diagramas de una feature a partir de
  su spec. Momentos naturales: después de `/specify` (flujos de negocio, para acompañar la
  firma del cliente) y después de `/plan` (refrescar la máquina de estados o sumar secuencias
  técnicas).
- `make diagrams-check` — valida que todos los `.mmd` compilen. Es lo que corre en CI.
- `make diagrams` — valida y además regenera el `README.md` embebido y las imágenes en `dist/diagramas/`
  (`pdf,png,svg`, fondo blanco) para compartir con el cliente.
- Ambos aceptan `RUTA=` para acotar a una feature:
  `make diagrams RUTA=docs/specs/001-portal-extraction`.
- Por debajo son `scripts/diagrams/validate.sh [ruta]` y
  `scripts/diagrams/export.sh [ruta] [formatos]`, que se pueden llamar directo.

Resolución de mmdc en ambos scripts: `$MMDC` → `mmdc` en el PATH → `npx -y @mermaid-js/mermaid-cli`.

## Compartir con el cliente

Tres opciones sin fricción, todas desde la misma fuente `.mmd`:
- **GitHub**: abrir la carpeta `diagrams/` de la feature — su `README.md` generado renderiza
  todos los diagramas embebidos en la web.
- **Archivos**: `dist/diagramas/<NNN-feature>/*.pdf` / `*.png` — se adjuntan por mail o en el
  paquete de `/approve-spec`.
- **Embeber**: pegar un `dist/diagramas/<NNN-feature>/<nombre>.png` en cualquier documento o slide.

Para el paquete completo —el brief y las specs en PDF, con estos diagramas adentro y en `.svg`
suelto— está `make client-docs`. Ver `docs/specs/README.md` → *El entregable para el cliente*.
