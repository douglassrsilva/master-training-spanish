-- Ejercicio 3 — Metric Views
-- Fuente (solo lectura): dbacademy.churn
-- Las views se crean en TU schema personal: reemplaza <tu_schema> por tu database.

-- =====================================================================
-- 1) mvw_churn — métricas de churn/retención
-- =====================================================================
CREATE OR REPLACE VIEW dbacademy.<tu_schema>.mvw_churn (
  `Segmento`      COMMENT 'Segmento del cliente',
  `Plan`          COMMENT 'Nombre del plan',
  `Mes`           COMMENT 'Mes de la cancelación',
  `Cancelaciones` COMMENT 'Suscripciones canceladas',
  `Clientes`      COMMENT 'Total de clientes',
  `Tasa de Churn` COMMENT 'Cancelaciones / Clientes'
) WITH METRICS LANGUAGE YAML
COMMENT 'Métricas de churn/retención' AS $$
version: 0.1
source: dbacademy.churn.hecho_suscripcion
joins:
  - name: cliente
    source: dbacademy.churn.dim_cliente
    'on': source.id_cliente = cliente.id_cliente
  - name: plan
    source: dbacademy.churn.dim_plan
    'on': source.id_plan = plan.id_plan
dimensions:
  - name: Segmento
    expr: cliente.segmento
  - name: Plan
    expr: plan.nombre_plan
  - name: Mes
    expr: date_trunc('MONTH', source.fecha_fin)
measures:
  - name: Cancelaciones
    expr: SUM(source.churn_flag)
  - name: Clientes
    expr: COUNT(DISTINCT source.id_cliente)
  - name: Tasa de Churn
    expr: SUM(source.churn_flag) / COUNT(DISTINCT source.id_cliente)
$$;

-- =====================================================================
-- 2) mvw_ingresos — métricas de ingresos y morosidad
-- =====================================================================
CREATE OR REPLACE VIEW dbacademy.<tu_schema>.mvw_ingresos (
  `Segmento`       COMMENT 'Segmento del cliente',
  `Mes`            COMMENT 'Periodo (mes)',
  `Ingresos`       COMMENT 'Suma facturada',
  `Morosidad`      COMMENT 'Porcentaje de facturas no pagadas',
  `Ticket Promedio` COMMENT 'Valor promedio por factura'
) WITH METRICS LANGUAGE YAML
COMMENT 'Métricas de ingresos' AS $$
version: 0.1
source: dbacademy.churn.hecho_facturacion
joins:
  - name: cliente
    source: dbacademy.churn.dim_cliente
    'on': source.id_cliente = cliente.id_cliente
dimensions:
  - name: Segmento
    expr: cliente.segmento
  - name: Mes
    expr: date_trunc('MONTH', source.periodo)
measures:
  - name: Ingresos
    expr: SUM(source.monto)
  - name: Morosidad
    expr: AVG(CASE WHEN NOT source.pago THEN 1.0 ELSE 0.0 END)
  - name: Ticket Promedio
    expr: AVG(source.monto)
$$;

-- =====================================================================
-- 3) mvw_soporte — métricas de atención
-- =====================================================================
CREATE OR REPLACE VIEW dbacademy.<tu_schema>.mvw_soporte (
  `Segmento`      COMMENT 'Segmento del cliente',
  `Canal`         COMMENT 'Canal del ticket',
  `Categoría`     COMMENT 'Categoría del ticket',
  `Tickets`       COMMENT 'Cantidad de tickets',
  `CSAT Promedio` COMMENT 'CSAT promedio (1-5)',
  `NPS Promedio`  COMMENT 'NPS promedio (0-10)'
) WITH METRICS LANGUAGE YAML
COMMENT 'Métricas de atención' AS $$
version: 0.1
source: dbacademy.churn.hecho_ticket_soporte
joins:
  - name: cliente
    source: dbacademy.churn.dim_cliente
    'on': source.id_cliente = cliente.id_cliente
dimensions:
  - name: Segmento
    expr: cliente.segmento
  - name: Canal
    expr: source.canal
  - name: Categoría
    expr: source.categoria
measures:
  - name: Tickets
    expr: COUNT(1)
  - name: CSAT Promedio
    expr: AVG(source.csat)
  - name: NPS Promedio
    expr: AVG(source.nps)
$$;

-- =====================================================================
-- Consultando con MEASURE()
-- =====================================================================
-- Tasa de churn por segmento
SELECT `Segmento`, ROUND(MEASURE(`Tasa de Churn`), 3) AS tasa_churn
FROM dbacademy.<tu_schema>.mvw_churn
GROUP BY `Segmento`
ORDER BY tasa_churn DESC;

-- Ingresos y morosidad por segmento
SELECT `Segmento`,
       ROUND(MEASURE(`Ingresos`), 2)  AS ingresos,
       ROUND(MEASURE(`Morosidad`), 3) AS morosidad
FROM dbacademy.<tu_schema>.mvw_ingresos
GROUP BY `Segmento`
ORDER BY ingresos DESC;

-- CSAT y NPS por categoría de ticket
SELECT `Categoría`,
       MEASURE(`Tickets`)                  AS tickets,
       ROUND(MEASURE(`CSAT Promedio`), 2)  AS csat,
       ROUND(MEASURE(`NPS Promedio`), 2)   AS nps
FROM dbacademy.<tu_schema>.mvw_soporte
GROUP BY `Categoría`
ORDER BY tickets DESC;
