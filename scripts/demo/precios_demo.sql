-- Datos de demostración para la pantalla de precios (feature 013).
--
-- Productos reales de ferretería con precio, precio anterior y rubro, para que
-- la lista de precios en local se vea como el diseño acordado (guía visual
-- `3k`) en vez de con los `Producto de prueba N` sin precio que trae la base.
--
-- **Es dato de demo, no del portal.** No pasó por el pipeline `raw → staging →
-- core`: se inserta directo, igual que el bloque `T012` del recorrido de la
-- 012. Todo lleva el prefijo `DEMO-` en el código para poder borrarlo de una:
--
--   DELETE FROM core.product WHERE code LIKE 'DEMO-%';   -- el precio cae solo (FK on delete cascade)
--
-- Cargar:
--   docker exec -i cordillera_postgres psql -U cordillera -d cordillera < scripts/demo/precios_demo.sql
--
-- Los `category_id` son los rubros que ya están en la base:
--   1 Electricidad · 2 Ferretería General · 3 Herramientas · 5 Pinturas y Adhesivos
--   6 Sanitarios · 7 Seguridad Industrial · (sin rubro = NULL)

begin;

-- El producto. `status`, `source`, `first_seen_at` y `last_seen_at` toman su
-- valor por defecto; sólo va lo que distingue a cada fila.
insert into core.product (id, code, description, category_id) values
    (9101, 'DEMO-AMOLA-820', 'Amoladora angular 4½" 820 W',          3),
    (9102, 'DEMO-TALAD-750', 'Taladro percutor 13 mm 750 W',          3),
    (9103, 'DEMO-LLAVE-COMB','Juego de llaves combinadas 8–19 mm',    3),
    (9104, 'DEMO-LATEX-20',  'Látex interior mate 20 L',              5),
    (9105, 'DEMO-ESMAL-4',   'Esmalte sintético brillante 4 L',       5),
    (9106, 'DEMO-RODIL-22',  'Rodillo antigota 22 cm',                5),
    (9107, 'DEMO-CODO-110',  'Codo PVC 110 mm',                       6),
    (9108, 'DEMO-FLEX-12',   'Flexible acero inoxidable ½" 40 cm',    6),
    (9109, 'DEMO-CABLE-25',  'Cable unipolar 2,5 mm² x 100 m',        1),
    (9110, 'DEMO-TERM-25',   'Térmica bipolar 25 A curva C',          1),
    (9111, 'DEMO-TORN-8',    'Tornillo autoperforante 8x1½" (x100)',  2),
    (9112, 'DEMO-CAND-40',   'Candado de bronce 40 mm',               2),
    (9113, 'DEMO-CASCO',     'Casco de obra con arnés',               7),
    (9114, 'DEMO-GUAN-NIT',  'Guantes de nitrilo (par)',              7),
    (9115, 'DEMO-SIERRA-500','Sierra caladora 500 W',                 3),
    (9116, 'DEMO-DISCO-115', 'Disco diamantado 115 mm',            null)
on conflict (id) do nothing;

-- El precio en vigencia contra el anterior. `is_highlighted` va en true cuando la
-- suba supera el 10 % (el umbral por defecto); `is_stale` marca los que dejaron
-- de figurar y conservan su último precio. `previous_price` nulo es «nuevo».
insert into core.product_price
    (product_id, price, effective_at, previous_price, is_highlighted, is_stale) values
    (9101,   84900.00, now(),   75800.00, true,  false),  -- +12,0 %
    (9102,  128500.00, now(),  119900.00, false, false),  -- +7,2 %
    (9103,   46200.00, now(),   46200.00, false, false),  -- =
    (9104,   62400.00, now(),   62400.00, false, false),  -- =
    (9105,   38900.00, now(),   41500.00, false, false),  -- −6,3 %
    (9106,    9800.00, now(),       null, false, false),  -- nuevo
    (9107,    4120.00, now(),    4310.00, false, false),  -- −4,4 %
    (9108,    6750.00, now(),    6200.00, false, false),  -- +8,9 %
    (9109,   89300.00, now(),   78000.00, true,  false),  -- +14,5 %
    (9110,   22400.00, now(),   22400.00, false, false),  -- =
    (9111,    7900.00, now(),    7100.00, true,  false),  -- +11,3 %
    (9112,   11200.00, now(),   12000.00, false, false),  -- −6,7 %
    (9113,    8600.00, now(),       null, false, false),  -- nuevo
    (9114,    2350.00, now(),    2500.00, false, false),  -- −6,0 %
    (9115,   95000.00, now(),   95000.00, false, true),   -- dejó de figurar
    (9116,    5400.00, now(),    4900.00, true,  false)   -- +10,2 %, sin rubro
on conflict (product_id) do nothing;

commit;
