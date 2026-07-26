import React, { useState, useEffect } from "react";
import Topbar from "../layout/Topbar";
import KarnatakaCommandMap from "../components/KarnatakaCommandMap";
import { mapApi } from "../api/mapApi";
import {
  Shield,
  SlidersHorizontal,
  AlertTriangle,
  Radio,
  Navigation,
  Eye,
  Crosshair,
  TrendingUp,
  Activity,
  Calendar,
  Filter,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  Layers,
  MapPin,
  Sparkles,
  ChevronRight,
  X,
} from "lucide-react";

const DISTRICTS = [
  "All Districts",
  "Bengaluru Urban",
  "Bengaluru Rural",
  "Mysuru",
  "Mandya",
  "Ramanagara",
  "Chamarajanagar",
  "Hassan",
  "Tumakuru",
  "Chitradurga",
  "Davanagere",
  "Shivamogga",
  "Chikkamagaluru",
  "Kodagu",
  "Udupi",
  "Dakshina Kannada",
  "Uttara Kannada",
  "Dharwad",
  "Belagavi",
  "Bagalkote",
  "Vijayapura",
  "Gadag",
  "Haveri",
  "Koppal",
  "Ballari",
  "Raichur",
  "Kalaburagi",
  "Yadgir",
  "Bidar",
  "Chikkaballapura",
  "Kolar",
];

const CRIME_TYPES = [
  "All Crimes",
  "Chain Snatching",
  "Armed Robbery",
  "Vehicle Theft",
  "Residential Burglary",
  "Cyber Fraud",
  "Aggravated Assault",
  "Extortion",
  "Kidnapping",
];

const SEVERITIES = [
  { key: "all", label: "All Severities" },
  { key: "very_high", label: "Very High", color: "#dc2626" },
  { key: "high", label: "High", color: "#f97316" },
  { key: "medium", label: "Medium", color: "#eab308" },
  { key: "low", label: "Low", color: "#22c55e" },
];

export default function MapIntelligence() {
  // State for map data
  const [stations, setStations] = useState([]);
  const [firMarkers, setFirMarkers] = useState([]);
  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [patrols, setPatrols] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({
    total_crimes: 2450,
    hotspots_count: 6,
    predictions_count: 4,
    patrol_units_count: 18,
    avg_response_time_mins: 11.4,
    solved_percentage: 67.5,
    active_cases_count: 810,
  });
  const [investigationOverlay, setInvestigationOverlay] = useState(null);

  // Filter states
  const [selectedDistrict, setSelectedDistrict] = useState("All Districts");
  const [selectedCrimeType, setSelectedCrimeType] = useState("All Crimes");
  const [selectedSeverity, setSelectedSeverity] = useState("all");
  const [selectedTimeframe, setSelectedTimeframe] = useState("7d");
  const [predictionHorizon, setPredictionHorizon] = useState("24h");
  const [repeatOffenderOnly, setRepeatOffenderOnly] = useState(false);
  const [timelineIndex, setTimelineIndex] = useState(100);

  // Active layer visibility toggles
  const [activeLayers, setActiveLayers] = useState({
    stations: true,
    firs: true,
    heatmap: true,
    predictions: true,
    clusters: true,
    patrols: true,
    alerts: true,
    investigation: true,
  });

  // Focused map location state
  const [focusedLocation, setFocusedLocation] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch API data
  const loadMapData = async () => {
    setIsLoading(true);
    try {
      const [
        stationsRes,
        firsRes,
        heatmapRes,
        hotspotsRes,
        predsRes,
        clustersRes,
        patrolsRes,
        alertsRes,
        statsRes,
      ] = await Promise.allSettled([
        mapApi.getPoliceStations(),
        mapApi.getFirMarkers({
          district: selectedDistrict !== "All Districts" ? selectedDistrict : undefined,
          crime_type: selectedCrimeType !== "All Crimes" ? selectedCrimeType : undefined,
          severity: selectedSeverity !== "all" ? selectedSeverity : undefined,
          repeat_offender_only: repeatOffenderOnly,
        }),
        mapApi.getHeatmapPoints({
          time_range: selectedTimeframe,
          district: selectedDistrict !== "All Districts" ? selectedDistrict : undefined,
          crime_type: selectedCrimeType !== "All Crimes" ? selectedCrimeType : undefined,
        }),
        mapApi.getHotspots(),
        mapApi.getPredictedZones(predictionHorizon),
        mapApi.getClusters(),
        mapApi.getPatrols(),
        mapApi.getAlerts(),
        mapApi.getMapStats(),
      ]);

      if (stationsRes.status === "fulfilled") setStations(stationsRes.value);
      if (firsRes.status === "fulfilled") setFirMarkers(firsRes.value);
      if (heatmapRes.status === "fulfilled") setHeatmapPoints(heatmapRes.value);
      if (hotspotsRes.status === "fulfilled") setHotspots(hotspotsRes.value);
      if (predsRes.status === "fulfilled") setPredictions(predsRes.value);
      if (clustersRes.status === "fulfilled") setClusters(clustersRes.value);
      if (patrolsRes.status === "fulfilled") setPatrols(patrolsRes.value);
      if (alertsRes.status === "fulfilled") setAlerts(alertsRes.value);
      if (statsRes.status === "fulfilled") setStats(statsRes.value);
    } catch (err) {
      console.error("Map intelligence fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMapData();
  }, [
    selectedDistrict,
    selectedCrimeType,
    selectedSeverity,
    selectedTimeframe,
    predictionHorizon,
    repeatOffenderOnly,
  ]);

  // Load investigation overlay demo for case 1
  const handleLoadInvestigationOverlay = async (caseId = 1) => {
    try {
      const data = await mapApi.getInvestigationOverlay(caseId);
      setInvestigationOverlay(data);
      if (data.crime_location) {
        setFocusedLocation({
          lat: data.crime_location.lat,
          lng: data.crime_location.lng,
          zoom: 13,
        });
      }
      setSelectedDetail({ type: "investigation", data });
    } catch (err) {
      console.error("Failed to load investigation overlay:", err);
    }
  };

  // Toggle individual layer
  const toggleLayer = (layerKey) => {
    setActiveLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  return (
    <div className="bg-slate-950 min-h-screen text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950">
      <Topbar
        title="Intelligent Map Command Center"
        subtitle="Real-time Karnataka Police Command & Predictive Policing Operational Dashboard"
      />

      <div className="p-4 md:p-6 space-y-4 max-w-[1600px] mx-auto w-full flex-1 flex flex-col">
        {/* Top Operational Statistics Command Panel */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">Total Crimes</span>
            <div className="text-xl font-black text-white mt-1">{stats.total_crimes}</div>
            <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1 mt-1">
              <TrendingUp size={12} /> Database Verified
            </span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">Active Cases</span>
            <div className="text-xl font-black text-amber-400 mt-1">{stats.active_cases_count}</div>
            <span className="text-[10px] text-amber-300 font-semibold">Under Investigation</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">Crime Hotspots</span>
            <div className="text-xl font-black text-red-400 mt-1">{stats.hotspots_count}</div>
            <span className="text-[10px] text-red-300 font-semibold">High Density Zones</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">AI Predictions</span>
            <div className="text-xl font-black text-rose-400 mt-1">{stats.predictions_count}</div>
            <span className="text-[10px] text-rose-300 font-semibold">Forecast Horizons</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">Active Patrols</span>
            <div className="text-xl font-black text-sky-400 mt-1">{stats.patrol_units_count}</div>
            <span className="text-[10px] text-sky-300 font-semibold">Deployments Active</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">Avg Response</span>
            <div className="text-xl font-black text-emerald-400 mt-1">{stats.avg_response_time_mins}m</div>
            <span className="text-[10px] text-emerald-300 font-semibold">Statewide Target &lt; 15m</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-2xl shadow-lg backdrop-blur-md flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase text-slate-400 font-mono tracking-wider">Clearance Rate</span>
            <div className="text-xl font-black text-emerald-400 mt-1">{stats.solved_percentage}%</div>
            <span className="text-[10px] text-slate-400 font-semibold">Solved & Chargesheeted</span>
          </div>
        </div>

        {/* Real-Time Live Emergency Alert Banner Ticker */}
        {alerts.length > 0 && (
          <div className="bg-red-950/70 border border-red-900/80 p-2.5 rounded-2xl flex items-center gap-3 overflow-x-auto shadow-xl">
            <div className="px-2.5 py-1 bg-red-600 text-white rounded-lg text-[10px] font-black tracking-widest uppercase flex items-center gap-1.5 shrink-0 animate-pulse">
              <Radio size={13} />
              <span>LIVE ALERTS</span>
            </div>

            <div className="flex items-center gap-4 text-xs overflow-x-auto scrollbar-none py-0.5">
              {alerts.map((alt) => (
                <button
                  key={alt.alert_id}
                  onClick={() => {
                    setFocusedLocation({ lat: alt.latitude, lng: alt.longitude, zoom: 14 });
                    setSelectedDetail({ type: "alert", data: alt });
                  }}
                  className="flex items-center gap-2 bg-slate-900/80 hover:bg-slate-800 border border-red-800/60 px-3 py-1 rounded-xl shrink-0 transition-colors text-left text-slate-200"
                >
                  <span className="h-2 w-2 rounded-full bg-red-500 animate-ping shrink-0" />
                  <strong className="text-red-300 font-bold">{alt.alert_type}:</strong>
                  <span className="truncate max-w-xs">{alt.title}</span>
                  <span className="text-[10px] font-mono text-slate-400">({alt.district_name})</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Control Room Interactive Filter Bar */}
        <div className="bg-slate-900/90 border border-slate-800 p-3.5 rounded-2xl shadow-xl space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-slate-200 font-bold text-xs">
              <SlidersHorizontal size={16} className="text-emerald-400" />
              <span>Operational Map Filters</span>
              {isLoading && <RefreshCw size={13} className="animate-spin text-emerald-400" />}
            </div>

            {/* AI Investigation Overlay Trigger Button */}
            <button
              onClick={() => handleLoadInvestigationOverlay(1)}
              className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-black shadow-lg transition-all flex items-center gap-2"
            >
              <Sparkles size={14} />
              <span>Load AI Investigation Overlay</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2.5">
            {/* District Filter */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">District</label>
              <select
                value={selectedDistrict}
                onChange={(e) => setSelectedDistrict(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-500"
              >
                {DISTRICTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            {/* Crime Type Filter */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Crime Type</label>
              <select
                value={selectedCrimeType}
                onChange={(e) => setSelectedCrimeType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-500"
              >
                {CRIME_TYPES.map((ct) => (
                  <option key={ct} value={ct}>{ct}</option>
                ))}
              </select>
            </div>

            {/* Severity Filter */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Severity</label>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-500"
              >
                {SEVERITIES.map((s) => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </select>
            </div>

            {/* Heatmap Timeframe Filter */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Heatmap Window</label>
              <select
                value={selectedTimeframe}
                onChange={(e) => setSelectedTimeframe(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-500"
              >
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="month">Last Month</option>
                <option value="year">Last Year</option>
              </select>
            </div>

            {/* AI Prediction Horizon */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">AI Prediction Horizon</label>
              <select
                value={predictionHorizon}
                onChange={(e) => setPredictionHorizon(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-500"
              >
                <option value="24h">Next 24 Hours</option>
                <option value="3d">Next 3 Days</option>
                <option value="7d">Next 7 Days</option>
                <option value="month">Next Month</option>
              </select>
            </div>
          </div>

          {/* Toggle Chips */}
          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
            <button
              onClick={() => setRepeatOffenderOnly(!repeatOffenderOnly)}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all border ${
                repeatOffenderOnly
                  ? "bg-red-950 text-red-300 border-red-700 shadow-md"
                  : "bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200"
              }`}
            >
              🎯 Repeat Offenders Only
            </button>

            <div className="h-4 w-px bg-slate-800 mx-1" />

            {/* Layer Visibility Toggles */}
            <span className="text-[10px] font-bold uppercase text-slate-500 font-mono">Layers:</span>
            {Object.keys(activeLayers).map((lk) => (
              <button
                key={lk}
                onClick={() => toggleLayer(lk)}
                className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold capitalize transition-all border ${
                  activeLayers[lk]
                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-700"
                    : "bg-slate-950 text-slate-500 border-slate-800 opacity-60"
                }`}
              >
                {lk}
              </button>
            ))}
          </div>
        </div>

        {/* Central Map Canvas & Side Panel Container */}
        <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-[580px] relative">
          {/* Main Leaflet Map Canvas */}
          <div className="flex-1 relative rounded-2xl overflow-hidden shadow-2xl border border-slate-800">
            <KarnatakaCommandMap
              stations={stations}
              firMarkers={firMarkers}
              heatmapPoints={heatmapPoints}
              hotspots={hotspots}
              predictions={predictions}
              clusters={clusters}
              patrols={patrols}
              alerts={alerts}
              investigationOverlay={investigationOverlay}
              activeLayers={activeLayers}
              onSelectFir={(fir) => setSelectedDetail({ type: "fir", data: fir })}
              onSelectStation={(st) => setSelectedDetail({ type: "station", data: st })}
              onSelectPrediction={(pz) => setSelectedDetail({ type: "prediction", data: pz })}
              onSelectAlert={(alt) => setSelectedDetail({ type: "alert", data: alt })}
              focusedLocation={focusedLocation}
            />

            {/* Bottom Floating Timeline Slider */}
            <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-[1000] w-11/12 max-w-xl bg-slate-900/95 backdrop-blur-md p-3 rounded-2xl border border-slate-800 shadow-2xl space-y-1.5">
              <div className="flex justify-between items-center text-xs font-bold text-slate-200">
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <Clock size={14} /> Timeline Slider Scrubbing
                </span>
                <span className="font-mono text-amber-400">
                  {timelineIndex === 100 ? "Present / Live" : `${100 - timelineIndex} Days Ago`}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={timelineIndex}
                onChange={(e) => setTimelineIndex(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <div className="flex justify-between text-[9px] font-mono text-slate-400">
                <span>1 Month Ago</span>
                <span>15 Days Ago</span>
                <span>Yesterday</span>
                <span className="text-emerald-400 font-bold">Now (Live)</span>
              </div>
            </div>
          </div>

          {/* Right Inspector & Control Panel */}
          {selectedDetail && (
            <div className="w-full lg:w-96 bg-slate-900/95 border border-slate-800 p-5 rounded-2xl shadow-2xl flex flex-col justify-between space-y-4 animate-in slide-in-from-right duration-300">
              <div className="space-y-4">
                <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2 text-emerald-400 font-black text-sm uppercase font-mono tracking-wider">
                    <Activity size={16} />
                    <span>{selectedDetail.type} Detail View</span>
                  </div>
                  <button
                    onClick={() => setSelectedDetail(null)}
                    className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Render station detail */}
                {selectedDetail.type === "station" && (
                  <div className="space-y-3 text-xs text-slate-200">
                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1">
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">{selectedDetail.data.station_code}</span>
                      <h3 className="text-sm font-black text-white">{selectedDetail.data.name}</h3>
                      <p className="text-slate-400">{selectedDetail.data.district_name} District</p>
                    </div>
                    <div className="space-y-1.5 bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <div className="flex justify-between"><span class="text-slate-400">Officer In-Charge:</span> <strong className="text-slate-100">{selectedDetail.data.officer_in_charge}</strong></div>
                      <div className="flex justify-between"><span class="text-slate-400">Avg Response Time:</span> <strong className="text-emerald-400">{selectedDetail.data.avg_response_time_mins} mins</strong></div>
                      <div className="flex justify-between"><span class="text-slate-400">Total FIRs Logged:</span> <strong className="text-slate-100">{selectedDetail.data.total_firs}</strong></div>
                    </div>
                  </div>
                )}

                {/* Render FIR detail */}
                {selectedDetail.type === "fir" && (
                  <div className="space-y-3 text-xs text-slate-200">
                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-mono text-amber-400 font-bold">{selectedDetail.data.fir_number}</span>
                        <span className="px-2 py-0.5 rounded text-[9px] font-black bg-red-950 text-red-400 border border-red-800 uppercase">{selectedDetail.data.severity}</span>
                      </div>
                      <h3 className="text-sm font-black text-white">{selectedDetail.data.crime_type}</h3>
                      <p className="text-slate-400">Victim/Complainant: {selectedDetail.data.victim_name}</p>
                    </div>

                    <div className="space-y-1.5 bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <div className="flex justify-between"><span className="text-slate-400">Status:</span> <strong className="text-amber-400">{selectedDetail.data.status}</strong></div>
                      <div className="flex justify-between"><span className="text-slate-400">Assigned IO:</span> <strong className="text-slate-100">{selectedDetail.data.assigned_officer}</strong></div>
                      <div className="flex justify-between"><span className="text-slate-400">Station:</span> <strong className="text-slate-100">{selectedDetail.data.nearest_police_station}</strong></div>
                      <div className="flex justify-between"><span className="text-slate-400">Registered Date:</span> <strong className="text-slate-300 font-mono">{selectedDetail.data.registered_date}</strong></div>
                    </div>
                  </div>
                )}

                {/* Render Prediction detail */}
                {selectedDetail.type === "prediction" && (
                  <div className="space-y-3 text-xs text-slate-200">
                    <div className="bg-red-950/60 p-3 rounded-xl border border-red-800/80 space-y-1">
                      <span className="text-[10px] font-mono text-red-300 font-bold">AI Crime Zone Prediction</span>
                      <h3 className="text-sm font-black text-white">{selectedDetail.data.likely_crime}</h3>
                      <div className="text-xs text-emerald-400 font-bold">Confidence: {selectedDetail.data.confidence_pct}%</div>
                    </div>
                    <div className="space-y-1 bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">Explainable AI Reasoning:</span>
                      <ul class="list-disc pl-4 space-y-1 text-slate-300 text-[11px]">
                        {selectedDetail.data.reasoning_factors.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={() => setSelectedDetail(null)}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition-colors border border-slate-700"
              >
                Close Panel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}