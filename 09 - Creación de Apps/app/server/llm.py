"""
Capa de IA de la app. Dos consumidores, ambos endpoints de serving del workspace, llamados con el
TOKEN DEL USUARIO logueado (OBO) — que pasan las rutas. Eso es lo que hace que el Supervisor
enrute como el usuario (que es dueño de los Genies), sin necesitar CAN_QUERY/CAN_RUN en el
service principal.

  1. supervisor_ask(): el Supervisor del Ej. 07 (mas-...-endpoint). Formato de "Responses API":
     body {"input":[{role,content}]}, y la respuesta final es el ÚLTIMO ítem `message` del arreglo
     `output` (los ítems intermedios son tool_calls y ecos con <name>...</name> del enrutamiento).

  2. explicar_grafico(): un foundation model (databricks-claude-sonnet-4-5) en el formato estándar
     de chat completions (/serving-endpoints/<modelo>/invocations), para la "lectura de la IA" de
     cada gráfico del cockpit. Respuesta corta (1-2 frases en español).

Degradación controlada: cualquier falla devuelve None / un texto de respaldo.
"""
from __future__ import annotations

import json
import os
import ssl
from functools import lru_cache
from typing import Optional

import aiohttp

from . import config


@lru_cache(maxsize=1)
def _ssl_context() -> Optional[ssl.SSLContext]:
    for ruta in (os.environ.get("SSL_CERT_FILE"), "/etc/ssl/cert.pem"):
        if ruta and os.path.exists(ruta):
            try:
                return ssl.create_default_context(cafile=ruta)
            except Exception:
                pass
    return None


def _connector():
    ctx = _ssl_context()
    return aiohttp.TCPConnector(ssl=ctx) if ctx else None


def _texto_del_contenido(contenido) -> str:
    """Extrae el texto de un contenido que puede ser string o lista de bloques."""
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, dict):
                partes.append(bloque.get("text") or bloque.get("content") or "")
        return "".join(partes)
    return str(contenido or "")


# -----------------------------------------------------------------------------
# 1. Supervisor (Ej. 07) — Responses API
# -----------------------------------------------------------------------------
async def supervisor_ask(pregunta: str, token: Optional[str]) -> Optional[str]:
    """Envía la pregunta al Supervisor (como el usuario) y devuelve el texto de la respuesta final."""
    if not token:
        return None
    host = config.get_workspace_host()
    url = f"{host}/serving-endpoints/{config.SUPERVISOR_ENDPOINT}/invocations"
    payload = {"input": [{"role": "user", "content": pregunta}]}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        timeout = aiohttp.ClientTimeout(total=240)
        async with aiohttp.ClientSession(timeout=timeout, connector=_connector()) as sess:
            async with sess.post(url, json=payload, headers=headers) as rr:
                txt = await rr.text()
                if rr.status != 200:
                    print(f"[supervisor] HTTP {rr.status}: {txt[:300]}")
                    return None
                data = json.loads(txt)
                return _extraer_respuesta_final(data)
    except Exception as exc:
        print(f"[supervisor] no disponible: {exc}")
        return None


def _extraer_respuesta_final(data: dict) -> Optional[str]:
    """La respuesta final es el último ítem `message`/assistant cuyo texto no es un eco <name>."""
    output = data.get("output") or []
    candidatos = []
    for item in output:
        if item.get("type") != "message":
            continue
        texto = _texto_del_contenido(item.get("content")).strip()
        if not texto or texto.startswith("<name>"):
            continue
        candidatos.append(texto)
    if candidatos:
        return candidatos[-1]
    # respaldo: algunos formatos traen el texto directamente
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    return None


# -----------------------------------------------------------------------------
# 2. Foundation model — chat completions (lectura de los gráficos)
# -----------------------------------------------------------------------------
async def _chat(system: str, user: str, token: Optional[str], max_tokens: int = 220,
                timeout_s: int = 45) -> Optional[str]:
    if not token:
        return None
    host = config.get_workspace_host()
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    if config.GATEWAY_MODEL:
        # Unity Gateway: API unificada (compatible con OpenAI); el model service va en el campo `model`.
        url = f"{host}/ai-gateway/mlflow/v1/chat/completions"
        payload["model"] = config.GATEWAY_MODEL
    else:
        url = f"{host}/serving-endpoints/{config.EXPLAIN_MODEL}/invocations"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with aiohttp.ClientSession(timeout=timeout, connector=_connector()) as sess:
            async with sess.post(url, json=payload, headers=headers) as rr:
                txt = await rr.text()
                if rr.status != 200:
                    print(f"[chat] HTTP {rr.status}: {txt[:300]}")
                    return None
                d = json.loads(txt)
                return _texto_del_contenido(d["choices"][0]["message"]["content"]).strip()
    except Exception as exc:
        print(f"[explicar] no disponible: {exc}")
        return None


async def explicar_grafico(grafico: str, region: str, datos: dict, token: Optional[str]) -> str:
    """Lectura en 1-2 frases en español de un gráfico del cockpit, a partir de los datos actuales."""
    donde = "en LATAM (todas las regiones)" if region == "LATAM" else f"en la región {region}"
    contexto = {
        "plan": "Churn (%) por plan de suscripción",
        "nivel": "Distribución de clientes por nivel de riesgo de churn (Alto/Medio/Bajo)",
        "meses": "Cancelaciones de suscripción por mes (sep/24 a ago/25)",
        "seg": "Churn (%) por segmento de cliente (Consumidor/PyME/Corporativo)",
    }.get(grafico, grafico)
    system = (
        "Eres un analista de retención (Customer Success) de una empresa de telecomunicaciones. "
        "Explicas gráficos de churn a un gerente, en español latinoamericano, de forma directa "
        "y accionable. Responde en COMO MÁXIMO 2 frases cortas. No uses markdown ni listas. "
        "Cita los números más relevantes y una recomendación práctica."
    )
    user = (
        f"Gráfico: {contexto}, {donde}.\n"
        f"Datos (JSON): {json.dumps(datos, ensure_ascii=False)}\n"
        "Escribe la lectura del gráfico."
    )
    # Margen de tokens: los modelos de razonamiento (ej.: gpt-oss) gastan parte del límite pensando.
    resp = await _chat(system, user, token, max_tokens=600)
    return resp or "No fue posible generar la lectura de la IA en este momento. Inténtalo de nuevo."


async def redactar_email_retencion(perfil: dict, token: Optional[str]) -> Optional[str]:
    """Redacta el e-mail de retención. Las OFERTAS ya vienen calculadas por la UC function
    get_cliente_360 (regla de negocio en SQL); la IA solo escribe el texto."""
    system = (
        "Eres un especialista en retención de clientes de una empresa de suscripción. "
        "Redacta un e-mail profesional y empático en español latinoamericano para convencer al "
        "cliente de permanecer. Ofrece EXACTAMENTE las ofertas indicadas, sin inventar otras y "
        "sin cambiar valores. No menciones el sector de la empresa. Comienza con el saludo (no "
        "incluyas línea de asunto) y escribe en texto simple, sin markdown: sin asteriscos, sin listas."
    )
    user = (
        f"Datos: Nombre: {perfil.get('nombre_cliente')}, Ciudad: {perfil.get('ciudad')}, "
        f"Años como cliente: {perfil.get('anios_como_cliente')}. "
        f"Ofertas: (a) descuento de {perfil.get('descuento')} en la mensualidad; "
        f"(b) {perfil.get('oferta_internet')}; (c) {perfil.get('oferta_factor')}. "
        "Menciona el nombre, la ciudad y los años como cliente, e incluye las tres ofertas de forma natural."
    )
    return await _chat(system, user, token, max_tokens=1500, timeout_s=120)


async def ping() -> dict:
    return {
        "supervisor": config.SUPERVISOR_ENDPOINT,
        "explain_model": config.EXPLAIN_MODEL,
        "gateway_model": config.GATEWAY_MODEL or None,
    }
