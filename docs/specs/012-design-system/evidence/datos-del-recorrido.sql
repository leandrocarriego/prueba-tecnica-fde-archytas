-- Datos de recorrido de la 012. Todo lleva el prefijo T012 para poder borrarlo.
begin;

insert into core.supplier (id, legal_name, tax_id, email, phone, payment_term_days, balance)
values (9001, 'T012 Metalúrgica del Valle SA', '30712345678', 'ventas@valle.test', '+5492944000111', 30, 1234567.0000),
       (9002, 'T012 Bulonera del Sur SRL', null, null, null, null, 0)
on conflict (id) do nothing;

-- Tres facturas: una vencida sin recibo (roja), una parcial de siete dígitos y
-- una saldada de cuatro. Las dos últimas son la comparación de RF-10.
insert into core.invoice (id, number, issued_on, total, supplier_id, supplier_text, due_on, original_due_on, file_kind, review_state)
values (9001, 'T012-0001', date '2026-07-15', 1234567.0000, 9001, 'T012 Metalúrgica del Valle SA', date '2026-08-20', date '2026-08-20', 'PDF (escaneado)', 'OK'),
       (9002, 'T012-0002', date '2026-08-10', 8900.0000,    9001, 'T012 Metalúrgica del Valle SA', date '2026-09-20', date '2026-09-20', 'PDF', 'OK'),
       (9003, 'T012-0003', date '2026-08-12', 4321.0000,    9001, 'T012 Metalúrgica del Valle SA', date '2026-09-25', date '2026-09-25', 'Excel', 'PENDING')
on conflict (id) do nothing;

update core.invoice set review_reason = 'No se pudo leer el CUIT del archivo' where id = 9003;

-- Un pago del portal (parcial sobre la de ocho mil) y uno cargado a mano.
insert into core.payment (id, supplier_id, invoice_id, amount, paid_on, origin, state, reference)
values (9001, 9001, 9002, 4000.0000, date '2026-08-20', 'PORTAL', 'IMPUTED', 'T012-REC-1'),
       (9002, 9001, 9002, 1000.0000, date '2026-08-25', 'MANUAL', 'IMPUTED', 'T012-REC-2')
on conflict (id) do nothing;

-- El vencimiento de la vencida sin recibo, para que la misma píldora roja
-- aparezca también en el calendario (mes anterior).
insert into core.due_date (id, on_date, description, amount, invoice_id, origin, original_date)
values (9001, date '2026-08-20', 'T012 Factura T012-0001', 1234567.0000, 9001, 'INVOICE', date '2026-08-20')
on conflict (id) do nothing;

-- Dos grafías: una que vio el sistema y una que asignó una persona.
insert into core.supplier_alias (id, supplier_id, text_normalized, text_original, source, created_by_user_id)
values (9001, 9001, 't012 metalurgica del valle', 'T012 METALURGICA DEL VALLE S.A.', 'OBSERVED', null),
       (9002, 9001, 't012 metalurgica valle', 'T012 Metalurgica Valle', 'LEARNED', 2)
on conflict (id) do nothing;

-- Dos ventas apartadas: una rota y una estimada por una persona.
insert into core.sale (id, code, code_key, sold_on, product_code, quantity, total, state, reason, is_estimated)
values (9001, 'T012-V-1', 't012-v-1', date '2026-08-18', 'BULON-8', 12, 45000.0000, 'HELD', 'La cantidad no se pudo interpretar', false),
       (9002, 'T012-V-2', 't012-v-2', date '2026-08-19', 'BULON-9', 3, 7500.0000, 'COUNTED', null, true)
on conflict (id) do nothing;

commit;
begin;

-- El incidente de la factura que venció sin recibo (RF de 005).
insert into core.receipt_incident (id, invoice_id, opened_on)
values (9001, 9001, date '2026-08-21')
on conflict (id) do nothing;

-- Dos productos: uno sin rubro —para la cola de sin clasificar— y uno con
-- rubro y precio, para que la lista de precios muestre algo.
insert into core.product (id, code, description, status, category_id, category_raw, subcategory_raw, source)
values (9001, 'T012-BULON-8', 'T012 Bulón hexagonal 8mm', 'ACTIVE', null, 'FERRETERIA GENERAL', 'BULONERIA', 'PORTAL'),
       (9002, 'T012-CANO-50', 'T012 Caño estructural 50x50', 'ACTIVE', (select id from core.category order by id limit 1), 'ESTRUCTURAS', 'CAÑOS', 'PORTAL')
on conflict (id) do nothing;

insert into core.product_price (product_id, price, currency, effective_at, previous_price, is_highlighted, is_stale, source)
values (9001, 1234.0000,    'ARS', now() - interval '2 days', 1000.0000,    true,  false, 'PORTAL'),
       (9002, 1234567.0000, 'ARS', now() - interval '9 days', 1200000.0000, false, true,  'SYSTEM')
on conflict (product_id) do nothing;

commit;
begin;
-- Tres pendientes de clases distintas: uno que se resuelve con una decisión,
-- uno que sólo se puede dar por revisado y uno de rubro.
insert into operations.exception (id, kind, payload, reason, fingerprint, status, section, occurrences)
values
 (9001, 'unknown_product',
  '{"product_code":"T012-NUEVO-1","description":"T012 Producto que no estaba en el catálogo","price":"9999","origin":"Lista de precios","read_at":"2026-08-30T10:00:00Z"}',
  'El producto no está en el catálogo', 't012-fp-1', 'PENDING', 'PURCHASING', 1),
 (9002, 'unreadable_invoice_row',
  '{"excerpt":"FC A 0001-00099999   ???   $ --","origin":"Facturas de compra","read_at":"2026-08-30T10:05:00Z"}',
  'La fila de facturas no se pudo interpretar', 't012-fp-2', 'PENDING', 'PURCHASING', 3),
 (9003, 'unknown_category',
  '{"category_text":"BULONERIA PESADA","origin":"Lista de precios","read_at":"2026-08-30T10:07:00Z"}',
  'La forma escrita no tiene rubro asignado', 't012-fp-3', 'PENDING', 'SALES', 1)
on conflict (id) do nothing;
commit;
