# Skill — Radiografía del estado real del proyecto

Tags: [diagnóstico]

Rol dueño: **Lead**.

## Objetivo
Dar una foto **verificada** del estado del proyecto: servicios, base, migraciones y qué falta
construir. Cada punto se comprueba ejecutándolo.

## Cuándo usarla
- Al retomar el trabajo después de un tiempo.
- Antes de planificar, para saber sobre qué se está parado de verdad.
- Cuando algo no anda y no está claro qué parte del entorno falta.

## Precondiciones
- Ninguna. Es diagnóstico: corre sobre cualquier estado del repositorio.

## Reglas (ESTRICTO)
- **No se asume nada.** Un punto que no se pudo verificar se informa como *no verificado*, no
  como *bien*.
- Es de sólo lectura: no levanta servicios ni aplica migraciones para "arreglar" lo que encuentra.

## Pasos (ORDEN OBLIGATORIO)
1. Verificar el estado ejecutando cada comprobación (servicios, base, migraciones, suite, y qué
   módulos de dominio existen contra los que el proyecto define).
2. Contrastar contra lo que la documentación dice que debería haber.
3. Reportar diferencias, no impresiones.

## Validación
- [ ] Cada afirmación del reporte salió de un comando, y se dice cuál.
- [ ] Lo que no se pudo verificar figura como tal.

## Errores comunes (evitar)
- Reportar "todo bien" a partir de leer la documentación en vez de ejecutar.
