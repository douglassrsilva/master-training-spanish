# Databricks notebook source
# MAGIC %md
# MAGIC # Ejercicio 3 — Metric Views (métricas gobernadas)
# MAGIC Crea `mvw_churn`, `mvw_ingresos` y `mvw_soporte` en **tu schema personal**, leyendo de la base
# MAGIC compartida `dbacademy.churn`. Luego consulta con `MEASURE()`.

# COMMAND ----------

dbutils.widgets.text("schema", "", "Tu schema")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Crear las metric views

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS IDENTIFIER('dbacademy.' || :schema)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW IDENTIFIER('dbacademy.' || :schema || '.mvw_churn') (
# MAGIC   `Segmento`      COMMENT 'Segmento del cliente',
# MAGIC   `Plan`          COMMENT 'Nombre del plan',
# MAGIC   `Mes`           COMMENT 'Mes de la cancelación',
# MAGIC   `Cancelaciones` COMMENT 'Suscripciones canceladas',
# MAGIC   `Clientes`      COMMENT 'Total de clientes',
# MAGIC   `Tasa de Churn` COMMENT 'Cancelaciones / Clientes'
# MAGIC ) WITH METRICS LANGUAGE YAML
# MAGIC COMMENT 'Métricas de churn/retención' AS $$
# MAGIC version: 0.1
# MAGIC source: dbacademy.churn.hecho_suscripcion
# MAGIC joins:
# MAGIC   - name: cliente
# MAGIC     source: dbacademy.churn.dim_cliente
# MAGIC     'on': source.id_cliente = cliente.id_cliente
# MAGIC   - name: plan
# MAGIC     source: dbacademy.churn.dim_plan
# MAGIC     'on': source.id_plan = plan.id_plan
# MAGIC dimensions:
# MAGIC   - name: Segmento
# MAGIC     expr: cliente.segmento
# MAGIC   - name: Plan
# MAGIC     expr: plan.nombre_plan
# MAGIC   - name: Mes
# MAGIC     expr: date_trunc('MONTH', source.fecha_fin)
# MAGIC measures:
# MAGIC   - name: Cancelaciones
# MAGIC     expr: SUM(source.churn_flag)
# MAGIC   - name: Clientes
# MAGIC     expr: COUNT(DISTINCT source.id_cliente)
# MAGIC   - name: Tasa de Churn
# MAGIC     expr: COUNT(source.churn_flag) / COUNT(DISTINCT source.id_cliente)
# MAGIC $$

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW IDENTIFIER('dbacademy.' || :schema || '.mvw_ingresos') (
# MAGIC   `Segmento`       COMMENT 'Segmento del cliente',
# MAGIC   `Mes`            COMMENT 'Periodo (mes)',
# MAGIC   `Ingresos`       COMMENT 'Suma facturada',
# MAGIC   `Morosidad`      COMMENT 'Porcentaje de facturas no pagadas',
# MAGIC   `Ticket Promedio` COMMENT 'Valor promedio por factura'
# MAGIC ) WITH METRICS LANGUAGE YAML
# MAGIC COMMENT 'Métricas de ingresos' AS $$
# MAGIC version: 0.1
# MAGIC source: dbacademy.churn.hecho_facturacion
# MAGIC joins:
# MAGIC   - name: cliente
# MAGIC     source: dbacademy.churn.dim_cliente
# MAGIC     'on': source.id_cliente = cliente.id_cliente
# MAGIC dimensions:
# MAGIC   - name: Segmento
# MAGIC     expr: cliente.segmento
# MAGIC   - name: Mes
# MAGIC     expr: date_trunc('MONTH', source.periodo)
# MAGIC measures:
# MAGIC   - name: Ingresos
# MAGIC     expr: SUM(source.monto)
# MAGIC   - name: Morosidad
# MAGIC     expr: AVG(CASE WHEN NOT source.pago THEN 1.0 ELSE 0.0 END)
# MAGIC   - name: Ticket Promedio
# MAGIC     expr: AVG(source.monto)
# MAGIC $$

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW IDENTIFIER('dbacademy.' || :schema || '.mvw_soporte') (
# MAGIC   `Segmento`      COMMENT 'Segmento del cliente',
# MAGIC   `Canal`         COMMENT 'Canal del ticket',
# MAGIC   `Categoría`     COMMENT 'Categoría del ticket',
# MAGIC   `Tickets`       COMMENT 'Cantidad de tickets',
# MAGIC   `CSAT Promedio` COMMENT 'CSAT promedio (1-5)',
# MAGIC   `NPS Promedio`  COMMENT 'NPS promedio (0-10)'
# MAGIC ) WITH METRICS LANGUAGE YAML
# MAGIC COMMENT 'Métricas de atención' AS $$
# MAGIC version: 0.1
# MAGIC source: dbacademy.churn.hecho_ticket_soporte
# MAGIC joins:
# MAGIC   - name: cliente
# MAGIC     source: dbacademy.churn.dim_cliente
# MAGIC     'on': source.id_cliente = cliente.id_cliente
# MAGIC dimensions:
# MAGIC   - name: Segmento
# MAGIC     expr: cliente.segmento
# MAGIC   - name: Canal
# MAGIC     expr: source.canal
# MAGIC   - name: Categoría
# MAGIC     expr: source.categoria
# MAGIC measures:
# MAGIC   - name: Tickets
# MAGIC     expr: COUNT(1)
# MAGIC   - name: CSAT Promedio
# MAGIC     expr: AVG(source.csat)
# MAGIC   - name: NPS Promedio
# MAGIC     expr: AVG(source.nps)
# MAGIC $$

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Consultar con MEASURE()

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tasa de churn por segmento
# MAGIC SELECT `Segmento`, ROUND(MEASURE(`Tasa de Churn`), 3) AS tasa_churn
# MAGIC FROM IDENTIFIER('dbacademy.' || :schema || '.mvw_churn')
# MAGIC GROUP BY `Segmento`
# MAGIC ORDER BY tasa_churn DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Ingresos y morosidad por segmento
# MAGIC SELECT `Segmento`,
# MAGIC        ROUND(MEASURE(`Ingresos`), 2)  AS ingresos,
# MAGIC        ROUND(MEASURE(`Morosidad`), 3) AS morosidad
# MAGIC FROM IDENTIFIER('dbacademy.' || :schema || '.mvw_ingresos')
# MAGIC GROUP BY `Segmento`
# MAGIC ORDER BY ingresos DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC -- CSAT y NPS por categoría de ticket
# MAGIC SELECT `Categoría`,
# MAGIC        MEASURE(`Tickets`)                 AS tickets,
# MAGIC        ROUND(MEASURE(`CSAT Promedio`), 2) AS csat,
# MAGIC        ROUND(MEASURE(`NPS Promedio`), 2)  AS nps
# MAGIC FROM IDENTIFIER('dbacademy.' || :schema || '.mvw_soporte')
# MAGIC GROUP BY `Categoría`
# MAGIC ORDER BY tickets DESC

# COMMAND ----------

print(f"✅ Metric views creadas en dbacademy.{dbutils.widgets.get('schema')}")
