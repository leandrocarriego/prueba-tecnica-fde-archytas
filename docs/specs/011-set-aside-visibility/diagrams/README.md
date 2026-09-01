<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## La vida de un pendiente

```mermaid
---
title: La vida de un pendiente
---
stateDiagram-v2
    [*] --> Pendiente: El sistema aparta algo<br/>que no pudo interpretar
    Pendiente --> Pendiente: Vuelve a aparecer lo mismo<br/>y suma una aparición
    Pendiente --> Demorado: Pasan más días<br/>que los configurados
    Demorado --> Pendiente: Deja de estar demorado sólo<br/>si cambia el plazo configurado
    Pendiente --> Revisado: Una persona lo da por revisado
    Demorado --> Revisado: Una persona lo da por revisado
    Pendiente --> Resuelto: Se resuelve lo que lo originó,<br/>en la pantalla que le corresponde
    Demorado --> Resuelto: Se resuelve lo que lo originó
    Resuelto --> Pendiente: Se deshace ese trabajo en la pantalla<br/>que le corresponde, y vuelve a la lista
    Revisado --> [*]: Sale de la lista y queda consultable
    Resuelto --> [*]: Sale de la lista y queda consultable
```

## El dueño — cuánto falta resolver y hace cuánto

```mermaid
---
title: El dueño — cuánto falta resolver y hace cuánto
---
flowchart TD
    A["El dueño entra a la lista de pendientes"] --> B["Ve los de todas las áreas"]
    B --> C["Puede pedir ver sólo los de un área"]
    B --> D["Lee cuántos hay sin resolver"]
    D --> E["Y desde cuándo espera cada uno"]
    E --> F{"¿Alguno lleva más días<br/>que los configurados?"}
    F -->|Sí| G["Lo ve señalado como demorado"]
    F -->|No| H["La lista está al día"]
    A --> I["Define a partir de cuántos días<br/>un pendiente se considera demorado"]
    I --> J["Mientras no lo cambie, son siete días"]
    B --> K["Consulta los ya resueltos, que no se borran nunca"]
```

## Lo apartado se ve — de punta a punta

```mermaid
---
title: Lo apartado se ve — de punta a punta
---
sequenceDiagram
    autonumber
    participant Portal as El portal
    participant Sistema as El sistema
    actor Marcela as Marcela, compras
    actor Julian as Julián, ventas
    actor Duenio as El dueño

    Note over Portal,Duenio: La regla que el cliente pidió: si algo no se puede resolver solo,<br/>que avise en vez de adivinar mal

    Sistema->>Portal: Lee las pantallas con la frecuencia configurada
    Portal-->>Sistema: Devuelve lo publicado, con datos que a veces no se pueden interpretar

    alt El sistema puede interpretar el dato
        Sistema->>Sistema: Lo registra y sigue
    else No lo puede interpretar
        Sistema->>Sistema: Lo aparta sin descartarlo y anota por qué
        Sistema->>Sistema: Si ya había apartado lo mismo, suma una aparición<br/>en vez de abrir otro pendiente
        Sistema-->>Duenio: Lo pone en la lista de pendientes con el motivo,<br/>lo que alcanzó a leer y de dónde salió
    end

    Note over Marcela,Julian: Cada uno entra a la misma lista y ve lo de su área

    Marcela->>Sistema: Revisa lo de proveedores, pagos, órdenes, mensajes y precios
    Julian->>Sistema: Revisa las ventas apartadas

    alt Se resuelve en la pantalla propia del origen (hoy, las ventas)
        Julian->>Sistema: Corrige la venta en la pantalla de ventas
        Sistema->>Sistema: Saca el pendiente de la lista sin que nadie lo cierre a mano
    else Sólo se puede dar por revisado
        Marcela->>Sistema: Deja constancia de que lo vio
        Sistema->>Sistema: Guarda quién lo hizo y cuándo
    end

    Duenio->>Sistema: Mira cuántos pendientes hay y desde cuándo esperan
    Sistema-->>Duenio: Le señala los que llevan más días de los configurados
    Note over Sistema,Duenio: Nada se borra: lo resuelto sale de la lista<br/>y se sigue pudiendo consultar
```

## Julián, ventas — lo apartado de su área

```mermaid
---
title: Julián, ventas — lo apartado de su área
---
flowchart TD
    A["Julián entra a la lista de pendientes"] --> B["Ve lo de su área: las ventas apartadas"]
    B --> C["De cada una lee el motivo, lo que se alcanzó<br/>a leer, de dónde salió y cuándo se leyó"]
    C --> D{"¿La corrige en la pantalla de ventas?"}
    D -->|Sí| E["El pendiente deja de figurar solo,<br/>sin que nadie lo cierre a mano"]
    D -->|"No, sólo mirarla"| F["La da por revisada, y queda quién y cuándo"]
    E --> G["Queda consultable, diciendo que se resolvió<br/>en la pantalla de ventas"]
    B --> H["Lo de proveedores, pagos, órdenes, mensajes<br/>y precios no le aparece"]
    H --> I["Y si intenta resolver uno de esos,<br/>el sistema se lo impide"]
```

## Marcela, compras — lo apartado de su área

```mermaid
---
title: Marcela, compras — lo apartado de su área
---
flowchart TD
    A["Marcela entra a la lista de pendientes"] --> B["Ve lo de su área: proveedores, pagos,<br/>órdenes, mensajes y precios"]
    B --> C["De cada uno lee el motivo, lo que el sistema<br/>alcanzó a leer, de dónde salió y cuándo se leyó"]
    C --> D{"¿Se puede decidir algo?"}
    D -->|Sí| E["Decide qué hacer con él,<br/>ahí mismo en la lista"]
    D -->|"No, sólo mirarlo"| F["Lo da por revisado"]
    E --> G["Queda registrado quién lo hizo y cuándo"]
    F --> G
    B --> H["Lo de ventas no le aparece, y si intenta<br/>resolverlo el sistema se lo impide"]
```

## Qué hace el sistema cuando no puede interpretar algo

```mermaid
---
title: Qué hace el sistema cuando no puede interpretar algo
---
flowchart TD
    A["El sistema lee una pantalla del portal"] --> B{"¿Puede interpretar el dato?"}
    B -->|Sí| C["Lo registra y sigue"]
    B -->|No| D["Lo aparta sin descartarlo"]
    D --> E["Anota el motivo, lo que alcanzó a leer,<br/>de qué pantalla salió y cuándo"]
    E --> F{"¿Ya había apartado lo mismo<br/>por el mismo motivo?"}
    F -->|Sí| G["Suma una aparición al pendiente que ya existe"]
    F -->|No| H["Abre un pendiente nuevo"]
    G --> I["Queda en la lista de pendientes"]
    H --> I
    I --> J{"¿Se resolvió lo que lo originó,<br/>en la pantalla que le corresponde?"}
    J -->|Sí| K["Deja de contarlo entre los pendientes,<br/>sin que nadie lo cierre a mano"]
    J -->|No| L["Sigue esperando, y el sistema cuenta desde cuándo"]
    L --> M{"¿Lleva más días que los configurados?"}
    M -->|Sí| N["Lo señala como demorado"]
    M -->|No| L
    K --> O["Queda consultable para siempre"]
```
