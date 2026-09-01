-- ¿Cuántos pendientes abre la 011 el primer día?
--
-- El único riesgo «Alto» que anotó `docs/specs/011-set-aside-visibility/plan.md`:
-- cuatro orígenes que nunca abrieron un caso van a abrir todo lo que tengan
-- apartado. Una lista impracticable se abandona, que es el fracaso exacto que la
-- feature quiere evitar, así que el número se mide **antes** de shipear.
--
-- Es de SÓLO LECTURA: no escribe, no bloquea y se puede correr en producción con
-- la base andando.
--
--   psql "$DATABASE_URL" -f scripts/dry-run/011_avalancha.sql
--
-- Cómo leerlo: `pendientes` es lo que va a aparecer en «Revisar esto», y
-- `filas_apartadas` es de cuántas filas sale. Cuando los dos números coinciden,
-- ese origen **no agrupa**, y es a propósito: el pendiente de un comprobante y
-- el de una venta se identifican por su fila de `staging` porque es la misma
-- clave con la que la pantalla que los resuelve los cierra sola (RF-20). El
-- padrón y el buzón sí agrupan, por recorte y motivo.
--
-- Ojo con el buzón: mide lo que hay apartado, y lo que se apartó **antes** de
-- que existieran estos suscriptores no abre caso solo en la próxima lectura
-- (`test_the_inbox_is_the_one_that_does_not`). Ese número se cobra sólo si se
-- decide backfillear.

WITH apartadas AS (
    SELECT 'padrón de proveedores' AS origen,
           md5(excerpt || '|' || reason)  AS agrupa_por
      FROM staging.supplier_row
     WHERE status = 'QUARANTINED'

    UNION ALL
    SELECT 'comprobantes de pago',
           id::text                        -- una fila, un pendiente
      FROM staging.payment_row
     WHERE status = 'QUARANTINED'

    UNION ALL
    SELECT 'buzón',
           md5(excerpt || '|' || reason)
      FROM staging.message_row
     WHERE status = 'QUARANTINED'

    UNION ALL
    SELECT 'ventas',
           id::text                        -- una fila, un pendiente
      FROM staging.sale_row
     WHERE status = 'QUARANTINED'
),
-- Los cuatro se nombran siempre, aunque no tengan nada apartado: un origen que
-- desaparece de la salida se lee como «no lo midió», que es otra cosa que cero.
origenes(origen) AS (
    VALUES ('padrón de proveedores'), ('comprobantes de pago'), ('buzón'), ('ventas')
)
SELECT o.origen,
       COUNT(DISTINCT a.agrupa_por) AS pendientes,
       COUNT(a.agrupa_por)          AS filas_apartadas
  FROM origenes o
  LEFT JOIN apartadas a ON a.origen = o.origen
 GROUP BY o.origen

UNION ALL

SELECT 'TOTAL', COUNT(DISTINCT origen || '|' || agrupa_por), COUNT(*)
  FROM apartadas
 ORDER BY 1;
