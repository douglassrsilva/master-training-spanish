# 01 - SQL con IA

![Recorrido del Master Training con énfasis en lo construido hasta el Ejercicio 01](../assets/01%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en el recorrido hasta este punto; en gris, lo que todavía viene._

Tu primer contacto con los datos de churn: vas a explorar en el **SQL Editor** y usar **Genie Code** para generar consultas a partir de lenguaje natural.

## Objetivo
- Navegar por la estructura de datos en Unity Catalog (catálogo → schema → tabla)
- Navegar en el SQL Editor y consultar la base compartida `dbacademy.churn`
- Usar Genie Code para escribir SQL a partir de preguntas en lenguaje natural
- Conocer recursos del formato Delta (historial, time travel)

> Puedes encontrar todas las consultas usadas aquí en [`consultas.sql`](./consultas.sql)

---

## Paso 0: Conocer la base en Unity Catalog
Antes de consultar, veamos cómo están organizados los datos. En Unity Catalog, todo dato tiene una dirección en tres partes: **catálogo → schema → tabla**.

### 0.1 Navegar en el Catalog Explorer
1. En el menú lateral izquierdo, haz clic en **Catalog**
2. Abre el catálogo **`dbacademy`** y luego el schema **`churn`**. Es la base compartida del curso, con las tablas de clientes, planes, suscripciones, uso, facturación y tickets de soporte
3. Haz clic en la tabla **`hecho_suscripcion`** y explora las pestañas:
    - **Overview:** las columnas y el comentario de cada una (ej.: `churn_flag` = "1 si canceló (churn), 0 si está activo")
    - **Sample Data:** algunas filas de ejemplo, sin escribir SQL
    - **Details:** dueño, formato (Delta) y fecha de creación
4. Todavía en la lista de columnas, fíjate que `id_cliente` está marcada como **clave foránea (FK)**: apunta a la tabla `dim_cliente`. Haz clic en **View relationships** para ver cómo se conectan las tablas

> Estos comentarios y relaciones no son solo documentación: son los que ayudan a **Genie Code** (en este ejercicio) y a los **Genies** (Ej. 7) a escribir el SQL correcto.

### 0.2 Abrir el SQL Editor
En el menú lateral izquierdo, selecciona **SQL Editor**. Debajo de **Create new**, haz clic en **SQL Query**.
En el selector de contexto junto a **Run all**, elige el catálogo `dbacademy` y el schema `churn`, como se muestra a continuación:
![Imagen del catálogo+schema en el SQL Editor](../assets/01%20-%20catálogo+schema%20en%20SQL%20Editor.png)

## Paso 1: Crea tu database personal
Ahora debes crear tu propio _schema_, donde quedarán todas las bases que generes a partir del Ej. 3.
Para el nombre del schema, sigue el patrón "1ª letra del nombre + primer apellido" (ej.: Gabriel García → ggarcia).
```sql
CREATE SCHEMA IF NOT EXISTS dbacademy.<tu_schema>;
```


## Paso 2: Consultas guiadas
Para cada una de las siguientes consultas:
1. Copia la consulta haciendo clic en el ícono de dos cuadrados en la esquina de cada bloque
2. Pégala en el SQL Editor
3. Ejecútala
4. Observa los resultados

**2.1 Clientes por segmento**
```sql
SELECT
    segmento,
    COUNT(*) AS clientes
FROM dbacademy.churn.dim_cliente
GROUP BY segmento
ORDER BY clientes DESC;
```

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

| Segmento | Clientes |
|----------|:---:|
| Consumidor | 1.200 |
| PyME | 595 |
| Corporativo | 205 |

</details>

**2.2 Suscripciones activas x canceladas**
```sql
SELECT
    status,
    COUNT(*) AS cant
FROM dbacademy.churn.hecho_suscripcion
GROUP BY status
ORDER BY cant DESC;
```

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

| Status | Cant. |
|--------|:---:|
| Activa | 1.460 |
| Cancelada | 540 |

</details>

## Paso 3: Usando Genie Code
**Genie Code** es el asistente de desarrollo de Databricks; podemos usarlo en el SQL Editor para escribir consultas SQL a partir de lenguaje natural. Es distinto de los _Genies_ que veremos en el Ej. 7, cuyo objetivo es _responder preguntas y generar insights_. Aquí el foco es armar la consulta.

Abre Genie Code haciendo clic en el ícono de la bombilla en la esquina superior derecha, pega un prompt a la vez, revisa el SQL generado y ejecútalo:

**1. Tasa de churn por segmento**
```text
Escribe el SQL de la tasa de churn por segmento usando la tabla dbacademy.churn.feature_churn.
```

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

```sql
SELECT
    segmento,
    ROUND(AVG(churn_flag), 3) AS tasa_churn
FROM dbacademy.churn.feature_churn
GROUP BY segmento
ORDER BY tasa_churn DESC;
```

| Segmento | Tasa de churn |
|----------|:---:|
| Consumidor | 0,303 |
| PyME | 0,239 |
| Corporativo | 0,166 |

</details>

**2. Top 5 motivos de cancelación**
```text
Escribe una consulta con los 5 principales motivos de cancelación de las suscripciones canceladas (churn_flag = 1) usando la tabla dbacademy.churn.hecho_suscripcion.
```

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

```sql
SELECT
    motivo_cancelacion,
    COUNT(*) AS cant
FROM dbacademy.churn.hecho_suscripcion
WHERE churn_flag = 1
GROUP BY motivo_cancelacion
ORDER BY cant DESC
LIMIT 5;
```

| Motivo | Cant. |
|--------|:---:|
| Insatisfacción | 196 |
| Precio | 148 |
| Competencia | 104 |
| Atención | 80 |
| Cambio de necesidad | 12 |

</details>

**3. Tasa de churn por plan**
```text
Escribe la tasa de churn por plan usando dbacademy.churn.hecho_suscripcion y dbacademy.churn.dim_plan.
```

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

```sql
SELECT
    p.nombre_plan,
    ROUND(AVG(a.churn_flag), 3) AS tasa_churn
FROM dbacademy.churn.hecho_suscripcion a
JOIN dbacademy.churn.dim_plan p ON a.id_plan = p.id_plan
GROUP BY p.nombre_plan
ORDER BY tasa_churn DESC;
```

| Plan | Tasa de churn |
|-------|:---:|
| Básico | 0,317 |
| Estándar | 0,274 |
| Premium | 0,225 |
| Empresarial | 0,157 |

</details>

**4. Cancelaciones por mes**
```text
Cuenta cuántas suscripciones se cancelaron por mes usando dbacademy.churn.hecho_suscripcion, considerando solo las canceladas (churn_flag = 1) según la fecha de cancelación (fecha_fin).
```

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

```sql
SELECT
    date_trunc('month', fecha_fin) AS mes,
    COUNT(*) AS cancelaciones
FROM dbacademy.churn.hecho_suscripcion
WHERE churn_flag = 1
GROUP BY 1
ORDER BY 1;
```

</details>

## 🎯 Desafío
¿Qué plan tiene la mayor tasa de churn y cuántos clientes perdió?

<details markdown="1">
<summary>👉 Resultado esperado:</summary>

| Plan | Tasa de churn | Clientes perdidos |
|-------|:---:|:---:|
| **Básico** | **0,317** | **257** |
| Estándar | 0,274 | 160 |
| Premium | 0,225 | 92 |
| Empresarial | 0,157 | 31 |

➡️ El plan **Básico** concentra la mayor tasa de churn, coherente con el negocio (menor barrera de salida, menor valor percibido).

</details>
