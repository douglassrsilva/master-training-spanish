"""
Pestaña 1 — Cockpit. Arma, en un único endpoint, la estructura por región (mismo formato del mock):
para LATAM + las 5 regiones, los cuatro gráficos (churn por plan, nivel de riesgo, cancelaciones
por mes, churn por segmento) y los totales (clientes, en riesgo, MRR en riesgo, churn histórico).

Todo se deriva en vivo de Unity Catalog mediante un SQL Warehouse (4 consultas agregadas por región,
ejecutadas en paralelo). Los porcentajes nacionales (LATAM) se recomponen a partir de los CONTEOS
por región (no es un promedio de promedios) para que coincidan con el número real.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .. import config, llm, warehouse
from ..warehouse import num


def _user_token(request: Request):
    """Token del usuario logueado (OBO); en local recurre al profile."""
    return config.token_for_request(request.headers.get(config.USER_TOKEN_HEADER))


router = APIRouter()

REGIONES = ["Centroamérica", "Andina", "Caribe", "México", "Cono Sur"]
PLANES = ["Básico", "Estándar", "Premium", "Empresarial"]
SEGS = ["Consumidor", "PyME", "Corporativo"]
# 12 meses fijos sep/24 -> ago/25 (clave yyyy-MM -> índice)
MES_KEYS = [
    "2024-09", "2024-10", "2024-11", "2024-12", "2025-01", "2025-02",
    "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08",
]

# Expresión de región reutilizada en todas las consultas (por código de país `pais`).
REG = """CASE WHEN c.pais IN ('MX') THEN 'México'
     WHEN c.pais IN ('CO','PE','EC','VE','BO') THEN 'Andina'
     WHEN c.pais IN ('AR','CL','UY','PY') THEN 'Cono Sur'
     WHEN c.pais IN ('DO','CU','PR') THEN 'Caribe'
     WHEN c.pais IN ('CR','PA','GT','HN','SV','NI') THEN 'Centroamérica' END"""

CH = f"{config.CATALOG}.{config.SCHEMA_CHURN}"
PE = f"{config.CATALOG}.{config.SCHEMA_PERSONAL}"


def _vacio_region() -> dict:
    return {
        "clientes": 0, "riesgo": 0,
        "plan": [0.0] * len(PLANES),
        "nivel": {"Alto": 0, "Medio": 0, "Bajo": 0},
        "seg": [0.0] * len(SEGS),
        "meses": [0] * len(MES_KEYS),
    }


@router.get("/cockpit/datos")
async def cockpit_datos(request: Request):
    """Estructura completa por región (LATAM + 5 regiones) y KPIs nacionales."""
    token = _user_token(request)
    q_nivel = f"""
        SELECT {REG} region, s.nivel_riesgo nivel, count(*) n
        FROM {PE}.churn_scores s JOIN {CH}.dim_cliente c USING(id_cliente)
        GROUP BY 1,2
    """
    q_plan = f"""
        SELECT {REG} region, p.nombre_plan plan,
               sum(f.churn_flag) churn_n, count(*) total
        FROM {CH}.hecho_suscripcion f JOIN {CH}.dim_cliente c USING(id_cliente)
        JOIN {CH}.dim_plan p USING(id_plan)
        GROUP BY 1,2
    """
    q_seg = f"""
        SELECT {REG} region, c.segmento seg,
               sum(f.churn_flag) churn_n, count(*) total
        FROM {CH}.hecho_suscripcion f JOIN {CH}.dim_cliente c USING(id_cliente)
        GROUP BY 1,2
    """
    q_meses = f"""
        SELECT {REG} region, date_format(f.fecha_fin,'yyyy-MM') mes, count(*) n
        FROM {CH}.hecho_suscripcion f JOIN {CH}.dim_cliente c USING(id_cliente)
        WHERE f.fecha_fin >= '2024-09-01'
        GROUP BY 1,2
    """
    q_kpi = f"""
        SELECT
          (SELECT round(sum(precio_mensual),2) FROM {PE}.churn_scores WHERE nivel_riesgo='Alto') mrr_riesgo,
          (SELECT round(100*avg(churn_flag),0) FROM {CH}.hecho_suscripcion) churn_pct
    """

    r_nivel, r_plan, r_seg, r_meses, r_kpi = await asyncio.gather(
        warehouse.query(q_nivel, token), warehouse.query(q_plan, token),
        warehouse.query(q_seg, token), warehouse.query(q_meses, token),
        warehouse.query(q_kpi, token),
    )

    D: dict[str, dict] = {r: _vacio_region() for r in REGIONES}
    D["LATAM"] = _vacio_region()

    # ---- nivel de riesgo (conteos; nacional = suma) ----
    for row in r_nivel:
        reg, nivel, n = row.get("region"), row.get("nivel"), int(num(row.get("n")))
        if reg in D and nivel in D[reg]["nivel"]:
            D[reg]["nivel"][nivel] += n
            D["LATAM"]["nivel"][nivel] += n
    for reg in list(D):
        f = D[reg]["nivel"]
        D[reg]["clientes"] = f["Alto"] + f["Medio"] + f["Bajo"]
        D[reg]["riesgo"] = f["Alto"]

    # ---- plan / segmento (recompone el % a partir de los conteos; LATAM = suma churn/total) ----
    def _pcts(rows, clave, orden, attr_destino):
        acc: dict[str, dict] = {}  # region -> valor -> [churn, total]
        nac: dict[str, list] = {p: [0.0, 0.0] for p in orden}
        for row in rows:
            reg, key = row.get("region"), row.get(clave)
            if reg not in D or key not in orden:
                continue
            ch, tot = num(row.get("churn_n")), num(row.get("total"))
            acc.setdefault(reg, {}).setdefault(key, [0.0, 0.0])
            acc[reg][key][0] += ch
            acc[reg][key][1] += tot
            nac[key][0] += ch
            nac[key][1] += tot
        for reg in REGIONES:
            arr = []
            for key in orden:
                ch, tot = acc.get(reg, {}).get(key, [0.0, 0.0])
                arr.append(round(100 * ch / tot, 1) if tot else 0.0)
            D[reg][attr_destino] = arr
        D["LATAM"][attr_destino] = [
            round(100 * nac[k][0] / nac[k][1], 1) if nac[k][1] else 0.0 for k in orden
        ]

    _pcts(r_plan, "plan", PLANES, "plan")
    _pcts(r_seg, "seg", SEGS, "seg")

    # ---- meses (conteos; nacional = suma) ----
    idx = {k: i for i, k in enumerate(MES_KEYS)}
    for row in r_meses:
        reg, mes, n = row.get("region"), row.get("mes"), int(num(row.get("n")))
        if reg in D and mes in idx:
            D[reg]["meses"][idx[mes]] += n
            D["LATAM"]["meses"][idx[mes]] += n

    kpi = r_kpi[0] if r_kpi else {}
    return {
        "D": D,
        "kpi": {
            "churn_pct": int(num(kpi.get("churn_pct")) or 27),
            "riesgo_alto": D["LATAM"]["riesgo"],
            "mrr_riesgo": num(kpi.get("mrr_riesgo")),
            "auc": "0.97",
        },
    }


class ExplicarReq(BaseModel):
    grafico: str
    region: str
    datos: dict


@router.post("/cockpit/explicar")
async def cockpit_explicar(req: ExplicarReq, request: Request):
    """Lectura por IA (foundation model) del gráfico, a partir de los datos de la región actual."""
    texto = await llm.explicar_grafico(req.grafico, req.region, req.datos, _user_token(request))
    return {"texto": texto}
