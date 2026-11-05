// Pestaña 2 — Asistente. Chat que llama al Supervisor (Ej. 07) vía /api/asistente/preguntar.
import { useEffect, useRef, useState } from "react";
import { api } from "../api";

type Msg = { de: "u" | "a"; texto: string; who?: string };

export function Asistente() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { de: "a", who: "Asistente", texto: "Puedo ayudarte con consultas sobre facturación y soporte de los clientes. ¿Qué quieres saber?" },
  ]);
  const [input, setInput] = useState("");
  const [cargando, setCargando] = useState(false);
  const finRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, cargando]);

  async function enviar() {
    const v = input.trim();
    if (!v || cargando) return;
    setMsgs((m) => [...m, { de: "u", texto: v }]);
    setInput("");
    setCargando(true);
    try {
      const r = await api.preguntar(v);
      setMsgs((m) => [...m, { de: "a", who: "Asistente · Supervisor", texto: r.respuesta }]);
    } catch (e) {
      setMsgs((m) => [...m, { de: "a", who: "Asistente", texto: "Falló la consulta al Supervisor. Inténtalo de nuevo." }]);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="panel">
      <div className="chat" style={{ marginBottom: 12 }}>
        <div className="hd">
          <span className="dot" /> Conectado al <b>&nbsp;Supervisor (Ej.07)</b> &nbsp;·&nbsp;
          endpoint <code>mas-3d713414-endpoint</code> &nbsp;·&nbsp; enruta entre los Genies de Facturación y Soporte
        </div>
        <div className="msgs">
          {msgs.map((m, i) => (
            <div className={`msg ${m.de}`} key={i}>
              {m.who && <div className="who">{m.who}</div>}
              {m.texto}
            </div>
          ))}
          {cargando && (
            <div className="msg a">
              <div className="who">Asistente · enrutando…</div>
              <span className="spin" /> &nbsp;consultando los Genies (Facturación / Soporte)…
            </div>
          )}
          <div ref={finRef} />
        </div>
        <div className="in">
          <input
            value={input}
            placeholder="Pregunta algo (ej.: NPS promedio por canal, facturas abiertas)…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && enviar()}
            disabled={cargando}
          />
          <button className="btn btn-primary" onClick={enviar} disabled={cargando}>Enviar</button>
        </div>
      </div>
      <p className="muted" style={{ fontSize: 12 }}>
        Cada mensaje llama al endpoint del Supervisor creado en el Ej.07
        (<code>/serving-endpoints/mas-3d713414-endpoint/invocations</code>).
      </p>
    </div>
  );
}
