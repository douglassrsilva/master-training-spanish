// Central de Retención — shell con 3 pestañas: Cockpit, Asistente, Retención Personalizada.
import { useState } from "react";
import { Cockpit } from "./modos/Cockpit";
import { Asistente } from "./modos/Asistente";
import { Retencion } from "./modos/Retencion";

type Pestana = "cockpit" | "asistente" | "retencion";

const PESTANAS: { id: Pestana; etiqueta: string }[] = [
  { id: "cockpit", etiqueta: "📊 Cockpit" },
  { id: "asistente", etiqueta: "💬 Asistente" },
  { id: "retencion", etiqueta: "🎯 Retención Personalizada" },
];

export default function App() {
  const [pestana, setPestana] = useState<Pestana>("cockpit");
  return (
    <div>
      <header className="app-header">
        <div className="logo">CR</div>
        <h1>Central de Retención</h1>
        <span className="sub">Master Training · Análisis de Churn</span>
      </header>

      <div className="tabs">
        {PESTANAS.map((p) => (
          <button key={p.id} className={`tab ${pestana === p.id ? "active" : ""}`} onClick={() => setPestana(p.id)}>
            {p.etiqueta}
          </button>
        ))}
      </div>

      <main>
        {pestana === "cockpit" && <Cockpit />}
        {pestana === "asistente" && <Asistente />}
        {pestana === "retencion" && <Retencion />}
      </main>
    </div>
  );
}
