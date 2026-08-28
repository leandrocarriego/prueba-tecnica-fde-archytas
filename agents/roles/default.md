# Rol — Default

## Propósito
Este rol es un alias explícito de `Lead`.

Garantiza que el agente siempre opere bajo un rol definido cuando el usuario no especifica
ninguno, tal como lo establece `AGENTS.md` ("Rol por defecto").

## Rol efectivo
- Lead

Todas las prioridades, restricciones y skills obligatorias se heredan de `lead.md`.

Consecuencia deliberada: por defecto el agente **orquesta y delega, no escribe código**. Para
trabajar directamente sobre el código hay que asumir un rol que lo permita (`Developer`,
`Tester`, `Backend-Architect`, `Frontend-Architect`).

## Notas
- Este rol no tiene comportamiento propio.
- El cambio de rol sigue rigiéndose por las reglas de `AGENTS.md` (selección automática de rol
  y triggers explícitos).
