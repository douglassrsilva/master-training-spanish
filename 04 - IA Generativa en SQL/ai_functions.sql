-- Ejercicio 4 — AI Functions (GenAI en SQL)
-- Base compartida (solo lectura): dbacademy.churn.hecho_ticket_soporte
-- Ejecuta en el SQL Editor. Las funciones llaman a un modelo de IA — puede tardar unos segundos por fila.

-- Muestra variada (csat alto, medio y bajo) para ver a la IA distinguiendo los casos
-- 1) ai_analyze_sentiment — sentimiento de los reclamos
WITH muestra AS (
  (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT LEFT(texto_reclamo, 60) AS fragmento, csat,
       ai_analyze_sentiment(texto_reclamo) AS sentimiento
FROM muestra ORDER BY csat DESC;

-- 1b) Distribución de sentimiento en los ÚLTIMOS 100 tickets (por fecha_apertura)
-- El ORDER BY fija la muestra: todos los alumnos ejecutan sobre los mismos 100 registros.
-- Para la base completa, quita ORDER BY + LIMIT (ejecuta la IA en toda la tabla — más lento).
SELECT sentimiento, COUNT(*) AS cant
FROM (
  SELECT ai_analyze_sentiment(texto_reclamo) AS sentimiento
  FROM dbacademy.churn.hecho_ticket_soporte
  ORDER BY fecha_apertura DESC
  LIMIT 100
)
GROUP BY sentimiento
ORDER BY cant DESC;

-- 1c) Sentimiento con un MODELO ESPECÍFICO vía ai_query
--     Cambia el endpoint: databricks-meta-llama-3-3-70b-instruct | databricks-gpt-oss-120b | databricks-claude-haiku-4-5
WITH muestra AS (
  (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT csat, LEFT(texto_reclamo, 60) AS fragmento,
       ai_query('databricks-meta-llama-3-3-70b-instruct',
                'Clasifica el sentimiento como positive, neutral o negative. Responde solo con la palabra. Comentario: ' || texto_reclamo) AS sentimiento
FROM muestra ORDER BY csat DESC;

-- 2) ai_classify — clasificar el asunto del ticket
WITH muestra AS (
  (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT LEFT(texto_reclamo, 60) AS fragmento, csat,
       ai_classify(texto_reclamo,
                   ARRAY('Cobranza','Técnico','Cancelación','Elogio','Consulta')) AS categoria_ia
FROM muestra ORDER BY csat DESC;

-- 2b) Clasificación con un MODELO ESPECÍFICO vía ai_query
WITH muestra AS (
  (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
  UNION ALL (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT csat, LEFT(texto_reclamo, 60) AS fragmento,
       ai_query('databricks-gpt-oss-120b',
                'Clasifica el asunto en una de estas categorías: Cobranza, Técnico, Cancelación, Elogio, Consulta. Responde solo con la categoría. Comentario: ' || texto_reclamo) AS categoria
FROM muestra ORDER BY csat DESC;

-- 3) ai_mask — enmascarar datos personales (PII) en el texto
SELECT ai_mask(texto_reclamo, ARRAY('person','phone','email')) AS texto_anonimizado
FROM dbacademy.churn.hecho_ticket_soporte
WHERE texto_reclamo LIKE '%@%' OR texto_reclamo LIKE '%+52%'
LIMIT 5;

-- 4) ai_summarize — resumir los últimos 100 comentarios (por fecha_apertura)
--    En el ejercicio, esta consulta la genera Genie Code (ver README).
SELECT ai_summarize(array_join(collect_list(texto_reclamo), ' | '), 150) AS resumen
FROM (
  SELECT texto_reclamo
  FROM dbacademy.churn.hecho_ticket_soporte
  ORDER BY fecha_apertura DESC
  LIMIT 100
);
