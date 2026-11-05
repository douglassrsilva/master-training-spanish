// Pestaña 3 — Retención Personalizada. Lista de riesgo (UC) + e-mail generado por la función de UC
// generar_email_retencion(id). "Enviar a CRM" saca al cliente de la lista (estado local del demo).
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Cliente } from "../api";

export function Retencion() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [input, setInput] = useState("");
  const [generando, setGenerando] = useState(false);
  const [actual, setActual] = useState<{ id: string; email: string; cliente?: Cliente } | null>(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    api.retencionLista().then((r) => setClientes(r.clientes)).catch(() => setClientes([]));
  }, []);

  function mostrarToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 3200);
  }

  async function generar(idArg?: string) {
    const id = (idArg ?? input).trim().toUpperCase();
    if (!id) return;
    setGenerando(true);
    setActual(null);
    try {
      const r = await api.generarEmail(id);
      if (!r.ok || !r.email) {
        mostrarToast(r.error || "ID no encontrado en la lista de riesgo.");
      } else {
        const cliente = clientes.find((c) => c.id === r.id_cliente);
        setActual({ id: r.id_cliente || id, email: r.email, cliente });
        setInput(r.id_cliente || id);
      }
    } catch {
      mostrarToast("Falló la generación del e-mail. Inténtalo de nuevo.");
    } finally {
      setGenerando(false);
    }
  }

  function enviarCrm() {
    if (!actual) return;
    const nombre = actual.cliente?.nombre || actual.id;
    setClientes((cs) => cs.filter((c) => c.id !== actual.id));
    mostrarToast(`E-mail de ${nombre} enviado al CRM ✓ — el cliente salió de la lista de riesgo.`);
    setActual(null);
    setInput("");
  }

  return (
    <div className="panel">
      <div className="search">
        <input
          value={input}
          placeholder="Pega el ID de un cliente de la lista de abajo (ej.: C01575)"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generar()}
        />
        <button className="btn btn-primary" onClick={() => generar()} disabled={generando}>
          {generando ? <><span className="spin" /> &nbsp;Generando…</> : "🎯 Retención Personalizada"}
        </button>
        <span className="muted" style={{ fontSize: 12 }}>Consejo: también puedes hacer clic en una fila de la lista.</span>
      </div>

      {actual && (
        <div className="email">
          <div className="meta">
            <span><b>Para:</b> {actual.cliente?.nombre || actual.id} &lt;{actual.id.toLowerCase()}@cliente.com&gt;</span>
            <span><b>Asunto:</b> Una oferta especial para que sigas con nosotros</span>
          </div>
          <pre>{actual.email}</pre>
          <div className="act">
            <button className="btn btn-crm" onClick={enviarCrm}>📤 Enviar a CRM</button>
            <span className="muted" style={{ fontSize: 12 }}>
              Ofertas de <code>get_cliente_360('{actual.id}')</code> · texto por el Unity Gateway
            </span>
          </div>
        </div>
      )}

      <div style={{ marginTop: 18 }}>
        <h2>Clientes con mayor propensión a churn &nbsp;<span className="muted">({clientes.length})</span></h2>
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Cliente</th><th>Ciudad</th><th>Antigüedad</th>
              <th>Plan</th><th>Prob. churn</th><th>Motivo principal</th>
            </tr>
          </thead>
          <tbody>
            {clientes.map((c) => (
              <tr key={c.id} onClick={() => { setInput(c.id); generar(c.id); }}>
                <td><b>{c.id}</b></td>
                <td>{c.nombre}</td>
                <td>{c.ciudad}/{c.pais}</td>
                <td>{c.anios} años</td>
                <td>{c.plan}</td>
                <td><span className="pill">{c.prob}%</span></td>
                <td><span className="tag">{c.factor}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className={`toast ${toast ? "show" : ""}`}>{toast}</div>
    </div>
  );
}
