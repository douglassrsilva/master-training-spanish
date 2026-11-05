# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # Desmontaje del Workshop: Base de Churn + clase (`00_setup`)
# MAGIC
# MAGIC Revierte los recursos creados por `00_setup`. **Idempotente**: cualquier cosa
# MAGIC que ya no exista se omite, por lo que es seguro volver a ejecutarlo.
# MAGIC
# MAGIC Cada interruptor es `true`/`false`. Los valores por defecto eliminan los recursos **específicos del workshop**
# MAGIC (grupo, warehouse, cluster). Eliminar el grupo también revoca todos los permisos otorgados a él.
# MAGIC
# MAGIC ⚠️ **`DROP CATALOG dbacademy` por defecto es `false`**: el catálogo pertenece al administrador y contiene
# MAGIC tanto la base COMPARTIDA `dbacademy.churn` (tablas + volumen `kb_volume`) como el schema personal
# MAGIC `dbacademy.<username>` de cada participante y sus datos. Defínelo como `true` solo si el notebook
# MAGIC de preparación creó el catálogo y el workshop terminó por completo.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Parámetros

# COMMAND ----------

dbutils.widgets.dropdown("delete_group", "true", ["true", "false"], "1. Eliminar grupo del workshop")
dbutils.widgets.dropdown("delete_warehouse", "true", ["true", "false"], "2. Eliminar SQL Warehouse")
dbutils.widgets.dropdown("delete_cluster", "true", ["true", "false"], "3. Eliminar cluster multiuso")
dbutils.widgets.dropdown("delete_catalog", "false", ["true", "false"], "4. ELIMINAR CATÁLOGO (DESTRUCTIVO)")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Convenciones fijas, deben coincidir con el notebook de preparación.
CATALOG = "dbacademy"
SCHEMA = "churn"
SCHEMA_FULL_NAME = f"{CATALOG}.{SCHEMA}"
VOLUME_FULL_NAME = f"{SCHEMA_FULL_NAME}.kb_volume"
GROUP = "dbacademy_workshop"
WAREHOUSE_NAME = "dbacademy_workshop_wh"
CLUSTER_NAME = "dbacademy_workshop_cluster"

DELETE_GROUP = dbutils.widgets.get("delete_group") == "true"
DELETE_WAREHOUSE = dbutils.widgets.get("delete_warehouse") == "true"
DELETE_CLUSTER = dbutils.widgets.get("delete_cluster") == "true"
DELETE_CATALOG = dbutils.widgets.get("delete_catalog") == "true"

OK, NO, ERR, NA = "✅", "❌", "⚠️", "➖"

def _acct_scim(method, path, **kw):
    return w.api_client.do(method, f"/api/2.0/account/scim/v2{path}", **kw)

print(f"Grupo:     {GROUP}            (eliminar={DELETE_GROUP})")
print(f"Warehouse: {WAREHOUSE_NAME}   (eliminar={DELETE_WAREHOUSE})")
print(f"Cluster:   {CLUSTER_NAME}     (eliminar={DELETE_CLUSTER})")
print(f"Catálogo:  {CATALOG}          (ELIMINAR={DELETE_CATALOG})  {'⚠️ DESTRUCTIVO (incluye base churn)' if DELETE_CATALOG else ''}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Desmontaje (idempotente)

# COMMAND ----------

print("=" * 70)
print("DESMONTAJE")
print("=" * 70)

# --- Cluster ---------------------------------------------------------------
if DELETE_CLUSTER:
    _cl = next((c for c in w.clusters.list() if c.cluster_name == CLUSTER_NAME), None)
    if _cl:
        try:
            w.clusters.permanent_delete(cluster_id=_cl.cluster_id)
            print(f"{OK} Cluster '{CLUSTER_NAME}' eliminado.")
        except Exception as e:
            print(f"{NO} No fue posible eliminar el cluster '{CLUSTER_NAME}': {e}")
    else:
        print(f"{OK} Cluster '{CLUSTER_NAME}' ya no existe.")
else:
    print(f"{NA} Cluster '{CLUSTER_NAME}' conservado (eliminar=false).")

# --- Warehouse -----------------------------------------------------------
if DELETE_WAREHOUSE:
    _wh = next((x for x in w.warehouses.list() if x.name == WAREHOUSE_NAME), None)
    if _wh:
        try:
            w.warehouses.delete(id=_wh.id)
            print(f"{OK} Warehouse '{WAREHOUSE_NAME}' eliminado.")
        except Exception as e:
            print(f"{NO} No fue posible eliminar el warehouse '{WAREHOUSE_NAME}': {e}")
    else:
        print(f"{OK} Warehouse '{WAREHOUSE_NAME}' ya no existe.")
else:
    print(f"{NA} Warehouse '{WAREHOUSE_NAME}' conservado (eliminar=false).")

# --- Grupo del workshop (revocar permisos, desasociar, eliminar) ----
if DELETE_GROUP:
    # Esfuerzo por revocar mientras el grupo aún existe (se omite si el recurso ya fue eliminado).
    for _sql, _label in [
        (f"REVOKE USE CATALOG, CREATE SCHEMA ON CATALOG {CATALOG} FROM `{GROUP}`", "catálogo"),
        (f"REVOKE USE SCHEMA, SELECT ON SCHEMA {SCHEMA_FULL_NAME} FROM `{GROUP}`", "schema"),
        (f"REVOKE READ VOLUME ON VOLUME {VOLUME_FULL_NAME} FROM `{GROUP}`", "volumen"),
    ]:
        try:
            spark.sql(_sql)
            print(f"{OK} Permisos de {_label} revocados de {GROUP}.")
        except Exception:
            print(f"{NA} Revocación de {_label} omitida (recurso o permiso ya eliminado).")

    _found = _acct_scim("GET", "/Groups", query={"filter": f'displayName eq "{GROUP}"'}).get("Resources") or []
    if _found:
        _gid = _found[0]["id"]
        try:
            w.api_client.do("DELETE", f"/api/2.0/preview/permissionassignments/principals/{_gid}")
        except Exception:
            pass  # la asignación quizás ya fue removida
        try:
            _acct_scim("DELETE", f"/Groups/{_gid}")
            print(f"{OK} Grupo de cuenta '{GROUP}' (id {_gid}) eliminado. Sus permisos y membresías también fueron eliminados.")
        except Exception as e:
            print(f"{NO} No fue posible eliminar el grupo de cuenta '{GROUP}': {e}")
    else:
        print(f"{OK} Grupo de cuenta '{GROUP}' ya no existe.")

    # Eliminar también cualquier grupo local de workspace obsoleto con el mismo nombre.
    for _g in w.groups.list(filter=f'displayName eq "{GROUP}"'):
        _meta = w.groups.get(_g.id).meta
        if _meta and _meta.resource_type == "WorkspaceGroup":
            w.groups.delete(_g.id)
            print(f"  eliminado grupo local de workspace obsoleto '{GROUP}' (id {_g.id}).")
else:
    print(f"{NA} Grupo '{GROUP}' conservado (eliminar=false). Sus permisos permanecerán.")

# --- Catálogo (DESTRUCTIVO, activación manual) --------------------------------
if DELETE_CATALOG:
    try:
        spark.sql(f"DROP CATALOG IF EXISTS {CATALOG} CASCADE")
        print(f"{OK} Catálogo '{CATALOG}' eliminado (CASCADE: todos los schemas/datos/volúmenes eliminados).")
    except Exception as e:
        print(f"{NO} No fue posible eliminar el catálogo '{CATALOG}': {e}")
else:
    print(f"{NA} Catálogo '{CATALOG}' conservado (ELIMINAR=false). Schemas/datos de los participantes preservados.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Informe final
# MAGIC ✅ = revertido (recurso ahora ausente) · ➖ = conservado por elección · ❌ = todavía presente · ⚠️ = desconocido.

# COMMAND ----------

import pandas as pd

def _account_group_exists(group):
    try:
        return len(_acct_scim("GET", "/Groups", query={"filter": f'displayName eq "{group}"'}).get("Resources") or []) > 0
    except Exception:
        return None

def _row(label, requested, still_present):
    if not requested:
        return {"Ítem": label, "Estado": NA, "Nota": "conservado (eliminar=false)"}
    if still_present is None:
        return {"Ítem": label, "Estado": ERR, "Nota": "no fue posible verificar"}
    return {"Ítem": label, "Estado": OK if not still_present else NO,
            "Nota": "eliminado" if not still_present else "TODAVÍA PRESENTE"}

try:
    w.catalogs.get(CATALOG); _catalog_present = True
except Exception:
    _catalog_present = False

report = [
    _row(f"Cluster '{CLUSTER_NAME}'",       DELETE_CLUSTER,   any(c.cluster_name == CLUSTER_NAME for c in w.clusters.list())),
    _row(f"Warehouse '{WAREHOUSE_NAME}'",   DELETE_WAREHOUSE, any(x.name == WAREHOUSE_NAME for x in w.warehouses.list())),
    _row(f"Grupo '{GROUP}'",                DELETE_GROUP,     _account_group_exists(GROUP)),
    _row(f"Catálogo '{CATALOG}'",           DELETE_CATALOG,   _catalog_present),
]

_done = all(r["Estado"] in (OK, NA) for r in report)
print("GENERAL:", "✅ Desmontaje concluido: todo lo solicitado fue revertido."
      if _done else "❌ Algunos ítems todavía están presentes: revisa abajo.")
display(pd.DataFrame(report, columns=["Ítem", "Estado", "Nota"]))
