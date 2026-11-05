# 07 - Análisis de Datos con Solución Multi-Agent

![Ruta del Master Training con énfasis en lo construido hasta el Ejercicio 07](../assets/07%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en la ruta hasta este punto; en gris, lo que todavía viene._

Hasta aquí construiste los análisis. Ahora vamos a abrirlos al equipo de negocio con los **Genie Agents**: cualquier persona hace su pregunta en español (*"¿cuál es el ingreso por segmento?"*) y el Genie escribe el SQL, lo ejecuta y responde, sin escribir una sola línea de código.

Y vamos un paso más allá. Vas a crear dos Genies especializados, uno de **Facturación** y uno de **Soporte**, y al final un **Supervisor** que orquesta a los dos. El usuario hace una sola pregunta, y el Supervisor descubre por sí mismo qué especialista debe responder. Eso es lo que llamamos una solución *multi-agent*.

---

# Parte 1: Genie de Facturación

## Paso 1: Crear el Genie Agent
1. En el menú lateral izquierdo, haz clic en **Genie Agents**
2. Haz clic en **New**
3. En **Connect your data**, agrega:
    - `dbacademy.churn.dim_cliente`
    - `dbacademy.churn.dim_plan`
    - `dbacademy.churn.hecho_suscripcion`
    - `dbacademy.churn.hecho_facturacion`
4. Asigna el nombre `Facturación - <tu_schema>`, reemplazando `<tu_schema>` por el nombre de tu schema

> El Genie infiere las relaciones entre las tablas; no necesitas configurar los joins a mano. Vamos a reutilizar este Genie Agent en la Parte 3, en el Supervisor

## Paso 2: Preguntar
Haz las preguntas de abajo, una por una:

```text
¿Cuáles son los ingresos totales por segmento?
```
Resultado esperado:
- Consumidor **US$ 3,62 millones**
- PyME **US$ 1,80 millones**
- Corporativo **US$ 680 mil**

```text
¿Cuál es el porcentaje de facturas no pagadas por plan?
```
Resultado esperado:
- Básico **7,90%**
- Estándar **6,49%**
- Premium **5,90%**
- Empresarial **5,45%**

La morosidad acompaña al churn: es peor en el plan Básico.

Fíjate que no dijiste de qué tabla sale el dato: el Genie lo descubre solo, muestra el SQL que escribió y todavía dibuja un gráfico.

---

# Parte 2: Genie de Soporte

## Paso 3: Crear el Genie Agent
1. Crea un nuevo Genie Agent como en el Paso 1 (**Genie Agents → New**)
2. En **Connect your data**, agrega:
    - `dbacademy.churn.dim_cliente`
    - `dbacademy.churn.hecho_ticket_soporte`
3. Asigna el nombre `Soporte - <tu_schema>`, reemplazando `<tu_schema>` por el nombre de tu schema

## Paso 4: Preguntar
Haz las preguntas de abajo, una por una:

```text
¿Cuál es el CSAT promedio por categoría de ticket?
```
Resultado esperado:
- Consulta **4,08**
- Cobranza **2,99**
- Técnico **2,28**
- Cancelación **2,27**

```text
¿Cuántos tickets de soporte tenemos por canal?
```
Resultado esperado:
- Chat **447**
- Email **407**
- Teléfono **399**

## Paso 5: Pregunta por el año fiscal
```text
¿Cuál es el NPS promedio del año fiscal 2024 en Costa Rica (CR)?
```
El Genie responde **≈ 7,3**, pero vale la pena leer su explicación: *"no hay una definición de año fiscal, así que lo interpreté como año calendario (ene–dic de 2024)"*. Es decir, asumió que año fiscal equivale a año calendario, porque nadie le dijo cuándo empieza el año fiscal de tu empresa.

## Paso 6: Enseña la regla y pregunta de nuevo
1. Abre el menú de configuración del agente en **Configure**, en la esquina superior derecha
2. En la pestaña **Instructions**, pega la regla de tu año fiscal:
```text
El año fiscal (AF) de la empresa va del 1 de octubre al 30 de septiembre del año siguiente, y se identifica por el año en que comienza. Ejemplo: el AF2024 va del 01/10/2024 al 30/09/2025. Siempre que la pregunta mencione "año fiscal", usa ese período (con base en fecha_apertura), nunca el año calendario.
```
3. Haz exactamente la misma pregunta:
```text
¿Cuál es el NPS promedio del año fiscal 2024 en Costa Rica (CR)?
```

Esta vez el Genie filtra del 01/10/2024 al 30/09/2025 y responde **≈ 6,5**. Es un número distinto porque cambió el período: la misma pregunta dio dos respuestas, y la diferencia fue la regla que le diste.

> Es la misma idea de la métrica gobernada del Ej. 3: sin la regla explícita, la IA adivina. Las *Instructions* son el lugar donde conviertes el conocimiento del negocio en respuestas confiables, y aplican para todos los que usan el Genie Agent.

---

# Parte 3: Supervisor (multi-agent)

Ya tienes dos especialistas. Ahora vamos a crear el **Supervisor**: recibe la pregunta del usuario y la deriva al Genie correcto, sin que el usuario tenga que saber cuál es cuál.

## Paso 7: Crear el Supervisor y adjuntar los agentes
1. En el menú lateral izquierdo, abre **Agents**
2. Haz clic en **Create agent** y selecciona **Supervisor Agent**
3. Ve a **Tools and sub-agents** y selecciona la opción **Genie Agents**
4. En el campo de búsqueda, escribe el nombre de tu agente de facturación (`Facturación - <tu_schema>`) y selecciónalo
5. En la descripción de la herramienta, pega:
```text
Especialista en facturación y cobranza. Responde sobre ingresos, morosidad, facturas pagadas y no pagadas, y montos por plan y por segmento.
```
6. Repite los pasos 3 a 5 para el agente de soporte (`Soporte - <tu_schema>`), con la descripción:
```text
Especialista en atención y satisfacción del cliente. Responde sobre tickets de soporte, CSAT, NPS, canales y categorías, incluso por año fiscal.
```
7. Elimina la herramienta que viene por defecto, llamada `python_exec`: pasa el cursor sobre ella, haz clic en el ícono de papelera y confirma la eliminación

> En este ejercicio el Supervisor solo coordina los dos Genies, por eso eliminamos `python_exec`

## Paso 8: Nombrar, instruir y describir
> El campo **nombre** solo se puede editar después de adjuntar al menos un agente (Paso 7); por eso dejamos este paso para ahora.

1. Asigna un nombre al Supervisor, por ejemplo `Analisis-Clientes-<tu_schema>`
2. En **Instructions**, pega las reglas de coordinación:
```text
Coordinas a dos especialistas: uno de Facturación (ingresos, morosidad, facturas, planes) y uno de Soporte (tickets, CSAT, NPS, canales). Dirige cada pregunta al especialista adecuado, combina las respuestas cuando la pregunta involucre los dos temas y responde siempre en español.
```
3. Más abajo, en **Description**, pega:
```text
Asistente de análisis de clientes: responde preguntas de negocio sobre facturación y sobre atención/soporte, derivando cada pregunta al especialista correcto.
```

## Paso 9: Probar el enrutamiento
Haz estas dos preguntas nuevas, una de cada dominio, y observa cómo el Supervisor elige al especialista correcto antes de responder:

```text
¿Cuál es el monto total en facturas no pagadas?
```
Resultado esperado: el Supervisor activa el agente de **Facturación** → **≈ US$ 383.335** (3.846 facturas abiertas)

```text
¿Cuál es la calificación promedio de NPS por canal de atención?
```
Resultado esperado: el Supervisor activa el agente de **Soporte** →
- Chat **6,57**
- Email **6,54**
- Teléfono **6,47**

> Fíjate en que no dijiste a qué Genie preguntar: el Supervisor leyó la pregunta, eligió al especialista y sintetizó la respuesta. Así una solución *multi-agent* simplifica la vida del usuario de negocio: una sola puerta de entrada, varios especialistas detrás.

## Paso 10: Renombrar el Supervisor y copiar el endpoint
1. Haz clic en el ícono de lápiz junto al nombre del supervisor y renómbralo como `supervisor-<tu_schema>`
2. Haz clic en el botón **Endpoint** arriba
3. Copia y guarda el nombre del endpoint que empieza con `mas-` (algo como `mas-3d713414-endpoint`)

Al crear el Supervisor, Databricks ya lo publica como un **endpoint de serving**. Es por ese endpoint que la app del Ej. 9 va a llamar al Supervisor.

> Vas a pegar el nombre del endpoint en el campo `supervisor_endpoint` del Ej. 9
