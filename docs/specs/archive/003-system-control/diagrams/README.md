<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## Qué le pasa a un dato que una persona puede corregir

```mermaid
---
title: Qué le pasa a un dato que una persona puede corregir
---
stateDiagram-v2
    state "Informado por el portal" as Portal
    state "Cargado a mano por una persona" as Manual
    state "Corregido a mano" as Corregido
    state "En conflicto con el portal" as Conflicto

    [*] --> Portal: lo trae el portal
    [*] --> Manual: lo carga una persona
    Manual --> Manual: se modifica con un motivo, conservando el valor anterior
    Manual --> Portal: la lista diaria informa ese mismo dato, y desde esa mañana el valor es del portal
    Portal --> Corregido: una persona de esa sección lo corrige, con un motivo
    Corregido --> Conflicto: el portal informa un valor distinto del original
    Conflicto --> Corregido: una persona lo corrige otra vez
    Conflicto --> Portal: el dueño deja sin efecto la corrección
    Corregido --> Portal: el dueño deja sin efecto la corrección

    note right of Portal
        Lo que el portal informó se conserva
        siempre, aunque encima haya una
        corrección. Si mañana un número no
        cierra, se explica con lo que dijo
        el origen
    end note

    note right of Corregido
        Se distingue a simple vista de un dato
        sin corregir, y al lado se ve el valor
        original. Se corrige cualquier campo:
        importe, fecha, número de comprobante
        o nombre del proveedor
    end note

    note right of Conflicto
        El sistema lo señala en la pantalla del
        propio dato y le avisa al dueño. Nunca
        decide solo cuál de los dos vale, y no
        hay una bandeja aparte que vaciar
    end note

    note right of Manual
        Mientras el portal no lo haya informado
        no ofrece volver a su valor, porque no
        hay a qué volver. Pero la pregunta se
        hace por dato y no por producto: el
        precio que tipeó una persona pasa a
        ofrecerlo el día que la lista informa
        ese producto
    end note
```

## Qué le pasa a un parámetro del sistema

```mermaid
---
title: Qué le pasa a un parámetro del sistema
---
stateDiagram-v2
    state "Con su valor inicial" as Inicial
    state "Ajustado por el dueño" as Ajustado

    [*] --> Inicial: el sistema arranca
    Inicial --> Inicial: el valor queda fuera del rango admitido y el cambio se rechaza
    Inicial --> Ajustado: el dueño pone un valor dentro del rango
    Ajustado --> Ajustado: el dueño lo vuelve a cambiar
    Ajustado --> Ajustado: el valor queda fuera del rango admitido y el cambio se rechaza

    note right of Inicial
        Vencimiento 3 días, orden estancada
        15 días, sesión 60 minutos, recibo
        3 días y resumen a las 8:00. Los dos
        parámetros de la actualización de
        precios llegan con el valor que fijó
        esa feature
    end note

    note right of Ajustado
        El valor nuevo rige de inmediato, sin
        ninguna intervención adicional, y queda
        registrado el anterior, el nuevo, quién
        lo cambió y cuándo. Sólo el dueño
    end note
```

## El dueño — qué puede hacer y qué ve

```mermaid
---
title: El dueño — qué puede hacer y qué ve
---
flowchart TD
    A["El dueño abre la aplicación"] --> B["Panel de parámetros del sistema"]
    B --> C["Los siete parámetros en una sola pantalla, con su valor vigente"]
    B --> D["Junto a cada uno, una frase que dice qué cambia si se lo modifica"]
    B --> E["Cambia el valor de un parámetro"]
    E --> F{"¿El valor está dentro del rango admitido?"}
    F -- "No" --> G["El sistema rechaza el cambio e informa entre qué valores tiene que estar"]
    F -- "Sí" --> H["Rige de inmediato, sin que nadie toque nada más"]
    H --> I["Queda registrado el valor anterior, el nuevo, quién lo cambió y cuándo"]
    B --> J["Mientras no cambie nada rigen los valores iniciales: vencimiento 3 días, orden estancada 15 días, sesión 60 minutos, recibo 3 días, resumen a las 8:00"]

    A --> K["Historial de cambios manuales"]
    K --> L["Ve los cambios de las tres personas, de más nuevo a más viejo"]
    K --> M["Filtra por persona y por rango de fechas"]
    K --> N["De cada cambio lee el motivo por el que se hizo"]

    A --> U["Pantalla del dato corregido"]
    U --> V["Ve el valor corregido y, al lado, el que había informado el portal"]
    U --> K2["Llega al historial de ese dato sin buscarlo en otra pantalla"]
    K2 --> K
    U --> O["Deja sin efecto la corrección"]
    K --> O
    O --> P["El dato vuelve a mostrar lo que informó el portal"]
    O --> Q["Queda registrado quién la anuló y cuándo"]
    O --> R["Sobre un dato que el portal nunca informó no hay corrección que anular, y la opción no aparece"]

    S["El portal informa un valor distinto del original sobre un dato ya corregido"] --> T["Le llega el aviso, sin tener que estar mirando la pantalla"]
```

## Control propio del sistema — de punta a punta

```mermaid
---
title: Control propio del sistema — de punta a punta
---
sequenceDiagram
    autonumber
    actor Duenio as El dueño
    actor Marcela as Marcela, compras
    actor Julian as Julián, ventas
    participant Sistema as El sistema
    participant Portal as Portal del proveedor

    Duenio->>Sistema: Abre el panel y ajusta un parámetro
    Note over Sistema: Mientras no los cambie rigen los valores iniciales:<br/>vencimiento 3 días, orden estancada 15 días, sesión 60 minutos,<br/>recibo 3 días y resumen diario a las 8:00
    alt El valor está dentro del rango admitido
        Sistema->>Sistema: Aplica el valor nuevo de inmediato
        Sistema->>Sistema: Registra el anterior, el nuevo, quién y cuándo
    else Queda fuera del rango
        Sistema-->>Duenio: Rechaza el cambio e informa entre qué valores tiene que estar
    end

    Marcela->>Sistema: Abre el único lugar de cargas y correcciones
    Sistema-->>Marcela: Sólo las acciones habilitadas para su rol
    Marcela->>Sistema: Corrige un dato de su sección y elige el motivo
    Sistema->>Sistema: Conserva lo que informó el portal y el valor que tenía antes
    Sistema->>Sistema: Señala el dato como corregido a mano
    Sistema-->>Marcela: Le avisa si la acción se aplicó o si falló

    loop En cada actualización posterior
        Sistema->>Portal: Vuelve a leer ese mismo dato
        Portal-->>Sistema: El valor que publica hoy
        alt Difiere del valor original
            Sistema->>Sistema: Señala el conflicto en la pantalla del dato, sin pisar la corrección
            Sistema-->>Duenio: Le avisa que hay un conflicto esperando a una persona
        else Coincide con el original
            Sistema->>Sistema: La corrección sigue en pie, sin novedad
        end
    end

    Duenio->>Sistema: Abre el historial y filtra por persona y fechas
    Sistema-->>Duenio: Los cambios de las tres personas, de más nuevo a más viejo, con su motivo
    Duenio->>Sistema: Deja sin efecto una corrección
    Sistema->>Sistema: Restituye el valor del portal y registra quién la anuló y cuándo

    Julian->>Sistema: Pide el historial de las facturas de compra
    Sistema-->>Julian: Sólo los cambios de las secciones a las que tiene acceso
```

## Julián, ventas — qué puede hacer y qué ve

```mermaid
---
title: Julián, ventas — qué puede hacer y qué ve
---
flowchart TD
    A["Julián abre la aplicación"] --> B["Un solo lugar con todas las cargas y correcciones"]
    B --> C["Ve acciones distintas de las que ve Marcela: sólo las de su rol"]
    B --> D["Corrige un dato de su sección que llegó mal del portal"]
    D --> E["Elige un motivo de la lista y, si quiere, agrega un detalle escrito"]
    E --> F["El sistema le avisa si se aplicó o si falló"]
    F --> G["El dato queda señalado como corregido a mano, con el valor del portal al lado"]

    B --> H["El total de una factura de compra no lo puede corregir: no es su sección"]

    A --> I["Historial de cambios manuales"]
    I --> J["Ve sus cambios y los de su sección"]
    I --> K["Los cambios de las facturas de compra no le aparecen"]

    A --> L["El panel de parámetros del sistema no lo encuentra"]
```

## Marcela, compras — qué puede hacer y qué ve

```mermaid
---
title: Marcela, compras — qué puede hacer y qué ve
---
flowchart TD
    A["Marcela abre la aplicación"] --> B["Un solo lugar con todas las cargas y correcciones"]
    B --> C["Ve únicamente las acciones habilitadas para su rol"]
    B --> D["Corrige un dato de su sección que llegó mal del portal"]
    D --> E["Cualquier campo: importe, fecha, número de comprobante o nombre del proveedor"]
    E --> F["Elige un motivo de la lista y, si quiere, agrega un detalle escrito"]
    F --> G{"¿Eligió un motivo?"}
    G -- "No" --> H["La corrección no se puede confirmar"]
    G -- "Sí" --> I["El sistema le avisa si se aplicó o si falló"]
    I --> J["El dato queda señalado como corregido a mano"]
    J --> K["Al lado se ve el valor que había informado el portal"]
    J --> L["Desde el dato llega a su historial, sin buscarlo en otra pantalla"]

    A --> M["Historial de cambios manuales"]
    M --> N["Ve sus cambios y los de las secciones a las que tiene acceso"]

    A --> O["El panel de parámetros del sistema no lo encuentra"]
```

## El sistema — qué hace por su cuenta ante cada cambio

```mermaid
---
title: El sistema — qué hace por su cuenta ante cada cambio
---
flowchart TD
    A["Alguien cambia un parámetro"] --> B{"¿Es el dueño?"}
    B -- "No" --> C["Se lo impide"]
    B -- "Sí" --> D{"¿El valor está dentro del rango admitido?"}
    D -- "No" --> E["Rechaza el cambio e informa el rango"]
    D -- "Sí" --> F["Aplica el valor nuevo de inmediato y registra el anterior, el nuevo, quién y cuándo"]

    G["Alguien carga o modifica un dato a mano"] --> H["Registra quién lo hizo y cuándo"]
    H --> I["Conserva el valor que tenía antes"]
    I --> J["Exige un motivo elegido de una lista, y admite un detalle escrito"]
    J --> K["Informa a quien la ejecutó si la acción se aplicó o si falló"]

    L["La corrección es sobre un dato traído del portal"] --> M["Conserva sin cambios lo que el portal había informado"]
    M --> N["Señala el dato como corregido a mano y muestra al lado el valor original"]

    O["Una actualización posterior del portal informa ese mismo dato"] --> P{"¿Coincide con el valor original?"}
    P -- "Sí" --> Q["La corrección sigue en pie, sin novedad"]
    P -- "No" --> R["Señala el conflicto en la pantalla de ese dato, sin pisar la corrección"]
    R --> S["Le avisa al dueño"]
    R --> T["No decide solo cuál de los dos vale: espera a una persona"]

    U["El historial de cambios"] --> V["No se puede modificar"]
    U --> W["No se puede eliminar"]
```
