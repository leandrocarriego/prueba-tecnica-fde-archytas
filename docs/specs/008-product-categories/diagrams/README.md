<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## El ciclo de vida de una equivalencia

```mermaid
---
title: El ciclo de vida de una equivalencia
---
stateDiagram-v2
    state "Vigente" as Vigente
    state "Sin efecto" as SinEfecto

    [*] --> Vigente: ventas decide a qué rubro corresponde una forma escrita
    Vigente --> Vigente: ventas la cambia de rubro y se reasignan sus productos
    Vigente --> SinEfecto: ventas la deja sin efecto
    SinEfecto --> Vigente: la forma escrita vuelve a decidirse y se guarda otra vez

    note right of Vigente
        Se aplica sola a todo producto que llegue después
        con esa misma forma escrita: la decisión se toma
        una sola vez.
        Se ve en la lista de equivalencias, con quién la
        decidió y cuándo
    end note

    note right of SinEfecto
        Los productos que esa equivalencia venía resolviendo
        vuelven a la pantalla de revisión, en lugar de quedar
        con un rubro que ya nadie sostiene
    end note
```

## El ciclo de vida de la clasificación de un producto

```mermaid
---
title: El ciclo de vida de la clasificación de un producto
---
stateDiagram-v2
    state "En un rubro" as Clasificado
    state "Sin rubro" as SinRubro
    state "Apartado para revisión" as Apartado

    [*] --> Clasificado: llega con una forma escrita que ya está decidida
    [*] --> SinRubro: llega sin categoría cargada
    [*] --> Apartado: llega con una forma escrita que el sistema no conoce

    SinRubro --> Clasificado: ventas confirma el rubro propuesto, o elige otro
    Apartado --> Clasificado: ventas decide a qué rubro corresponde esa forma escrita
    Clasificado --> Clasificado: ventas le cambia el rubro
    Clasificado --> Clasificado: cambia de rubro la equivalencia que lo resolvía
    Clasificado --> Apartado: queda sin efecto la equivalencia que lo resolvía

    note right of SinRubro
        Si trae una subcategoría conocida, el sistema
        propone un rubro; si no, lo presenta sin propuesta.
        En los dos casos espera: mientras nadie confirme,
        no queda en ningún rubro.
        No está escondido, es una categoría más y entra
        en los totales generales
    end note

    note right of Apartado
        Se ve con la forma escrita con la que llegó.
        El sistema no lo asigna por su cuenta ni lo manda
        a un cajón de «otros»
    end note

    note right of Clasificado
        Queda registrado quién lo asignó y cuándo.
        Deja de figurar entre los productos sin rubro
    end note
```

## El dueño — cómo quedó clasificado el catálogo

```mermaid
---
title: El dueño — cómo quedó clasificado el catálogo
---
flowchart TD
    A["Entra y ve todo el sistema"] --> B["Abre el corte por rubro"]
    B --> C["Ve los 7 rubros del negocio"]
    C --> D["Cada uno dice cuántos productos tiene"]
    B --> E["Y ve «sin rubro» como una categoría más, junto a los demás"]
    E --> F["No está escondido: es lo que antes le dejaba pedazos sueltos"]

    D --> G["La suma de todos, «sin rubro» incluido, da el total general"]
    F --> G

    E --> H["Ve cuántos productos están sin rubro y puede listarlos"]
    A --> I["Ve cuántos productos están pendientes de revisión por su categoría"]
    I --> J["Sabe cuánto trabajo de clasificación queda por hacer"]

    A --> K["Los nombres de los rubros son los que él acordó,<br/>y son los que lee en sus informes"]

    L["Cuánto se gasta en cada rubro no está en esta feature:<br/>ni las facturas ni las órdenes de compra dicen qué productos se compraron.<br/>Esta feature deja los rubros limpios, que es la condición para poder medirlo"]
```

## Rubros unificados — de punta a punta

```mermaid
---
title: Rubros unificados — de punta a punta
---
sequenceDiagram
    autonumber
    participant Sistema as El sistema
    actor Julian as Julián, ventas
    actor Duenio as El dueño
    actor Marcela as Marcela, compras

    Sistema->>Sistema: Trae la lista del proveedor y lee la categoría de cada producto
    Sistema->>Sistema: Reconoce las 18 formas escritas y las agrupa en los 7 rubros
    Note over Sistema: Guarda también la subcategoría con la que llegó cada producto,<br/>aunque no agrupe por ella

    Sistema-->>Julian: Le muestra los 8 productos sin rubro, cada uno con un rubro propuesto<br/>a partir de su subcategoría
    Note over Sistema,Julian: Mientras Julián no confirme, el producto no queda en ningún rubro<br/>y sigue contando en «sin rubro»
    Julian->>Sistema: Confirma las propuestas que están bien y corrige la que no
    Sistema->>Sistema: Registra quién lo asignó y cuándo, y los saca de «sin rubro»

    alt Llega una forma de escribir el rubro que el sistema no conoce
        Sistema->>Sistema: Aparta el producto para revisión y no lo asigna a ningún rubro
        Sistema-->>Julian: Se lo muestra con la forma escrita con la que llegó
        Julian->>Sistema: Le indica a qué rubro corresponde esa forma escrita
        Sistema->>Sistema: Guarda la decisión como equivalencia
        Note over Sistema: El próximo producto que llegue con esa misma forma escrita<br/>entra directo al rubro, sin volver a preguntar
    end

    alt Una equivalencia quedó apuntando al rubro que no era
        Julian->>Sistema: La cambia de rubro desde la lista de equivalencias
        Sistema->>Sistema: Reasigna todos los productos que dependían de ella
    else Julián prefiere dejarla sin efecto
        Julian->>Sistema: La deja sin efecto
        Sistema->>Sistema: Los productos que esa equivalencia resolvía vuelven a revisión
    end

    Duenio->>Sistema: Mira cómo quedó clasificado el catálogo
    Sistema-->>Duenio: Los 7 rubros más «sin rubro», cada uno con cuántos productos tiene
    Note over Sistema,Duenio: La suma de todos, «sin rubro» incluido, da el total general:<br/>no quedan pedazos sueltos

    Marcela->>Sistema: Consulta en qué rubro está un producto que le facturaron
    Sistema-->>Marcela: Se lo muestra, junto con la forma en que llegó escrito

    Note over Sistema,Marcela: Cuánto se gasta en cada rubro no es parte de esta feature:<br/>hoy ninguna fuente dice qué productos se compraron
```

## Julián, ventas — mantiene los rubros y el catálogo

```mermaid
---
title: Julián, ventas — mantiene los rubros y el catálogo
---
flowchart TD
    A["Abre la pantalla de rubros"] --> B["Ve los 7 rubros, las formas en que llega escrito cada uno<br/>y cuántos productos tiene"]
    B --> C["Agrega un rubro nuevo"]
    B --> D["Le cambia el nombre a un rubro"]
    B --> E{"¿Puede borrar un rubro?"}
    E -->|Sólo si no tiene productos| F["Se borra"]
    E -->|Si tiene productos| G["El sistema no lo permite y le dice por qué"]

    A --> H["Abre la lista de productos sin clasificar"]
    H --> I["Cada producto llega con un rubro propuesto<br/>a partir de su subcategoría"]
    I --> J{"¿La propuesta es correcta?"}
    J -->|Sí| K["La confirma"]
    J -->|No| L["La corrige y elige otro rubro"]
    K --> M["El producto pasa a ese rubro y sale de la lista"]
    L --> M
    M --> N["Queda registrado que lo asignó él, y cuándo"]
    N --> O["Si más adelante se equivocó, le cambia el rubro igual"]

    A --> P["Abre la pantalla de revisión"]
    P --> Q["Ve los productos que llegaron con una forma escrita<br/>que el sistema no conoce"]
    Q --> R["Le indica a qué rubro corresponde esa forma escrita"]
    R --> S["La decisión queda guardada como equivalencia<br/>y no se la vuelven a preguntar"]

    A --> T["Abre la lista de equivalencias"]
    T --> U["Las ve todas, con quién decidió cada una y cuándo"]
    U --> V["Cambia una de rubro y el sistema reasigna<br/>los productos que dependían de ella"]
    U --> W["O la deja sin efecto, y esos productos vuelven a revisión"]
```

## Marcela, compras — consulta los rubros

```mermaid
---
title: Marcela, compras — consulta los rubros
---
flowchart TD
    A["Entra con su acceso"] --> B["Consulta los rubros para entender qué le están facturando"]
    B --> C["Ve en qué rubro quedó cada producto"]
    C --> D["Y con qué forma escrita llegó del proveedor"]
    B --> E["Ve «sin rubro» como una categoría más"]

    A --> F["Mantener los rubros no es suyo"]
    F --> G["Agregar un rubro, cambiarle el nombre, clasificar un producto<br/>o corregir una equivalencia son cosas de ventas"]
```

## El sistema — qué hace con cada producto que llega

```mermaid
---
title: El sistema — qué hace con cada producto que llega
---
flowchart TD
    A["Llega un producto de la lista del proveedor"] --> B["Guarda la subcategoría con la que llegó escrito"]
    B --> C{"¿Trae categoría cargada?"}

    C -->|Sí| D{"¿Ya está decidido a qué rubro<br/>corresponde esa forma escrita?"}
    D -->|Sí| E["Lo asigna a ese rubro, sin preguntar nada"]
    D -->|No| F["Lo aparta para revisión y no lo asigna a ningún rubro"]
    F --> G["Lo muestra con la forma escrita con la que llegó,<br/>para que ventas decida"]
    G --> H["Cuenta cuántos productos están pendientes de revisión"]

    C -->|No| I{"¿Trae una subcategoría conocida?"}
    I -->|Sí| J["Propone el rubro que le corresponde a esa subcategoría"]
    I -->|No| K["Lo presenta para clasificar, sin proponer ningún rubro"]

    J --> L["Hasta que alguien confirme, no queda en ningún rubro"]
    K --> L
    L --> M["Figura en «sin rubro», que es una categoría más<br/>y entra en los totales generales"]

    E --> N["Cuenta cuántos productos tiene cada rubro"]
    M --> N
    N --> O["La suma de todos los rubros da el total general"]

    P["Nunca inventa un rubro ni manda nada a un cajón de «otros»:<br/>lo que no conoce lo pregunta"]
```

