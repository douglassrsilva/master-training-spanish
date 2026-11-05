# Databricks notebook source
# MAGIC %md
# MAGIC # Ejercicio 9 — Central de Retención (Databricks App)
# MAGIC
# MAGIC Este notebook **despliega tu app** *Central de Retención* — el panel que une todo el curso:
# MAGIC el **Cockpit** de churn (mapa + gráficos con lectura por IA), el **Asistente**
# MAGIC (el Supervisor del Ej. 7) y la **Retención Personalizada** (la función `get_cliente_360` del Ej. 8).
# MAGIC
# MAGIC La IA del app (la lectura de los gráficos y el e-mail de retención) pasa por un **model service del
# MAGIC Unity Gateway** que este notebook crea en **tu** schema: un modelo gobernado por Unity
# MAGIC Catalog, con límite de uso y registro de cada llamada.
# MAGIC
# MAGIC No **escribes código** y **no otorgas ningún permiso manual**: completa los campos de arriba y
# MAGIC haz clic en **Run all**.
# MAGIC
# MAGIC **Cómo accede el app a los datos (on-behalf-of):** el app ejecuta cada consulta y cada llamada de
# MAGIC IA **con la identidad del usuario logueado** (autenticación *on-behalf-of-user*, mediante el encabezado
# MAGIC `X-Forwarded-Access-Token`). Como TÚ ya tienes acceso — `SELECT` en `dbacademy.churn` (por el
# MAGIC grupo del curso), eres dueño de tu schema y de tus funciones, y eres dueño de tu Supervisor/Genies — **no hay
# MAGIC nada que otorgar** al *service principal* del app. Ese es el truco clave de este deploy:
# MAGIC cero permisos manuales, funciona para cualquier alumno.
# MAGIC
# MAGIC **Requisitos previos** (en tu schema `dbacademy.<tu_schema>`):
# MAGIC - **Ej. 7** — tu **Supervisor** publicado (endpoint `mas-...-endpoint`).
# MAGIC - **Ej. 6** — la tabla `churn_scores`.
# MAGIC - **Ej. 8** — la función `get_cliente_360` (con las ofertas calculadas en SQL).
# MAGIC
# MAGIC > Ejecútalo en el cluster `dbacademy_workshop_cluster`. El app corre en compute propio de Databricks Apps.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 1 — Completa los campos y ejecuta todo
# MAGIC 1. **Ejecuta solo la celda de abajo** (Shift+Enter) para que los campos aparezcan en la parte superior del notebook.
# MAGIC 2. Completa **Tu schema** (ej.: `tu_schema`) y **Endpoint del Supervisor (Ej.07)**
# MAGIC    (el endpoint de tu Supervisor del Ej. 7, ej.: `mas-3d713414-endpoint`).
# MAGIC 3. El campo **Model service** ya viene con `retencion-gateway`: es el nombre del modelo que el
# MAGIC    notebook va a crear en el Unity Gateway, dentro de tu schema. Puedes dejarlo como está.
# MAGIC 4. Recién entonces haz clic en **Run all**.

# COMMAND ----------

# Crea los campos en la parte superior del notebook. Ejecuta ESTA celda primero, completa los campos y luego Run all.
# El warehouse se convierte en un desplegable con los warehouses reales del workspace, ya con el del Setup seleccionado.
from databricks.sdk import WorkspaceClient as _WC
_wh_names = [x.name for x in _WC().warehouses.list()]
_WH_DEFAULT = "dbacademy_workshop_wh"
_wh_choices = _wh_names or [""]
_wh_sel = _WH_DEFAULT if _WH_DEFAULT in _wh_names else (_wh_names[0] if _wh_names else "")

dbutils.widgets.text("schema", "", "Tu schema")
dbutils.widgets.text("supervisor_endpoint", "", "Endpoint del Supervisor (Ej.07)")
dbutils.widgets.dropdown("warehouse", _wh_sel, _wh_choices, "Warehouse")
dbutils.widgets.text("model_service", "retencion-gateway", "Model service")

# COMMAND ----------

SCHEMA = dbutils.widgets.get("schema").strip()
SUPERVISOR = dbutils.widgets.get("supervisor_endpoint").strip()
CATALOG = "dbacademy"
WAREHOUSE_W = dbutils.widgets.get("warehouse").strip()
MODEL_SERVICE_NAME = dbutils.widgets.get("model_service").strip() or "retencion-gateway"

assert SCHEMA, "Completa el widget 'Tu schema' (ej.: tu_schema)."
assert SUPERVISOR, "Completa el widget 'Endpoint del Supervisor (Ej.07)' (ej.: mas-...-endpoint del Ej. 7)."

import os, re, shutil, time
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Scopes OBO: `sql` (SQL Warehouse) + `model-serving` (serving endpoints: Supervisor) +
# `ai-gateway` (model service del Unity Gateway). Sin `ai-gateway`, el Gateway responde 403.
USER_API_SCOPES = ["sql", "model-serving", "ai-gateway"]
EXPLAIN_MODEL = "databricks-claude-sonnet-4-5"   # lectura por IA de los gráficos (Cockpit)
WAREHOUSE_NAME = "dbacademy_workshop_wh"          # creado en el Setup (Ej. 00)
GATEWAY_DEST_MODEL = "models/system.ai.gpt-oss-20b"  # modelo detrás del model service

# Nombre del app: prefijo + database normalizado, LIMITADO a 30 caracteres
# (Databricks Apps exige un nombre entre 2 y 30 caracteres). Trunca y quita el guion sobrante al final.
APP_NAME = ("central-retencion-" + re.sub(r"[^a-z0-9-]", "-", SCHEMA.lower()).strip("-"))[:30].rstrip("-")
ME = w.current_user.me().user_name

print("Alumno           :", ME)
print("App              :", APP_NAME, f"({len(APP_NAME)} chars)")
print("Catálogo/schema  :", f"{CATALOG}.{SCHEMA}  (+ {CATALOG}.churn compartido)")
GATEWAY_MODEL = f"{CATALOG}.{SCHEMA}.{MODEL_SERVICE_NAME}"
print("Supervisor       :", SUPERVISOR)
print("Model service    :", GATEWAY_MODEL, "(Unity Gateway)")
print("Auth             : on-behalf-of-user (se ejecuta como TÚ; sin grants al service principal)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 2 — Resolver el SQL Warehouse
# MAGIC El app lee los datos mediante el warehouse (con TU token). Lo resolvemos por **nombre** (el ID no es
# MAGIC portable): widget → `dbacademy_workshop_wh` → primer warehouse disponible.

# COMMAND ----------

def resolver_warehouse():
    whs = list(w.warehouses.list())
    if not whs:
        raise RuntimeError("No se encontró ningún SQL Warehouse en el workspace. Ejecuta el Setup (Ej. 00).")
    if WAREHOUSE_W:
        m = next((x for x in whs if x.id == WAREHOUSE_W or x.name == WAREHOUSE_W), None)
        if m:
            return m.id, m.name, "widget"
        print(f"  aviso: el warehouse '{WAREHOUSE_W}' del widget no se encontró; se usa la cascada de respaldo.")
    m = next((x for x in whs if x.name == WAREHOUSE_NAME), None)
    if m:
        return m.id, m.name, f"nombre '{WAREHOUSE_NAME}'"
    m = next((x for x in whs if str(getattr(x, "state", "")).upper().endswith("RUNNING")), whs[0])
    return m.id, m.name, "fallback (primero disponible)"

WH_ID, WH_NAME, WH_VIA = resolver_warehouse()
print(f"Warehouse: '{WH_NAME}' (id {WH_ID}) — resuelto por {WH_VIA}.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 3 — Crear tu model service en el Unity Gateway
# MAGIC Un **model service** es un modelo de IA gobernado por Unity Catalog: vive en **tu**
# MAGIC schema (tú eres el dueño), tiene **límite de uso** (60 llamadas por minuto) y una **tabla de
# MAGIC inferencia** que registra cada llamada (pregunta y respuesta). El app lo usará para leer los
# MAGIC gráficos y para redactar el e-mail de retención. Si ya existe, lo reutilizamos.

# COMMAND ----------

def api(method, path, body=None):
    return w.api_client.do(method, path, body=body)

_ms_path = f"/api/2.1/unity-catalog/model-services/{GATEWAY_MODEL}"
try:
    api("GET", _ms_path)
    print(f"Model service '{GATEWAY_MODEL}' ya existe — reutilizando.")
except Exception:
    api("POST", f"/api/2.1/unity-catalog/model-services?model_service_id={MODEL_SERVICE_NAME}"
                f"&parent=schemas/{CATALOG}.{SCHEMA}", body={
        "comment": "Master Training — modelo de la Central de Retención (Unity Gateway)",
        "config": {
            "routing": {"destinations": [{
                "destination_type": "DESTINATION_TYPE_PAY_PER_TOKEN_FOUNDATION_MODEL",
                "name": "primary", "traffic_percentage": 100,
                "pay_per_token_config": {"model": GATEWAY_DEST_MODEL}}]},
            "rate_limits": [{"key": "RATE_LIMIT_KEY_SERVICE",
                             "renewal_period": "RATE_LIMIT_RENEWAL_PERIOD_MINUTE", "requests": 60}],
            "inference_table": {"parent": f"schemas/{CATALOG}.{SCHEMA}",
                                "table_name_prefix": MODEL_SERVICE_NAME.replace("-", "_")},
        },
    })
    print(f"Model service '{GATEWAY_MODEL}' creado.")
_ms = api("GET", _ms_path)
_dest = (_ms.get("config") or {}).get("routing", {}).get("destinations", [{}])[0]
print("  destino        :", (_dest.get("pay_per_token_config") or {}).get("model"))
print("  inference table:", ((_ms.get("config") or {}).get("inference_table") or {}).get("table"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 4 — Preparar el código fuente del app (con TU configuración)
# MAGIC Este notebook es **autocontenido**: **descarga el código del app** del repositorio público en
# MAGIC GitHub (la carpeta `09 - Creación de Apps/app/`), lo copia a una carpeta tuya en el workspace y escribe
# MAGIC tus valores en el `app.yaml`. El app está **completamente dirigido por configuración**
# MAGIC (`server/config.py` lee las variables `CR_*`) — no se escribe nada en el código.

# COMMAND ----------

import urllib.request, zipfile, tempfile, glob

# Descarga el repositorio de GitHub (el compute de Databricks alcanza github.com) y usa su carpeta app/.
ZIP_URL = "https://github.com/douglassrsilva/master-training-spanish/archive/refs/heads/main.zip"
_tmp = tempfile.mkdtemp()
_zip = os.path.join(_tmp, "repo.zip")
urllib.request.urlretrieve(ZIP_URL, _zip)
with zipfile.ZipFile(_zip) as _zf:
    _zf.extractall(_tmp)
_matches = glob.glob(os.path.join(_tmp, "*", "09 - Creación de Apps", "app"))
assert _matches, (
    "No pude descargar la carpeta app/ desde GitHub. Verifica que el compute tenga acceso a github.com "
    "(o agrega el repositorio como Git folder y usa la carpeta app/ local)."
)
SRC_APP = _matches[0]
print("app descargado desde GitHub:", SRC_APP)

STAGE = f"/Workspace/Users/{ME}/.central-retencion/{APP_NAME}"
if os.path.exists(STAGE):
    shutil.rmtree(STAGE)
shutil.copytree(SRC_APP, STAGE)

# app.yaml con la configuración del alumno. Nota: los scopes OBO NO van en el app.yaml (clave ignorada y
# puede hacer fallar el build); se configuran en el APP (campo user_api_scopes) en el Paso 6.
APP_YAML = f"""command:
  - "uvicorn"
  - "app:app"
  - "--host"
  - "0.0.0.0"
  - "--port"
  - "8000"

env:
  - name: CR_WAREHOUSE_ID
    value: "{WH_ID}"
  - name: CR_SUPERVISOR_ENDPOINT
    value: "{SUPERVISOR}"
  - name: CR_EXPLAIN_MODEL
    value: "{EXPLAIN_MODEL}"
  - name: CR_GATEWAY_MODEL
    value: "{GATEWAY_MODEL}"
  - name: CR_CATALOG
    value: "{CATALOG}"
  - name: CR_SCHEMA_CHURN
    value: "churn"
  - name: CR_SCHEMA_PERSONAL
    value: "{SCHEMA}"
"""
with open(os.path.join(STAGE, "app.yaml"), "w") as f:
    f.write(APP_YAML)

print("Código preparado en:", STAGE)
print(APP_YAML)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 5 — Crear el app (compute propio + service principal)
# MAGIC Si ya existe (re-ejecución), seguimos adelante. Esperamos a que el compute esté **ACTIVE**.

# COMMAND ----------

try:
    api("GET", f"/api/2.0/apps/{APP_NAME}")
    print(f"App '{APP_NAME}' ya existe — reutilizando.")
except Exception:
    api("POST", "/api/2.0/apps", body={
        "name": APP_NAME,
        "description": "Central de Retención — Master Training (churn): Cockpit + Asistente + Retención.",
    })
    print(f"App '{APP_NAME}' creado.")

for _ in range(60):
    app = api("GET", f"/api/2.0/apps/{APP_NAME}")
    if (app.get("compute_status") or {}).get("state") == "ACTIVE":
        break
    time.sleep(10)

SP = app.get("service_principal_client_id")
APP_URL = app.get("url")
print(f"compute: {(app.get('compute_status') or {}).get('state')}  |  SP: {SP}")
print("URL     :", APP_URL)
assert SP, "El service principal del app todavía no está disponible; vuelve a ejecutar esta celda."

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 6 — Configurar OBO (scopes) + el warehouse
# MAGIC La ÚNICA preparación necesaria — y ninguna es una concesión al usuario/SP:
# MAGIC - **user_api_scopes** = `sql`, `model-serving`, `ai-gateway` → permite que el app use el token
# MAGIC   del usuario en las llamadas de SQL, del Supervisor y de tu model service del Unity Gateway;
# MAGIC - **recurso warehouse** (CAN_USE) → el app debe declarar el warehouse que va a usar.
# MAGIC
# MAGIC **No hay** GRANT de UC, EXECUTE, CAN_QUERY en endpoints, ni CAN_RUN en Genies: todo eso lo hace innecesario el OBO
# MAGIC (las llamadas se ejecutan como el usuario, que ya tiene acceso).

# COMMAND ----------

api("PATCH", f"/api/2.0/apps/{APP_NAME}", body={
    "name": APP_NAME,
    "user_api_scopes": USER_API_SCOPES,
    "resources": [
        {"name": "sql-warehouse", "description": "Warehouse para leer el Unity Catalog (como el usuario)",
         "sql_warehouse": {"id": WH_ID, "permission": "CAN_USE"}},
    ],
})
_app = api("GET", f"/api/2.0/apps/{APP_NAME}")
print("scopes OBO  :", _app.get("effective_user_api_scopes"))
print("recursos    :", [r["name"] for r in _app.get("resources", [])])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 7 — Publicar (deploy)

# COMMAND ----------

api("POST", f"/api/2.0/apps/{APP_NAME}/deployments",
    body={"source_code_path": STAGE, "mode": "SNAPSHOT"})
estado = None
for _ in range(60):
    app = api("GET", f"/api/2.0/apps/{APP_NAME}")
    ad = app.get("active_deployment") or {}
    estado = (ad.get("status") or {}).get("state")
    if estado in ("SUCCEEDED", "FAILED", "STOPPED"):
        break
    time.sleep(10)
print("deploy:", estado)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ¡Listo! 🎉

# COMMAND ----------

print("=" * 66)
print("  CENTRAL DE RETENCIÓN — publicada (autenticación on-behalf-of usuario)")
print("=" * 66)
print("  App URL :", APP_URL)
print("  Deploy  :", estado)
print("  Modelo  :", GATEWAY_MODEL, "(Unity Gateway)")
print("  Scopes  :", USER_API_SCOPES, "(el app usa TU token en las llamadas)")
print("  Grants  : NINGUNO otorgado al service principal — innecesario bajo OBO.")
print("  Manual  : nada además de los 2 campos de este notebook.")
print("=" * 66)
print("  Abre la URL de arriba y explora las 3 pestañas. Todo se ejecuta con TU identidad:")
print("  el Cockpit lee los datos, el Asistente usa tu Supervisor/Genies y la")
print("  Retención llama a tus UC functions — sin necesidad de otorgar nada.")
displayHTML(f'<h3>Central de Retención</h3><a href="{APP_URL}" target="_blank">{APP_URL}</a>')
