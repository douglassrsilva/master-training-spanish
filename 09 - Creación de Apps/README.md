# 09 - Creación de Apps

![Ruta del Master Training con énfasis en lo construido hasta el Ejercicio 09](../assets/09%20-%20arquitetura.gif?v=20260928)

> _Todo lo que construiste durante la ruta._

Detectaste el riesgo (dashboards + modelo del Ej. 6), diagnosticaste el porqué (agentes del Ej. 7) y creaste las funciones que actúan (Ej. 8). Ahora vamos a reunir todo en un producto: la **Central de Retención**, un app que cualquier agente de atención abre en el navegador, sin SQL y sin notebook.

El app reúne lo que construiste en los módulos anteriores en tres pestañas, y lo publicas ejecutando un único notebook: completas dos campos y haces clic en **Run all**. El notebook crea el app, configura automáticamente todo lo que necesita y devuelve la URL.

Y hay una novedad: la IA del app (la lectura de los gráficos y el e-mail de retención) pasa por un **model service del Unity Gateway**, creado en tu schema. Es un modelo gobernado por Unity Catalog, con límite de uso y registro de cada llamada, exactamente como una empresa pondría IA en producción.

**Requisitos previos:**
- [Ej. 1 - SQL con IA](<../01 - SQL con IA/README.md>)
- [Ej. 6 - Predicción de Churn (ML)](<../06 - Predicción de Churn (ML)/README.md>)
- [Ej. 7 - Análisis de Datos Multi-Agent](<../07 - Análisis de Datos Multi-Agent/README.md>)
- [Ej. 8 - Retención con ML y GenAI](<../08 - Retención con ML y GenAI/README.md>)

---

## Paso 1: Publicar el app
1. Importa el notebook: **Workspace → Tres puntitos en la parte superior → Import → URL**, y pega lo siguiente:
```
https://github.com/douglassrsilva/master-training-spanish/blob/main/09%20-%20Creaci%C3%B3n%20de%20Apps/deploy_app.py
```
2. Después de hacer clic en **Import**, se abrirá el notebook
3. En el desplegable de la barra superior, junto a **Run all**, selecciona el cluster `dbacademy_workshop_cluster`
4. Ejecuta la primera celda de código, debajo de **Paso 1 — Completa los campos y ejecuta todo**, para mostrar los widgets
5. Completa los widgets:
    - **1. Tu schema**: el schema que creaste en el Ej. 1
    - **2. Endpoint del Supervisor (Ej.07)**: el nombre del endpoint que copiaste en el Paso 10 del Ej. 7 (ej.: `mas-3d713414-endpoint`)
    - **5. Model service (Unity Gateway)**: ya viene completado con `retencion-gateway`. Puedes dejarlo como está
6. Haz clic en **Run all**

> ¿No guardaste el endpoint? En **Agents**, abre tu Supervisor y haz clic en el botón **Endpoint** de arriba

El notebook hace todo el trabajo pesado:
- Descarga el código del app desde GitHub y lo prepara con tu configuración
- Resuelve el SQL Warehouse por nombre (`dbacademy_workshop_wh`), con respaldo
- Crea tu **model service** `dbacademy.<tu_schema>.retencion-gateway` en el Unity Gateway (modelo `gpt-oss-20b`, límite de 60 llamadas por minuto y tabla de inferencia)
- Crea el app (`central-retencion-<tu_schema>`) con compute y *service principal* propios
- Habilita el **on-behalf-of** (scopes `sql`, `model-serving` y `ai-gateway`) y declara el warehouse que usa el app
- Publica el app e imprime la URL

> El notebook es **autocontenido**: descarga por sí mismo el código del app (la carpeta `app/`, con el front-end ya compilado) desde GitHub en tiempo de ejecución. No necesitas clonar el repositorio.

Fíjate en lo que no hace: ninguna concesión de permisos. Sin `GRANT`, sin `EXECUTE`, sin `CAN_QUERY`, sin `CAN_RUN` en Genie. Bajo el on-behalf-of, el app actúa con tu identidad, que ya tiene acceso a todo.


## Paso 2: Abrir el app
1. Haz clic en la URL que el notebook imprime al final
2. La primera vez, Databricks te pide que **autorices el app** para actuar en tu nombre (SQL, Model Serving y AI Gateway). Haz clic en **Authorize**
3. En la pestaña **📊 Cockpit**, haz clic en una región del mapa y mira cómo se filtran los gráficos
4. Todavía en el **Cockpit**, haz clic en **✨ Explicar** en uno de los gráficos
5. En la pestaña **💬 Asistente**, haz estas preguntas, una por una:
```text
¿Cuál es el NPS promedio por canal de atención?
```
```text
¿Cuál es el monto total de facturas sin pagar?
```
6. En la pestaña **🎯 Retención Personalizada**, pega `C01575` (Mariana), genera el e-mail y haz clic en **Enviar a CRM**. Luego repite con `C00018` (Gabriela)

En el **Asistente**, fíjate en que cada pregunta se enruta al especialista correcto (Soporte / Facturación).

En **Retención**, compara los dos e-mails: Mariana recibe 15% + 10 GB + gerente dedicado, y Gabriela 10% + el doble de internet con WhatsApp + renegociación. Las ofertas vienen de tu `get_cliente_360` (la regla del Ej. 8), y el modelo del Unity Gateway solo redacta el texto.

> **¿Por qué el app necesita autorizar el AI Gateway?** Porque cada llamada al modelo se hace **con tu identidad** (on-behalf-of). Sin el scope `ai-gateway`, el Gateway rechaza la llamada. Esto es lo que permite saber, después, quién usó el modelo y cuándo.

## Paso 3: Ver la gobernanza del Unity Gateway
1. En el **Catalog Explorer**, abre `dbacademy` → tu schema. Además de tus tablas y funciones, verás el model service **`retencion-gateway`**: es un activo de Unity Catalog, con dueño (tú), permisos y linaje, como cualquier tabla
2. Cada llamada que el app hizo al modelo quedó registrada en la **tabla de inferencia** del model service. En el **SQL Editor**, ejecuta (reemplazando `<tu_schema>`):
```sql
SELECT
    event_time,
    status_code,
    latency_ms,
    destination_model,
    LEFT(get_json_object(request, '$.messages[1].content'), 200) AS pedido
FROM dbacademy.<tu_schema>.retencion_gateway_payload
ORDER BY event_time DESC
LIMIT 10;
```
Verás una fila por cada **✨ Explicar** y por cada **e-mail** generado. En la columna `pedido`, fíjate en que las ofertas ya llegan preparadas al modelo: la regla la decidió tu función, no la IA.

> La tabla de inferencia puede tardar unos minutos en mostrar las llamadas más recientes. Para una vista de toda la cuenta (quién llamó, cuántos tokens, qué modelo), Databricks también registra el uso en la tabla de sistema `system.ai_gateway.usage`, con algunas horas de retraso.

### ¿Qué es la Central de Retención?
Un **Databricks App** (la plataforma aloja el app con compute propio) con tres pestañas, cada una consumiendo lo que construiste:

| Pestaña | Qué hace | De dónde viene |
|---------|----------|----------------|
| **📊 Cockpit** | KPIs de churn, un mapa de LATAM con el riesgo por región y 4 gráficos que se filtran al hacer clic en una región. Cada gráfico tiene un botón **✨ Explicar** que pide una lectura a la IA. | `churn_scores` (Ej. 6) + schema compartido `dbacademy.churn`, leídos por un SQL Warehouse; la lectura viene de tu model service del Unity Gateway |
| **💬 Asistente** | Un chat que responde preguntas de negocio (*"¿cuál es el NPS promedio por canal?"*, *"¿total de facturas abiertas?"*) enrutando al Genie correcto. | tu Supervisor del Ej. 7 |
| **🎯 Retención Personalizada** | Lista los clientes con mayor propensión a cancelar; pegas un id, generas el e-mail de retención y haces clic en **Enviar a CRM**. | función `get_cliente_360` del Ej. 8 (perfil + ofertas) + tu model service del Unity Gateway (texto) |

> **¿Por qué un app y no otro dashboard?** Porque un app te permite hacer mucho más que un dashboard: aquí navegas el riesgo, conversas con los datos y disparas la retención, todo en un solo lugar, con la gobernanza de Unity Catalog por detrás (el app accede a los datos con tu propia identidad)

## Explore
Acabas de cerrar el ciclo del curso: desde los datos crudos (Setup) hasta un producto de retención que un equipo de negocio usa en el día a día (detectar, diagnosticar, decidir y actuar), todo gobernado por Unity Catalog, incluido el modelo de IA, a través de Unity Gateway. Es el mismo patrón que llevas a cualquier caso de uso: **datos → métricas → IA → agentes → app**.
