"""
Lectura de Unity Catalog con la identidad del USUARIO logueado (OBO).

Usa el `databricks-sql-connector` (camino de datos del SQL Warehouse,
`/sql/1.0/warehouses/<id>`) — y NO la REST `/api/2.0/sql/statements`. Motivo: el token OAuth
del usuario que pasa Databricks Apps (X-Forwarded-Access-Token) está *down-scoped* a los scopes
del app (`sql`); ese token autoriza el conector SQL (patrón OBO documentado), pero la REST de
Statement Execution devuelve vacío con él. El conector es síncrono; lo ejecutamos en un thread
para no bloquear las rutas async. Degradación controlada: error o token ausente -> lista vacía.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from . import config


def _run_query(sql: str, token: str, host: str, warehouse_id: str) -> list[dict]:
    from databricks import sql as dbsql

    hostname = host.replace("https://", "").replace("http://", "").rstrip("/")
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"
    conn = dbsql.connect(server_hostname=hostname, http_path=http_path, access_token=token)
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            cols = [c[0] for c in cur.description] if cur.description else []
            return [dict(zip(cols, list(row))) for row in cur.fetchall()]
        finally:
            cur.close()
    finally:
        conn.close()


async def query(sql: str, token: Optional[str]) -> list[dict]:
    """Ejecuta un SELECT en el warehouse COMO EL USUARIO y devuelve una lista de dicts."""
    if not token:
        print("[warehouse] sin token de usuario; devolviendo vacío")
        return []
    try:
        return await asyncio.to_thread(
            _run_query, sql, token, config.get_workspace_host(), config.WAREHOUSE_ID
        )
    except Exception as exc:
        causa = exc.__cause__ or exc.__context__
        print(f"[warehouse] error: {type(exc).__name__}: {exc} | causa: {type(causa).__name__ if causa else None}: {str(causa)[:300] if causa else ''}")
        return []


def num(v) -> float:
    """Convierte un valor a float de forma segura (el conector puede devolver Decimal/int/str)."""
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
