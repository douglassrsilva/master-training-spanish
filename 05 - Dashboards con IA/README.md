# 05 - Dashboards con IA

![Recorrido del Master Training con énfasis en lo construido hasta el Ejercicio 05](../assets/05%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en el recorrido hasta este punto; en gris, lo que todavía viene._

Vamos a transformar los datos de churn en un **panel ejecutivo**: dejas que **Genie** arme los gráficos a partir de prompts y reutilizas la metric view que creaste en el Ej. 3. Tú describes los análisis, él los arma; tú solo ajustas y publicas.

**Requisitos previos:**
- [Ej. 1 - SQL con IA](<../01 - SQL con IA/README.md>)
- [Ej. 3 - Métricas de Negocio](<../03 - Métricas de Negocio/README.md>)

## Objetivo
Construir un **dashboard AI/BI** de retención con:
- Un KPI de tasa de churn
- Churn por plan y por segmento
- Cancelaciones a lo largo del tiempo
- Un mapa de churn por región
- 2 filtros (plan y segmento) que vuelven interactivo el panel
- El logo del curso en la parte superior

> Los primeros 4 análisis salen directo de tu `mvw_churn`: la misma medida gobernada que definiste en el Ej. 3, ahora convertida en gráfico

---

## Paso 1: Crear el dashboard
1. En el menú lateral izquierdo, haz clic en **Dashboards**
2. Haz clic en **Create Dashboard**

## Paso 2: Generar los análisis con Genie (sobre tu metric view)
Justo después de crear el dashboard, pega este prompt en el espacio de texto debajo de **Create a dashboard with Genie**, reemplazando `<tu_schema>` por el nombre de tu schema:
```text
Usando la metric view mvw_churn de dbacademy.<tu_schema>, crea análisis de churn: un indicador (KPI) con la Tasa de Churn general; un gráfico de barras con la Tasa de Churn por Plan, de mayor a menor; un gráfico de barras con la Tasa de Churn por Segmento; y un gráfico de línea con las Cancelaciones por Mes.
```

Resultado esperado: 4 gráficos en el dashboard:
- Un KPI con la Tasa de Churn general
- Barras con la Tasa de Churn por Plan
- Barras con la Tasa de Churn por Segmento
- Una línea con las Cancelaciones por Mes: serie mensual (2023–2025) con ~12 a 21 cancelaciones/mes

> Fíjate: armaste 4 gráficos sin escribir una sola línea de SQL, usando la medida gobernada que ya habías creado en el Ej. 3. Es la fuente única de la verdad convertida en panel.

### Paso 2.1: 🕵️ ¿Notaste el error? Corrígelo y mira cómo se propaga
Revisa tu dashboard: el KPI de churn marca **100%**, pero a lo largo de la guía el churn aparece como **~27%**. El número no cuadra, y descubrir por qué es el desafío. 😉

1. En el menú lateral izquierdo, ve a **Catalog → `dbacademy` → `<tu_schema>` → Tables → `mvw_churn`**
2. Justo arriba, haz clic en el botón **Edit**
3. Selecciona la measure llamada **`Tasa de Churn`**
4. Corrige la **Expresión** cambiando `COUNT` por `SUM` en el numerador, de:
    ```
    COUNT(source.churn_flag) / COUNT(DISTINCT source.id_cliente)
    ```
    a:
    ```
    SUM(source.churn_flag) / COUNT(DISTINCT source.id_cliente)
    ```
5. Haz clic en **Save**
6. Vuelve al dashboard y haz clic en el botón de **refresh**

El KPI y los gráficos de churn bajan de 100% a la tasa real:

| | KPI | Básico | Estándar | Premium | Empresarial |
|---|---|---|---|---|---|
| **Antes (COUNT, incorrecto)** | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 |
| **Después (SUM, correcto)** | 0,27 | 0,317 | 0,274 | 0,225 | 0,157 |

La causa estaba en la medida `Tasa de Churn`: `COUNT(churn_flag)` cuenta **todas** las filas (todo cliente tiene la flag, 0 o 1), mientras que `SUM(churn_flag)` suma solo las **cancelaciones** (flag = 1). Solo el `SUM` da la tasa de churn real.

Resultados esperados después de la corrección:

**KPI Tasa de Churn:** ≈ **27%** (540 cancelaciones en 2.000 clientes)

**Por plan:**
- Básico **31,7%**
- Estándar **27,4%**
- Premium **22,5%**
- Empresarial **15,7%**

**Por segmento:**
- Consumidor **30,3%**
- PyME **23,9%**
- Corporativo **16,6%**

Cuanto más barato el plan, mayor el churn.

Esa es la gran ventaja de una metric view: cambias la regla una sola vez y todos los gráficos que la usan cambian juntos.

### Paso 2.2: Agregar 2 filtros
En el mismo asistente de Genie, pega el prompt de abajo:
```text
Agrega 2 filtros al dashboard: uno para Plan y otro para Segmento.
```

Al elegir un valor en cualquier filtro, los gráficos se ajustan juntos.

## Paso 3: Incluir el logo
1. Desde el menú inferior del panel, agrega un widget de **Image**
2. Haz clic en **use a URL** y pega lo siguiente:
```text
https://raw.githubusercontent.com/douglassrsilva/master-training-spanish/main/assets/logo_master_training.png
```
3. Posiciona el logo en la parte superior del dashboard, ocupando todo el ancho de la página

## Paso 4: Mapa de churn por región (con Genie)
1. Selecciona **Genie** nuevamente
2. Pega el prompt de abajo:
```text
Incluye un mapa con la cantidad de suscripciones canceladas por país. Usa la columna pais (código ISO de 2 letras) de dbacademy.churn.dim_cliente y las tablas dbacademy.churn.hecho_suscripcion y dbacademy.churn.dim_cliente.
```

Resultado esperado: un mapa de LATAM con las cancelaciones distribuidas entre ~8 países, con mayor concentración en **MX, AR, CO y PE**.

## Paso 5: Nombrar y publicar
1. Haz clic en el título del dashboard, en la parte superior de la página, y renómbralo como **`Análisis de Churn <tu_schema>`**, reemplazando `<tu_schema>` por el nombre de tu schema
2. Haz clic en **Publish** en la esquina superior derecha

El dashboard publicado es el que compartes con el equipo de negocio: ellos interactúan con los filtros sin necesitar el editor.

> Volveremos a este panel en el Ej. 6
