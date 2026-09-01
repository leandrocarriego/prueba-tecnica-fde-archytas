<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## El vencimiento de una factura — reprogramar a tiempo y reprogramar tarde

```mermaid
---
title: El vencimiento de una factura — reprogramar a tiempo y reprogramar tarde
---
stateDiagram-v2
    state "Por vencer, sin su recibo de recepción" as PorVencer
    state "Reprogramada antes de vencer" as ATiempo
    state "Vencida sin su recibo de recepción" as VencidaSinRecibo
    state "Reprogramada después de haber vencido" as Tarde
    state "Con su recibo de recepción emitido" as ConRecibo

    [*] --> PorVencer: la factura entra al calendario en la fecha en que vence
    PorVencer --> ATiempo: el dueño o compras la mueve antes de que llegue su fecha
    ATiempo --> PorVencer: la fecha nueva vale a todos los efectos
    PorVencer --> ConRecibo: se emite su recibo antes del vencimiento
    PorVencer --> VencidaSinRecibo: llega su fecha y el recibo no se emitió
    VencidaSinRecibo --> Tarde: el dueño o compras la mueve después de que su fecha pasó
    Tarde --> VencidaSinRecibo: la fecha nueva dice cuándo se va a pagar, y nada más
    ConRecibo --> [*]

    note right of ATiempo
        El acuerdo con el proveedor se hizo antes: hasta
        la fecha nueva se puede emitir el recibo, y contra
        ella se mide el atraso del proveedor
    end note

    note right of Tarde
        No destraba el recibo ni borra el atraso: eso ya
        pasó y el sistema no lo reescribe. El atraso se
        sigue midiendo contra la fecha original, y en el
        calendario sigue señalada como vencida sin recibo
    end note

    note right of ConRecibo
        El calendario distingue a simple vista las que
        tienen su recibo de las que no, y permite mostrar
        sólo las que no lo tienen. Emitirlo se hace fuera
        del calendario
    end note
```

## La vida de un vencimiento en el calendario

```mermaid
---
title: La vida de un vencimiento en el calendario
---
stateDiagram-v2
    state "Colocado por el sistema, desde una factura" as DesdeFactura
    state "Cargado a mano por una persona" as AMano
    state "En el calendario, por venir" as PorVenir
    state "En el calendario, ya vencido" as Vencido
    state "Reprogramado, con su fecha anterior guardada" as Reprogramado
    state "Eliminado del calendario" as Eliminado

    [*] --> DesdeFactura: se registra una factura con su vencimiento
    [*] --> AMano: el dueño o compras carga un vencimiento propio
    DesdeFactura --> PorVenir
    AMano --> PorVenir
    PorVenir --> PorVenir: si se cargó a mano, se corrige su descripción o su monto, y queda el valor anterior
    PorVenir --> Vencido: llega su fecha y pasa
    PorVenir --> Reprogramado: el dueño o compras lo mueve a otro día
    Vencido --> Reprogramado: el dueño o compras lo mueve a otro día
    Reprogramado --> Reprogramado: se lo vuelve a mover, y el historial suma otra fecha
    Reprogramado --> PorVenir: la fecha nueva todavía no llegó
    Reprogramado --> Vencido: la fecha nueva ya pasó
    PorVenir --> Eliminado: sólo si es un vencimiento cargado a mano
    Vencido --> Eliminado: sólo si es un vencimiento cargado a mano
    Eliminado --> [*]

    note right of DesdeFactura
        En el calendario se distingue de los cargados a
        mano. No se elimina: la factura existe y vence,
        así que se puede reprogramar, no hacer
        desaparecer. Su monto y su descripción se
        corrigen en la factura
    end note

    note right of Reprogramado
        Nunca se pierde la fecha original. Cada
        movimiento guarda de dónde venía, quién lo movió,
        cuándo, y el motivo si se escribió. Al abrirlo se
        ven todas las fechas por las que pasó, y en el
        calendario queda señalado como reprogramado
    end note

    note right of Vencido
        Mover un vencimiento mueve la fecha, no la deuda:
        el monto, el estado de pago y lo que se le debe al
        proveedor quedan como estaban. Si la fecha nueva
        ya pasó, el sistema pide confirmación antes de
        aplicar el cambio
    end note

    note right of Eliminado
        Si dos personas mueven el mismo vencimiento casi
        a la vez, vale la última fecha y los dos
        movimientos quedan registrados: el sistema no
        elige cuál tenía razón, deja ver qué pasó
    end note
```

## El dueño — el mismo calendario, al mismo tiempo

```mermaid
---
title: El dueño — el mismo calendario, al mismo tiempo
---
flowchart TD
    A["Abre el calendario completo"] --> B["Todo lo que vence, mes por mes, con su monto y su proveedor"]
    B --> C["Cuáles facturas están saldadas, cuáles van por la mitad y cuáles no se tocaron"]
    C --> D["Oculta las saldadas y le queda a la vista lo que todavía hay que resolver"]
    B --> E["Cuáles tienen su recibo de recepción emitido y cuáles no"]
    E --> F["Las que ya vencieron sin su recibo aparecen señaladas"]

    A --> G["Agrega vencimientos propios y reprograma, igual que compras"]

    A --> H{"¿Marcela está mirando el mismo calendario?"}
    H -->|Ella mueve un vencimiento| I["Él lo ve moverse en el momento, sin recargar la pantalla"]
    I --> J["Y ve que ese cambio lo hizo ella"]
    H -->|Los dos mueven el mismo| K["Queda la última fecha, y el historial conserva los dos movimientos"]
    H -->|Se interrumpe la conexión en vivo| L["El sistema le avisa que el calendario puede estar desactualizado"]
    L --> M["Cuando se restablece, se lo muestra al día"]

    A --> N["Abre un vencimiento reprogramado"]
    N --> O["Su fecha original, todas sus reprogramaciones, quién las hizo y los motivos escritos"]

    A --> P["Julián consulta el calendario, pero no lo cambia"]
```

## Calendario de vencimientos — de punta a punta

```mermaid
---
title: Calendario de vencimientos — de punta a punta
---
sequenceDiagram
    autonumber
    participant Sistema as El sistema
    actor Marcela as Marcela, compras
    actor Duenio as El dueño
    actor Julian as Julián, ventas

    Sistema->>Sistema: Coloca en el calendario el vencimiento de cada factura registrada
    Marcela->>Sistema: Abre el calendario
    Sistema-->>Marcela: El mes en curso, con cada vencimiento en su día, su descripción, su monto y su proveedor
    Sistema-->>Marcela: Distingue lo ya vencido de lo por venir, lo que tiene su recibo de lo que no, y si la factura está saldada, a medias o sin pagos
    Note over Sistema,Marcela: Un día con más vencimientos de los que entran en pantalla<br/>indica cuántos hay y deja verlos todos
    Marcela->>Sistema: Pide ver sólo las facturas sin su recibo, y ocultar las saldadas
    Marcela->>Sistema: Abre un vencimiento y llega a la factura que lo originó

    Marcela->>Sistema: Carga un vencimiento propio con su fecha, su descripción y su monto
    Sistema->>Sistema: Lo coloca en su día, lo distingue de los que vienen de una factura, y registra quién lo cargó y cuándo

    Marcela->>Sistema: Arrastra un vencimiento del 10 al 20
    alt La fecha nueva ya pasó
        Sistema-->>Marcela: Pide confirmación antes de aplicar el cambio
    end
    Sistema->>Sistema: Guarda la fecha anterior, quién lo movió y cuándo, y le ofrece escribir un motivo sin exigirlo

    alt La factura todavía no había vencido
        Sistema->>Sistema: Su recibo se puede emitir hasta la fecha nueva, y el atraso del proveedor se mide contra ella
    else La factura ya se había vencido
        Sistema->>Sistema: Su recibo sigue sin poder emitirse, el atraso se mide contra la fecha original, y sigue señalada como vencida sin recibo
    end

    Sistema-->>Duenio: En su pantalla, abierta al mismo tiempo, el vencimiento se mueve solo y con el nombre de quién lo movió
    Note over Sistema,Duenio: Sin que tenga que recargar nada. Si dos personas mueven el mismo vencimiento,<br/>queda la última fecha y los dos movimientos quedan en el historial
    alt Se interrumpe la conexión en vivo
        Sistema-->>Duenio: Le avisa que el calendario puede estar desactualizado
        Sistema-->>Duenio: Al restablecerse, le muestra el calendario al día
    end

    Duenio->>Sistema: Abre un vencimiento reprogramado
    Sistema-->>Duenio: Su fecha original, todas sus reprogramaciones y los motivos que se hayan escrito

    Julian->>Sistema: Abre el calendario y consulta qué se viene
    Julian->>Sistema: Intenta arrastrar un vencimiento
    Sistema-->>Julian: No se lo permite, porque agregar, corregir, mover y eliminar no son de su rol

    Marcela->>Sistema: Desde el teléfono, consulta qué vence y reprograma eligiendo la fecha nueva de un selector
```

## Julián, ventas — consulta el calendario, no lo cambia

```mermaid
---
title: Julián, ventas — consulta el calendario, no lo cambia
---
flowchart TD
    A["Abre el calendario y lo ve completo"] --> B["Sabe qué vence cada día, con su monto y su proveedor"]
    B --> C{"¿Intenta cambiar algo?"}
    C -->|Arrastrar un vencimiento a otro día| D["El sistema no se lo permite"]
    C -->|Agregar un vencimiento propio| D
    C -->|Corregirlo o eliminarlo| D
    D --> E["Mover fechas de compras no es su trabajo; saber qué se viene, sí"]
```

## Marcela, compras — el calendario en el día a día

```mermaid
---
title: Marcela, compras — el calendario en el día a día
---
flowchart TD
    A["Abre el calendario y lo encuentra en el mes en curso"] --> B["En cada día, lo que vence, con su descripción, su monto y su proveedor"]
    B --> C["Pasa al mes siguiente y al anterior"]
    B --> D["Un día con más vencimientos de los que entran indica cuántos hay y los muestra todos"]
    B --> E["Lo ya vencido se distingue a simple vista de lo que está por venir"]
    B --> F["Abre un vencimiento y llega a la factura que lo originó"]

    A --> G{"¿Qué me falta hacer esta semana?"}
    G -->|Facturas sin su recibo de recepción| H["Se distinguen de las que ya lo tienen, y puede mostrar sólo esas"]
    H --> I["Las que ya vencieron sin su recibo aparecen señaladas"]
    G -->|Facturas sin terminar de pagar| J["Cada una se ve saldada, a medias o sin pagos, y puede ocultar las saldadas"]

    A --> K{"¿Este vencimiento viene de una factura?"}
    K -->|No, lo cargo yo| L["Carga su fecha, su descripción y su monto, y queda con su nombre y el momento en que lo cargó"]
    L --> M["En el calendario se distingue de los que vienen de una factura"]
    M --> N{"¿Lo cargó mal?"}
    N -->|Sí| O["Corrige la descripción o el monto, y queda registrado quién corrigió, cuándo y qué valor había antes"]
    N -->|Ya no corresponde| P["Lo elimina del calendario"]
    K -->|Sí| Q["El monto y la descripción se corrigen en la factura, no acá, y el vencimiento no se puede eliminar"]

    A --> R{"¿El proveedor avisó una fecha nueva?"}
    R -->|Desde la computadora| S["Arrastra el vencimiento al día nuevo"]
    R -->|Desde el teléfono| T["Elige la fecha nueva de un selector, sin arrastrar"]
    S --> U{"¿La fecha nueva ya pasó?"}
    T --> U
    U -->|Sí| V["El sistema pide confirmación antes de aplicar el cambio"]
    U -->|No| W["Queda guardada la fecha anterior, quién lo movió y cuándo"]
    V --> W
    W --> X["Puede escribir un motivo, y también dejarlo sin motivo"]
    X --> Y["El vencimiento queda señalado como reprogramado, y al abrirlo se ven todas las fechas por las que pasó"]
```

## El sistema — qué pone en el calendario y qué avisa

```mermaid
---
title: El sistema — qué pone en el calendario y qué avisa
---
flowchart TD
    A["Se registra una factura con su vencimiento"] --> B["La coloca en el calendario, en su día, sin que nadie la agregue"]
    B --> C["La muestra con su descripción, su monto y su proveedor"]
    C --> D["Y con si tiene su recibo emitido, y si está saldada, a medias o sin pagos"]

    E["El dueño o compras mueve un vencimiento"] --> F["Guarda la fecha anterior, quién lo movió, cuándo, y el motivo si lo escribió"]
    F --> G{"¿La factura ya se había vencido cuando la movieron?"}
    G -->|Todavía no vencía| H["El plazo para emitir su recibo pasa a ser la fecha nueva"]
    H --> I["Y el atraso de su proveedor se mide contra la fecha nueva"]
    G -->|Ya estaba vencida| J["No destraba el recibo: sigue sin poder emitirse"]
    J --> K["El atraso de su proveedor se mide contra la fecha original"]
    K --> L["Y en el calendario sigue señalada como vencida sin su recibo"]
    F --> M["El monto de la factura, su estado de pago y lo que se le debe al proveedor no cambian"]

    N["Alguien agrega, mueve, corrige o elimina un vencimiento"] --> O["Refleja el cambio en las pantallas de las demás personas que están mirando el calendario"]
    O --> P["Sin que tengan que recargar la pantalla, e indicando quién lo hizo"]
    P --> Q{"¿Dos personas movieron el mismo vencimiento?"}
    Q -->|Sí| R["Aplica el último cambio y conserva el anterior en el historial"]

    S{"¿La conexión en vivo se interrumpió?"} -->|Sí| T["Avisa a quien está mirando que el calendario puede estar desactualizado"]
    T --> U["Cuando se restablece, le muestra el estado actualizado del calendario"]
```
