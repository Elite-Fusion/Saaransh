import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  Shield,
  AlertTriangle,
  Radio,
  Navigation,
  Eye,
  Crosshair,
  Zap,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  Sparkles,
} from "lucide-react";

// District boundaries center list for reference
const KARNATAKA_DISTRICT_BOUNDS = [
  { name: "Bengaluru Urban", lat: 12.9716, lng: 77.5946 },
  { name: "Mysuru", lat: 12.2958, lng: 76.6394 },
  { name: "Belagavi", lat: 15.8497, lng: 74.4977 },
  { name: "Dharwad", lat: 15.4589, lng: 75.0078 },
  { name: "Dakshina Kannada", lat: 12.9141, lng: 74.8560 },
  { name: "Kalaburagi", lat: 17.3297, lng: 76.8343 },
  { name: "Ballari", lat: 15.1394, lng: 76.9214 },
  { name: "Davanagere", lat: 14.4644, lng: 75.9218 },
  { name: "Shivamogga", lat: 13.9299, lng: 75.5681 },
  { name: "Tumakuru", lat: 13.3379, lng: 77.1173 },
];

export default function KarnatakaCommandMap({
  stations = [],
  firMarkers = [],
  heatmapPoints = [],
  hotspots = [],
  predictions = [],
  clusters = [],
  patrols = [],
  alerts = [],
  investigationOverlay = null,
  activeLayers = {
    stations: true,
    firs: true,
    heatmap: true,
    predictions: true,
    clusters: true,
    patrols: true,
    alerts: true,
    investigation: true,
  },
  onSelectFir,
  onSelectStation,
  onSelectPrediction,
  onSelectAlert,
  focusedLocation = null,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layerGroupsRef = useRef({});
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentZoom, setCurrentZoom] = useState(7);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const map = L.map(mapContainerRef.current, {
      center: [14.5204, 75.7224],
      zoom: 7,
      zoomControl: false,
      attributionControl: false,
    });

    mapInstanceRef.current = map;

    // Smooth Dark / Voyager CartoDB tiles for Police Command Room feel
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      {
        maxZoom: 19,
        subdomains: "abcd",
      }
    ).addTo(map);

    // Create Layer Groups
    layerGroupsRef.current = {
      stations: L.layerGroup().addTo(map),
      firs: L.layerGroup().addTo(map),
      heatmap: L.layerGroup().addTo(map),
      hotspots: L.layerGroup().addTo(map),
      predictions: L.layerGroup().addTo(map),
      clusters: L.layerGroup().addTo(map),
      patrols: L.layerGroup().addTo(map),
      alerts: L.layerGroup().addTo(map),
      investigation: L.layerGroup().addTo(map),
    };

    map.on("zoomend", () => {
      setCurrentZoom(map.getZoom());
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Handle focused location pan
  useEffect(() => {
    if (focusedLocation && mapInstanceRef.current) {
      mapInstanceRef.current.flyTo(
        [focusedLocation.lat, focusedLocation.lng],
        focusedLocation.zoom || 14,
        { duration: 1.5 }
      );
    }
  }, [focusedLocation]);

  // Render Police Stations Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.stations;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.stations || !stations) return;

    stations.forEach((st) => {
      const stationHtml = `
        <div class="ksp-station-marker">
          <div class="badge-ring"></div>
          <div class="inner-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
        </div>
      `;

      const icon = L.divIcon({
        html: stationHtml,
        className: "custom-station-pin",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([st.latitude, st.longitude], { icon }).addTo(lg);

      const popupHtml = `
        <div class="ksp-popup-card">
          <div class="popup-header bg-slate-900 text-white p-3 rounded-t-xl flex justify-between items-center">
            <div>
              <span class="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-wider">${st.station_code}</span>
              <h3 class="text-xs font-black tracking-tight">${st.name}</h3>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Active Station</span>
          </div>
          <div class="p-3 bg-slate-950 text-slate-200 text-xs space-y-2 rounded-b-xl border-t border-slate-800">
            <div class="flex justify-between items-center text-[11px]">
              <span class="text-slate-400">Officer In-Charge:</span>
              <span class="font-bold text-slate-100">${st.officer_in_charge}</span>
            </div>
            <div class="flex justify-between items-center text-[11px]">
              <span class="text-slate-400">District:</span>
              <span class="font-semibold text-slate-300">${st.district_name}</span>
            </div>
            <div class="grid grid-cols-3 gap-1 pt-1 text-center font-mono text-[10px]">
              <div class="bg-slate-900 p-1.5 rounded border border-slate-800">
                <div class="text-slate-400">Total</div>
                <div class="font-bold text-white text-xs">${st.total_firs}</div>
              </div>
              <div class="bg-slate-900 p-1.5 rounded border border-slate-800">
                <div class="text-amber-400">Active</div>
                <div class="font-bold text-amber-300 text-xs">${st.active_cases}</div>
              </div>
              <div class="bg-slate-900 p-1.5 rounded border border-slate-800">
                <div class="text-emerald-400">Solved</div>
                <div class="font-bold text-emerald-300 text-xs">${st.solved_cases}</div>
              </div>
            </div>
            <div class="pt-1 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-900">
              <span>Avg Response Time:</span>
              <span class="font-bold text-emerald-400">${st.avg_response_time_mins} mins</span>
            </div>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { className: "ksp-custom-leaflet-popup" });
      marker.on("click", () => onSelectStation && onSelectStation(st));
    });
  }, [stations, activeLayers.stations]);

  // Render FIR Markers Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.firs;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.firs || !firMarkers) return;

    firMarkers.forEach((fir) => {
      let colorClass = "bg-amber-500 border-amber-300 text-amber-950";
      let badgeLabel = "MED";

      if (fir.severity === "very_high") {
        colorClass = "bg-red-600 border-red-300 text-white animate-pulse";
        badgeLabel = "CRIT";
      } else if (fir.severity === "high") {
        colorClass = "bg-orange-500 border-orange-200 text-white";
        badgeLabel = "HIGH";
      } else if (fir.severity === "low") {
        colorClass = "bg-emerald-500 border-emerald-200 text-white";
        badgeLabel = "LOW";
      }

      const firHtml = `
        <div class="ksp-fir-marker ${fir.severity}">
          <span class="severity-badge ${colorClass}">${badgeLabel}</span>
        </div>
      `;

      const icon = L.divIcon({
        html: firHtml,
        className: "custom-fir-pin",
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const marker = L.marker([fir.latitude, fir.longitude], { icon }).addTo(lg);

      const popupHtml = `
        <div class="ksp-popup-card w-64">
          <div class="p-3 bg-slate-950 text-white rounded-t-xl flex justify-between items-center border-b border-slate-800">
            <div>
              <span class="text-[10px] font-mono text-amber-400 font-bold">${fir.fir_number}</span>
              <h4 class="text-xs font-bold text-slate-100">${fir.crime_type}</h4>
            </div>
            <span class="px-1.5 py-0.5 text-[9px] font-black uppercase rounded bg-red-950 text-red-400 border border-red-800">${fir.severity.replace("_", " ")}</span>
          </div>
          <div class="p-3 bg-slate-900 text-slate-300 text-xs space-y-1.5 rounded-b-xl">
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">Registered:</span> <span>${fir.registered_date}</span></div>
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">Victim/Complainant:</span> <span class="font-semibold text-slate-100">${fir.victim_name || fir.complainant_name}</span></div>
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">Status:</span> <span class="text-amber-400 font-bold">${fir.status}</span></div>
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">IO:</span> <span>${fir.assigned_officer}</span></div>
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">Nearest Station:</span> <span>${fir.nearest_police_station}</span></div>
            ${fir.is_repeat_offender_involved ? `<div class="p-1 mt-1 rounded bg-red-950/60 border border-red-800/60 text-[10px] font-bold text-red-300 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-red-500 animate-ping"></span> Repeat Offender Linked</div>` : ""}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { className: "ksp-custom-leaflet-popup" });
      marker.on("click", () => onSelectFir && onSelectFir(fir));
    });
  }, [firMarkers, activeLayers.firs]);

  // Render Crime Heatmap Density Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.heatmap;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.heatmap || !heatmapPoints) return;

    heatmapPoints.forEach((hp) => {
      const radius = 22000 * (hp.weight || 0.7);
      const color = hp.weight > 0.8 ? "#dc2626" : (hp.weight > 0.6 ? "#f97316" : "#eab308");

      L.circle([hp.lat, hp.lng], {
        radius: radius,
        color: color,
        fillColor: color,
        fillOpacity: 0.25,
        weight: 1,
      }).addTo(lg);
    });
  }, [heatmapPoints, activeLayers.heatmap]);

  // Render AI Predicted Crime Zones Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.predictions;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.predictions || !predictions) return;

    predictions.forEach((pz) => {
      // Pulsing radar animated dashed circle
      const circle = L.circle([pz.lat, pz.lng], {
        radius: pz.radius_meters || 1500,
        color: "#f43f5e",
        dashArray: "6, 8",
        fillColor: "#f43f5e",
        fillOpacity: 0.15,
        weight: 2,
        className: "ksp-prediction-radar-circle",
      }).addTo(lg);

      const predictionIconHtml = `
        <div class="ksp-prediction-center-pin">
          <div class="pulse-ring"></div>
          <div class="icon-core">AI</div>
        </div>
      `;

      const pIcon = L.divIcon({
        html: predictionIconHtml,
        className: "custom-pred-pin",
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const pMarker = L.marker([pz.lat, pz.lng], { icon: pIcon }).addTo(lg);

      const popupHtml = `
        <div class="ksp-popup-card w-72">
          <div class="p-3 bg-gradient-to-r from-red-950 to-slate-950 text-white rounded-t-xl border-b border-red-900/50 flex justify-between items-center">
            <div>
              <div class="flex items-center gap-1 text-[10px] font-mono text-red-400 font-bold uppercase">
                <span>AI Prediction Horizon</span> • <span>${pz.timeframe}</span>
              </div>
              <h3 class="text-xs font-black text-white">${pz.likely_crime}</h3>
            </div>
            <div class="text-right">
              <div class="text-sm font-black text-emerald-400">${pz.confidence_pct}%</div>
              <div class="text-[9px] text-slate-400 uppercase font-mono">Confidence</div>
            </div>
          </div>
          <div class="p-3 bg-slate-950 text-slate-300 text-xs space-y-2 rounded-b-xl border-t border-slate-900">
            <div class="flex justify-between items-center text-[11px]">
              <span class="text-slate-400">Expected Time Window:</span>
              <span class="font-bold text-amber-300 font-mono">${pz.expected_time_window}</span>
            </div>
            <div class="space-y-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase">Explainable AI Reasoning:</span>
              <ul class="text-[10px] space-y-0.5 text-slate-300 list-disc pl-3">
                ${pz.reasoning_factors.map((f) => `<li>${f}</li>`).join("")}
              </ul>
            </div>
            <div class="pt-1.5 border-t border-slate-900">
              <span class="text-[10px] font-bold text-emerald-400 uppercase">Suggested Patrol Units:</span>
              <div class="flex flex-wrap gap-1 mt-1">
                ${pz.suggested_patrol_units.map((u) => `<span class="px-1.5 py-0.5 bg-emerald-950 text-emerald-300 text-[9px] font-bold rounded border border-emerald-800">${u}</span>`).join("")}
              </div>
            </div>
          </div>
        </div>
      `;

      circle.bindPopup(popupHtml, { className: "ksp-custom-leaflet-popup" });
      pMarker.bindPopup(popupHtml, { className: "ksp-custom-leaflet-popup" });

      pMarker.on("click", () => onSelectPrediction && onSelectPrediction(pz));
    });
  }, [predictions, activeLayers.predictions]);

  // Render Crime Cluster Detection Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.clusters;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.clusters || !clusters) return;

    clusters.forEach((cl) => {
      const clusterHtml = `
        <div class="ksp-cluster-marker">
          <span class="cluster-count">${cl.crime_count}</span>
          <span class="cluster-type">${cl.common_crime_type.slice(0, 10)}</span>
        </div>
      `;

      const icon = L.divIcon({
        html: clusterHtml,
        className: "custom-cluster-pin",
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });

      const marker = L.marker([cl.center_lat, cl.center_lng], { icon }).addTo(lg);

      marker.on("click", () => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.flyTo([cl.center_lat, cl.center_lng], 13);
        }
      });

      marker.bindTooltip(
        `<strong class="text-xs">${cl.crime_count} Crimes Clustered</strong><br/><span class="text-[10px]">${cl.common_crime_type} • Peak: ${cl.most_active_hours}</span>`,
        { direction: "top" }
      );
    });
  }, [clusters, activeLayers.clusters]);

  // Render Patrol Recommendations Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.patrols;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.patrols || !patrols) return;

    patrols.forEach((pt) => {
      // Polyline route path
      L.polyline(pt.route_coords, {
        color: pt.color || "#eab308",
        weight: 3,
        dashArray: "6, 6",
        opacity: 0.8,
      }).addTo(lg);

      // Coverage radius circle
      L.circle(pt.current_position, {
        radius: pt.coverage_radius_meters || 2000,
        color: pt.color,
        fillColor: pt.color,
        fillOpacity: 0.08,
        weight: 1,
      }).addTo(lg);

      // Moving Vehicle Icon
      const vehicleHtml = `
        <div class="ksp-patrol-vehicle-marker" style="border-color:${pt.color}">
          <div class="v-icon">🚓</div>
        </div>
      `;

      const vIcon = L.divIcon({
        html: vehicleHtml,
        className: "custom-vehicle-pin",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const vMarker = L.marker(pt.current_position, { icon: vIcon }).addTo(lg);

      const popupHtml = `
        <div class="ksp-popup-card w-64">
          <div class="p-2.5 bg-slate-950 text-white rounded-t-xl flex justify-between items-center border-b border-slate-800">
            <div>
              <span class="text-[9px] font-mono text-amber-400 font-bold uppercase">${pt.unit_id}</span>
              <h4 class="text-xs font-black">${pt.unit_name}</h4>
            </div>
            <span class="px-1.5 py-0.5 text-[9px] font-extrabold uppercase rounded bg-emerald-950 text-emerald-400 border border-emerald-800">${pt.priority} Priority</span>
          </div>
          <div class="p-3 bg-slate-900 text-slate-300 text-xs space-y-1.5 rounded-b-xl">
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">Vehicle Type:</span> <span>${pt.vehicle_type}</span></div>
            <div class="flex justify-between text-[11px]"><span class="text-slate-400">Est. Response Time:</span> <span class="font-bold text-emerald-400">${pt.est_response_time_mins} mins</span></div>
            <div class="pt-1 text-[10px] text-slate-400 border-t border-slate-800">
              <span class="font-bold text-slate-200">Deployment Rationale:</span>
              <p class="mt-0.5 text-slate-300">${pt.reason}</p>
            </div>
          </div>
        </div>
      `;

      vMarker.bindPopup(popupHtml, { className: "ksp-custom-leaflet-popup" });
    });
  }, [patrols, activeLayers.patrols]);

  // Render Live Alerts Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.alerts;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.alerts || !alerts) return;

    alerts.forEach((alt) => {
      const alertHtml = `
        <div class="ksp-live-alert-marker">
          <div class="alert-halo"></div>
          <div class="alert-core">🚨</div>
        </div>
      `;

      const aIcon = L.divIcon({
        html: alertHtml,
        className: "custom-alert-pin",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const aMarker = L.marker([alt.latitude, alt.longitude], { icon: aIcon }).addTo(lg);

      const popupHtml = `
        <div class="ksp-popup-card w-72">
          <div class="p-3 bg-red-950 text-white rounded-t-xl border-b border-red-800 flex justify-between items-center">
            <div>
              <span class="text-[10px] font-mono text-red-300 font-bold uppercase">LIVE ALERT • ${alt.alert_type}</span>
              <h3 class="text-xs font-black text-white">${alt.title}</h3>
            </div>
            <span class="px-1.5 py-0.5 text-[9px] font-black uppercase rounded bg-red-600 text-white animate-pulse">EMERGENCY</span>
          </div>
          <div class="p-3 bg-slate-950 text-slate-300 text-xs space-y-2 rounded-b-xl">
            <p class="text-slate-200 text-[11px] font-medium leading-relaxed">${alt.description}</p>
            <div class="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-900">
              <span>District: <strong class="text-slate-200">${alt.district_name}</strong></span>
              <span>Time: <strong class="text-amber-400 font-mono">${alt.timestamp.split(" ")[1] || alt.timestamp}</strong></span>
            </div>
          </div>
        </div>
      `;

      aMarker.bindPopup(popupHtml, { className: "ksp-custom-leaflet-popup" });
      aMarker.on("click", () => onSelectAlert && onSelectAlert(alt));
    });
  }, [alerts, activeLayers.alerts]);

  // Render Investigation Overlay Layer
  useEffect(() => {
    const lg = layerGroupsRef.current.investigation;
    if (!lg) return;
    lg.clearLayers();

    if (!activeLayers.investigation || !investigationOverlay) return;

    const io = investigationOverlay;

    // Crime scene marker
    if (io.crime_location) {
      const csIcon = L.divIcon({
        html: `<div class="ksp-invest-scene-pin">🎯</div>`,
        className: "custom-invest-pin",
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      });
      L.marker([io.crime_location.lat, io.crime_location.lng], { icon: csIcon })
        .bindTooltip(`<b>Primary Crime Scene</b><br/>${io.fir_number}`, { permanent: true, direction: "top" })
        .addTo(lg);
    }

    // Escape routes polylines
    if (io.escape_routes) {
      io.escape_routes.forEach((route, idx) => {
        L.polyline(route, {
          color: idx === 0 ? "#dc2626" : "#f59e0b",
          weight: 4,
          dashArray: "8, 8",
          opacity: 0.9,
        })
          .bindTooltip(`Predicted Escape Route #${idx + 1}`, { sticky: true })
          .addTo(lg);
      });
    }

    // Repeat offender locations
    if (io.repeat_offender_locations) {
      io.repeat_offender_locations.forEach((loc) => {
        const susIcon = L.divIcon({
          html: `<div class="ksp-suspect-pin">👤</div>`,
          className: "custom-suspect-pin",
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        L.marker([loc.lat, loc.lng], { icon: susIcon })
          .bindTooltip(`<b>Suspect Location</b><br/>${loc.name} (${loc.accused})`, { direction: "top" })
          .addTo(lg);
      });
    }

    // Linked FIRs
    if (io.linked_firs) {
      io.linked_firs.forEach((lf) => {
        const linkIcon = L.divIcon({
          html: `<div class="ksp-linked-fir-pin">🔗</div>`,
          className: "custom-link-pin",
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        L.marker([lf.lat, lf.lng], { icon: linkIcon })
          .bindTooltip(`<b>Linked FIR ${lf.fir_number}</b><br/>Similarity: ${lf.similarity}`, { direction: "top" })
          .addTo(lg);
      });
    }
  }, [investigationOverlay, activeLayers.investigation]);

  const handleZoomIn = () => mapInstanceRef.current?.zoomIn();
  const handleZoomOut = () => mapInstanceRef.current?.zoomOut();
  const handleResetZoom = () => mapInstanceRef.current?.setView([14.5204, 75.7224], 7);

  return (
    <div
      className={`relative w-full h-full min-h-[550px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden select-none shadow-2xl ${
        isFullscreen ? "fixed inset-0 z-[9999] rounded-none border-none" : ""
      }`}
    >
      {/* Dynamic Keyframe Animations CSS */}
      <style>{`
        .ksp-custom-leaflet-popup .leaflet-popup-content-wrapper {
          background: transparent !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .ksp-custom-leaflet-popup .leaflet-popup-tip {
          background: #020617 !important;
        }
        .ksp-station-marker {
          width: 28px; height: 28px;
          border-radius: 50%;
          background: #020617;
          border: 2px solid #38bdf8;
          color: #38bdf8;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }
        .ksp-fir-marker {
          width: 22px; height: 22px;
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 0 8px rgba(0,0,0,0.5);
        }
        .severity-badge {
          font-size: 8px; font-weight: 900; padding: 1px 3px; border-radius: 4px;
        }
        .ksp-prediction-center-pin {
          position: relative; width: 26px; height: 26px;
          border-radius: 50%; background: #991b1b;
          border: 2px solid #f87171; color: white;
          font-size: 9px; font-weight: 900;
          display: flex; align-items: center; justify-content: center;
        }
        .ksp-prediction-center-pin .pulse-ring {
          position: absolute; inset: -6px; border-radius: 50%;
          border: 2px dashed #f87171;
          animation: radar-spin 4s linear infinite;
        }
        @keyframes radar-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .ksp-live-alert-marker {
          position: relative; width: 32px; height: 32px;
          border-radius: 50%; background: #dc2626;
          display: flex; align-items: center; justify-content: center;
          font-size: 14px; box-shadow: 0 0 15px #dc2626;
        }
        .ksp-live-alert-marker .alert-halo {
          position: absolute; inset: -8px; border-radius: 50%;
          background: rgba(220, 38, 38, 0.4);
          animation: alert-pulse 1.5s ease-out infinite;
        }
        @keyframes alert-pulse {
          0% { transform: scale(0.8); opacity: 1; }
          100% { transform: scale(1.8); opacity: 0; }
        }
        .ksp-cluster-marker {
          width: 36px; height: 36px; border-radius: 50%;
          background: #1e1b4b; border: 2px solid #818cf8;
          color: white; display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          box-shadow: 0 0 12px rgba(129, 140, 248, 0.6);
        }
        .ksp-cluster-marker .cluster-count {
          font-size: 11px; font-weight: 900; color: #a5b4fc;
        }
        .ksp-cluster-marker .cluster-type {
          font-size: 7px; text-transform: uppercase; color: #cbd5e1;
        }
        .ksp-patrol-vehicle-marker {
          width: 28px; height: 28px; border-radius: 50%;
          background: #0f172a; border: 2px solid #eab308;
          display: flex; align-items: center; justify-content: center;
          font-size: 12px; box-shadow: 0 0 10px rgba(234, 179, 8, 0.5);
        }
        .ksp-invest-scene-pin {
          width: 30px; height: 30px; border-radius: 50%; background: #b91c1c;
          border: 2px solid #fca5a5; display: flex; align-items: center; justify-content: center; font-size: 14px;
          box-shadow: 0 0 15px #b91c1c;
        }
        .ksp-suspect-pin {
          width: 24px; height: 24px; border-radius: 50%; background: #451a03;
          border: 2px solid #f97316; display: flex; align-items: center; justify-content: center; font-size: 12px;
        }
        .ksp-linked-fir-pin {
          width: 24px; height: 24px; border-radius: 50%; background: #14532d;
          border: 2px solid #4ade80; display: flex; align-items: center; justify-content: center; font-size: 12px;
        }
      `}</style>

      {/* Top Left Watermark Badge */}
      <div className="absolute top-4 left-4 z-[1000] pointer-events-none flex items-center gap-2">
        <div className="bg-slate-900/90 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-slate-800 text-slate-100 shadow-xl flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></div>
          <span className="text-xs font-black tracking-wider uppercase font-mono text-emerald-400">
            KSP Control Room Map • Live
          </span>
        </div>
      </div>

      {/* Map Element Container */}
      <div ref={mapContainerRef} className="w-full h-full z-0 bg-slate-950" />

      {/* Map Control Buttons (Zoom, Reset, Fullscreen) */}
      <div className="absolute bottom-5 left-5 z-[1000] flex items-center gap-3">
        <div className="flex flex-col bg-slate-900/90 backdrop-blur-md rounded-xl border border-slate-800 shadow-xl overflow-hidden text-slate-300">
          <button
            onClick={handleZoomIn}
            className="p-2.5 hover:bg-slate-800 hover:text-white transition-colors border-b border-slate-800/80"
            title="Zoom In"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2.5 hover:bg-slate-800 hover:text-white transition-colors border-b border-slate-800/80"
            title="Zoom Out"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-2.5 hover:bg-slate-800 hover:text-white transition-colors"
            title="Reset Map Bounds"
          >
            <RotateCcw size={15} />
          </button>
        </div>

        <button
          onClick={() => setIsFullscreen(!isFullscreen)}
          className="p-2.5 bg-slate-900/90 backdrop-blur-md rounded-xl border border-slate-800 text-slate-200 hover:text-white hover:bg-slate-800 shadow-xl transition-colors"
          title={isFullscreen ? "Exit Fullscreen" : "Fullscreen View"}
        >
          {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      </div>
    </div>
  );
}
