"""
Configuración central y autenticación de la Central de Retención.

AUTENTICACIÓN ON-BEHALF-OF (OBO): dentro del Databricks App, TODAS las llamadas de datos e IA
se ejecutan con la identidad del USUARIO LOGUEADO — no con la del service principal del app.
Databricks Apps inyecta el token OAuth del usuario en el encabezado `X-Forwarded-Access-Token`
(habilitado por los scopes `user_api_scopes` del app: `sql` para el SQL Warehouse y
`model-serving` para los serving endpoints). Las rutas leen ese encabezado y pasan el token a
warehouse.py y llm.py.

Consecuencia (el punto del OBO): el app NO necesita ningún GRANT en su service principal. El
usuario ya tiene SELECT en `dbacademy.churn` (grupo del curso), es dueño de su schema personal y
de las funciones de UC, y es dueño del Supervisor/Genies — así que todo funciona sin otorgar
nada al SP.

Localmente (fuera del App) no hay encabezado: se recurre al token del profile de la CLI (dev),
vía `get_workspace_token()`.

Trampas resueltas aquí:
  1. Token OAuth local: `w.config.token` es None en auth U2M/OAuth. Usa `w.config.authenticate()`.
  2. DATABRICKS_HOST dentro del App viene SIN esquema (solo el hostname). Hay que anteponer https://.
"""
from __future__ import annotations

import json
import os
import subprocess
from functools import lru_cache
from typing import Optional

# -----------------------------------------------------------------------------
# Entorno
# -----------------------------------------------------------------------------
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

DATABRICKS_PROFILE = os.environ.get("DATABRICKS_CONFIG_PROFILE") or os.environ.get(
    "DATABRICKS_PROFILE", "mastertraining"
)

WORKSPACE_HOST_DEFAULT = "https://TU_WORKSPACE_HOST"

# Encabezado que Databricks Apps inyecta con el token OAuth del usuario logueado (OBO).
USER_TOKEN_HEADER = "x-forwarded-access-token"

# -----------------------------------------------------------------------------
# Recursos (parametrizables por variable de entorno; defaults = valores del workspace del curso).
# Bajo OBO, el SQL Warehouse igual se adjunta como recurso del App (el SP necesita CAN_USE en el
# COMPUTE del warehouse), pero las consultas se ejecutan con el token del usuario. Los serving
# endpoints NO necesitan adjunto/CAN_QUERY: el token del usuario (scope model-serving) autoriza
# la invocación.
# -----------------------------------------------------------------------------
WAREHOUSE_ID = os.environ.get("CR_WAREHOUSE_ID", "d788121d0edfbb7a")

# Schemas de Unity Catalog. Datos compartidos (solo lectura) en churn; datos personales y las dos
# funciones de UC en tu schema personal (CR_SCHEMA_PERSONAL).
CATALOG = os.environ.get("CR_CATALOG", "dbacademy")
SCHEMA_CHURN = os.environ.get("CR_SCHEMA_CHURN", "churn")
SCHEMA_PERSONAL = os.environ.get("CR_SCHEMA_PERSONAL", "tu_schema")

# Supervisor (Ej. 07) — enruta entre los Genies de Facturación y Soporte.
SUPERVISOR_ENDPOINT = os.environ.get("CR_SUPERVISOR_ENDPOINT", "mas-3d713414-endpoint")
# Foundation model para la "lectura de la IA" de los gráficos (✨ Explicar).
EXPLAIN_MODEL = os.environ.get("CR_EXPLAIN_MODEL", "databricks-claude-sonnet-4-5")
# Model service del Unity Gateway (catalogo.schema.nombre). Cuando está definido, las llamadas de
# chat del app (✨ Explicar y el e-mail de retención) pasan por el Gateway en vez del serving endpoint.
GATEWAY_MODEL = os.environ.get("CR_GATEWAY_MODEL", "").strip()


@lru_cache(maxsize=1)
def _workspace_client():
    """WorkspaceClient autenticado. Importación perezosa del SDK."""
    from databricks.sdk import WorkspaceClient

    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    return WorkspaceClient(profile=DATABRICKS_PROFILE)


def get_workspace_host() -> str:
    """Host del workspace CON esquema https://."""
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host or WORKSPACE_HOST_DEFAULT
    try:
        return _workspace_client().config.host or WORKSPACE_HOST_DEFAULT
    except Exception:
        return os.environ.get("CR_HOST", WORKSPACE_HOST_DEFAULT)


def get_workspace_token() -> Optional[str]:
    """Token bearer para las APIs REST (SQL Statements + serving endpoints).

    Trampa: en auth OAuth/U2M, `config.token` es None. Se recurre a `authenticate()`.
    """
    try:
        w = _workspace_client()
        if getattr(w.config, "token", None):
            return w.config.token
        headers = w.config.authenticate()
        if headers and "Authorization" in headers:
            return headers["Authorization"].replace("Bearer ", "")
    except Exception as exc:  # pragma: no cover
        print(f"[config] token del SDK no disponible ({exc}); intentando con la CLI")
    if not IS_DATABRICKS_APP:
        try:
            out = subprocess.run(
                ["databricks", "auth", "token", "-p", DATABRICKS_PROFILE],
                capture_output=True, text=True, check=True,
            ).stdout
            return json.loads(out)["access_token"]
        except Exception as exc:
            print(f"[config] no se pudo obtener el token mediante la CLI: {exc}")
    return None


def token_for_request(header_token: Optional[str]) -> Optional[str]:
    """Token a usar en las llamadas (SQL + serving).

    En el App: SIEMPRE el token del USUARIO logueado (X-Forwarded-Access-Token) — OBO. Si falta el
    encabezado en producción, devolvemos None (no caemos al SP, que no tiene grants; eso solo
    enmascararía el error). Local (fuera del App): usa el token del profile de la CLI (dev).
    """
    if header_token:
        return header_token
    if IS_DATABRICKS_APP:
        return None
    return get_workspace_token()


def summary() -> dict:
    """Diagnóstico legible del entorno, expuesto en /api/health."""
    return {
        "modo": "databricks_app" if IS_DATABRICKS_APP else "local",
        "auth": "on-behalf-of-user (X-Forwarded-Access-Token)",
        "profile": None if IS_DATABRICKS_APP else DATABRICKS_PROFILE,
        "host": get_workspace_host(),
        "warehouse_id": WAREHOUSE_ID,
        "catalog": CATALOG,
        "schema_churn": SCHEMA_CHURN,
        "schema_personal": SCHEMA_PERSONAL,
        "supervisor_endpoint": SUPERVISOR_ENDPOINT,
        "explain_model": EXPLAIN_MODEL,
    }
