"""
Central de Retención — entrypoint FastAPI (Master Training / churn).

Sirve la API (/api/*) y el build de React (frontend/dist). Tres pestañas: Cockpit (mapa + gráficos),
Asistente (Supervisor, Ej. 07) y Retención Personalizada (lista de riesgo + e-mail vía función de UC).
Todos los datos vienen de Unity Catalog mediante un SQL Warehouse; la IA, de dos serving endpoints.

Local:  uv run uvicorn app:app --reload --port 8000
Remoto: definido en app.yaml (uvicorn en el puerto 8000).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server import config, llm, warehouse
from server.routes import assistente, cockpit, retencion

FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

app = FastAPI(title="Central de Retención")

app.include_router(cockpit.router, prefix="/api")
app.include_router(assistente.router, prefix="/api")
app.include_router(retencion.router, prefix="/api")


@app.get("/api/health")
async def health(request: Request):
    """Salud + diagnóstico OBO: confirma que llegó el encabezado del usuario y muestra CON QUIÉN se
    ejecutan las consultas (current_user()) — debe ser el usuario logueado, no el service principal."""
    hdr = request.headers.get(config.USER_TOKEN_HEADER)
    token = config.token_for_request(hdr)
    obo = {"encabezado_usuario_presente": bool(hdr)}
    try:
        rows = await warehouse.query("SELECT current_user() AS u", token)
        obo["consulta_ok"] = bool(rows)
        obo["consulta_corre_como"] = rows[0].get("u") if rows else None
    except Exception as exc:  # pragma: no cover
        obo["consulta_ok"] = False
        obo["error"] = str(exc)[:200]
    return {
        "app": "central-retencion",
        "ambiente": config.summary(),
        "obo": obo,
        "ia": await llm.ping(),
    }


# -----------------------------------------------------------------------------
# Frontend (SPA). En dev, Vite sirve en el 5173 con proxy /api -> 8000.
# -----------------------------------------------------------------------------
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"error": "ruta no encontrada"}, status_code=404)
        archivo = FRONTEND_DIST / full_path
        if full_path and archivo.is_file():
            return FileResponse(archivo)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def sin_build():
        return JSONResponse(
            {"aviso": "frontend/dist no construido. Ejecuta `npm run build` en frontend/.",
             "health": "/api/health"}
        )
