// Pestaña 1 — Cockpit. KPIs + mapa de LATAM + panel de la región + 4 gráficos filtrables por región.
// Cada gráfico tiene un botón "✨ Explicar" que llama al foundation model con los datos actuales.
import { useEffect, useMemo, useState } from "react";
import { api, nf, pc, fmtDolares } from "../api";
import type { CockpitDatos, RegionDatos } from "../api";
import { MapaLatam } from "../components/MapaLatam";

const PLANES = ["Básico", "Estándar", "Premium", "Empresarial"];
const SEGS = ["Consumidor", "PyME", "Corporativo"];
const MESES = ["sep", "oct", "nov", "dic", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago"];
const MESESF = ["sep/24", "oct/24", "nov/24", "dic/24", "ene/25", "feb/25", "mar/25", "abr/25", "may/25", "jun/25", "jul/25", "ago/25"];

const argmin = (a: number[]) => a.indexOf(Math.min(...a));

function Bars({ labels, vals }: { labels: string[]; vals: number[] }) {
  const max = 40; // escala fija para comparar regiones
  const green = argmin(vals);
  return (
    <div>
      {labels.map((l, i) => {
        const w = Math.min(100, (vals[i] / max) * 100);
        return (
          <div className="hbar" key={l}>
            <div className="t"><span>{l}</span><b>{pc(vals[i])}</b></div>
            <div className="track">
              <div className={`fill ${i === green ? "g" : ""}`} style={{ width: `${w.toFixed(0)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Donut({ nivel }: { nivel: RegionDatos["nivel"] }) {
  const tot = nivel.Alto + nivel.Medio + nivel.Bajo || 1;
  const p1 = (nivel.Alto / tot) * 100;
  const p2 = ((nivel.Alto + nivel.Medio) / tot) * 100;
  const bg = `conic-gradient(var(--orange) 0 ${p1}%, var(--amber) ${p1}% ${p2}%, var(--green) ${p2}% 100%)`;
  return (
    <div className="donut-wrap">
      <div className="donut" style={{ background: bg }}>
        <div className="hole"><div><b>{nf(nivel.Alto)}</b><span>riesgo Alto</span></div></div>
      </div>
      <div className="legend">
        <div className="lg"><span className="sw" style={{ background: "var(--orange)" }} />🔴 Alto — {nf(nivel.Alto)} ({Math.round((nivel.Alto / tot) * 100)}%)</div>
        <div className="lg"><span className="sw" style={{ background: "var(--amber)" }} />🟡 Medio — {nf(nivel.Medio)} ({Math.round((nivel.Medio / tot) * 100)}%)</div>
        <div className="lg"><span className="sw" style={{ background: "var(--green)" }} />🟢 Bajo — {nf(nivel.Bajo)} ({Math.round((nivel.Bajo / tot) * 100)}%)</div>
      </div>
    </div>
  );
}

function Line({ data }: { data: number[] }) {
  const W = 480, H = 160, padX = 26, padT = 16, padB = 26;
  const max = Math.max(...data, 1);
  const x = (i: number) => padX + (i * (W - 2 * padX)) / (data.length - 1);
  const y = (v: number) => padT + (1 - v / max) * (H - padT - padB);
  const pts = data.map((v, i) => [x(i), y(v)] as [number, number]);
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = line + ` L ${x(data.length - 1).toFixed(1)} ${H - padB} L ${x(0).toFixed(1)} ${H - padB} Z`;
  const peak = data.indexOf(max);
  return (
    <svg className="line-chart" viewBox="0 0 480 160" role="img">
      <defs>
        <linearGradient id="ar" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#FF3621" stopOpacity=".18" />
          <stop offset="1" stopColor="#FF3621" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#ar)" />
      <path d={line} fill="none" stroke="#FF3621" strokeWidth={2.2} strokeLinejoin="round" />
      {pts.map((p, i) => (
        <circle key={i} cx={p[0].toFixed(1)} cy={p[1].toFixed(1)} r={i === peak ? 4 : 2.5}
          fill={i === peak ? "#FF3621" : "#fff"} stroke="#FF3621" strokeWidth={2} />
      ))}
      <text x={x(peak).toFixed(1)} y={(y(max) - 9).toFixed(1)} fontSize={10} fontWeight={700} fill="#FF3621" textAnchor="middle">{max}</text>
      {MESES.map((l, i) => (
        <text key={l} x={x(i).toFixed(1)} y={H - 8} fontSize={9} fill="#9AA0AA" textAnchor="middle">{l}</text>
      ))}
    </svg>
  );
}

type ChartId = "plan" | "nivel" | "meses" | "seg";

function VizCard({
  tag, titulo, grafico, region, datosIA, children,
}: {
  tag: "retro" | "prev"; titulo: string; grafico: ChartId; region: string; datosIA: any; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [texto, setTexto] = useState("");

  // al cambiar de región, invalida la lectura; si está abierta, la recarga.
  useEffect(() => {
    setTexto("");
    if (open) fetchTexto();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region]);

  async function fetchTexto() {
    setLoading(true);
    try {
      const r = await api.explicar(grafico, region, datosIA);
      setTexto(r.texto);
    } catch {
      setTexto("No fue posible generar la lectura de la IA en este momento.");
    } finally {
      setLoading(false);
    }
  }

  function toggle() {
    const nuevo = !open;
    setOpen(nuevo);
    if (nuevo && !texto && !loading) fetchTexto();
  }

  return (
    <div className="viz">
      <div className="viz-hd">
        <div>
          <span className={`viz-tag ${tag}`}>{tag === "retro" ? "Retrospectiva" : "Predicción"}</span>
          <h3>{titulo}</h3>
        </div>
        <button className={`ai-btn ${open ? "on" : ""}`} onClick={toggle}>
          {open ? "✨ Ocultar" : "✨ Explicar"}
        </button>
      </div>
      {children}
      {open && (
        <div className="ai-exp">
          <div className="who">✨ Lectura de la IA</div>
          <span>{loading ? <><span className="spin" /> &nbsp;generando lectura…</> : texto}</span>
        </div>
      )}
    </div>
  );
}

export function Cockpit() {
  const [datos, setDatos] = useState<CockpitDatos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reg, setReg] = useState("LATAM");

  useEffect(() => {
    api.cockpitDatos().then(setDatos).catch((e) => setError(String(e)));
  }, []);

  const d: RegionDatos | null = useMemo(() => (datos ? datos.D[reg] : null), [datos, reg]);

  if (error) return <div className="panel"><p className="muted">Error al cargar los datos: {error}</p></div>;
  if (!datos || !d) return <div className="panel"><p className="muted"><span className="spin" /> &nbsp;Cargando panorama de churn…</p></div>;

  const kpi = datos.kpi;
  const tasa = d.clientes ? (d.riesgo / d.clientes) * 100 : 0;
  const nombreReg = reg === "LATAM" ? "LATAM — todas las regiones" : `Región ${reg}`;

  return (
    <div className="panel">
      <div className="cockpit-hd">
        <h2>Panorama de Churn</h2>
        <p>Selecciona una región en el mapa para ver los números y filtrar los gráficos. Cada gráfico tiene una lectura por IA ✨.</p>
      </div>

      <div className="kpi-grid">
        <div className="kpi" style={{ ["--accent" as any]: "var(--orange)", ["--soft" as any]: "#FFF0ED" }}>
          <div className="ic">📉</div><div className="lbl">Churn histórico</div>
          <div className="val">{kpi.churn_pct}%</div>
          <div className="foot">{nf(2000)} suscripciones <span className="chip up">LATAM</span></div>
        </div>
        <div className="kpi" style={{ ["--accent" as any]: "var(--orange)", ["--soft" as any]: "#FFF0ED" }}>
          <div className="ic">⚠️</div><div className="lbl">En riesgo Alto</div>
          <div className="val">{nf(kpi.riesgo_alto)}</div>
          <div className="foot">prob. promedio 82%</div>
        </div>
        <div className="kpi" style={{ ["--accent" as any]: "var(--amber)", ["--soft" as any]: "#FFF6E6" }}>
          <div className="ic">💰</div><div className="lbl">MRR en riesgo</div>
          <div className="val">{fmtDolares(kpi.mrr_riesgo)}</div>
          <div className="foot">ingreso mensual en juego</div>
        </div>
        <div className="kpi" style={{ ["--accent" as any]: "var(--green)", ["--soft" as any]: "#E7F5EF" }}>
          <div className="ic">🎯</div><div className="lbl">Calidad del modelo</div>
          <div className="val">AUC {kpi.auc}</div>
          <div className="foot">Predicción de Churn (Ej.06) <span className="chip ok">bueno</span></div>
        </div>
      </div>

      <div className="map-row">
        <div className="map-card">
          <h3>Clientes por región</h3>
          <MapaLatam D={datos.D} seleccionada={reg} onSelect={setReg} />
          <div className="map-scale">
            <span>menos</span>
            <i style={{ background: "#FED2C9" }} /><i style={{ background: "#FCB4A6" }} />
            <i style={{ background: "#F98C79" }} /><i style={{ background: "#F2604A" }} />
            <i style={{ background: "#E8412B" }} />
            <span>+ en riesgo</span>
          </div>
        </div>
        <div className="region-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0 }}>Región seleccionada</h3>
            <button className="reset" onClick={() => setReg("LATAM")}>🌎 LATAM (todas)</button>
          </div>
          <div className="big">{nombreReg}</div>
          <div className="rstat">
            <div><div className="n">{nf(d.clientes)}</div><div className="k">clientes</div></div>
            <div><div className="n red">{nf(d.riesgo)}</div><div className="k">en riesgo Alto</div></div>
            <div><div className="n">{pc(tasa)}</div><div className="k">tasa de riesgo</div></div>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "12px 0 0" }}>
            {reg === "LATAM"
              ? "Los cuatro gráficos de abajo muestran LATAM completo. Haz clic en una región del mapa para filtrar."
              : `Los cuatro gráficos de abajo están filtrados para la región ${reg}.`}
          </p>
        </div>
      </div>

      <p className="filter-cap">
        Mostrando: <b>{reg === "LATAM" ? "LATAM — todas las regiones" : reg}</b>
        {reg !== "LATAM" && (
          <button className="reset" onClick={() => setReg("LATAM")}>✕ limpiar filtro</button>
        )}
      </p>

      <div className="viz-grid">
        <VizCard tag="retro" titulo="Churn por plan" grafico="plan" region={reg}
          datosIA={{ planes: PLANES, churn_pct: d.plan }}>
          <Bars labels={PLANES} vals={d.plan} />
        </VizCard>

        <VizCard tag="prev" titulo="Clientes por nivel de riesgo" grafico="nivel" region={reg}
          datosIA={d.nivel}>
          <Donut nivel={d.nivel} />
        </VizCard>

        <VizCard tag="retro" titulo="Cancelaciones por mes" grafico="meses" region={reg}
          datosIA={{ meses: MESESF, cancelaciones: d.meses }}>
          <Line data={d.meses} />
        </VizCard>

        <VizCard tag="retro" titulo="Churn por segmento" grafico="seg" region={reg}
          datosIA={{ segmentos: SEGS, churn_pct: d.seg }}>
          <Bars labels={SEGS} vals={d.seg} />
        </VizCard>
      </div>
    </div>
  );
}
