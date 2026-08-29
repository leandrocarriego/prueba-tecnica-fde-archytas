<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## El camino de un comprobante de pago

```mermaid
---
title: El camino de un comprobante de pago
---
stateDiagram-v2
    state "Traído del portal" as Traido
    state "Cargado a mano" as AMano
    state "Apartado para revisión" as Apartado
    state "Imputado a su factura" as Imputado
    state "Unificado en un solo pago" as Unificado
    state "Dejado sin efecto" as SinEfecto

    [*] --> Traido: el sistema lo trae con la frecuencia configurada
    [*] --> AMano: compras registra un pago que todavía no aparece en el portal
    Traido --> Imputado: indica una sola factura registrada y no se parece a ningún pago cargado a mano
    AMano --> Imputado: se imputa a la factura sobre la que se cargó
    Traido --> Apartado: su factura no está registrada
    Traido --> Apartado: cubre más de una factura
    Traido --> Apartado: coincide en factura y monto con un pago cargado a mano
    Apartado --> Imputado: entra la factura que faltaba y el sistema lo imputa e informa
    Apartado --> Imputado: compras reparte el monto y el reparto suma exacto
    Apartado --> Imputado: una persona resuelve que no era el mismo pago
    Apartado --> Unificado: una persona resuelve que era el mismo pago y la factura queda con uno solo
    AMano --> SinEfecto: compras lo deja sin efecto
    Imputado --> [*]
    Unificado --> [*]
    SinEfecto --> [*]

    note right of Traido
        Se conserva tal como llegó del portal, y si vuelve
        a llegar no se imputa dos veces. Nunca se borra:
        lo que se puede dejar sin efecto es lo que cargó
        una persona
    end note

    note right of Apartado
        Mientras está apartado ningún saldo se mueve.
        Nada se descarta ni se aplica a la factura que
        más se le parezca
    end note
```

## El estado de pago de una factura

```mermaid
---
title: El estado de pago de una factura
---
stateDiagram-v2
    state "Sin pagos" as SinPagos
    state "Parcialmente pagada" as Parcial
    state "Saldada" as Saldada
    state "Señalada como inconsistente" as Inconsistente

    [*] --> SinPagos: la factura entra al sistema
    SinPagos --> Parcial: se le imputa un pago que no llega a cubrir su total
    Parcial --> Parcial: se le imputa otro pago a cuenta
    Parcial --> Saldada: los pagos imputados cubren el total
    SinPagos --> Saldada: un solo pago cubre el total
    Parcial --> SinPagos: se deja sin efecto un pago cargado a mano
    Saldada --> Parcial: se deja sin efecto un pago cargado a mano
    SinPagos --> Inconsistente: los pagos imputados superan el total
    Parcial --> Inconsistente: los pagos imputados superan el total
    Saldada --> Inconsistente: los pagos imputados superan el total
    Inconsistente --> Parcial: se deja sin efecto el pago cargado a mano que sobraba
    Saldada --> [*]

    note right of SinPagos
        El estado sale siempre de los pagos imputados.
        Si el portal informa otra cosa, no gana el portal:
        la diferencia queda señalada con los dos datos
        a la vista
    end note

    note right of Parcial
        Muestra el monto pagado, el saldo pendiente y
        el porcentaje pagado
    end note

    note right of Inconsistente
        Muestra su total y la suma de sus pagos, queda
        afuera de los totales de deuda —que informan que
        la excluyeron— y nunca figura como saldada
    end note
```

## El recibo de recepción de una factura

```mermaid
---
title: El recibo de recepción de una factura
---
stateDiagram-v2
    state "Sin recibo emitido" as SinRecibo
    state "Avisada por vencimiento cercano" as Avisada
    state "Recibo emitido" as Emitido
    state "Incidente abierto" as Incidente
    state "Incidente cerrado" as Cerrado

    [*] --> SinRecibo: la factura entra al sistema
    SinRecibo --> Avisada: faltan para su vencimiento los días de anticipación configurados
    Avisada --> Avisada: sigue sin recibo, y no se vuelve a avisar por la misma causa
    SinRecibo --> Emitido: compras emite el recibo antes del vencimiento
    Avisada --> Emitido: compras emite el recibo antes del vencimiento
    Emitido --> SinRecibo: compras anula el recibo y la fecha todavía no pasó
    SinRecibo --> Incidente: se pasa la fecha de vencimiento sin recibo
    Avisada --> Incidente: se pasa la fecha de vencimiento sin recibo
    Emitido --> Incidente: compras anula el recibo y la fecha ya pasó
    Incidente --> Cerrado: compras lo cierra indicando qué se hizo
    Emitido --> [*]
    Cerrado --> [*]

    note right of Emitido
        Lleva su número propio y correlativo, su documento
        se descarga para el proveedor, y queda registrado
        quién lo emitió y cuándo
    end note

    note right of Incidente
        Pasada la fecha ya no se emite el recibo, ni
        siquiera con el incidente cerrado. Las 17 facturas
        que arrancan vencidas sin recibo entran acá,
        con la fecha en que se pasaron
    end note

    note right of Cerrado
        Deja de contarse entre los pendientes, y el motivo
        queda consultable con quién lo cerró y cuándo
    end note
```

## El dueño — cuánto debe, a quién, y hace cuánto

```mermaid
---
title: El dueño — cuánto debe, a quién, y hace cuánto
---
flowchart TD
    A["Abre la lista de facturas"] --> B["Ve de un vistazo cuáles están saldadas, a medias y sin tocar"]
    B --> C["De cada una, el monto pagado, el saldo y el porcentaje pagado"]
    C --> D{"¿El número le cierra con la cuenta hecha a mano?"}
    D -->|No cierra| E["La factura aparece señalada, con su total y la suma de sus pagos"]
    E --> F["El sistema la dejó afuera de la deuda y lo dice, en lugar de acomodar el número"]

    A --> G["Abre la ficha de un proveedor"]
    G --> H["Cuánto le pagó y cuánto le debe"]
    G --> I["Cómo se reparte esa deuda por antigüedad, contada desde cada vencimiento"]
    G --> J["Cuántos días en promedio se le paga tarde contra el plazo pactado con él"]
    G --> K["Cuántas facturas quedaron excluidas, y llega a verlas"]

    A --> L["Recibe por WhatsApp, en copia, el aviso de un vencimiento sin recibo"]
    L --> M["Un aviso por vencimiento, no uno por día"]
    A --> N["Define con cuántos días de anticipación quiere que avise"]
    N --> O["Arranca en tres días y el próximo aviso sale con el valor nuevo"]
```

## Pagos y recibos de recepción — de punta a punta

```mermaid
---
title: Pagos y recibos de recepción — de punta a punta
---
sequenceDiagram
    autonumber
    participant Portal as El portal del proveedor
    participant Sistema as El sistema
    actor Marcela as Marcela, compras
    actor Duenio as El dueño

    Sistema->>Portal: Con la frecuencia configurada, trae los comprobantes de pago y los recibos ya emitidos
    Sistema->>Sistema: Conserva cada comprobante tal como llegó
    Sistema->>Sistema: Lo imputa a la factura que indica y actualiza su saldo
    Sistema-->>Duenio: La lista muestra cada factura saldada, a medias o sin tocar, con su saldo

    alt El comprobante no se puede imputar solo
        Sistema->>Sistema: Lo aparta sin tocar ningún saldo
        Note over Sistema,Marcela: Apunta a una factura que todavía no está,<br/>cubre varias facturas,<br/>o se parece a un pago cargado a mano
        Marcela->>Sistema: Reparte el monto entre las facturas que cubre, o resuelve si son el mismo pago
        Sistema->>Sistema: Recién ahí mueve los saldos, y registra quién lo decidió
    else Aparece después la factura que faltaba
        Sistema->>Sistema: Le imputa el comprobante que estaba esperando e informa que lo hizo
    end

    alt Los números no cierran
        Sistema-->>Duenio: Señala la factura con su total y la suma de sus pagos a la vista
        Sistema->>Sistema: La deja afuera de los totales de deuda y avisa que la excluyó
        Note over Sistema,Duenio: Si el portal la da por pagada y sus comprobantes no llegan al total,<br/>gana la suma de los comprobantes y la diferencia queda señalada
    end

    Marcela->>Sistema: Emite el recibo de recepción de una factura que todavía no venció
    Sistema-->>Marcela: Le da su número correlativo y el documento para descargar
    Sistema->>Sistema: Registra quién lo emitió y cuándo

    Sistema-->>Marcela: Tres días antes del vencimiento de una factura sin recibo, avisa por WhatsApp
    Sistema-->>Duenio: El mismo aviso le llega en copia
    Note over Sistema,Duenio: Un aviso por vencimiento, no uno por día.<br/>Si el recibo ya está emitido, no avisa

    alt La fecha se pasó igual
        Marcela->>Sistema: Intenta emitir el recibo de una factura vencida
        Sistema-->>Marcela: No la deja y le explica por qué
        Sistema->>Sistema: Señala la factura como incidente, con la fecha en que se pasó
        Marcela->>Sistema: Cierra el incidente indicando qué se hizo
        Sistema->>Sistema: Deja de contarlo entre los pendientes y conserva el motivo, con quién lo cerró y cuándo
    end

    Duenio->>Sistema: Abre un proveedor
    Sistema-->>Duenio: Le muestra cuánto le pagó, cuánto le debe, desde cuándo venció cada parte y cuántos días en promedio se le paga tarde
    Sistema-->>Duenio: Y cuántas facturas quedaron afuera de esos totales
    Duenio->>Sistema: Cambia con cuántos días de anticipación quiere el aviso
```

## Julián, ventas — qué queda fuera de su alcance

```mermaid
---
title: Julián, ventas — qué queda fuera de su alcance
---
flowchart TD
    A["Entra con su acceso y trabaja sobre ventas y el tablero comercial"] --> B["Los pagos y las cuentas de proveedores no son suyos"]
    B --> C["El estado de pago de una factura, sus comprobantes y sus recibos no aparecen en su menú"]
    B --> D["La deuda por proveedor y su antigüedad tampoco"]
    C --> E{"¿Y si abre la dirección exacta de esa pantalla?"}
    E -->|Queda afuera igual| F["El sistema no se los muestra: no le corresponden por su rol"]
    D --> E
```

## Marcela, compras — el trabajo del día sobre pagos y recibos

```mermaid
---
title: Marcela, compras — el trabajo del día sobre pagos y recibos
---
flowchart TD
    A["Abre la lista de facturas"] --> B["Ve cuáles están saldadas, a medias y sin tocar, con su saldo"]
    B --> C["Filtra por estado de pago, por proveedor, por vencimiento o por si tienen recibo"]

    A --> D{"¿Pagamos algo que todavía no aparece del sistema viejo?"}
    D -->|Sí| E["Registra el pago a mano con su monto y su fecha"]
    E --> F{"¿El monto supera el saldo de la factura?"}
    F -->|Sí| G["El sistema la advierte antes de confirmar"]
    F -->|No| H["El saldo baja y el pago queda con su nombre y la fecha en que lo cargó"]
    H --> I{"¿Lo cargó mal?"}
    I -->|Sí| J["Lo deja sin efecto y el saldo vuelve a lo anterior"]
    I -->|Vino del portal| K["Ese no se puede dejar sin efecto: es lo que informó el origen"]

    A --> L["Revisa lo que el sistema apartó"]
    L --> M{"¿Por qué está apartado?"}
    M -->|Cubre varias facturas| N["Reparte el monto entre esas facturas hasta que sume exacto"]
    M -->|Se parece a un pago que ella cargó| O["Resuelve si son el mismo pago o dos distintos"]
    M -->|Su factura todavía no estaba| P["No hace nada: el sistema lo imputa solo cuando la factura entre"]

    A --> Q{"¿Esta factura ya tiene su recibo de recepción?"}
    Q -->|No, y todavía no venció| R["Lo emite desde el sistema"]
    R --> S["Queda con su número correlativo y descarga el documento para el proveedor"]
    S --> T{"¿Lo emitió por error?"}
    T -->|Sí| U["Lo anula, y queda registrado quién lo anuló y cuándo"]
    U --> V["Si la fecha todavía no pasó, emite uno nuevo"]
    U --> W["Si la fecha ya pasó, la factura queda señalada como incidente"]
    Q -->|No, y la fecha ya pasó| X["El sistema no la deja emitirlo y le explica por qué"]
    X --> Y["Cierra el incidente indicando qué se hizo"]
    Y --> Z["Deja de figurar entre los pendientes, y el motivo queda a la vista con su nombre"]
    Q -->|Sí| AA["Por esa factura no le llega ningún aviso de vencimiento"]
```

## El sistema — qué hace con cada comprobante y con cada vencimiento

```mermaid
---
title: El sistema — qué hace con cada comprobante y con cada vencimiento
---
flowchart TD
    A["Con la frecuencia configurada, trae del portal los comprobantes de pago y los recibos emitidos"] --> B["Conserva cada comprobante tal como llegó"]
    B --> C{"¿Ya lo había traído antes?"}
    C -->|Sí| D["No lo imputa de nuevo: el saldo no se descuenta dos veces"]
    C -->|No| E{"¿A cuántas facturas apunta?"}

    E -->|A una que no tiene registrada| F["Lo aparta para revisión, sin perderlo"]
    F --> G{"¿Entró después esa factura?"}
    G -->|Sí| H["Le imputa el comprobante que estaba esperando e informa que lo hizo"]
    G -->|Todavía no| F

    E -->|A varias facturas| I["Lo aparta para que una persona reparta el monto"]
    I --> J{"¿El reparto suma exacto el monto del comprobante?"}
    J -->|No| K["No deja confirmarlo y ningún saldo se mueve"]
    K --> I
    J -->|Sí| L["Imputa cada parte a su factura y registra quién repartió y cuándo"]

    E -->|A una sola factura| M{"¿Coincide en factura y monto con un pago cargado a mano?"}
    M -->|Sí| N["Lo aparta y pregunta, en lugar de unirlos o contarlos dos veces"]
    M -->|No| O["Lo imputa a su factura"]
    H --> O
    L --> P["Recalcula el saldo y el estado de la factura"]
    O --> P

    P --> Q{"¿Los pagos superan el total de la factura?"}
    Q -->|Sí| R["La señala como inconsistente, con los dos números a la vista"]
    R --> S["La deja afuera de los totales de deuda e informa que la excluyó"]
    Q -->|No| T{"¿El portal informa un estado distinto del que dan los pagos?"}
    T -->|Sí| U["Manda la suma de los pagos, y señala la diferencia mostrando los dos estados"]
    T -->|No| V["Muestra la factura como saldada, parcial con su porcentaje, o sin pagos"]

    W["Vigila las facturas que siguen sin su recibo de recepción"] --> X{"¿Faltan para su vencimiento los días de anticipación configurados?"}
    X -->|Sí, y no avisó antes por este vencimiento| Y["Avisa por WhatsApp a compras, con copia al dueño"]
    X -->|Ya avisó| Z["No vuelve a avisar por la misma causa"]
    X -->|La fecha ya pasó| AA["Señala la factura como incidente y no permite emitirle el recibo"]
```

