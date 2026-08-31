<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## El dueño — no le cambia nada

```mermaid
---
title: El dueño — no le cambia nada
---
flowchart TD
    A["Entra con su acceso"] --> B["Ve todo el sistema, como en todas las secciones"]
    B --> C["Y también hace todo: ninguna sección se le cierra"]

    C --> D["Mantiene los rubros igual que compras"]
    C --> E["Clasifica un producto sin rubro"]
    C --> F["Decide qué significa una forma escrita nueva"]
    C --> G["Corrige o deja sin efecto una equivalencia"]

    B --> H["Sigue leyendo el corte por rubro con los nombres que él acordó"]

    I["Lo único que cambia para él es quién más puede hacerlo:<br/>antes ventas, ahora compras"]
```

## Quién mantiene los rubros — de punta a punta

```mermaid
---
title: Quién mantiene los rubros — de punta a punta
---
sequenceDiagram
    autonumber
    participant Sistema as El sistema
    actor Marcela as Marcela, compras
    actor Julian as Julián, ventas
    actor Duenio as El dueño

    Note over Sistema,Duenio: Hasta ahora los rubros los mantenía ventas.<br/>Desde esta feature los mantiene compras: el rubro es la categoría<br/>de lo que se compra para revender

    Marcela->>Sistema: Entra con su acceso
    Sistema-->>Marcela: Le muestra los rubros entre las secciones a las que entra

    Marcela->>Sistema: Agrega un rubro nuevo y le cambia el nombre a otro
    Sistema-->>Marcela: Le muestra los productos sin rubro, cada uno con el rubro que propone
    Marcela->>Sistema: Confirma la propuesta, la corrige, o asigna el rubro si no había ninguna
    Marcela->>Sistema: Le cambia el rubro a un producto ya clasificado

    alt Llega una forma de escribir el rubro que el sistema no conoce
        Sistema->>Sistema: La aparta para revisión, en la misma cola donde ya cae<br/>todo lo que la actualización no puede resolver sola
        Sistema-->>Marcela: Se la muestra junto al resto de lo apartado
        Marcela->>Sistema: Le indica a qué rubro corresponde esa forma escrita
        Note over Sistema,Marcela: Una sola persona cierra el circuito de punta a punta:<br/>la cola de revisión vuelve a tener un solo dueño
    end

    alt Una equivalencia quedó apuntando al rubro que no era
        Marcela->>Sistema: La cambia de rubro
    else Marcela prefiere dejarla sin efecto
        Marcela->>Sistema: La deja sin efecto
    end

    Julian->>Sistema: Abre los rubros para saber lo que vende
    Sistema-->>Julian: Se los muestra con su conteo y sus formas escritas
    Note over Sistema,Julian: No le ofrece ninguna acción para cambiarlos
    Julian->>Sistema: Manda igual el pedido de cambiar un rubro
    Sistema-->>Julian: Lo rechaza

    Duenio->>Sistema: Entra con su acceso
    Sistema-->>Duenio: Ve todo y hace todo, también acá
```

## Julián, ventas — los sigue viendo, sin poder cambiarlos

```mermaid
---
title: Julián, ventas — los sigue viendo, sin poder cambiarlos
---
flowchart TD
    A["Entra con su acceso"] --> B["Abre los rubros del catálogo del que vende"]
    B --> C["Los ve con cuántos productos tiene cada uno"]
    B --> D["Y con todas las formas en que llega escrito cada rubro"]
    C --> E["Vende sabiendo en qué rubro cae cada producto"]
    D --> E

    B --> F["No encuentra ninguna acción para agregar, renombrar<br/>ni eliminar un rubro"]
    B --> G["Tampoco para clasificar un producto ni para corregir una equivalencia"]

    F --> H{"¿Y si manda el pedido igual?"}
    G --> H
    H --> I["El sistema lo rechaza"]
    I --> J["Esconder el botón no alcanza, y ya estaba acordado así<br/>cuando se definieron los accesos"]

    K["Es el mismo trato que ya tiene con los precios de lista<br/>y con el calendario: los ve y no los toca"]

    L["El catálogo sigue siendo suyo: sigue corrigiendo<br/>la descripción de un producto, y ya no su rubro"]
```

## Marcela, compras — pasa a mantener los rubros

```mermaid
---
title: Marcela, compras — pasa a mantener los rubros
---
flowchart TD
    A["Entra con su acceso"] --> B["Encuentra los rubros entre las secciones a las que entra"]

    B --> C["Agrega un rubro nuevo a la lista"]
    B --> D["Le cambia el nombre a un rubro"]
    B --> E{"¿Puede eliminar un rubro?"}
    E -->|Si no tiene productos asignados| F["Se elimina"]
    E -->|Si tiene productos| G["El sistema lo sigue impidiendo y dice por qué"]

    B --> H["Abre los productos que quedaron sin rubro"]
    H --> R["Cada uno llega con el rubro que el sistema propone, o sin ninguno"]
    R --> I["Confirma la propuesta, la corrige, o asigna el rubro si no había ninguna"]
    B --> J["Le cambia el rubro a un producto ya clasificado"]

    B --> K["Abre la pantalla donde ya resuelve lo que la actualización aparta"]
    K --> L["Ahí también aparecen las formas escritas de categoría<br/>que el sistema no conoce"]
    L --> M["Le indica a qué rubro corresponde esa forma escrita"]

    B --> N["Abre la lista de equivalencias guardadas"]
    N --> O["Cambia una de rubro y se reasignan los productos que dependían de ella"]
    N --> P["O la deja sin efecto, y esos productos vuelven a revisión"]

    Q["Lo que hacen los rubros no cambia con esta feature:<br/>cambia que ahora las decisiones las toma ella"]
```

## El sistema — a quién le deja cambiar un rubro

```mermaid
---
title: El sistema — a quién le deja cambiar un rubro
---
flowchart TD
    A["Llega un pedido de cambiar un rubro, la clasificación<br/>de un producto o una equivalencia"] --> B{"¿Quién lo pide?"}

    B -->|El dueño| C["Lo deja pasar"]
    B -->|Compras| C
    B -->|Ventas| D["Lo rechaza"]

    C --> E["El cambio queda hecho"]
    D --> F["El cambio no se hace, aunque el pedido haya llegado igual"]

    G["Llega un pedido de sólo consultar los rubros"] --> H{"¿Quién lo pide?"}
    H -->|Los tres| I["Se los muestra con su conteo y sus formas escritas"]

    J["A ventas no le ofrece ninguna acción para cambiarlos"] --> K["Y si el pedido llega igual, lo rechaza:<br/>esconder el botón no alcanza"]

    L["A compras le muestra los rubros entre las secciones a las que entra"]
```

