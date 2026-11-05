-- Ejercicio 1 — Consultas en el SQL Editor + Genie Code
-- Base compartida (solo lectura): dbacademy.churn
-- Ajusta el catálogo si usaste otro en el Setup.

-- Paso 0 — Crea tu database personal (lo usarás a partir del Ej. 3)
-- Convención: 1ª letra del nombre + primer apellido (ej.: Gabriel García -> ggarcia)
CREATE SCHEMA IF NOT EXISTS dbacademy.<tu_schema>;

-- Paso 2 — Consultas guiadas -------------------------------------------------

-- 2.1 Clientes por segmento
SELECT segmento, COUNT(*) AS clientes
FROM dbacademy.churn.dim_cliente
GROUP BY segmento
ORDER BY clientes DESC;

-- 2.2 Suscripciones activas x canceladas
SELECT status, COUNT(*) AS cant
FROM dbacademy.churn.hecho_suscripcion
GROUP BY status
ORDER BY cant DESC;

-- Paso 3 — Respuestas de referencia de los prompts de Genie Code (Paso 3 del README) -----------
-- Genie genera el SQL a partir del texto; estas son las consultas de REFERENCIA
-- (mismo resultado esperado). Fíjate en los filtros que evitan un resultado erróneo.

-- #1 Tasa de churn por segmento (vía feature_churn)
SELECT segmento, ROUND(AVG(churn_flag), 3) AS tasa_churn
FROM dbacademy.churn.feature_churn
GROUP BY segmento
ORDER BY tasa_churn DESC;

-- #2 Top 5 motivos de cancelación (SOLO las canceladas: sin el filtro, el "motivo"
--    campeón sería la cadena vacía de las 1.460 activas)
SELECT motivo_cancelacion, COUNT(*) AS cant
FROM dbacademy.churn.hecho_suscripcion
WHERE churn_flag = 1
GROUP BY motivo_cancelacion
ORDER BY cant DESC
LIMIT 5;

-- #3 Tasa de churn por plan
SELECT p.nombre_plan, ROUND(AVG(a.churn_flag), 3) AS tasa_churn
FROM dbacademy.churn.hecho_suscripcion a
JOIN dbacademy.churn.dim_plan p ON a.id_plan = p.id_plan
GROUP BY p.nombre_plan
ORDER BY tasa_churn DESC;

-- #4 Cancelaciones por mes (SOLO las canceladas, por fecha_fin; si no, entra un
--    grupo de mes nulo con las 1.460 activas con fecha_fin NULL)
SELECT date_trunc('month', fecha_fin) AS mes, COUNT(*) AS cancelaciones
FROM dbacademy.churn.hecho_suscripcion
WHERE churn_flag = 1
GROUP BY 1
ORDER BY 1;

-- Paso 4 (bonus) — Recursos Delta (solo lectura en la base compartida) ---------
DESCRIBE HISTORY dbacademy.churn.hecho_suscripcion;
DESCRIBE DETAIL  dbacademy.churn.dim_cliente;
-- Time travel: primera versión de la tabla
SELECT COUNT(*) FROM dbacademy.churn.hecho_suscripcion VERSION AS OF 0;

-- 🎯 DESAFÍO — ¿Qué plan tiene la mayor tasa de churn y cuántos clientes perdió?
-- (intenta armarla tú solo antes de mirar; compruébala pidiéndole a Genie Code)
SELECT p.nombre_plan,
       ROUND(AVG(a.churn_flag), 3) AS tasa_churn,
       SUM(a.churn_flag)           AS clientes_perdidos
FROM dbacademy.churn.hecho_suscripcion a
JOIN dbacademy.churn.dim_plan p ON a.id_plan = p.id_plan
GROUP BY p.nombre_plan
ORDER BY tasa_churn DESC;
