# 02 - Generación de Alertas

![Recorrido del Master Training con énfasis en lo construido hasta el Ejercicio 02](../assets/02%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en el recorrido hasta este punto; en gris, lo que todavía viene._

Ahora vamos a configurar una alerta que te avise sola cuando un indicador de churn cruce un límite, sin necesidad de abrir reportes todos los días.

## Objetivo
Crear una **Alerta** en Databricks: una consulta que se ejecuta con una programación y notifica cuando se cumple una condición.

> Puedes encontrar todas las consultas usadas aquí en [`alertas.sql`](./alertas.sql)

---

## Paso 1: Crear la alerta
1. En el menú lateral izquierdo, ve a **Alerts**
2. Haz clic en **Create alert**
3. Pega la siguiente consulta en el espacio en blanco:
```sql
SELECT
    ROUND(AVG(churn_flag) * 100, 1) AS tasa_churn_pct
FROM dbacademy.churn.hecho_suscripcion;
```
4. Ejecuta la consulta (Run all). El resultado debe ser `tasa_churn_pct = 27.0`

La alerta observa el resultado de una consulta. La consulta que pegamos sirve para monitorear la tasa de churn global (%).

## Paso 2: Configurar la alerta
1. Configura la **condición de disparo**:
    - Columna: `tasa_churn_pct`
    - Operador: **mayor que (>)**
    - Valor (threshold): **25**
2. Cambia el nombre de la alerta haciendo clic en "New Alert \[...\]" en la pestaña superior, por `Alerta_Churn_<tu_nombre>`
3. En **Notifications**, indica el correo electrónico donde quieres recibir la alerta
4. Haz clic en el ícono de calendario y define la programación (ej.: todos los días)
5. Haz clic en **Run Alert**

> Como la tasa actual es **27,0** y el límite es **25**, la alerta entra en estado disparado (triggered)

## Paso 3 (variación): Alerta de NPS bajo
Repite los pasos 1 y 2 con esta consulta y la condición `nps_promedio < 7`:
```sql
SELECT
    ROUND(AVG(nps), 2) AS nps_promedio
FROM dbacademy.churn.hecho_ticket_soporte;
```
Valor actual: **6,53** → también dispara.

> **Nota:** aquí los datos son fijos, así que el valor no cambia, lo que es ideal para ver la alerta dispararse de forma predecible. En producción, la misma configuración se convierte en monitoreo continuo: la programación vuelve a evaluar la consulta y avisa cuando el indicador cruza el límite.

---

## Resultado esperado
| Alerta | La consulta devuelve | Condición | Estado |
|--------|:---:|:---:|:---:|
| Tasa de churn | **27,0** | > 25 | 🔴 Disparado |
| NPS promedio | **6,53** | < 7 | 🔴 Disparado |
