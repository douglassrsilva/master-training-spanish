-- Ejercicio 2 — Generación de Alertas
-- Base compartida (solo lectura): dbacademy.churn

-- Alerta principal — Tasa de churn global (%)
-- Condición de la alerta: tasa_churn_pct > 25   (valor actual: 27,0 -> dispara)
SELECT ROUND(AVG(churn_flag) * 100, 1) AS tasa_churn_pct
FROM dbacademy.churn.hecho_suscripcion;

-- Variación — NPS promedio de los tickets de soporte
-- Condición de la alerta: nps_promedio < 7     (valor actual: 6,53 -> dispara)
SELECT ROUND(AVG(nps), 2) AS nps_promedio
FROM dbacademy.churn.hecho_ticket_soporte;
