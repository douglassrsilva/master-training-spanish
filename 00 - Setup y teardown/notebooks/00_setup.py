# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # Setup del Workshop: Base de Churn + Habilitación de la clase
# MAGIC Ejecútalo **1 vez** como **administrador de cuenta**. Este notebook hace todo de una vez:
# MAGIC 1. **Prepara la clase**: grupo `dbacademy_workshop` (participantes + accesos), catálogo,
# MAGIC    SQL Warehouse, cluster multiuso y los permisos.
# MAGIC 2. **Carga la base COMPARTIDA** `<catálogo>.churn` (CSV → Delta, `feature_churn`,
# MAGIC    comentarios + PK/FK, volumen de conocimiento) y libera **lectura** para la clase.
# MAGIC 3. **Verifica** que cada participante tiene lo necesario y que el workspace tiene las funcionalidades
# MAGIC    de IA usadas en los Ej. 4/6/7 (Model Serving/Foundation Model APIs y Multi-Agent Supervisor).
# MAGIC
# MAGIC **Es idempotente** (create-if-not-exists + grants idempotentes): es seguro volver a ejecutarlo.
# MAGIC
# MAGIC ***Este notebook (y el entrenamiento) debe ejecutarse en el workspace corporativo, y no en Databricks Free Edition.***
# MAGIC
# MAGIC > ⚠️ Ejecuta las **dos primeras celdas** para mostrar los widgets, selecciona los participantes y
# MAGIC > usa **Run all**. **Todas las celdas deben terminar con éxito.** El veredicto final está en la
# MAGIC > sección **7. Informe final** (`✅ VERIFICACIONES COMPLETAS`). Si hay ❌/⚠️, corrige y vuelve a ejecutar.
# MAGIC
# MAGIC > Las metric views (Ej. 3), el modelo (Ej. 6) y los Genies/Supervisor (Ej. 7) los crea cada participante
# MAGIC > en su schema personal `<catálogo>.<tu_schema>`, habilitado aquí mediante `CREATE SCHEMA`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Parámetros

# COMMAND ----------

# Conectar y reunir los usuarios del workspace que completan el selector de participantes.
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

_PICK_ATT = "(elige participantes)"
_user_choices = sorted({u.user_name for u in w.users.list(attributes="userName") if u.user_name})
_attendee_opts = [_PICK_ATT] + _user_choices

print(f"Se encontraron {len(_user_choices)} usuario(s) del workspace para el selector de participantes.")
more_than_1024_users = len(_attendee_opts) > 1024
if more_than_1024_users:
    print("⚠️  Este workspace tiene más usuarios de los que admite el widget de selección múltiple. "
          "Será necesario completar la lista de participantes manualmente en la siguiente celda.")

# COMMAND ----------

# Crear los widgets de entrada.
# (Si ves "widget already exists with a different type", usa Edit -> Clear all widget values
#  una vez y vuelve a ejecutar esta celda.)
dbutils.widgets.dropdown("create_catalog", "true", ["true", "false"], "1. Crear catálogo")
dbutils.widgets.dropdown("create_warehouse", "true", ["true", "false"], "2. Crear SQL Warehouse")
dbutils.widgets.dropdown("create_cluster", "true", ["true", "false"], "3. Crear cluster multiuso")
if not more_than_1024_users:
    dbutils.widgets.multiselect("attendees", _PICK_ATT, _attendee_opts, "4. Participantes (usuarios del workspace)")
else:
    attendees_manual = [
        # completa esta lista con los emails de los participantes solo si se indica en la celda de arriba
    ]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Acción necesaria
# MAGIC Completa el widget `4. Participantes` con todos los participantes y haz clic en **Run all**.

# COMMAND ----------

# Convenciones fijas para los recursos que este notebook gestiona.
import os

NOMBRE_CATALOGO = "dbacademy"               # catálogo de Unity Catalog de destino
NOMBRE_SCHEMA   = "churn"                   # schema COMPARTIDO (solo lectura para los participantes)
GROUP          = "dbacademy_workshop"
WAREHOUSE_NAME = "dbacademy_workshop_wh"
CLUSTER_NAME   = "dbacademy_workshop_cluster"
fq = f"{NOMBRE_CATALOGO}.{NOMBRE_SCHEMA}"
PREP_CHECK_VERSION = "1.5"                  # versión de este setup (se muestra en el informe final)

# Origen de los CSV: la carpeta data/ del Git folder del workspace. El repo es privado (GitHub EMU),
# así que no se usa la URL raw de GitHub. El notebook se ejecuta desde .../00 - Setup y teardown/notebooks,
# por lo que ../data es la carpeta con los CSV.
# Override opcional: asigna una ruta absoluta (p.ej. /Workspace/... o /Volumes/...) o una URL http(s) a CSV_OVERRIDE.
CSV_OVERRIDE = ""
CSV_BASE = CSV_OVERRIDE or os.path.abspath(os.path.join(os.getcwd(), "..", "data"))
if not CSV_BASE.startswith(("http://", "https://")) and not os.path.isdir(CSV_BASE):
    raise FileNotFoundError(
        f"No se encontró la carpeta de CSV: {CSV_BASE}. Ejecuta el setup desde el Git folder clonado "
        "(ver el README del módulo 00) o define CSV_OVERRIDE.")

CREATE_CATALOG   = dbutils.widgets.get("create_catalog") == "true"
CREATE_WAREHOUSE = dbutils.widgets.get("create_warehouse") == "true"
CREATE_CLUSTER   = dbutils.widgets.get("create_cluster") == "true"
ATTENDEES = ([a.strip() for a in dbutils.widgets.get("attendees").split(",")
              if a.strip() and a.strip() != _PICK_ATT] if not more_than_1024_users else attendees_manual)

if not ATTENDEES:
    dbutils.notebook.exit("⏳ Elige al menos un participante arriba y ejecuta 'Run all'.")

def nice_print(resource, resource_name, should_create=None):
    print(f"{resource}:".rjust(16), resource_name.ljust(28),
          f"(crear={should_create})" if should_create is not None else "")
    print("-" * 70)

print("-" * 70)
nice_print("Catálogo", NOMBRE_CATALOGO, CREATE_CATALOG)
nice_print("Base compart.", fq)
nice_print("Origen CSV", CSV_BASE)
nice_print("Grupo", GROUP)
nice_print("Warehouse", WAREHOUSE_NAME, CREATE_WAREHOUSE)
nice_print("Cluster", CLUSTER_NAME, CREATE_CLUSTER)
print(f"Participantes ({len(ATTENDEES)}):".rjust(16), *[f"\t\t- {a}" for a in ATTENDEES], sep="\n")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Funciones auxiliares

# COMMAND ----------

import time
from urllib.parse import quote

OK, NO, ERR, NA = "✅", "❌", "⚠️", "➖"

def _sym(v):
    return OK if v is True else (NO if v is False else ERR)

def _acct_scim(method, path, **kw):
    return w.api_client.do(method, f"/api/2.0/account/scim/v2{path}", **kw)

def _acct_user_id(email):
    res = _acct_scim("GET", "/Users", query={"filter": f'userName eq "{email}"'}).get("Resources") or []
    return res[0]["id"] if res else None

def grant_with_retry(sql, attempts=5, delay=3):
    """Reintenta una concesión mientras UC se actualiza para un principal recién creado."""
    last = None
    for _ in range(attempts):
        try:
            spark.sql(sql)
            return True
        except Exception as e:
            last = e
            if "PRINCIPAL_DOES_NOT_EXIST" in str(e) or "Could not find principal" in str(e):
                time.sleep(delay)
                continue
            raise
    raise last

def uc_effective_privileges(securable_type, full_name, principal):
    try:
        resp = w.api_client.do(
            "GET",
            f"/api/2.1/unity-catalog/effective-permissions/{securable_type}/{quote(full_name, safe='')}",
            query={"principal": principal})
    except Exception:
        return None
    privs = set()
    for pa in (resp.get("privilege_assignments") or []):
        for p in (pa.get("privileges") or []):
            if p.get("privilege"):
                privs.add(p["privilege"])
    return privs

def uc_has(privs, needed):
    if privs is None:
        return None
    return ("ALL_PRIVILEGES" in privs) or (needed in privs)

def get_user_info(email):
    users = list(w.users.list(filter=f'userName eq "{email}"',
                              attributes="userName,groups,entitlements"))
    if not users:
        return None
    u = users[0]
    groups = {g.display for g in (u.groups or []) if g.display}
    ents = {e.value for e in (u.entitlements or []) if e.value}
    for gname in groups:
        ents |= GROUP_ENTITLEMENTS.get(gname, set())
    return {"groups": groups, "entitlements": ents}

def acl_has_permission(acl, user_email, user_groups, accepted_levels):
    """True = otorgado (directo o vía grupo); False = no; None = ACL no disponible."""
    if acl is None:
        return None
    email_l = user_email.lower()
    for entry in acl:
        levels = {p.permission_level.value for p in (entry.all_permissions or []) if p.permission_level}
        if not (levels & accepted_levels):
            continue
        if entry.user_name and entry.user_name.lower() == email_l:
            return True
        if entry.group_name and entry.group_name in user_groups:
            return True
    return False

print("Funciones auxiliares definidas.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Preparación de la clase (idempotente)

# COMMAND ----------

from databricks.sdk.service.compute import (
    AutoScale, DataSecurityMode, ClusterAccessControlRequest, ClusterPermissionLevel,
)
from databricks.sdk.service.sql import (
    WarehouseAccessControlRequest, WarehousePermissionLevel, CreateWarehouseRequestWarehouseType,
)

print("=" * 70); print("PREPARACIÓN"); print("=" * 70)

# --- 3a. Grupo del workshop (nivel de CUENTA, para que Unity Catalog pueda otorgar permisos) ----
# UC acepta solo grupos de nivel de CUENTA como principals de concesión. Un grupo local de
# workspace falla con PRINCIPAL_DOES_NOT_EXIST. Aprovisionamos un grupo de cuenta, lo asignamos a
# este workspace y agregamos a los participantes como usuarios de cuenta.
try:
    # Eliminar cualquier grupo local de workspace remanente con el mismo nombre (evita ambigüedad).
    for _g in w.groups.list(filter=f'displayName eq "{GROUP}"'):
        _meta = w.groups.get(_g.id).meta
        if _meta and _meta.resource_type == "WorkspaceGroup":
            w.groups.delete(_g.id)
            print(f"  eliminado grupo local de workspace obsoleto '{GROUP}' (id {_g.id}).")

    _found = _acct_scim("GET", "/Groups", query={"filter": f'displayName eq "{GROUP}"'}).get("Resources") or []
    if _found:
        GROUP_ID = _found[0]["id"]
        print(f"{OK} Grupo de cuenta '{GROUP}' ya existe (id {GROUP_ID}).")
    else:
        GROUP_ID = _acct_scim("POST", "/Groups",
            body={"schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"], "displayName": GROUP})["id"]
        print(f"{OK} Grupo de cuenta '{GROUP}' creado (id {GROUP_ID}).")

    # Asignar el grupo a ESTE workspace (necesario para ACLs de warehouse/cluster y visibilidad).
    w.api_client.do("PUT", f"/api/2.0/preview/permissionassignments/principals/{GROUP_ID}",
                    body={"permissions": ["USER"]})
    print(f"{OK} Grupo asignado a este workspace.")

    # Agregar los participantes seleccionados (resueltos a IDs de usuario de CUENTA) como miembros.
    _existing = {m["value"] for m in (_acct_scim("GET", f"/Groups/{GROUP_ID}").get("members") or [])}
    _to_add = []
    for _email in ATTENDEES:
        _uid = _acct_user_id(_email)
        if not _uid:
            print(f"  {ERR} no encontrado como usuario de cuenta, no es posible agregarlo: {_email}")
            continue
        if _uid not in _existing:
            _to_add.append(_uid)
    if _to_add:
        _acct_scim("PATCH", f"/Groups/{GROUP_ID}",
            body={"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                  "Operations": [{"op": "add", "path": "members",
                                  "value": [{"value": u} for u in _to_add]}]})
    print(f"{OK} Membresía del grupo: {len(_existing)} ya miembros, {len(_to_add)} agregados.")

    # Definir los derechos de acceso del workspace EN EL GRUPO.
    _ws_gid = None
    for _ in range(6):
        _wsg = list(w.groups.list(filter=f'displayName eq "{GROUP}"', attributes="id"))
        if _wsg:
            _ws_gid = _wsg[0].id
            break
        time.sleep(3)
    if _ws_gid:
        w.api_client.do("PATCH", f"/api/2.0/preview/scim/v2/Groups/{_ws_gid}",
            body={"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                  "Operations": [{"op": "add", "path": "entitlements",
                                  "value": [{"value": "workspace-access"}, {"value": "databricks-sql-access"}]}]})
        print(f"{OK} Derechos de acceso garantizados para '{GROUP}': workspace-access, databricks-sql-access.")
    else:
        print(f"{ERR} Grupo no visible en el SCIM del workspace para definir derechos; vuelve a ejecutar para aplicar.")
except Exception as e:
    if any(k in str(e) for k in ("403", "PERMISSION_DENIED")) or "not authorized" in str(e).lower():
        raise RuntimeError(
            "Aprovisionar el grupo a nivel de cuenta requiere ADMIN DE CUENTA. Ejecuta como administrador "
            f"de cuenta, o en la consola de la cuenta crea un grupo '{GROUP}', asígnalo a este workspace, "
            "agrega a los participantes y vuelve a ejecutar el resto.") from e
    raise

# COMMAND ----------

# --- 3b. Catálogo (manejar metastore sin almacenamiento por defecto) -----------
try:
    w.catalogs.get(NOMBRE_CATALOGO)
    print(f"{OK} Catálogo '{NOMBRE_CATALOGO}' ya existe (creación omitida).")
except Exception as _e:
    if "404" not in str(_e) and "NotFound" not in type(_e).__name__:
        raise  # 403, timeout, etc.: no es "el catálogo no existe"
    if CREATE_CATALOG:
        try:
            spark.sql(f"CREATE CATALOG IF NOT EXISTS {NOMBRE_CATALOGO}")
            print(f"{OK} Catálogo '{NOMBRE_CATALOGO}' listo.")
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ["managed location", "storage location", "default storage",
                                      "location is required", "no metastore storage", "storage root"]):
                raise RuntimeError(
                    f"Catálogo '{NOMBRE_CATALOGO}' no puede crearse automáticamente: este metastore no "
                    f"tiene almacenamiento por defecto, así que necesita una UBICACIÓN GESTIONADA explícita. Créalo a mano "
                    f"(Catalog Explorer → Create catalog → Default Storage), o bien:\n"
                    f"    CREATE CATALOG {NOMBRE_CATALOGO} MANAGED LOCATION 'gs://<bucket>/<path>';\n"
                    f"luego vuelve a ejecutar con 'Crear catálogo' = false.") from e
            raise
    else:
        print(f"{NO} Catálogo '{NOMBRE_CATALOGO}' no encontrado y 'Crear catálogo' = false. Créalo o activa la opción.")

# --- 3c. Permisos de catálogo para el grupo (crear el schema personal del participante) ---
# Modelo: el participante tiene USE CATALOG + CREATE SCHEMA; al crear su schema, pasa a ser dueño
# solo en su propio schema (lectura y escritura).
try:
    grant_with_retry(f"GRANT USE CATALOG, CREATE SCHEMA ON CATALOG {NOMBRE_CATALOGO} TO `{GROUP}`")
    print(f"{OK} USE CATALOG + CREATE SCHEMA otorgados en {NOMBRE_CATALOGO} a {GROUP}.")
except Exception as e:
    print(f"{NO} No fue posible otorgar permisos en el catálogo '{NOMBRE_CATALOGO}': {e}")

# Modelos de system.ai (Ej. 9: el model service del Unity Gateway apunta a system.ai.gpt-oss-20b).
try:
    grant_with_retry(f"GRANT USE SCHEMA, EXECUTE ON SCHEMA system.ai TO `{GROUP}`")
    print(f"{OK} USE SCHEMA + EXECUTE otorgados en system.ai a {GROUP}.")
except Exception as e:
    print(f"{NO} No fue posible otorgar permisos en 'system.ai': {e}")

# COMMAND ----------

# --- 3d. SQL Warehouse (Ej. 01, 02, 04, 05, 06) ------------------------------
def ensure_warehouse(name):
    existing = next((x for x in w.warehouses.list() if x.name == name), None)
    if existing:
        return existing.id, "ya existe"
    try:
        wh = w.warehouses.create(name=name, cluster_size="Small", min_num_clusters=1, max_num_clusters=3,
                                 auto_stop_mins=30, enable_serverless_compute=True,
                                 warehouse_type=CreateWarehouseRequestWarehouseType.PRO)
    except Exception as e:
        if "serverless" not in str(e).lower() and "not supported" not in str(e).lower():
            raise  # cuota, auth, nombre: no es limitación de serverless
        print("  el warehouse serverless falló; probando PRO clásico")
        wh = w.warehouses.create(name=name, cluster_size="Small", min_num_clusters=1, max_num_clusters=3,
                                 auto_stop_mins=30, enable_serverless_compute=False,
                                 warehouse_type=CreateWarehouseRequestWarehouseType.PRO)
    return wh.id, "creado"

WAREHOUSE_ID = None
if CREATE_WAREHOUSE:
    try:
        WAREHOUSE_ID, _st = ensure_warehouse(WAREHOUSE_NAME)
        print(f"{OK} Warehouse '{WAREHOUSE_NAME}' {_st} (id {WAREHOUSE_ID}).")
    except Exception as e:
        print(f"{NO} No fue posible crear el warehouse '{WAREHOUSE_NAME}': {e}")
else:
    WAREHOUSE_ID = next((x.id for x in w.warehouses.list() if x.name == WAREHOUSE_NAME), None)
    print(f"{OK if WAREHOUSE_ID else NO} Warehouse '{WAREHOUSE_NAME}' "
          f"{'encontrado' if WAREHOUSE_ID else 'no encontrado'} (creación omitida).")

if WAREHOUSE_ID:
    try:
        w.warehouses.update_permissions(warehouse_id=WAREHOUSE_ID, access_control_list=[
            WarehouseAccessControlRequest(group_name=GROUP, permission_level=WarehousePermissionLevel.CAN_MANAGE)])
        print(f"{OK} CAN_MANAGE del warehouse otorgado a {GROUP}.")
    except Exception as e:
        print(f"{NO} No fue posible otorgar permiso de warehouse: {e}")

# COMMAND ----------

# --- 3e. Cluster multiuso (notebooks: Setup, Ej. 03, Ej. 06) -----------------
def ensure_cluster(name):
    existing = next((c for c in w.clusters.list() if c.cluster_name == name), None)
    if existing:
        return existing.cluster_id, "ya existe"
    # Mismo tipo de nodo para driver + workers: consciente de la nube y evita incompatibilidad ARM/no ARM.
    _node = w.clusters.select_node_type(min_memory_gb=32, local_disk=True)
    cl = w.clusters.create(
        cluster_name=name,
        spark_version=w.clusters.select_spark_version(latest=True, long_term_support=True),
        node_type_id=_node, driver_node_type_id=_node,
        autoscale=AutoScale(min_workers=2, max_workers=8),
        autotermination_minutes=240,
        data_security_mode=DataSecurityMode.USER_ISOLATION)  # Compartido (multiusuario + UC)
    return cl.cluster_id, "creado"

CLUSTER_ID = None
if CREATE_CLUSTER:
    try:
        CLUSTER_ID, _st = ensure_cluster(CLUSTER_NAME)
        print(f"{OK} Cluster '{CLUSTER_NAME}' {_st} (id {CLUSTER_ID}). Se detiene automáticamente cuando está inactivo.")
    except Exception as e:
        print(f"{NO} No fue posible crear el cluster '{CLUSTER_NAME}': {e}")
else:
    CLUSTER_ID = next((c.cluster_id for c in w.clusters.list() if c.cluster_name == CLUSTER_NAME), None)
    print(f"{OK if CLUSTER_ID else NO} Cluster '{CLUSTER_NAME}' "
          f"{'encontrado' if CLUSTER_ID else 'no encontrado'} (creación omitida).")

if CLUSTER_ID:
    try:
        w.clusters.update_permissions(cluster_id=CLUSTER_ID, access_control_list=[
            ClusterAccessControlRequest(group_name=GROUP, permission_level=ClusterPermissionLevel.CAN_ATTACH_TO)])
        print(f"{OK} CAN_ATTACH_TO del cluster otorgado a {GROUP}.")
    except Exception as e:
        print(f"{NO} No fue posible otorgar permiso de cluster: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Base COMPARTIDA de churn
# MAGIC Lee los CSV de la carpeta `data/` del Git folder → tablas Delta, deriva `feature_churn`, documenta
# MAGIC (comentarios + PK/FK) y arma la base de conocimiento. **El éxito de la carga confirma que el cómputo
# MAGIC puede leer los datos del Git folder.**

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {fq} COMMENT 'Base compartida de churn del Master Training'")

# ## 4.1 Carga de los CSV (Git folder) → tablas Delta
import pandas as pd
from pyspark.sql.functions import to_date, col, lower, when, trim

def carga(nombre, dates=(), bools=()):
    pdf = pd.read_csv(os.path.join(CSV_BASE, f"{nombre}.csv"), keep_default_na=False)  # "" en lugar de NaN
    df = spark.createDataFrame(pdf)   # numéricos inferidos; fechas/booleanos vienen como string
    for d in dates:  # trata vacío como NULL antes del cast (ANSI: to_date('') falla)
        df = df.withColumn(d, to_date(when(trim(col(d)) == "", None).otherwise(col(d))))
    for b in bools:
        df = df.withColumn(b, lower(col(b).cast("string")) == "true")
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fq}.{nombre}")
    print(f"  {nombre:22} {df.count():>6} filas")

carga("dim_plan")
carga("dim_cliente", dates=["fecha_registro"])
carga("dim_fecha", dates=["fecha"], bools=["fin_de_semana"])
carga("hecho_suscripcion", dates=["fecha_inicio", "fecha_fin"])
carga("hecho_uso", dates=["periodo"])
carga("hecho_facturacion", dates=["periodo"], bools=["pago"])
carga("hecho_ticket_soporte", dates=["fecha_apertura"])

# COMMAND ----------
# ## 4.2 feature_churn (variables de comportamiento, sin leakage)
spark.sql(f"""CREATE OR REPLACE TABLE {fq}.feature_churn AS
WITH u AS (SELECT id_cliente, AVG(logins_mes) uso_promedio, AVG(horas_uso) horas_promedio FROM {fq}.hecho_uso GROUP BY id_cliente),
f AS (SELECT id_cliente, AVG(dias_atraso) dias_atraso_promedio, AVG(CASE WHEN NOT pago THEN 1.0 ELSE 0.0 END) pct_facturas_atraso FROM {fq}.hecho_facturacion GROUP BY id_cliente),
t AS (SELECT id_cliente, AVG(csat) csat_promedio, AVG(nps) nps_promedio FROM {fq}.hecho_ticket_soporte GROUP BY id_cliente)
SELECT c.id_cliente, c.segmento, p.nombre_plan, CAST(p.precio_mensual AS DOUBLE) precio_mensual,
 CAST(COALESCE(u.uso_promedio,0) AS DOUBLE) uso_promedio, CAST(COALESCE(u.horas_promedio,0) AS DOUBLE) horas_promedio,
 CAST(COALESCE(f.dias_atraso_promedio,0) AS DOUBLE) dias_atraso_promedio, CAST(COALESCE(f.pct_facturas_atraso,0) AS DOUBLE) pct_facturas_atraso,
 CAST(COALESCE(t.csat_promedio,3) AS DOUBLE) csat_promedio, CAST(COALESCE(t.nps_promedio,7) AS DOUBLE) nps_promedio, a.churn_flag
FROM {fq}.dim_cliente c JOIN {fq}.hecho_suscripcion a ON a.id_cliente=c.id_cliente
JOIN {fq}.dim_plan p ON p.id_plan=a.id_plan
LEFT JOIN u ON u.id_cliente=c.id_cliente LEFT JOIN f ON f.id_cliente=c.id_cliente LEFT JOIN t ON t.id_cliente=c.id_cliente""")

# COMMAND ----------
# ## 4.3 Comentarios + constraints (documentación para Genie y Discovery)
tabc={"dim_cliente":"Dimensión de clientes.","dim_plan":"Dimensión de planes.","dim_fecha":"Dimensión calendario.",
 "hecho_suscripcion":"Suscripciones: una por cliente, con estado y churn.","hecho_uso":"Uso mensual por cliente.",
 "hecho_facturacion":"Facturación mensual por cliente.","hecho_ticket_soporte":"Tickets de soporte con texto, CSAT y NPS.",
 "feature_churn":"Tabla analítica por cliente (variables de comportamiento) para el modelo de churn."}
colc={"dim_cliente":{"id_cliente":"Identificador único del cliente","nombre_cliente":"Nombre del cliente","segmento":"Segmento: Consumidor, PyME o Corporativo","ciudad":"Ciudad","pais":"País (código ISO de 2 letras)","fecha_registro":"Fecha de registro","canal_adquisicion":"Canal de adquisición","rango_edad":"Rango de edad"},
 "dim_plan":{"id_plan":"Identificador del plan","nombre_plan":"Nombre del plan: Básico, Estándar, Premium o Empresarial","periodicidad":"Mensual o Anual","precio_mensual":"Precio mensual en dólares (USD)"},
 "dim_fecha":{"fecha":"Fecha","anio":"Año","mes":"Mes","nombre_mes":"Nombre del mes","trimestre":"Trimestre","dia_semana":"Día de la semana","fin_de_semana":"¿Fin de semana?"},
 "hecho_suscripcion":{"id_suscripcion":"ID de la suscripción","id_cliente":"FK dim_cliente","id_plan":"FK dim_plan","fecha_inicio":"Inicio","fecha_fin":"Cancelación (nulo si está activa)","status":"Activa o Cancelada","motivo_cancelacion":"Motivo de la cancelación","churn_flag":"1 si canceló (churn), 0 si está activo"},
 "hecho_uso":{"id_uso":"ID","id_cliente":"FK dim_cliente","periodo":"Mes de referencia","logins_mes":"Inicios de sesión en el mes","horas_uso":"Horas de uso","funcionalidades_usadas":"Funcionalidades usadas"},
 "hecho_facturacion":{"id_factura":"ID","id_cliente":"FK dim_cliente","id_suscripcion":"FK suscripción","periodo":"Mes","monto":"Monto en US$","pago":"¿Pagado?","dias_atraso":"Días de atraso"},
 "hecho_ticket_soporte":{"id_ticket":"ID","id_cliente":"FK dim_cliente","fecha_apertura":"Apertura","canal":"Chat, Email o Teléfono","categoria":"Cobranza, Técnico, Cancelación o Consulta","texto_reclamo":"Texto del contacto (puede contener PII)","csat":"Satisfacción 1-5","nps":"NPS 0-10"}}
for t,c in tabc.items(): spark.sql(f"COMMENT ON TABLE {fq}.{t} IS '{c}'")
for t,cols in colc.items():
    for cc,cm in cols.items(): spark.sql(f"ALTER TABLE {fq}.{t} ALTER COLUMN {cc} COMMENT '{cm}'")
def _run(s):
    try: spark.sql(s)
    except Exception as e: print("omitido:", str(e)[:70])
_run(f"ALTER TABLE {fq}.dim_cliente ALTER COLUMN id_cliente SET NOT NULL")
_run(f"ALTER TABLE {fq}.dim_plan ALTER COLUMN id_plan SET NOT NULL")
_run(f"ALTER TABLE {fq}.dim_cliente ADD CONSTRAINT pk_cliente PRIMARY KEY (id_cliente)")
_run(f"ALTER TABLE {fq}.dim_plan ADD CONSTRAINT pk_plan PRIMARY KEY (id_plan)")
for t in ["hecho_suscripcion","hecho_uso","hecho_facturacion","hecho_ticket_soporte"]:
    _run(f"ALTER TABLE {fq}.{t} ADD CONSTRAINT fk_{t}_cli FOREIGN KEY (id_cliente) REFERENCES {fq}.dim_cliente(id_cliente) NOT ENFORCED RELY")

# COMMAND ----------
# ## 4.4 Base de conocimiento (volumen + documentos)
spark.sql(f"CREATE VOLUME IF NOT EXISTS {fq}.kb_volume COMMENT 'Base de conocimiento de retención'")
docs={
"FAQ_Atencion.md":"# FAQ de Atención\n\n## Cancelación\n- ¿Cómo cancelo? En Cuenta > Suscripción > Cancelar, o con Customer Success.\n- ¿Hay multa? Los planes mensuales no tienen; los anuales tienen multa proporcional a los meses restantes.\n\n## Reembolso\n- Hasta 7 días después del cobro (arrepentimiento) o falla comprobada. Anual: reembolso proporcional.\n\n## Cobranza\n- Vencimiento el día 10. Un atraso mayor a 20 días suspende el servicio.\n\n## Soporte\n- Chat 24/7, Email y Teléfono (lun-vie 8h-20h).\n",
"Politica_Retencion.md":"# Política de Retención y Cancelación\n\n## Ofertas autorizadas\n- Precio: hasta 20% de descuento por 3 meses o upgrade gratis por 1 mes.\n- Atención/Insatisfacción: atención prioritaria 60 días + gerente de cuenta.\n- Competencia: igualación de precio por hasta 6 meses.\n- Corporativo: revisión contractual, descuento por volumen y SLA dedicado.\n\n## Reglas\n- Los descuentos superiores al 20% requieren aprobación del gestor de CS.\n- Cliente de alto riesgo (score del modelo) debe ser contactado en hasta 48h.\n",
"Playbook_Customer_Success.md":"# Playbook de Customer Success\n\n## Priorización\n1. Alto valor (Premium/Empresarial) con riesgo alto.\n2. Caída de uso > 40% en el trimestre.\n3. Facturas en atraso y CSAT < 3.\n\n## Flujo\n1. Detectar riesgo. 2. Diagnosticar causa. 3. Seleccionar oferta (Política). 4. Contactar y registrar. 5. Dar seguimiento durante 90 días.\n"}
base=f"/Volumes/{NOMBRE_CATALOGO}/{NOMBRE_SCHEMA}/kb_volume"
for nombre,contenido in docs.items():
    with open(f"{base}/{nombre}","w") as fp: fp.write(contenido)
print("Base de conocimiento:", os.listdir(base))

# COMMAND ----------

# --- 4.5 Otorgar LECTURA de la base compartida a la clase ------------------
# Modelo: los participantes solo tienen lectura en {fq} (sin MODIFY, CREATE TABLE, etc.).
try:
    grant_with_retry(f"GRANT USE SCHEMA, SELECT ON SCHEMA {fq} TO `{GROUP}`")
    print(f"{OK} USE SCHEMA + SELECT (solo lectura) otorgados en {fq} a {GROUP}.")
    try:
        grant_with_retry(f"GRANT READ VOLUME ON VOLUME {fq}.kb_volume TO `{GROUP}`")
        print(f"{OK} READ VOLUME otorgado en {fq}.kb_volume a {GROUP}.")
    except Exception as ve:
        print(f"{ERR} No fue posible otorgar READ VOLUME (quizás el volumen aún no existe): {ve}")
except Exception as e:
    print(f"{NO} No fue posible otorgar lectura de la base compartida: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verificación: matriz de permisos por participante
# MAGIC | Columna | Requisito | Necesario por |
# MAGIC |---|---|---|
# MAGIC | Acceso al workspace | `workspace-access` | Todos |
# MAGIC | Databricks SQL | `databricks-sql-access` | 01, 02, 04, 05, 06 |
# MAGIC | USE CATALOG | `USE CATALOG` en el catálogo | Todos |
# MAGIC | CREATE SCHEMA | `CREATE SCHEMA` en el catálogo (schema personal) | 01, 03, 07 |
# MAGIC | Lectura base churn | `SELECT` en el schema `churn` compartido | 01-07 |
# MAGIC | Warehouse CAN USE | `CAN_USE` en el SQL Warehouse | 01, 02, 04, 05, 06 |
# MAGIC | Cluster CAN ATTACH | `CAN_ATTACH_TO` en el cluster | 00, 03, 07 (notebooks) |

# COMMAND ----------

# Reconstruir el mapa grupo->derechos DESPUÉS de la preparación para reflejar el nuevo grupo.
GROUP_ENTITLEMENTS = {}
for g in w.groups.list(attributes="displayName,entitlements"):
    if g.display_name:
        GROUP_ENTITLEMENTS[g.display_name] = {e.value for e in (g.entitlements or []) if e.value}

WAREHOUSE = next((x for x in w.warehouses.list() if x.name == WAREHOUSE_NAME), None)
CLUSTER = next((c for c in w.clusters.list() if c.cluster_name == CLUSTER_NAME), None)
try:
    WAREHOUSE_ACL = w.warehouses.get_permissions(warehouse_id=WAREHOUSE.id).access_control_list if WAREHOUSE else None
except Exception:
    WAREHOUSE_ACL = None
try:
    CLUSTER_ACL = w.clusters.get_permissions(cluster_id=CLUSTER.cluster_id).access_control_list if CLUSTER else None
except Exception:
    CLUSTER_ACL = None

# Los grants recién aplicados tardan unos segundos en llegar a UC; un sondeo breve evita ❌ falsos.
for _ in range(6):
    _p = uc_effective_privileges("catalog", NOMBRE_CATALOGO, ATTENDEES[-1])
    if _p and ("USE_CATALOG" in _p or "ALL_PRIVILEGES" in _p):
        break
    time.sleep(3)

import pandas as pd
COLUMNS = ["Acceso al workspace", "Databricks SQL", "USE CATALOG", "CREATE SCHEMA",
           "Lectura base churn", "Warehouse CAN USE", "Cluster CAN ATTACH"]
matrix_rows, detail_rows = {}, []

def note(email, col, symbol, message):
    if symbol in (NO, ERR):
        detail_rows.append({"Participante": email, "Verificación": col, "Estado": symbol, "Detalle": message})

for email in ATTENDEES:
    row = {c: NA for c in COLUMNS}
    info = get_user_info(email)
    if info is None:
        matrix_rows[email] = {c: ERR for c in COLUMNS}
        detail_rows.append({"Participante": email, "Verificación": "(búsqueda de usuario)", "Estado": ERR,
                            "Detalle": "Usuario no encontrado en el workspace (SCIM)."})
        continue
    groups, ents = info["groups"], info["entitlements"]

    row["Acceso al workspace"] = OK if "workspace-access" in ents else NO
    note(email, "Acceso al workspace", row["Acceso al workspace"], "Derecho 'workspace-access' faltante")
    row["Databricks SQL"] = OK if "databricks-sql-access" in ents else NO
    note(email, "Databricks SQL", row["Databricks SQL"], "Derecho 'databricks-sql-access' faltante")

    cat_privs = uc_effective_privileges("catalog", NOMBRE_CATALOGO, email)
    for _col, priv in [("USE CATALOG", "USE_CATALOG"), ("CREATE SCHEMA", "CREATE_SCHEMA")]:
        res = uc_has(cat_privs, priv)
        row[_col] = OK if res else (NO if res is False else ERR)
        if res is False:
            note(email, _col, NO, f"Ningún {priv} en el catálogo '{NOMBRE_CATALOGO}'")
        elif res is None:
            note(email, _col, ERR, f"No fue posible leer permisos en el catálogo '{NOMBRE_CATALOGO}'")

    sch_privs = uc_effective_privileges("schema", fq, email)
    res = uc_has(sch_privs, "SELECT")
    row["Lectura base churn"] = OK if res else (NO if res is False else ERR)
    if res is False:
        note(email, "Lectura base churn", NO, f"Ningún SELECT en el schema '{fq}'")
    elif res is None:
        note(email, "Lectura base churn", ERR, f"No fue posible leer permisos en el schema '{fq}'")

    ok = acl_has_permission(WAREHOUSE_ACL, email, groups, {"CAN_USE", "CAN_MANAGE"})
    row["Warehouse CAN USE"] = OK if ok else (NO if ok is False else ERR)
    if ok is False:
        note(email, "Warehouse CAN USE", NO, f"Ningún CAN_USE en el warehouse '{WAREHOUSE_NAME}'")
    elif ok is None:
        note(email, "Warehouse CAN USE", ERR, f"Warehouse '{WAREHOUSE_NAME}' no encontrado / ACL ilegible")

    ok = acl_has_permission(CLUSTER_ACL, email, groups, {"CAN_ATTACH_TO", "CAN_RESTART", "CAN_MANAGE"})
    row["Cluster CAN ATTACH"] = OK if ok else (NO if ok is False else ERR)
    if ok is False:
        note(email, "Cluster CAN ATTACH", NO, f"Ningún CAN_ATTACH_TO en el cluster '{CLUSTER_NAME}'")
    elif ok is None:
        note(email, "Cluster CAN ATTACH", ERR, f"Cluster '{CLUSTER_NAME}' no encontrado / ACL ilegible")

    matrix_rows[email] = row

matrix_df = pd.DataFrame.from_dict(matrix_rows, orient="index", columns=COLUMNS)
matrix_df.index.name = "Participante"
print(f"Verificados {len(ATTENDEES)} participante(s). Leyenda: {OK} ok  {NO} ausente  {ERR} indeterminado  {NA} n/a")
display(matrix_df.reset_index())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5b. Detalles: solo fallas y advertencias

# COMMAND ----------

if detail_rows:
    display(pd.DataFrame(detail_rows, columns=["Participante", "Verificación", "Estado", "Detalle"]))
else:
    print("Sin fallas ni advertencias. Todos los participantes tienen todos los permisos verificados. 🎉")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Funcionalidades de IA del workspace
# MAGIC Funcionalidades del **workspace completo** (no por participante), necesarias para los Ej. 4, 6 y 7:
# MAGIC | Funcionalidad | Señal | Necesaria por |
# MAGIC |---|---|---|
# MAGIC | Model Serving / Foundation Model APIs | `serving_endpoints.list()` funciona vs `NotFound` | 4 (AI Functions) |
# MAGIC | Endpoints del `ai_query` (Ej. 4) | `databricks-meta-llama-3-3-70b-instruct` y `databricks-gpt-oss-120b` presentes en la lista | 4 (pasos 1c, 2b) |
# MAGIC | Multi-Agent Supervisor (Agent Bricks) | se habilita junto con Knowledge Assistant (`GET /knowledge-assistants` responde vs 404) | 7 (Supervisor) |
# MAGIC
# MAGIC > El registro del modelo en UC (Ej. 6) usa el Model Registry de Unity Catalog, inherente a
# MAGIC > workspaces con UC, sin sondeo dedicado. El Ej. 6 **no** crea endpoint de serving.

# COMMAND ----------

# El list del Multi-Agent Supervisor responde [] incluso en regiones sin la funcionalidad, así que no sirve de
# condición; derivamos MAS del Knowledge Assistant (se habilita junto, y su 404 es una señal clara). Cliente con timeout
# corto para que el sondeo no bloquee el notebook durante minutos en regiones sin la funcionalidad.
from databricks.sdk.core import Config
try:
    w_probe = WorkspaceClient(config=Config(http_timeout_seconds=5, retry_timeout_seconds=5))
except Exception:
    w_probe = w

def _feature_probe(path, attempts=2):
    """True = API disponible; False = no disponible (404 o timeout); None = indeterminado."""
    last = None
    for _i in range(attempts):
        try:
            w_probe.api_client.do("GET", path)
            return True
        except Exception as e:
            s, tn = str(e), type(e).__name__
            if "Timeout" in tn or "Timed out" in s:
                last = False; continue  # región sin la funcionalidad (o fallo transitorio: reintenta)
            if "NotFound" in tn or "404" in s:
                return False  # API no disponible: funcionalidad no habilitada
            if "403" in s or "PERMISSION_DENIED" in s or "not authorized" in s.lower():
                return None  # sin permiso para verificar: probablemente la funcionalidad existe
            return None  # indeterminado
    return last

# El Ej. 4 ejecuta ai_query contra estos endpoints (pasos 1c y 2b). Si no están aprovisionados
# en la región/workspace, el ejercicio falla; por eso verificamos que existan, no solo que la API responda.
EX4_QUERY_ENDPOINTS = ["databricks-meta-llama-3-3-70b-instruct", "databricks-gpt-oss-120b"]
EX4_OPTIONAL = ["databricks-claude-haiku-4-5"]  # tercera opción citada en el Ej. 4 (no se ejecuta por defecto)

SERVING_OK, _ep_ready = False, {}
try:
    for e in w.serving_endpoints.list():
        _ep_ready[e.name] = getattr(getattr(getattr(e, "state", None), "ready", None), "value", None)
    SERVING_OK = True  # la API respondió (una región sin serving devuelve NotFound)
except Exception as e:
    print(f"{NO} Model Serving no disponible en este workspace ({type(e).__name__}).")

_missing_ex4 = [n for n in EX4_QUERY_ENDPOINTS if n not in _ep_ready]
EX4_OK = SERVING_OK and not _missing_ex4
if SERVING_OK and _missing_ex4:
    print(f"{NO} Endpoints del Ej. 4 ausentes (el ai_query tal como está escrito va a fallar): {', '.join(_missing_ex4)}")
_opt = [n for n in EX4_OPTIONAL if n in _ep_ready]
print(f"ℹ️  Opción adicional del Ej. 4 presente: {', '.join(_opt) if _opt else 'ninguna (databricks-claude-haiku-4-5)'}")

KA_OK = _feature_probe("/api/2.1/knowledge-assistants")
MAS_OK = KA_OK  # se habilita junto con KA

feature_report = [
    ("Model Serving / Foundation Model APIs: AI Functions (Ej. 4)", SERVING_OK),
    ("Endpoints del ai_query del Ej. 4 (llama-3-3-70b + gpt-oss-120b)", EX4_OK),
    ("Multi-Agent Supervisor / Agent Bricks (Ej. 7)", MAS_OK),
]
print(f"Funcionalidades de IA. Leyenda: {OK} disponible  {NO} no disponible  {ERR} indeterminado")
display(pd.DataFrame([{"Funcionalidad": _l, "Estado": _sym(_v)} for _l, _v in feature_report],
                     columns=["Funcionalidad", "Estado"]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Informe final
# MAGIC Un único ✅ / ❌ por ítem preparado o verificado (⚠️ = no fue posible determinarlo).
# MAGIC Incluye las funcionalidades de IA de la sección 6: si falta alguna, el entorno queda NO LISTO.

# COMMAND ----------

def _group_has_uc(securable_type, full_name, group, needed):
    try:
        r = w.api_client.do("GET",
            f"/api/2.1/unity-catalog/permissions/{securable_type}/{quote(full_name, safe='')}",
            query={"principal": group})
        privs = {p for pa in (r.get("privilege_assignments") or []) for p in (pa.get("privileges") or [])}
        return ("ALL_PRIVILEGES" in privs) or needed.issubset(privs)
    except Exception:
        return None

def _group_in_acl(acl, group, levels):
    if acl is None:
        return None
    for e in acl:
        if e.group_name == group and (
                {p.permission_level.value for p in (e.all_permissions or []) if p.permission_level} & levels):
            return True
    return False

def _account_group_exists(group):
    try:
        return len(_acct_scim("GET", "/Groups", query={"filter": f'displayName eq "{group}"'}).get("Resources") or []) > 0
    except Exception:
        return None

# Informe de validación de la base (valores exactos esperados: 2000 / 1253 / 0.27 / -0.504 / 0.125)
try:
    rep = spark.sql(f"""SELECT
     (SELECT COUNT(*) FROM {fq}.dim_cliente) clientes,
     (SELECT COUNT(*) FROM {fq}.hecho_ticket_soporte) tickets,
     (SELECT ROUND(AVG(churn_flag),3) FROM {fq}.hecho_suscripcion) tasa_churn,
     (SELECT ROUND(corr(uso_promedio, churn_flag),3) FROM {fq}.feature_churn) corr_uso_churn,
     (SELECT ROUND(corr(dias_atraso_promedio, churn_flag),3) FROM {fq}.feature_churn) corr_atraso_churn""").first()
    display(spark.createDataFrame([rep]))
    _base_ok = (rep["clientes"] == 2000 and rep["tickets"] == 1253 and
                round(rep["tasa_churn"], 3) == 0.27 and
                round(rep["corr_uso_churn"], 3) == -0.504 and
                round(rep["corr_atraso_churn"], 3) == 0.125)
except Exception as _e:
    print(f"{NO} No fue posible validar la base (¿falta alguna tabla?): {_e}")
    _base_ok = False

try:
    w.catalogs.get(NOMBRE_CATALOGO); _catalog_exists = True
except Exception:
    _catalog_exists = False

_schema_grants = _group_has_uc("schema", fq, GROUP, {"USE_SCHEMA", "SELECT"})
_volume_grants = _group_has_uc("volume", f"{fq}.kb_volume", GROUP, {"READ_VOLUME"})
if ATTENDEES:
    _det_statuses = {d["Estado"] for d in detail_rows}
    _attendees_ok = False if NO in _det_statuses else (None if ERR in _det_statuses else True)
else:
    _attendees_ok = None

report = [
    ("Grupo del workshop existe y fue asignado", _account_group_exists(GROUP)),
    ("Derechos del grupo (workspace + Databricks SQL)", {"workspace-access", "databricks-sql-access"}.issubset(GROUP_ENTITLEMENTS.get(GROUP, set()))),
    ("Catálogo existe", _catalog_exists),
    ("Permisos del catálogo para el grupo (USE CATALOG + CREATE SCHEMA)", _group_has_uc("catalog", NOMBRE_CATALOGO, GROUP, {"USE_CATALOG", "CREATE_SCHEMA"})),
    ("Base churn cargada (2000 clientes / 1253 tickets / churn 0.27)", _base_ok),
    ("Lectura de la base churn para el grupo (USE SCHEMA + SELECT, solo lectura)", _schema_grants),
    ("Lectura del volumen kb_volume para el grupo (READ VOLUME)", _volume_grants),
    ("USE SCHEMA + EXECUTE en system.ai para el grupo (Ej. 9)", _group_has_uc("schema", "system.ai", GROUP, {"USE_SCHEMA", "EXECUTE"})),
    ("SQL Warehouse existe", WAREHOUSE is not None),
    ("CAN_USE del warehouse otorgado al grupo", _group_in_acl(WAREHOUSE_ACL, GROUP, {"CAN_USE", "CAN_MANAGE"})),
    ("Cluster multiuso existe", CLUSTER is not None),
    ("CAN_ATTACH_TO del cluster otorgado al grupo", _group_in_acl(CLUSTER_ACL, GROUP, {"CAN_ATTACH_TO", "CAN_MANAGE"})),
    (f"Los {len(ATTENDEES)} participante(s) pasan todas las verificaciones", _attendees_ok),
]
report += feature_report  # las funcionalidades de IA (sección 6) bloquean el veredicto

_all_ok = all(v is True for _, v in report)
print("=" * 70)
if _all_ok:
    print(f"{OK} VERIFICACIONES COMPLETAS: base compartida cargada y los {len(ATTENDEES)} participante(s) "
          f"habilitados. Entorno listo: ya pueden iniciar el entrenamiento. 🎉")
else:
    print(f"{NO} ENTORNO NO LISTO: uno o más ítems están ❌/⚠️ abajo. Corrige la causa y vuelve a ejecutar "
          f"el notebook completo antes del entrenamiento (detalles por participante en la sección 5b).")
print("=" * 70)
display(pd.DataFrame([{"Ítem": "Versión", "Estado": PREP_CHECK_VERSION}] +
                     [{"Ítem": label, "Estado": _sym(val)} for label, val in report], columns=["Ítem", "Estado"]))
