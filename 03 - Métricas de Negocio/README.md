# 03 - Métricas de Negocio

![Recorrido del Master Training con énfasis en lo construido hasta el Ejercicio 03](../assets/03%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en el recorrido hasta este punto; en gris, lo que todavía viene._

Ahora vamos a definir las métricas de negocio una sola vez (gobernadas en Unity Catalog) y reutilizarlas en SQL, dashboards y Genie. Este es el primer ejercicio en el que vas a crear objetos en tu propio schema.

> Puedes encontrar el SQL completo de las views en [`metric_views.sql`](./metric_views.sql)

---

## Paso 1: Crear tus metric views
1. Importa el notebook: **Workspace → Tres puntitos arriba → Import → URL**, y pega lo siguiente:
```
https://github.com/douglassrsilva/master-training-spanish/blob/main/03%20-%20M%C3%A9tricas%20de%20Negocio/notebook_metric_views.py
```
2. Después de hacer clic en **Import**, se abrirá el notebook
3. En el selector de la barra superior, junto a Run all, selecciona el cluster `dbacademy_workshop_cluster`
4. Ejecuta la primera celda del notebook para mostrar el widget
5. En el widget **Tu schema**, selecciona el schema que creaste en el Ej. 1
6. Haz clic en **Run all**

El notebook crea tres metric views en tu schema, leyendo del schema compartido `dbacademy.churn`:
- `mvw_churn`: Cancelaciones, Clientes, Tasa de Churn (por Segmento, Plan, Mes)
- `mvw_ingresos`: Ingresos, Morosidad, Ticket Promedio (por Segmento, Mes)
- `mvw_soporte`: Tickets, CSAT Promedio, NPS Promedio (por Segmento, Canal, Categoría)

> Una vez creadas, las metric views quedan disponibles para consultas SQL, dashboards (Ej. 5) y Genie (Ej. 7)

### ¿Qué es una Metric View?
Una view especial (`WITH METRICS`, en YAML) que separa las **dimensiones** (por dónde cortar) de las **medidas** (qué calcular). Las medidas se consultan con la función `MEASURE()`, y la definición queda gobernada y consistente para todos: dashboards y Genie pasan a usar la misma fuente de la verdad.

## Paso 2: ¿Por qué Metric Views? (antes × después)
Ahora que tus metric views existen, vamos a comparar las dos formas de calcular la misma métrica: la morosidad por segmento. Dan el mismo número, pero con esfuerzo y riesgo muy distintos.

Vuelve al **SQL Editor** desde el menú lateral izquierdo para ejecutar las dos consultas siguientes.

**Sin metric view (SQL puro):** tienes que acertar el join, la lógica condicional y la forma del promedio:
```sql
SELECT
    c.segmento,
    ROUND(AVG(CASE WHEN NOT f.pago THEN 1.0 ELSE 0.0 END), 3) AS morosidad
FROM dbacademy.churn.hecho_facturacion f
JOIN dbacademy.churn.dim_cliente c ON f.id_cliente = c.id_cliente
GROUP BY c.segmento
ORDER BY morosidad DESC;
```

**Con la metric view:** la fórmula ya está gobernada, así que solo pides la métrica por su nombre:
```sql
SELECT
    `Segmento`,
    ROUND(MEASURE(`Morosidad`), 3) AS morosidad
FROM dbacademy.<tu_schema>.mvw_ingresos
GROUP BY `Segmento`
ORDER BY morosidad DESC;
```

Ambas devuelven **Corporativo 0,069 · PyME 0,068 · Consumidor 0,068**. La diferencia: en la metric view, la fórmula compleja (join + `CASE` + promedio) se escribió una vez por quien la entiende, y todos la reutilizan sin riesgo de equivocarse. Cuanto más compleja es la métrica, mayor es la ganancia.

## Explora en el catálogo
Navega por tu catálogo para entender cómo se almacenan y dónde quedan disponibles las metric views. También las usaremos en los próximos ejercicios.
