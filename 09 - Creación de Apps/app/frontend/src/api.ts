// Cliente HTTP liviano. En dev, Vite hace proxy de /api -> :8000; en producción el propio
// FastAPI sirve SPA + API, así que las rutas relativas funcionan.

export type RegionDatos = {
  clientes: number;
  riesgo: number;
  plan: number[];
  nivel: { Alto: number; Medio: number; Bajo: number };
  seg: number[];
  meses: number[];
};
export type CockpitDatos = {
  D: Record<string, RegionDatos>;
  kpi: { churn_pct: number; riesgo_alto: number; mrr_riesgo: number; auc: string };
};
export type Cliente = {
  id: string; nombre: string; ciudad: string; pais: string;
  anios: number; plan: string; prob: number; factor: string;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<any>("/health"),
  cockpitDatos: () => req<CockpitDatos>("/cockpit/datos"),
  explicar: (grafico: string, region: string, datos: any) =>
    req<{ texto: string }>("/cockpit/explicar", {
      method: "POST",
      body: JSON.stringify({ grafico, region, datos }),
    }),
  preguntar: (pregunta: string) =>
    req<{ respuesta: string; ok: boolean }>("/asistente/preguntar", {
      method: "POST",
      body: JSON.stringify({ pregunta }),
    }),
  retencionLista: () => req<{ clientes: Cliente[] }>("/retencion/lista"),
  generarEmail: (id_cliente: string) =>
    req<{ ok: boolean; email?: string; error?: string; id_cliente?: string }>(
      "/retencion/email",
      { method: "POST", body: JSON.stringify({ id_cliente }) }
    ),
};

// Formatos en español latinoamericano (es-419): separador decimal ".", moneda en US$.
export const nf = (n: number) => n.toLocaleString("es-419");
export const pc = (n: number) =>
  n.toLocaleString("es-419", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
export const fmtDolares = (n: number) =>
  new Intl.NumberFormat("es-419", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
