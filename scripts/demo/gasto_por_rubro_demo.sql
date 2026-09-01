-- Datos de demostración del gasto por rubro (P7, feature del gasto por rubro).
--
-- Simula lo que dejaría el evento `PurchaseOrdersNormalized` sobre la proyección
-- `core.order_spend` de `catalog`: una fila por línea de orden, con el producto
-- y el monto. La pantalla de Rubros suma esto por rubro.
--
-- **Es dato de demo, no del portal.** Igual que `precios_demo.sql`, se inserta
-- directo. Los `staging_row_id` van en el rango 990001–990999 para poder borrarlo:
--
--   DELETE FROM core.order_spend WHERE staging_row_id BETWEEN 990001 AND 990999;
--
-- Cargar (después de precios_demo.sql, que crea los productos DEMO):
--   docker exec -i cordillera_postgres psql -U cordillera -d cordillera < scripts/demo/gasto_por_rubro_demo.sql
--
-- Las dos últimas líneas (VARIOS) tienen un código que no matchea ningún
-- producto: son «pedazos sueltos», el gasto que cae en «sin rubro».

begin;

insert into core.order_spend (staging_row_id, product_code, amount) values
    (990001, 'DEMO-AMOLA-820', 340000.00),  -- Herramientas
    (990002, 'DEMO-TALAD-750', 257000.00),
    (990003, 'DEMO-LLAVE-COMB', 92400.00),
    (990004, 'DEMO-SIERRA-500', 95000.00),
    (990005, 'DEMO-LATEX-20',  312000.00),   -- Pinturas y Adhesivos
    (990006, 'DEMO-ESMAL-4',   155600.00),
    (990007, 'DEMO-RODIL-22',   49000.00),
    (990008, 'DEMO-CODO-110',   41200.00),   -- Sanitarios
    (990009, 'DEMO-FLEX-12',    33750.00),
    (990010, 'DEMO-CABLE-25',  446500.00),   -- Electricidad
    (990011, 'DEMO-TERM-25',   112000.00),
    (990012, 'DEMO-TORN-8',     79000.00),   -- Ferretería General
    (990013, 'DEMO-CAND-40',    56000.00),
    (990014, 'DEMO-CASCO',      43000.00),   -- Seguridad Industrial
    (990015, 'DEMO-GUAN-NIT',   47000.00),
    (990016, 'DEMO-DISCO-115',  27000.00),   -- producto sin rubro
    (990017, 'DEMO-VARIOS-1',   18400.00),   -- código que no matchea: sin rubro
    (990018, 'DEMO-VARIOS-2',   12900.00)
on conflict (staging_row_id) do nothing;

commit;
