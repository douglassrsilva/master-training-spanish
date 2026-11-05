"""
Pestaña 3 — Retención Personalizada.

  - /retencion/lista: los 12 clientes con mayor propensión a churn (nivel de riesgo Alto).
  - /retencion/email: llama a la función de UC get_cliente_360(id), que devuelve el perfil Y las
    ofertas ya calculadas en SQL (CASE: la regla de negocio queda gobernada en Unity Catalog). El
    texto del e-mail lo redacta el modelo del Unity Gateway (CR_GATEWAY_MODEL); la IA solo escribe.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .. import config, llm, warehouse
from ..warehouse import num

router = APIRouter()

CH = f"{config.CATALOG}.{config.SCHEMA_CHURN}"
PE = f"{config.CATALOG}.{config.SCHEMA_PERSONAL}"


def _user_token(request: Request):
    return config.token_for_request(request.headers.get(config.USER_TOKEN_HEADER))


@router.get("/retencion/lista")
async def lista(request: Request):
    rows = await warehouse.query(f"""
        SELECT s.id_cliente, c.nombre_cliente, c.ciudad, c.pais,
               floor(datediff(DATE '2026-09-23', c.fecha_registro)/365) anios,
               s.nombre_plan, round(s.prob_churn,3) prob, s.factor_principal
        FROM {PE}.churn_scores s JOIN {CH}.dim_cliente c USING(id_cliente)
        WHERE s.nivel_riesgo='Alto'
        ORDER BY s.prob_churn DESC
        LIMIT 12
    """, _user_token(request))
    clientes = [
        {
            "id": r.get("id_cliente"),
            "nombre": r.get("nombre_cliente"),
            "ciudad": r.get("ciudad"),
            "pais": r.get("pais"),
            "anios": int(num(r.get("anios"))),
            "plan": r.get("nombre_plan"),
            "prob": round(num(r.get("prob")) * 100),
            "factor": r.get("factor_principal"),
        }
        for r in rows
    ]
    return {"clientes": clientes}


class EmailReq(BaseModel):
    id_cliente: str


def _sanitizar_id(raw: str) -> str:
    """Solo letras/dígitos en mayúscula — evita inyección en el literal de la UC function."""
    return "".join(ch for ch in (raw or "").strip().upper() if ch.isalnum())[:16]


@router.post("/retencion/email")
async def email(req: EmailReq, request: Request):
    cid = _sanitizar_id(req.id_cliente)
    if not cid:
        return {"ok": False, "error": "ID inválido."}
    token = _user_token(request)
    rows = await warehouse.query(f"SELECT * FROM {PE}.get_cliente_360('{cid}')", token)
    if not rows:
        return {"ok": False, "error": "ID no encontrado en la base de riesgo."}
    perfil = rows[0]
    texto = await llm.redactar_email_retencion(perfil, token)
    if not texto:
        return {"ok": False, "error": "No fue posible generar el e-mail en este momento. Inténtalo de nuevo."}
    return {
        "ok": True,
        "id_cliente": cid,
        "email": texto,
        "ofertas": {k: perfil.get(k) for k in ("descuento", "oferta_internet", "oferta_factor")},
    }
