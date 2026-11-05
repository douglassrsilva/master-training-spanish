"""Pestaña 2 — Asistente. Envía la pregunta al Supervisor (Ej. 07) y devuelve la respuesta."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .. import config, llm

router = APIRouter()


class PreguntaReq(BaseModel):
    pregunta: str


@router.post("/asistente/preguntar")
async def preguntar(req: PreguntaReq, request: Request):
    pregunta = (req.pregunta or "").strip()
    if not pregunta:
        return {"respuesta": "Escribe una pregunta.", "ok": False}
    token = config.token_for_request(request.headers.get(config.USER_TOKEN_HEADER))
    respuesta = await llm.supervisor_ask(pregunta, token)
    if not respuesta:
        return {
            "respuesta": "El Supervisor no respondió en este momento (puede estar en cold start). Inténtalo de nuevo.",
            "ok": False,
        }
    return {"respuesta": respuesta, "ok": True}
