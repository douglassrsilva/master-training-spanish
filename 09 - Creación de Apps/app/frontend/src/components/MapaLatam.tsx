// Mapa de LATAM (Leaflet + tiles oscuros ArcGIS World_Dark_Gray_Base, igual a la demo Cargill).
// Una burbuja por región: tamaño según el nº de clientes, color según la intensidad de riesgo,
// número = clientes en riesgo Alto. Tooltip "Región — X clientes · Y en riesgo". Clic selecciona la región.
import { useEffect, useRef } from "react";
import L from "leaflet";
import type { RegionDatos } from "../api";
import { nf } from "../api";

// Coordenadas aproximadas (centro) de cada región del mapa.
const GEO: Record<string, [number, number]> = {
  "México": [23, -102],
  "Centroamérica": [11, -85],
  "Caribe": [18.5, -70.5],
  "Andina": [-2, -76],
  "Cono Sur": [-34, -64],
};
// Sombra por región (más oscuro = más en riesgo), calibrada en el mock.
const SHADE: Record<string, string> = {
  "Andina": "#E8412B",
  "México": "#F2604A",
  "Cono Sur": "#F98C79",
  "Centroamérica": "#FCB4A6",
  "Caribe": "#FED2C9",
};

type Props = {
  D: Record<string, RegionDatos>;
  seleccionada: string;
  onSelect: (reg: string) => void;
};

export function MapaLatam({ D, seleccionada, onSelect }: Props) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Record<string, L.Marker>>({});
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  function burbujaIcon(reg: string, sel: boolean) {
    const d = D[reg];
    const size = Math.round(30 + (d.clientes - 150) / 500 * 36);
    return L.divIcon({
      className: "",
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      html: `<div class="burbuja ${sel ? "burbuja-sel" : ""}" style="width:${size}px;height:${size}px;background:${SHADE[reg]};position:relative"><span style="font-size:${size > 46 ? 13 : 11}px">${d.riesgo}</span></div>`,
    });
  }

  // inicialización del mapa (una vez)
  useEffect(() => {
    if (!elRef.current || mapRef.current) return;
    const lmap = L.map(elRef.current, {
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
    }).setView([-5, -80], 3);
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 16 }
    ).addTo(lmap);
    // encuadra de México a Argentina
    lmap.fitBounds([
      [25, -108],
      [-36, -62],
    ]);
    mapRef.current = lmap;
    return () => {
      lmap.remove();
      mapRef.current = null;
      markersRef.current = {};
    };
  }, []);

  // (re)crea las burbujas cuando llegan los datos
  useEffect(() => {
    const lmap = mapRef.current;
    if (!lmap || !D || !D["México"]) return;
    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};
    Object.keys(GEO).forEach((reg) => {
      const m = L.marker(GEO[reg], { icon: burbujaIcon(reg, reg === seleccionada) }).addTo(lmap);
      m.bindTooltip(
        `<b>${reg}</b><br>${nf(D[reg].clientes)} clientes · ${nf(D[reg].riesgo)} en riesgo`,
        { direction: "top", offset: [0, -6] }
      );
      m.on("click", () => onSelectRef.current(reg));
      markersRef.current[reg] = m;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [D]);

  // resalta la región seleccionada
  useEffect(() => {
    Object.keys(markersRef.current).forEach((reg) =>
      markersRef.current[reg].setIcon(burbujaIcon(reg, reg === seleccionada))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seleccionada, D]);

  return <div id="latmap" ref={elRef} />;
}
