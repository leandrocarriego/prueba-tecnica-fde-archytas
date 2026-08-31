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

    Marcela->>Sistema: Revisa lo de proveedores, pagos, órdenes y mensajes
    Julian->>Sistema: Revisa lo de precios y ventas

    alt Se puede resolver desde su pantalla
        Marcela->>Sistema: Lo resuelve donde corresponde
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
    A["Julián entra a la lista de pendientes"] --> B["Ve lo de su área: precios y ventas"]
    B --> C["De cada uno lee el motivo y lo que se alcanzó a leer"]
    C --> D{"¿Se puede resolver?"}
    D -->|Sí| E["Lo resuelve en la pantalla que le corresponde"]
    D -->|No, sólo mirarlo| F["Lo da por revisado, y queda quién y cuándo"]
    B --> G["Lo de proveedores, pagos, órdenes y mensajes<br/>no le aparece"]
    G --> H["Y si intenta resolver uno de esos,<br/>el sistema se lo impide"]
```

## Marcela, compras — lo apartado de su área

```mermaid
---
title: Marcela, compras — lo apartado de su área
---
flowchart TD
    A["Marcela entra a la lista de pendientes"] --> B["Ve lo de su área: proveedores, pagos,<br/>órdenes de compra y mensajes"]
    B --> C["De cada uno lee el motivo, lo que el sistema<br/>alcanzó a leer y de dónde salió"]
    C --> D{"¿Se puede resolver?"}
    D -->|Sí| E["Lo resuelve en la pantalla que le corresponde"]
    E --> F["El pendiente deja de figurar solo"]
    D -->|No, sólo mirarlo| G["Lo da por revisado"]
    G --> H["Queda registrado quién lo hizo y cuándo"]
    B --> I["Si intenta abrir algo de precios o de ventas,<br/>el sistema no se lo muestra"]
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

