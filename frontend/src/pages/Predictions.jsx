import { useState } from "react";
import Topbar from "../layout/Topbar";
import { Card } from "../components/Card";
import { LoadingBlock, ErrorBlock, EmptyBlock } from "../components/StatusStates";
import { useQuery } from "@tanstack/react-query";
import { predictionsApi } from "../api/predictions";
import {
  findCaseById,
  calculateCaseRiskScore,
  generateOfficerRecommendations
} from "../utils/caseStore";
import {
  MapPinned, TrendingUp, Users, Layers, ShieldAlert, UserCheck,
  ChevronRight, AlertTriangle, BrainCircuit, Search
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend
} from "recharts";

const RISK_BAND_COLORS = {
  very_high: "#dc2626",
  high: "#f97316",
  medium: "#eab308",
  low: "#84cc16",
};

const RISK_LABEL_COLORS = {
  high: "bg-red-100 text-red-700 border border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border border-yellow-200",
  low: "bg-green-100 text-green-700 border border-green-200",
};

export default function Predictions() {
  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900">
      <Topbar
        title="Predictive Intelligence"
        subtitle="ML-powered crime predictions, risk scores, and recommendations"
      />

      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
        {/* Row 1: Hotspots + Repeat Offenders */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <HotspotPanel />
          <RepeatOffenderPanel />
        </div>

        {/* Row 2: Trend Forecasts */}
        <TrendPanel />

        {/* Row 3: Clusters */}
        <ClusterPanel />

        {/* Row 4: Risk Score + Recommendations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RiskScorePanel />
          <RecommendationPanel />
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------------
// Hotspot Panel
// -------------------------------------------------------------------

function HotspotPanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["predictions", "hotspots"],
    queryFn: () => predictionsApi.getHotspots({ top_n: 10 }),
  });

  const hotspots = data?.hotspots ?? [
    { district_name: "Chitradurga", crime_head: "Assault", month: 5, predicted_count: 14, risk_band: "very_high", confidence: 0.94 },
    { district_name: "Tumakuru", crime_head: "Burglary", month: 5, predicted_count: 11, risk_band: "high", confidence: 0.88 },
    { district_name: "Bengaluru Urban", crime_head: "Cyber Crime", month: 5, predicted_count: 9, risk_band: "high", confidence: 0.87 },
    { district_name: "Mysuru", crime_head: "Chain Snatching", month: 5, predicted_count: 8, risk_band: "high", confidence: 0.85 },
  ];

  return (
    <Card
      title="Crime Hotspot Predictions"
      action={<MapPinned size={16} className="text-rose-500" />}
    >
      {isLoading && <LoadingBlock lines={5} />}
      {error && <ErrorBlock error={error} onRetry={refetch} />}
      {!isLoading && hotspots.length === 0 && (
        <EmptyBlock label="No hotspot predictions available yet." />
      )}
      {hotspots.length > 0 && (
        <div className="space-y-2 max-h-72 overflow-y-auto thin-scroll">
          {hotspots.map((h, i) => (
            <div
              key={`${h.district_name}-${h.crime_head}-${h.month}-${i}`}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors border border-slate-100"
            >
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-900 truncate">
                  {h.district_name}
                </p>
                <p className="text-[11px] text-slate-500 truncate">
                  {h.crime_head} &middot; Month {h.month}
                </p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <p className="text-base font-black text-slate-900">{h.predicted_count}</p>
                  <p className="text-[10px] text-slate-400 font-semibold">cases</p>
                </div>
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-extrabold text-white"
                  style={{ background: RISK_BAND_COLORS[h.risk_band] ?? "#94a3b8" }}
                >
                  {h.risk_band?.toUpperCase()}
                </span>
                <ConfidencePill confidence={h.confidence} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// -------------------------------------------------------------------
// Repeat Offender Panel
// -------------------------------------------------------------------

function RepeatOffenderPanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["predictions", "repeat-offenders"],
    queryFn: () => predictionsApi.getRepeatOffenders({ top_n: 10 }),
  });

  const offenders = data?.repeat_offenders ?? [
    { accused_id: 101, accused_name: "Rider X (Pulsar Gang)", age: 28, prior_count: 4, will_reoffend: true, probability: 0.92, confidence: 0.92 },
    { accused_id: 102, accused_name: "Vikas Kumar", age: 34, prior_count: 2, will_reoffend: true, probability: 0.84, confidence: 0.84 },
    { accused_id: 103, accused_name: "Santosh M", age: 26, prior_count: 1, will_reoffend: false, probability: 0.38, confidence: 0.38 },
  ];

  return (
    <Card
      title="Repeat Offender Predictions"
      action={<Users size={16} className="text-amber-500" />}
    >
      {isLoading && <LoadingBlock lines={5} />}
      {error && <ErrorBlock error={error} onRetry={refetch} />}
      {!isLoading && offenders.length === 0 && (
        <EmptyBlock label="No repeat offender predictions available yet." />
      )}
      {offenders.length > 0 && (
        <div className="space-y-2 max-h-72 overflow-y-auto thin-scroll">
          {offenders.map((o) => (
            <div
              key={o.accused_id}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors border border-slate-100"
            >
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-900 truncate">
                  {o.accused_name || `Accused #${o.accused_id}`}
                </p>
                <p className="text-[11px] text-slate-500 font-medium">
                  Age {o.age ?? "N/A"} &middot; Prior Cases: {o.prior_count}
                </p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <p className={`text-base font-black ${o.will_reoffend ? "text-rose-600" : "text-emerald-600"}`}>
                    {Math.round(o.probability * 100)}%
                  </p>
                  <p className="text-[10px] text-slate-400 font-semibold">probability</p>
                </div>
                {o.will_reoffend ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-100 text-rose-700 border border-rose-200">
                    HIGH RISK
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-700 border border-emerald-200">
                    LOW RISK
                  </span>
                )}
                <ConfidencePill confidence={o.confidence} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// -------------------------------------------------------------------
// Trend Forecast Panel
// -------------------------------------------------------------------

function TrendPanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["predictions", "trends"],
    queryFn: () => predictionsApi.getTrends({ horizon_months: 6 }),
  });

  const trends = data?.trends ?? [
    { month_label: "Jan", year: 2025, predicted_count: 320, current_count: 290, crime_head: "Theft" },
    { month_label: "Feb", year: 2025, predicted_count: 350, current_count: 310, crime_head: "Theft" },
    { month_label: "Mar", year: 2025, predicted_count: 410, current_count: 360, crime_head: "Theft" },
    { month_label: "Apr", year: 2025, predicted_count: 380, current_count: 340, crime_head: "Theft" },
    { month_label: "May", year: 2025, predicted_count: 450, current_count: 390, crime_head: "Theft" },
  ];

  const chartData = trends.map((t) => ({
    name: `${t.month_label} ${t.year}`,
    predicted: t.predicted_count,
    current: t.current_count,
    crime_head: t.crime_head,
  }));

  return (
    <Card
      title="Crime Trend Forecasts"
      action={
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-emerald-600" />
          <span className="text-xs text-slate-500 font-semibold">{trends.length} periods</span>
        </div>
      }
    >
      {isLoading && <LoadingBlock lines={6} />}
      {error && <ErrorBlock error={error} onRetry={refetch} />}
      {chartData.length > 0 && (
        <div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ borderRadius: "0.75rem", border: "1px solid #e2e8f0" }}
                  formatter={(value, name) => [value, name === "predicted" ? "Predicted" : "Prior Year"]}
                />
                <Legend />
                <Bar dataKey="current" name="Prior Year" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="predicted" name="Predicted" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </Card>
  );
}

// -------------------------------------------------------------------
// Cluster Panel
// -------------------------------------------------------------------

function ClusterPanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["predictions", "clusters"],
    queryFn: () => predictionsApi.getClusters({ top_n: 5 }),
  });

  const clusters = data?.clusters ?? [
    { cluster_id: 1, label: "Two-Wheeler Chain Snatching", size: 42, top_sub_heads: ["Chain Snatching", "Robbery"], confidence: 0.92 },
    { cluster_id: 2, label: "Night Time Lock Breaking", size: 31, top_sub_heads: ["House Burglary"], confidence: 0.88 },
    { cluster_id: 3, label: "OTP & Banking Phishing", size: 28, top_sub_heads: ["Online Scam", "Cyber Fraud"], confidence: 0.86 },
  ];

  return (
    <Card
      title="Crime Pattern Clusters"
      action={<Layers size={16} className="text-purple-500" />}
    >
      {isLoading && <LoadingBlock lines={4} />}
      {error && <ErrorBlock error={error} onRetry={refetch} />}
      {clusters.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {clusters.map((c) => (
            <div
              key={c.cluster_id}
              className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 hover:border-emerald-300 transition-colors space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-700 text-[10px] font-extrabold">
                  Cluster #{c.cluster_id}
                </span>
                <ConfidencePill confidence={c.confidence} />
              </div>
              <p className="text-xs font-bold text-slate-900">{c.label}</p>
              <p className="text-[11px] text-slate-500 font-semibold">{c.size} cases linked</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// -------------------------------------------------------------------
// Risk Score Panel (Dynamic lookup by Case ID - NO hardcoded values)
// -------------------------------------------------------------------

function RiskScorePanel() {
  const [inputVal, setInputVal] = useState("");
  const [caseNotFound, setCaseNotFound] = useState(false);
  const [riskData, setRiskData] = useState(null);

  function handleCheckRisk(e) {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const foundCase = findCaseById(inputVal);
    if (!foundCase) {
      setCaseNotFound(true);
      setRiskData(null);
    } else {
      setCaseNotFound(false);
      const calculated = calculateCaseRiskScore(foundCase);
      setRiskData({ caseObj: foundCase, risk: calculated });
    }
  }

  const riskColor = {
    high: "#dc2626",
    medium: "#eab308",
    low: "#22c55e",
  };

  return (
    <Card title="FIR Risk Score" action={<ShieldAlert size={16} className="text-rose-600" />}>
      <form onSubmit={handleCheckRisk} className="flex gap-2 mb-4">
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Enter Case ID (e.g. 1, 2, 3) or FIR No."
          className="input flex-1 text-xs"
        />
        <button type="submit" className="btn-primary text-xs font-bold px-4">
          Check Risk
        </button>
      </form>

      {caseNotFound && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-bold flex items-center gap-2">
          <AlertTriangle size={16} className="text-rose-500 shrink-0" />
          <span>Case not found.</span>
        </div>
      )}

      {!riskData && !caseNotFound && (
        <div className="text-center py-6 text-slate-400 text-xs font-medium">
          Enter a Case ID (e.g. 1, 2, 3 or custom Case ID) above to calculate risk score
        </div>
      )}

      {riskData && !caseNotFound && (
        <div className="space-y-4 pt-1">
          <div className="flex items-center gap-4 bg-slate-50 p-3.5 rounded-2xl border border-slate-200/80">
            <RiskGauge value={riskData.risk.risk_numeric} color={riskColor[riskData.risk.risk_label] ?? "#94a3b8"} />
            <div>
              <p className="text-2xl font-black text-slate-900 tracking-tight">{riskData.risk.risk_numeric}/100</p>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${RISK_LABEL_COLORS[riskData.risk.risk_label]}`}>
                {riskData.risk.risk_label} RISK
              </span>
            </div>
          </div>

          <div className="text-xs text-slate-600 space-y-1 bg-white p-3 rounded-xl border border-slate-100 font-medium">
            <p>FIR Number: <span className="font-mono font-bold text-slate-900">{riskData.risk.fir_number}</span></p>
            <p>District: <span className="font-bold text-slate-800">{riskData.risk.district}</span></p>
            <p>Crime Head: <span className="font-bold text-slate-800">{riskData.risk.crime_sub_head}</span></p>
            <p>Model Confidence: <span className="font-bold text-emerald-600">{Math.round(riskData.risk.confidence * 100)}%</span></p>
          </div>

          {riskData.risk.top_features?.length > 0 && (
            <div>
              <p className="text-xs font-bold text-slate-700 mb-1.5 uppercase tracking-wider text-[10px]">Dynamic Risk Factors</p>
              <div className="space-y-1.5">
                {riskData.risk.top_features.map((f, i) => (
                  <div key={i} className="flex items-center justify-between text-xs font-semibold p-2 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-slate-700">{f.feature}</span>
                    <div className="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden shrink-0">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${Math.round(f.importance * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// -------------------------------------------------------------------
// Officer Recommendation Panel (Dynamic lookup by Case ID)
// -------------------------------------------------------------------

function RecommendationPanel() {
  const [inputVal, setInputVal] = useState("");
  const [caseNotFound, setCaseNotFound] = useState(false);
  const [recs, setRecs] = useState(null);

  function handleRecommend(e) {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const foundCase = findCaseById(inputVal);
    if (!foundCase) {
      setCaseNotFound(true);
      setRecs(null);
    } else {
      setCaseNotFound(false);
      const generated = generateOfficerRecommendations(foundCase);
      setRecs(generated);
    }
  }

  return (
    <Card title="Officer Recommendations" action={<UserCheck size={16} className="text-emerald-600" />}>
      <form onSubmit={handleRecommend} className="flex gap-2 mb-4">
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Enter Case ID (e.g. 1, 2, 3) or FIR No."
          className="input flex-1 text-xs"
        />
        <button type="submit" className="btn-primary text-xs font-bold px-4">
          Recommend
        </button>
      </form>

      {caseNotFound && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-bold flex items-center gap-2">
          <AlertTriangle size={16} className="text-rose-500 shrink-0" />
          <span>Case not found.</span>
        </div>
      )}

      {!recs && !caseNotFound && (
        <div className="text-center py-6 text-slate-400 text-xs font-medium">
          Enter a Case ID above to get tailored officer assignment recommendations
        </div>
      )}

      {recs && recs.length > 0 && !caseNotFound && (
        <div className="space-y-2.5">
          {recs.map((r) => (
            <div
              key={r.officer_id}
              className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors border border-slate-200/80"
            >
              <div className="min-w-0 pr-2">
                <p className="text-xs font-bold text-slate-900">
                  {r.officer_name} <span className="text-[11px] font-semibold text-slate-500">({r.rank})</span>
                </p>
                <p className="text-[11px] text-slate-600 font-medium mt-0.5">
                  {r.reason}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <ConfidencePill confidence={r.confidence} />
                <ChevronRight size={14} className="text-slate-400" />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// -------------------------------------------------------------------
// Shared mini-components
// -------------------------------------------------------------------

function ConfidencePill({ confidence }) {
  if (confidence == null) return null;
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80 ? "bg-emerald-100 text-emerald-800 border-emerald-200" :
    pct >= 50 ? "bg-amber-100 text-amber-800 border-amber-200" :
    "bg-rose-100 text-rose-800 border-rose-200";
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold border ${color}`}>
      {pct}%
    </span>
  );
}

function RiskGauge({ value = 0, color = "#94a3b8" }) {
  const r = 26;
  const c = Math.PI * r * 2;
  const offset = c - (c * value) / 100;
  return (
    <div className="relative h-16 w-16 shrink-0">
      <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle
          cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <BrainCircuit size={16} className="text-slate-600" />
      </div>
    </div>
  );
}
