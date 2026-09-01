<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## Qué le pasa a un grupo de ventas que comparten el mismo código

```mermaid
---
title: Qué le pasa a un grupo de ventas que comparten el mismo código
---
stateDiagram-v2
    state "Detectado: dos o más ventas con el mismo código" as Detectado
    state "Sin diferencias entre sus versiones" as Identico
    state "Con diferencias entre sus versiones" as Discrepante
    state "Pendiente de decisión" as Pendiente
    state "Contado una sola vez, sin que nadie decidiera" as Contado
    state "Resuelto: vale una versión, y es la que suma" as ResueltoUna
    state "Resuelto: son ventas distintas, y suman todas" as ResueltoDistintas

    [*] --> Detectado: los códigos se comparan ignorando las diferencias de escritura que no cambian el código
    Detectado --> Identico: ninguna versión difiere de las otras
    Detectado --> Discrepante: alguna versión difiere en algún dato

    Identico --> Contado: se cuenta una sola vez, sin intervención humana
    Discrepante --> Pendiente

    Pendiente --> ResueltoUna: una persona elige cuál de las versiones vale
    Pendiente --> ResueltoDistintas: una persona declara que son ventas distintas

    ResueltoUna --> Pendiente: se deshace la resolución y los indicadores se recalculan
    ResueltoDistintas --> Pendiente: se deshace la resolución y los indicadores se recalculan

    Contado --> [*]
    ResueltoUna --> [*]
    ResueltoDistintas --> [*]

    note right of Identico
        Lo idéntico no necesita a una persona.
        El tablero informa cuántas ventas unificó solo
    end note

    note right of Pendiente
        Ninguna de sus versiones suma mientras el grupo
        esté pendiente, y el tablero dice cuántos grupos
        están esperando una decisión
    end note

    note right of ResueltoUna
        Queda registrado qué se decidió, quién lo decidió
        y cuándo. La versión elegida suma y la descartada
        se sigue viendo al lado
    end note

    note right of ResueltoDistintas
        Sólo se deshace lo que una persona decidió: un
        grupo que el sistema contó solo no tiene ninguna
        resolución que deshacer
    end note
```

## Qué le pasa a cada venta que llega del portal

```mermaid
---
title: Qué le pasa a cada venta que llega del portal
---
stateDiagram-v2
    state "Obtenida del portal, conservada tal como llegó" as Obtenida
    state "Repetida idéntica, unificada sin preguntar" as Unificada
    state "Repetida con datos en conflicto" as EnConflicto
    state "Con un dato roto" as Rota
    state "Con un monto fuera de lo habitual" as MontoAtipico
    state "Apartada, esperando una decisión" as Apartada
    state "Contada en los indicadores" as Contada
    state "Contada por decisión de una persona" as ContadaResuelta
    state "Descartada como versión no válida" as Descartada

    [*] --> Obtenida
    Obtenida --> Unificada: comparte código con otra y no difiere en ningún dato
    Obtenida --> EnConflicto: comparte código con otra y difieren en algún dato
    Obtenida --> Rota: llegó sin fecha, con una fecha que no existe, sin total, con cantidad negativa o apuntando a un producto que no existe
    Obtenida --> MontoAtipico: su total se aparta del promedio de su producto más que la diferencia tolerada
    Obtenida --> Contada: el dato está completo y es plausible

    Unificada --> Contada: se cuenta una sola vez y el tablero informa cuántas unificó

    EnConflicto --> Apartada
    Rota --> Apartada
    MontoAtipico --> Apartada

    Apartada --> Contada: una persona corrige el dato que faltaba o carga uno estimado
    Apartada --> ContadaResuelta: una persona la elige como la versión válida, o declara que son ventas distintas
    Apartada --> Descartada: es la versión de la repetida que la persona no eligió

    ContadaResuelta --> Apartada: se deshace la resolución de la repetida
    Descartada --> Apartada: se deshace la resolución de la repetida

    Contada --> [*]
    ContadaResuelta --> [*]

    note right of Obtenida
        Lo que informó el portal se conserva siempre.
        Una corrección se muestra encima, y el dato
        original queda para explicar cualquier diferencia
    end note

    note right of Apartada
        No suma en ningún indicador y no se borra.
        Queda contada y visible con su motivo, y el
        sistema no completa por suposición lo que falta
    end note

    note right of ContadaResuelta
        Suma igual que cualquier otra. Lo que la distingue
        es que salió de una decisión, y por eso se puede
        deshacer: lo que se contó solo no tiene nada que deshacer
    end note

    note right of Descartada
        Se sigue viendo junto a la elegida: una decisión
        se puede deshacer, y los números se recalculan
    end note
```

## El dueño — qué mira y qué decide

```mermaid
---
title: El dueño — qué mira y qué decide
---
flowchart TD
    A["El dueño quiere ver de un vistazo cómo viene el negocio desde 2023"] --> B["Abre el tablero completo"]
    B --> C["Lee primero el total facturado y cuántos registros quedaron afuera"]
    C --> D{"¿Puede confiar en el número?"}
    D -->|Ninguna venta repetida se contó dos veces| E["Sabe cuántas unificó el sistema solo por ser idénticas"]
    D -->|"Ninguna venta rota entró al total"| F["Las que faltan están contadas, visibles y con su motivo"]
    D -->|Algún valor es estimado| G["El indicador lo declara: estimar no es saber"]

    E --> H["Mira la facturación mes a mes, los precios, el stock y las altas"]
    F --> H
    G --> H

    A --> I["Ve el tablero completo: sobre las ventas, los mismos números que ve Julián"]
    I --> J["También resuelve ventas apartadas: elige entre las versiones de una repetida o corrige un dato roto"]
    J --> K["Y puede deshacer la resolución de una repetida: el caso vuelve a pendiente y los números se recalculan"]

    H --> L["El tablero se mira desde el primer día, aunque queden casos pendientes"]
    L --> M["Sus números mejoran a medida que la revisión avanza"]
```

## Tablero del negocio — de punta a punta

```mermaid
---
title: Tablero del negocio — de punta a punta
---
sequenceDiagram
    autonumber
    participant Sistema as El sistema
    participant Portal as Portal del proveedor
    actor Julian as Julián, ventas
    actor Duenio as El dueño
    actor Marcela as Marcela, compras

    loop Con la frecuencia configurada
        Sistema->>Portal: Entra por su cuenta y pide los registros de ventas
        Portal-->>Sistema: Los registros de ventas
        Sistema->>Sistema: Conserva cada registro tal como llegó
        Sistema->>Sistema: Compara los códigos ignorando las diferencias de escritura que no cambian el código

        alt Las que comparten código no difieren en ningún dato
            Sistema->>Sistema: Las cuenta una sola vez y anota cuántas unificó solo
        else Difieren en algún dato
            Sistema->>Sistema: Las aparta enteras, esperando una decisión
        end

        opt La venta llega sin fecha, con una fecha que no existe, sin total, con cantidad negativa, apuntando a un producto que no existe o con un total que se aparta del promedio de su producto más que la diferencia tolerada
            Sistema->>Sistema: La aparta con su motivo, sin frenar a las demás
            Note over Sistema: Ninguna se borra y ningún dato faltante<br/>se completa por suposición
        end

        Sistema->>Sistema: Calcula los indicadores sólo con las ventas que no están apartadas
    end

    Julian->>Sistema: Abre el tablero
    Sistema-->>Julian: Primero el total facturado del período y cuántos registros dejó afuera
    Sistema-->>Julian: La facturación mes a mes desde 2023, cuántas ventas hubo, y los cortes de precios, stock y altas
    Note over Julian,Sistema: Cada corte elige su propio período,<br/>y cada indicador dice cuántos registros excluyó

    Julian->>Sistema: Desde un indicador, pide ver los registros que excluyó
    Sistema-->>Julian: La lista, cada uno con el motivo por el que se apartó

    Julian->>Sistema: Abre un caso de venta repetida con datos en conflicto
    Sistema-->>Julian: Las versiones enfrentadas, con las diferencias señaladas
    Julian->>Sistema: Elige cuál vale, o declara que son ventas distintas
    Sistema->>Sistema: Incluye lo declarado válido, recalcula los indicadores y registra qué se decidió, quién y cuándo
    Sistema-->>Julian: El caso sale de pendientes y la versión descartada se sigue viendo

    opt La decisión estuvo equivocada
        Julian->>Sistema: Deshace la resolución
        Sistema->>Sistema: El caso vuelve a pendiente y los indicadores se recalculan
    end

    Julian->>Sistema: Corrige la fecha, el total, la cantidad o el producto de una venta apartada
    alt El dato correcto se puede conocer
        Sistema->>Sistema: La venta entra a los indicadores
    else No hay forma de conocerlo
        Julian->>Sistema: Carga el valor que estima
        Sistema->>Sistema: Marca el valor como estimado y lo avisa en todo indicador que lo use
    end
    Note over Sistema: Lo que informó el portal se conserva siempre,<br/>y la corrección se muestra encima

    Duenio->>Sistema: Abre el tablero completo y resuelve ventas apartadas
    Sistema-->>Duenio: Los mismos números y las mismas decisiones que ve ventas

    Marcela->>Sistema: Intenta abrir el tablero comercial o las ventas
    Sistema-->>Marcela: No tiene permiso, ni siquiera conociendo la dirección de la pantalla
```

## Julián, ventas — mira el tablero y resuelve lo apartado

```mermaid
---
title: Julián, ventas — mira el tablero y resuelve lo apartado
---
flowchart TD
    A["Julián quiere saber cómo viene el negocio sin armar la planilla a mano"] --> B["Abre el tablero"]
    B --> C["Lo primero que lee es el total facturado del período y cuántas ventas quedaron excluidas"]
    C --> D["Ve la facturación mes a mes desde 2023 y cuántas ventas hubo en el período"]
    D --> E["Ve cómo se movieron los precios del proveedor, cuánto stock había al inicio y al final, y qué productos se dieron de alta"]
    E --> F["Elige el período de cada corte por separado, sin mover el de los demás"]

    C --> G{"¿El total del mes cierra con la suma hecha a mano?"}
    G -->|Sí| H["Puede confiar en el número"]
    G -->|"No, y el tablero dice cuántas dejó afuera"| I["Hace un clic y ve cuáles son las ventas excluidas"]

    I --> J["Abre la pantalla de revisión"]
    J --> K{"¿Qué tipo de caso es?"}

    K -->|Una venta repetida con datos en conflicto| L["Ve las dos versiones enfrentadas, con las diferencias señaladas"]
    L --> M{"¿Son la misma venta cargada dos veces?"}
    M -->|Sí| N["Elige cuál de las versiones vale"]
    M -->|"No, son dos ventas distintas"| O["Declara que son ventas distintas y entran las dos"]
    N --> P["El total del mes se recalcula y la versión descartada se sigue viendo"]
    O --> P
    P --> Q{"¿Se equivocó al decidir?"}
    Q -->|Sí| R["Deshace la resolución: el caso vuelve a pendiente y los números vuelven atrás"]
    Q -->|No| S["El caso sale de pendientes, con qué decidió, quién y cuándo"]

    K -->|"Una venta con un dato roto o un monto atípico"| T["Lee el motivo por el que se apartó"]
    T --> U{"¿Se puede conocer el dato correcto?"}
    U -->|Sí| V["Corrige la fecha, el total, la cantidad o el producto"]
    V --> W["La venta entra a los indicadores"]
    U -->|No hay forma de saberlo| X["Carga el valor que estima"]
    X --> Y["El valor queda señalado como estimado y el indicador que lo usa lo avisa"]
    W --> S
    Y --> S
    S --> Z["Lo que informó el portal se sigue viendo debajo de la corrección"]
```

## Marcela, compras — qué queda fuera de su alcance

```mermaid
---
title: Marcela, compras — qué queda fuera de su alcance
---
flowchart TD
    A["Entra con su acceso y trabaja sobre compras y proveedores"] --> B["El tablero comercial y las ventas no son suyos"]
    B --> C["La facturación del negocio y sus cortes no aparecen en su menú"]
    B --> D["La pantalla de revisión de ventas apartadas tampoco"]
    C --> E{"¿Y si abre la dirección exacta de esa pantalla?"}
    D --> E
    E -->|Queda afuera igual| F["El sistema no se los muestra: no le corresponden por su rol"]
    D --> G["Tampoco resuelve una venta apartada: eso es de ventas y del dueño"]
```

## El sistema — qué hace con cada venta que llega del portal

```mermaid
---
title: El sistema — qué hace con cada venta que llega del portal
---
flowchart TD
    A["Con la frecuencia configurada, trae del portal los registros de ventas"] --> B["Conserva cada registro tal como llegó"]
    B --> C{"¿Hay otra venta con el mismo código?"}
    C -->|"Compara los códigos ignorando las diferencias de escritura que no cambian el código"| D{"¿Las versiones difieren en algún dato?"}

    D -->|No difieren en nada| E["Las cuenta una sola vez, sin esperar a nadie"]
    E --> F["Informa cuántas ventas repetidas unificó solo"]
    D -->|Difieren| G["Las aparta enteras y las deja esperando una decisión"]
    G --> H["Informa cuántos grupos de repetidas hay pendientes"]

    C -->|Es la única con ese código| I{"¿El dato es utilizable?"}
    F --> I
    I -->|Sin fecha| J["La aparta con su motivo"]
    I -->|"Con una fecha que no existe, como el 31 de febrero"| J
    I -->|Sin total| J
    I -->|Con una cantidad negativa| J
    I -->|Apunta a un producto que no existe| J
    I -->|"El total se aparta del promedio de ese producto más que la diferencia tolerada"| K["La aparta como monto atípico"]
    K --> J
    I -->|Está completo y es plausible| L["Entra al cálculo de los indicadores"]

    J --> M["No suma en ningún indicador, y no se borra ni se completa por suposición"]
    G --> M
    M --> N["Queda en la pantalla de revisión, contada y con su motivo"]

    L --> O["Calcula la facturación mes a mes desde 2023 y la cantidad de ventas del período"]
    O --> P["Calcula los cortes de precios del proveedor, de stock y de altas de productos"]
    P --> Q["Junto a cada indicador informa cuántos registros excluyó, incluso cuando no excluyó ninguno"]
    Q --> R["Y avisa si alguno de los valores que lo componen es estimado"]

    N --> S["Una persona resuelve el caso"]
    S --> T["Recalcula los indicadores con lo que esa persona declaró válido"]
    T --> Q
```
