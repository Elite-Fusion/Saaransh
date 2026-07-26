import React, { useState, useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Plus, Minus, RotateCcw, Map as MapIcon, Layers } from "lucide-react";

// Karnataka Districts with real lat/lng coordinates
export const KARNATAKA_DISTRICT_COORDS = [
  { id: "bengaluru_urban", name: "Bengaluru Urban", lat: 12.9716, lng: 77.5946, risk: "veryhigh", cases: 2450, alert: true },
  { id: "bengaluru_rural", name: "Bengaluru Rural", lat: 13.2257, lng: 77.5750, risk: "high", cases: 980, alert: false },
  { id: "mysuru", name: "Mysuru", lat: 12.2958, lng: 76.6394, risk: "veryhigh", cases: 1420, alert: true },
  { id: "mandya", name: "Mandya", lat: 12.5218, lng: 76.8951, risk: "high", cases: 650, alert: false },
  { id: "ramanagara", name: "Ramanagara", lat: 12.7209, lng: 77.2799, risk: "high", cases: 540, alert: false },
  { id: "chamarajanagar", name: "Chamarajanagar", lat: 11.9261, lng: 76.9437, risk: "veryhigh", cases: 490, alert: true },
  { id: "hassan", name: "Hassan", lat: 13.0033, lng: 76.1004, risk: "high", cases: 710, alert: false },
  { id: "tumakuru", name: "Tumakuru", lat: 13.3379, lng: 77.1173, risk: "veryhigh", cases: 1180, alert: true },
  { id: "chitradurga", name: "Chitradurga", lat: 14.2251, lng: 76.3980, risk: "veryhigh", cases: 1310, alert: true },
  { id: "davanagere", name: "Davanagere", lat: 14.4644, lng: 75.9218, risk: "medium", cases: 520, alert: false },
  { id: "shivamogga", name: "Shivamogga", lat: 13.9299, lng: 75.5681, risk: "medium", cases: 480, alert: false },
  { id: "chikkamagaluru", name: "Chikkamagaluru", lat: 13.3161, lng: 75.7720, risk: "low", cases: 310, alert: false },
  { id: "kodagu", name: "Kodagu", lat: 12.4244, lng: 75.7382, risk: "low", cases: 220, alert: false },
  { id: "udupi", name: "Udupi", lat: 13.3409, lng: 74.7421, risk: "low", cases: 390, alert: false },
  { id: "dakshina_kannada", name: "Dakshina Kannada", lat: 12.9141, lng: 74.8560, risk: "low", cases: 410, alert: false },
  { id: "uttara_kannada", name: "Uttara Kannada", lat: 14.8142, lng: 74.1297, risk: "high", cases: 620, alert: true },
  { id: "dharwad", name: "Dharwad", lat: 15.4589, lng: 75.0078, risk: "medium", cases: 590, alert: false },
  { id: "belagavi", name: "Belagavi", lat: 15.8497, lng: 74.4977, risk: "low", cases: 780, alert: false },
  { id: "bagalkote", name: "Bagalkote", lat: 16.1852, lng: 75.6961, risk: "medium", cases: 450, alert: false },
  { id: "vijayapura", name: "Vijayapura", lat: 16.8302, lng: 75.7100, risk: "high", cases: 670, alert: false },
  { id: "gadag", name: "Gadag", lat: 15.4309, lng: 75.6355, risk: "medium", cases: 380, alert: false },
  { id: "haveri", name: "Haveri", lat: 14.7946, lng: 75.3998, risk: "medium", cases: 410, alert: false },
  { id: "koppal", name: "Koppal", lat: 15.3519, lng: 76.1554, risk: "medium", cases: 430, alert: false },
  { id: "ballari", name: "Ballari", lat: 15.1394, lng: 76.9214, risk: "high", cases: 820, alert: true },
  { id: "raichur", name: "Raichur", lat: 16.2076, lng: 77.3463, risk: "high", cases: 740, alert: false },
  { id: "kalaburagi", name: "Kalaburagi", lat: 17.3297, lng: 76.8343, risk: "verylow", cases: 320, alert: false },
  { id: "yadgir", name: "Yadgir", lat: 16.7700, lng: 77.1300, risk: "verylow", cases: 210, alert: false },
  { id: "bidar", name: "Bidar", lat: 17.9104, lng: 77.5199, risk: "verylow", cases: 250, alert: false },
  { id: "chikkaballapura", name: "Chikkaballapura", lat: 13.4355, lng: 77.7275, risk: "high", cases: 530, alert: false },
  { id: "kolar", name: "Kolar", lat: 13.1367, lng: 78.1292, risk: "high", cases: 610, alert: false },
];

const RISK_COLORS = {
  veryhigh: "#f43f5e",
  high: "#fb923c",
  medium: "#facc15",
  low: "#a3e635",
  verylow: "#34d399",
};

const RISK_LEVELS = [
  { key: "very_high", label: "Very High", color: "#f43f5e" },
  { key: "high",       label: "High",      color: "#fb923c" },
  { key: "medium",     label: "Medium",    color: "#facc15" },
  { key: "low",        label: "Low",       color: "#a3e635" },
  { key: "very_low",   label: "Very Low",  color: "#34d399" },
];

export default function KarnatakaMap({ selectedDistrict, onSelectDistrict, className = "" }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [mapMode, setMapMode] = useState("leaflet"); // "leaflet" or "vector"

  useEffect(() => {
    if (mapMode !== "leaflet" || !mapContainerRef.current) return;

    // Destroy existing map instance if any
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    // Initialize Leaflet Map centered on Karnataka state center
    const map = L.map(mapContainerRef.current, {
      center: [14.5204, 75.7224],
      zoom: 7,
      zoomControl: false,
      attributionControl: false,
    });

    mapInstanceRef.current = map;

    // Smooth CartoDB Positron Tile Layer
    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(map);

    // Add district risk circles and markers
    KARNATAKA_DISTRICT_COORDS.forEach((d) => {
      const circleColor = RISK_COLORS[d.risk] || "#cbd5e1";

      // Choropleth Circle Overlay
      const circle = L.circle([d.lat, d.lng], {
        color: circleColor,
        fillColor: circleColor,
        fillOpacity: 0.5,
        radius: d.risk === "veryhigh" ? 35000 : 25000,
        weight: 2,
      }).addTo(map);

      // District Popup & Tooltip
      circle.bindTooltip(
        `<div style="font-family:Inter,sans-serif; padding:2px 4px;">
          <strong style="font-size:12px; color:#0f172a;">${d.name}</strong><br/>
          <span style="font-size:10px; color:#64748b; text-transform:capitalize;">${d.risk} Risk (${d.cases} cases)</span>
        </div>`,
        { permanent: false, direction: "top" }
      );

      circle.on("click", () => {
        if (onSelectDistrict) onSelectDistrict(d);
      });

      // High Risk Warning Marker Icon
      if (d.alert) {
        const iconHtml = `
          <div style="background:#dc2626; color:white; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:12px; border:2px solid white; box-shadow:0 2px 6px rgba(0,0,0,0.3);">
            !
          </div>
        `;
        const customIcon = L.divIcon({
          html: iconHtml,
          className: "custom-alert-marker",
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        });

        L.marker([d.lat, d.lng], { icon: customIcon }).addTo(map);
      }
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [mapMode]);

  const handleZoomIn = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomIn();
  };

  const handleZoomOut = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomOut();
  };

  const handleResetZoom = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.setView([14.5204, 75.7224], 7);
  };

  return (
    <div className={`relative w-full h-full min-h-[460px] bg-slate-50 rounded-2xl border border-slate-200 overflow-hidden flex flex-col justify-between p-0 select-none shadow-xs ${className}`}>

      {/* Top Left Title & Risk Level Legend Card */}
      <div className="absolute top-4 left-4 z-[1000] space-y-2 pointer-events-none">
        <h2 className="text-sm font-black text-slate-900 tracking-tight drop-shadow-xs bg-white/80 backdrop-blur-md px-3 py-1 rounded-lg border border-slate-200">
          Crime Risk Map – Karnataka
        </h2>

        <div className="bg-white/95 backdrop-blur-md p-3 rounded-2xl border border-slate-200/90 shadow-md space-y-2 pointer-events-auto w-38">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Risk Level (Predicted)</p>
          <div className="space-y-1">
            {RISK_LEVELS.map((r) => (
              <div key={r.key} className="flex items-center gap-2 text-xs font-bold text-slate-700">
                <span className="h-2.5 w-2.5 rounded-full shrink-0 shadow-xs border border-white" style={{ background: r.color }} />
                <span>{r.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Map Display Container */}
      <div className="relative w-full h-full min-h-[460px] flex-1">
        {mapMode === "leaflet" ? (
          <div ref={mapContainerRef} className="w-full h-full min-h-[460px] rounded-2xl z-0" />
        ) : (
          <VectorHeatmapView onSelectDistrict={onSelectDistrict} />
        )}
      </div>

      {/* Top Right Mode Toggle (Leaflet Map vs Vector) */}
      <div className="absolute top-4 right-4 z-[1000]">
        <div className="bg-white/95 backdrop-blur-md p-1 rounded-xl border border-slate-200 shadow-md flex items-center gap-1">
          <button
            onClick={() => setMapMode("leaflet")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              mapMode === "leaflet" ? "bg-emerald-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <MapIcon size={13} />
            <span>Interactive Map</span>
          </button>
          <button
            onClick={() => setMapMode("vector")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              mapMode === "vector" ? "bg-emerald-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Layers size={13} />
            <span>Choropleth</span>
          </button>
        </div>
      </div>

      {/* Bottom Left Controls: Zoom Buttons + View Full Map Pill Button */}
      <div className="absolute bottom-4 left-4 z-[1000] flex items-center gap-3">
        <div className="flex flex-col rounded-2xl bg-white/95 backdrop-blur-md border border-slate-200 shadow-md overflow-hidden">
          <button
            onClick={handleZoomIn}
            className="w-9 h-9 flex items-center justify-center text-slate-700 hover:bg-slate-100 border-b border-slate-100 transition-colors"
            title="Zoom In"
          >
            <Plus size={16} />
          </button>
          <button
            onClick={handleZoomOut}
            className="w-9 h-9 flex items-center justify-center text-slate-700 hover:bg-slate-100 border-b border-slate-100 transition-colors"
            title="Zoom Out"
          >
            <Minus size={16} />
          </button>
          <button
            onClick={handleResetZoom}
            className="w-9 h-9 flex items-center justify-center text-slate-700 hover:bg-slate-100 transition-colors"
            title="Reset Map"
          >
            <RotateCcw size={14} />
          </button>
        </div>

        <button className="px-4 py-2.5 bg-white/95 backdrop-blur-md border border-slate-200 hover:bg-slate-50 text-slate-800 text-xs font-bold rounded-2xl shadow-md transition-colors">
          View Full Map
        </button>
      </div>
    </div>
  );
}

// Fallback Vector Heatmap SVG view
function VectorHeatmapView({ onSelectDistrict }) {
  return (
    <div className="w-full h-full flex items-center justify-center p-4 bg-gradient-to-tr from-[#f6faf6] to-[#f8fbfd]">
      <svg viewBox="75 10 420 570" className="w-full h-full max-h-[500px]">
        {KARNATAKA_DISTRICT_COORDS.map((d) => (
          <g key={d.id} className="cursor-pointer" onClick={() => onSelectDistrict && onSelectDistrict(d)}>
            <circle cx={d.lng * 24 - 1650} cy={600 - d.lat * 28} r={d.risk === "veryhigh" ? 18 : 12} fill={RISK_COLORS[d.risk]} opacity="0.8" />
            <text x={d.lng * 24 - 1650} y={600 - d.lat * 28 + 4} fill="#0f172a" fontSize="9" fontWeight="bold" textAnchor="middle">{d.name.slice(0, 3)}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}
