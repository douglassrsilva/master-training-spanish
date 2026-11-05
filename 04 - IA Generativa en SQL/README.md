# 04 - IA Generativa en SQL

![Recorrido del Master Training con énfasis en lo construido hasta el Ejercicio 04](../assets/04%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en el recorrido hasta este punto; en gris, lo que todavía viene._

Vamos a aplicar **IA Generativa directo en SQL** sobre el texto de los tickets de soporte (la "voz del cliente"), sin entrenar modelos y sin salir del SQL Editor.

> Puedes encontrar todas las consultas usadas aquí en [`ai_functions.sql`](./ai_functions.sql)

## Objetivo
Usar las **AI Functions** de Databricks para analizar el campo `texto_reclamo` de la tabla `hecho_ticket_soporte`:
- `ai_analyze_sentiment`: sentimiento (positive / neutral / negative)
- `ai_classify`: clasificar el asunto del ticket
- `ai_mask`: enmascarar datos personales (PII)
- `ai_summarize`: resumir los principales problemas

> Las funciones llaman a un modelo de IA, así que pueden tardar unos segundos por fila. Por eso las consultas usan `LIMIT`

---

## Paso 0: Abrir el SQL Editor
1. En el menú lateral izquierdo, selecciona **SQL Editor**
2. Deberías quedar redirigido al editor con una consulta; si no, crea una con **SQL Query** debajo de **Create New**

Para cada consulta de este ejercicio, copia la consulta haciendo clic en el ícono de dos cuadrados en la esquina del bloque, pégala en el SQL Editor y ejecútala.

## Paso 1: Análisis de sentimiento

### 1a. Sentimiento con `ai_analyze_sentiment`
```sql
WITH muestra AS (
    ( SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    ( SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    ( SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT
    LEFT(texto_reclamo, 60) AS fragmento,
    csat,
    ai_analyze_sentiment(texto_reclamo) AS sentimiento
FROM muestra
ORDER BY csat DESC;
```
Resultado:
- `csat 5 → positive`
- `csat 3 → neutral`
- `csat 1 → negative`

El sentimiento acompaña la calificación.

> **Consejo:** usamos una muestra variada (csat 5, 3 y 1) a propósito, para ver a la IA distinguiendo los casos. Si ordenas solo por los peores tickets, todo vuelve negativo. El `ORDER BY id_ticket` garantiza que todo el grupo vea los **mismos** tickets: sin él, el `LIMIT 2` toma filas cualesquiera, y algunos tickets de csat 3 tienen texto positivo ("Estoy satisfecho...").

### 1b. Distribución de sentimiento con Genie Code (últimos 100)
Ahora vamos a pedirle el SQL a Genie Code en lugar de escribirlo:
1. Abre Genie Code haciendo clic en el ícono de la bombilla en la esquina superior derecha
2. Pega el prompt de abajo
3. Revisa el SQL generado y ejecútalo
```text
Usando la tabla dbacademy.churn.hecho_ticket_soporte, escribe una consulta que aplique ai_analyze_sentiment a la columna texto_reclamo de los últimos 100 tickets (por fecha_apertura) y cuente cuántos son positivos, neutros y negativos.
```

<details>
<summary>👉 Resultado esperado:</summary>

```sql
SELECT
    sentimiento,
    COUNT(*) AS cant
FROM (
    SELECT
        ai_analyze_sentiment(texto_reclamo) AS sentimiento
    FROM dbacademy.churn.hecho_ticket_soporte
    ORDER BY fecha_apertura DESC
    LIMIT 100
)
GROUP BY sentimiento
ORDER BY cant DESC;
```

</details>

Resultado esperado (últimos 100), que puede variar 1–2 porque se trata de IA:
- **~32** positive
- **~36** neutral
- **~32** negative

> El texto libre se convirtió en un indicador contable, y generaste la consulta solo describiendo lo que querías

### 1c. Sentimiento con un modelo específico: `ai_query`
1. Copia la consulta de abajo
2. Cambia el 1º argumento de `ai_query` por uno de estos modelos:
    - `databricks-claude-haiku-4-5` (Claude)
    - `databricks-meta-llama-3-3-70b-instruct` (Llama)
    - `databricks-gpt-oss-120b` (OpenAI)
3. Ejecuta la consulta
```sql
WITH muestra AS (
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT
    csat,
    LEFT(texto_reclamo, 60) AS fragmento,
    ai_query(
        'databricks-meta-llama-3-3-70b-instruct',
        'Clasifica el sentimiento como positive, neutral o negative. Responde solo con la palabra. Comentario: ' || texto_reclamo
    ) AS sentimiento
FROM muestra
ORDER BY csat DESC;
```
Resultado (Claude):
- `csat 5 → Positive`
- `csat 3 → Neutral`
- `csat 1 → Negative`

Las funciones de los pasos anteriores usan el modelo predeterminado de Databricks. Con `ai_query` eliges qué modelo usar.

## Paso 2: Clasificación

### 2a. Clasificación con `ai_classify`
```sql
WITH muestra AS (
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT
    LEFT(texto_reclamo, 60) AS fragmento,
    csat,
    ai_classify(texto_reclamo, ARRAY('Cobranza','Técnico','Cancelación','Elogio','Consulta')) AS categoria_ia
FROM muestra
ORDER BY csat DESC;
```
La IA lee el texto libre y elige una de las categorías que definiste (ej.: un elogio → `Elogio`, "ya pedí la cancelación…" → `Cancelación`).

### 2b. Clasificación con un modelo específico: `ai_query`
La misma idea del 1c, ahora clasificando el asunto:
1. Copia la consulta de abajo
2. Cambia el 1º argumento de `ai_query` por uno de los modelos del 1c
3. Ejecuta la consulta
```sql
WITH muestra AS (
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 5 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 3 ORDER BY id_ticket LIMIT 2)
    UNION ALL
    (SELECT texto_reclamo, csat FROM dbacademy.churn.hecho_ticket_soporte WHERE csat = 1 ORDER BY id_ticket LIMIT 2)
)
SELECT
    csat,
    LEFT(texto_reclamo, 60) AS fragmento,
    ai_query(
        'databricks-gpt-oss-120b',
        'Clasifica el asunto en una de estas categorías: Cobranza, Técnico, Cancelación, Elogio, Consulta. Responde solo con la categoría. Comentario: ' || texto_reclamo
    ) AS categoria
FROM muestra
ORDER BY csat DESC;
```
Resultado (GPT-OSS):
- `csat 5 → Elogio`
- `csat 3 → Consulta`
- `csat 1 → Cancelación`

> Uno de los tickets de csat 1 dice *"Ya pedí la cancelación y me siguen cobrando"*. Habla de cancelación **y** de cobranza, así que el modelo puede clasificarlo como **Cobranza**. Ambas respuestas son defendibles: por eso vale la pena elegir bien las categorías (y el modelo) para tu caso.

## Paso 3: Enmascaramiento de PII con `ai_mask`
```sql
SELECT
    ai_mask(texto_reclamo, ARRAY('person','phone','email')) AS texto_anonimizado
FROM dbacademy.churn.hecho_ticket_soporte
WHERE texto_reclamo LIKE '%@%' OR texto_reclamo LIKE '%+52%'
LIMIT 5;
```
Ej.: *"Mi email es c00015@ejemplo.com y todavía no recibo respuesta."* → *"Mi email es **[MASKED]** y todavía no recibo respuesta."*

Ideal para compartir datos de soporte sin exponer información personal: un puente hacia la gobernanza de Unity Catalog.

## Paso 4: Resumen de comentarios con Genie Code y `ai_summarize`
Nuevamente, vamos a pedirle el SQL a Genie Code:
1. Abre Genie Code haciendo clic en el ícono de la bombilla en la esquina superior derecha
2. Pega el prompt de abajo
3. Revisa el SQL generado y ejecútalo
```text
Usando la tabla dbacademy.churn.hecho_ticket_soporte, genera una consulta que tome los últimos 100 comentarios y use ai_summarize para resumir lo que dicen los clientes.
```

<details>
<summary>👉 Resultado esperado:</summary>

```sql
SELECT
    ai_summarize(array_join(collect_list(texto_reclamo), ' | '), 150) AS resumen
FROM (
    SELECT
        texto_reclamo
    FROM dbacademy.churn.hecho_ticket_soporte
    ORDER BY fecha_apertura DESC
    LIMIT 100
);
```

</details>

Devuelve algo como:
> *"Los últimos 100 tickets revelan que los clientes reportan sobre todo problemas de atención, cobros indebidos e inestabilidad del servicio, aunque también hay registros de elogios al soporte y a la calidad de la atención."*

En lugar de leer 100 tickets, tienes el panorama en un párrafo, y generaste la consulta solo describiendo lo que querías.

---

## 🎯 Desafío
Estás recibiendo muchos comentarios negativos y eso está afectando la relación con tus clientes. Muestra cómo puedes seleccionar 50 comentarios negativos y generar respuestas para ellos.

**Consejo:** Genie Code + AI Functions 😉

## Explora
Las AI Functions transforman texto libre en datos estructurados: el sentimiento y la categoría se convierten en columnas que puedes agregar, filtrar y cruzar con el churn. Esa "señal" de la voz del cliente se usará más adelante en el modelo (Ej. 6) y en los agentes.
