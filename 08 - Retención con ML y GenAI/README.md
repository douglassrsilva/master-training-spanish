# 08 - Retención con ML y GenAI

![Ruta del Master Training con énfasis en lo construido hasta el Ejercicio 08](../assets/08%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en la ruta hasta este punto; en gris, lo que todavía viene._

Hasta aquí **detectaste** quién está en riesgo (dashboards + modelo del Ej. 6) y **diagnosticaste** el porqué (IA + agentes). Ahora vamos a **actuar**: vamos a crear las funciones que, a partir de un `id_cliente`, arman la oferta de retención adecuada y generan un e-mail de marketing personalizado. Y vamos a crearlas conversando con el **Genie Code**, sin escribir SQL a mano.

El gran truco de este módulo: las reglas de negocio quedan **gobernadas en Unity Catalog** (reutilizables por la app del Ej. 9, por el Genie y por cualquier agente) y la **IA solo escribe el texto**, sin decidir la oferta.

**Requisitos previos:**
- [Ej. 1 - SQL con IA](<../01 - SQL con IA/README.md>)
- [Ej. 6 - Predicción de Churn (ML)](<../06 - Predicción de Churn (ML)/README.md>)

## Objetivo
Crear dos UC Functions en tu schema `dbacademy.<tu_schema>`, una a la vez, usando el **Genie Code**:
- **`get_cliente_360(id)`**: pasas el id del cliente, recibes su perfil (registro + riesgo) **y las ofertas de retención ya calculadas por las reglas de negocio**
- **`generar_email_retencion(id)`**: pasas el id, recibes el e-mail de retención listo, con la oferta correcta aplicada

---

## Paso 1: Las reglas de retención
Las ofertas salen de tres reglas de negocio. Usan solo datos que ya tenemos, incluido el `factor_principal` que calculó el modelo del Ej. 6:

| Regla | Condición | Oferta |
|-------|-----------|--------|
| **Antigüedad como cliente** | 5 años o más | descuento de **15%** en la factura |
| | menos de 5 años | descuento de **10%** |
| **Plan** | Básico | **10 GB** de internet gratis |
| | por encima del Básico | **el doble** de internet + WhatsApp ilimitado |
| **Motivo del riesgo** | Insatisfacción (CSAT) | gerente de cuenta dedicado |
| | Morosidad | renegociación de la factura sin intereses |
| | Bajo uso | sesión gratuita de capacitación |
| | Detractor (NPS) | llamada con un especialista |

La antigüedad como cliente se mide contra la **fecha de referencia de la base**, `DATE '2026-09-23'` (y no contra la fecha de hoy), para que el resultado sea el mismo para todo el grupo en cualquier día.

## Paso 2: Crear la `get_cliente_360` (del id al perfil + ofertas)
1. En el menú lateral izquierdo, selecciona **SQL Editor**
2. Deberías llegar al editor con una query; si no, crea una con **SQL Query** debajo de **Create new**
3. Abre el Genie Code haciendo clic en el ícono de bombilla en la esquina superior derecha
4. Pega el prompt de abajo, reemplazando `<tu_schema>` por el nombre de tu schema:
```text
Crea una UC Function (función SQL de tabla) llamada get_cliente_360(p_id STRING) en el schema dbacademy.<tu_schema>. Une las tablas dbacademy.churn.dim_cliente y dbacademy.<tu_schema>.churn_scores por id_cliente y devuelve, para el cliente cuyo id_cliente = p_id: nombre_cliente, ciudad, pais, segmento, canal_adquisicion, fecha_registro (de dim_cliente) y nombre_plan, precio_mensual, prob_churn, nivel_riesgo, factor_principal (de churn_scores). Agrega cuatro columnas calculadas en SQL, midiendo la antigüedad como cliente con datediff entre la fecha de referencia DATE '2026-09-23' y fecha_registro: anios_como_cliente (entero); descuento = '15%' si tiene 5 años o más como cliente, si no '10%'; oferta_internet = '10 GB de internet gratis' si nombre_plan = 'Básico', si no 'el doble de tu internet actual + WhatsApp ilimitado'; oferta_factor según factor_principal: 'Insatisfacción (CSAT)' -> 'un gerente de cuenta dedicado', 'Morosidad' -> 'renegociación de tu factura sin intereses', 'Bajo uso' -> 'una sesión gratuita de capacitación', en otro caso -> 'una llamada con un especialista'.
```
5. Revisa el `CREATE FUNCTION` generado y haz clic en **Run**

<details>
<summary>👉 Resultado esperado:</summary>

> Reemplaza `<tu_schema>` por el nombre de tu schema antes de ejecutar

```sql
CREATE OR REPLACE FUNCTION dbacademy.<tu_schema>.get_cliente_360(p_id STRING)
RETURNS TABLE (nombre_cliente STRING, ciudad STRING, pais STRING, segmento STRING,
  canal_adquisicion STRING, fecha_registro DATE, nombre_plan STRING, precio_mensual DOUBLE,
  prob_churn DOUBLE, nivel_riesgo STRING, factor_principal STRING,
  anios_como_cliente INT, descuento STRING, oferta_internet STRING, oferta_factor STRING)
RETURN
  SELECT c.nombre_cliente, c.ciudad, c.pais, c.segmento, c.canal_adquisicion, c.fecha_registro,
         s.nombre_plan, s.precio_mensual, s.prob_churn, s.nivel_riesgo, s.factor_principal,
         CAST(FLOOR(DATEDIFF(DATE '2026-09-23', c.fecha_registro) / 365) AS INT) AS anios_como_cliente,
         CASE WHEN DATEDIFF(DATE '2026-09-23', c.fecha_registro) >= 5 * 365 THEN '15%' ELSE '10%' END AS descuento,
         CASE WHEN s.nombre_plan = 'Básico' THEN '10 GB de internet gratis'
              ELSE 'el doble de tu internet actual + WhatsApp ilimitado' END AS oferta_internet,
         CASE WHEN s.factor_principal = 'Insatisfacción (CSAT)' THEN 'un gerente de cuenta dedicado'
              WHEN s.factor_principal = 'Morosidad' THEN 'renegociación de tu factura sin intereses'
              WHEN s.factor_principal = 'Bajo uso' THEN 'una sesión gratuita de capacitación'
              ELSE 'una llamada con un especialista' END AS oferta_factor
  FROM dbacademy.churn.dim_cliente c
  JOIN dbacademy.<tu_schema>.churn_scores s ON c.id_cliente = s.id_cliente
  WHERE c.id_cliente = p_id;
```

</details>

Prueba la función con dos clientes, uno a cada lado de las reglas:
```sql
SELECT nombre_cliente, nombre_plan, anios_como_cliente, descuento, oferta_internet, oferta_factor
FROM dbacademy.<tu_schema>.get_cliente_360('C01575')
UNION ALL
SELECT nombre_cliente, nombre_plan, anios_como_cliente, descuento, oferta_internet, oferta_factor
FROM dbacademy.<tu_schema>.get_cliente_360('C00018');
```
Resultado esperado:

| nombre | plan | años como cliente | descuento | internet | acción |
|--------|------|:---:|:---:|----------|--------|
| Mariana López | Básico | 5 | **15%** | 10 GB de internet gratis | un gerente de cuenta dedicado |
| Gabriela Rodríguez | Empresarial | 4 | **10%** | el doble de tu internet actual + WhatsApp ilimitado | renegociación de tu factura sin intereses |

> Un único punto de entrada para "todo sobre el cliente": junta el registro (`dim_cliente`) con su score del Ej. 6 (`churn_scores`) y ya trae la oferta decidida por la regla. Es exactamente esta función la que va a llamar la app del Ej. 9.

### ¿Por qué funciones y no SQL suelto en la app?
Una función se convierte en un activo gobernado de Unity Catalog: la app queda liviana (solo llama a la función), el acceso está controlado (EXECUTE) y la misma lógica se reutiliza en otras herramientas. Es la diferencia entre "cada uno lo hace a su manera" y "una regla única, gobernada".

## Paso 3: Crear la `generar_email_retencion` (del perfil al e-mail)
1. De vuelta en el Genie Code, pega el prompt de abajo, reemplazando `<tu_schema>` por el nombre de tu schema:
```text
Crea una UC Function (función SQL de tabla) llamada generar_email_retencion(p_id STRING) en el schema dbacademy.<tu_schema>, usando las tablas dbacademy.churn.dim_cliente y dbacademy.<tu_schema>.churn_scores unidas por id_cliente. Devuelve una columna email con un e-mail de retención personalizado en español para el cliente cuyo id_cliente = p_id. Mide la antigüedad como cliente con datediff entre la fecha de referencia de la base DATE '2026-09-23' y fecha_registro (usa esa fecha fija, no la fecha actual, para que el resultado sea estable). Calcula en SQL con CASE tres ofertas y luego usa ai_query('databricks-meta-llama-3-3-70b-instruct', ...) para redactar el e-mail citando nombre, ciudad y años como cliente, ofreciendo exactamente: (a) descuento de 15% si el cliente tiene 5 años o más como cliente, si no 10%; (b) si nombre_plan = 'Básico' entonces 10 GB de internet gratis, si no el doble de internet + WhatsApp ilimitado; (c) según factor_principal: 'Insatisfacción (CSAT)' -> gerente de cuenta dedicado, 'Morosidad' -> renegociación de la factura sin intereses, 'Bajo uso' -> sesión gratuita de capacitación, en otro caso -> llamada con un especialista.
```
2. Revisa el `CREATE FUNCTION` generado y haz clic en **Run**

<details>
<summary>👉 Resultado esperado:</summary>

> Reemplaza `<tu_schema>` por el nombre de tu schema antes de ejecutar

```sql
CREATE OR REPLACE FUNCTION dbacademy.<tu_schema>.generar_email_retencion(p_id STRING)
RETURNS TABLE (email STRING)
RETURN
    WITH datos AS (
        SELECT
            dc.nombre_cliente,
            dc.ciudad,
            -- fecha de referencia de la base (la base es una fotografía al 23/09/2026); medir la antigüedad
            -- contra ella, y no contra la fecha actual, mantiene el resultado estable en el tiempo.
            FLOOR(DATEDIFF(DATE '2026-09-23', dc.fecha_registro) / 365) AS anios_como_cliente,
            cs.nombre_plan,
            cs.factor_principal,
            CASE WHEN DATEDIFF(DATE '2026-09-23', dc.fecha_registro) >= 5 * 365 THEN '15%' ELSE '10%' END AS descuento,
            CASE WHEN cs.nombre_plan = 'Básico' THEN '10 GB de internet gratis'
                 ELSE 'el doble de tu internet actual + WhatsApp ilimitado' END AS oferta_internet,
            CASE WHEN cs.factor_principal = 'Insatisfacción (CSAT)' THEN 'un gerente de cuenta dedicado'
                 WHEN cs.factor_principal = 'Morosidad' THEN 'renegociación de tu factura sin intereses'
                 WHEN cs.factor_principal = 'Bajo uso' THEN 'una sesión gratuita de capacitación'
                 ELSE 'una llamada con un especialista' END AS oferta_factor
        FROM dbacademy.churn.dim_cliente dc
        JOIN dbacademy.<tu_schema>.churn_scores cs ON dc.id_cliente = cs.id_cliente
        WHERE dc.id_cliente = p_id
    )
    SELECT
        ai_query(
            'databricks-meta-llama-3-3-70b-instruct',
            'Eres un especialista en retención de clientes. Redacta un e-mail profesional y empático en español neutro latinoamericano (usa "tú") para convencer al cliente de seguir con Conecta+. ' ||
            'Datos: Nombre: ' || nombre_cliente || ', Ciudad: ' || ciudad || ', Años como cliente: ' || CAST(anios_como_cliente AS STRING) ||
            '. Ofertas: (a) descuento de ' || descuento || ' en la mensualidad; (b) ' || oferta_internet || '; (c) ' || oferta_factor ||
            '. Menciona el nombre, la ciudad y los años como cliente, incluye las tres ofertas de forma natural y firma como "Equipo de Conecta+".'
        ) AS email
    FROM datos;
```

</details>

El Genie Code calcula las reglas del Paso 2 en SQL (`CASE`) y usa `ai_query` para redactar el e-mail.

> **Fíjate en lo que hace el Genie solo:** consulta las tablas, descubre los valores de `factor_principal` y `nombre_plan`, arma los `CASE` correctos y el `ai_query`. Tú solo describiste las reglas. Si asume un sector específico (ej.: "telecom"), agrega al prompt *"empresa de suscripción genérica, no menciones el sector"*.

> **¿Por qué una fecha fija (`DATE '2026-09-23'`) y no `CURRENT_DATE()`?** La base que estamos usando es una fotografía (datos estáticos). Medir la antigüedad contra la fecha de hoy haría que el resultado cambie solo a medida que pasan los días (un cliente en la víspera de sus 5 años pasaría a 15% al día siguiente). Usando la fecha de referencia de la base, el resultado es el mismo para todo el grupo, en cualquier día.

Prueba con Mariana (5 años · Básico · Insatisfacción):
```sql
SELECT
    email
FROM dbacademy.<tu_schema>.generar_email_retencion('C01575');
```
Resultado esperado:
> *"Hola Mariana López… es un gusto tenerte con nosotros desde hace **5 años**… en **Lima**… un **descuento de 15%** en tu factura… **10 GB de internet gratis**… un **gerente de cuenta dedicado**…"*

## Paso 4: Revisar las reglas
Prueba un cliente del otro lado de las reglas:
```sql
SELECT
    email
FROM dbacademy.<tu_schema>.generar_email_retencion('C00018');
```
Es Gabriela Rodríguez (4 años · Empresarial · Morosidad), y el e-mail cambia solo:

| Cliente | Antigüedad | Plan | Motivo | El e-mail ofrece |
|---------|-----------|------|--------|------------------|
| Mariana (C01575) | 5 años | Básico | Insatisfacción | 15% · 10 GB gratis · gerente dedicado |
| Gabriela (C00018) | 4 años | Empresarial | Morosidad | **10%** · **el doble + WhatsApp** · **renegociación sin intereses** |

Lee los dos e-mails lado a lado: la misma función, ofertas distintas, cada una correcta para el cliente.

> **La lección:** la regla de negocio está **gobernada** (SQL, verificable, igual para todos) y la **IA se encarga solo del lenguaje**. Nunca quedas a merced de que la IA "invente" un descuento, y creaste todo esto solo describiendo lo que querías al Genie Code.

## Explore
Acabas de construir el motor de acción de la retención: dado un cliente en riesgo, salen la oferta correcta y el e-mail listo, con la regla de negocio gobernada y la IA solo en la redacción. En el próximo módulo (Ej. 9 - Creación de Apps), la app **Central de Retención** va a llamar a la `get_cliente_360`: el agente de atención escribe el id, ve el perfil y el riesgo, y hace clic para generar el e-mail. Ahí, quien redacta el texto es un modelo gobernado por Unity Gateway, que vas a crear en tu schema, a partir de las mismas ofertas calculadas aquí.
