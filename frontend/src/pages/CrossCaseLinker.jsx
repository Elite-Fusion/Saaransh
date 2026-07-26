import React, { useState } from "react";
import Topbar from "../layout/Topbar";
import { Sparkles, Share2, AlertTriangle, CheckCircle, Search, ArrowRight } from "lucide-react";

const LINKED_NODES = [
  { id: "bengaluru", name: "Bengaluru City", cases: "3 Linked Cases", similarity: "high", color: "#dc2626", angle: 30 },
  { id: "chamarajanagar", name: "Chamarajanagar", cases: "1 Linked Case", similarity: "high", color: "#dc2626", angle: 90 },
  { id: "hassan", name: "Hassan", cases: "2 Linked Cases", similarity: "low", color: "#84cc16", angle: 160 },
  { id: "davanagere", name: "Davanagere", cases: "1 Linked Case", similarity: "low", color: "#84cc16", angle: 220 },
  { id: "mandya", name: "Mandya", cases: "2 Linked Cases", similarity: "high", color: "#dc2626", angle: 310 },
];

export default function CrossCaseLinker() {
  const [baseFir, setBaseFir] = useState("MRPS/2025/12345");
  const [linkStrength, setLinkStrength] = useState("All");
  const [crimeType, setCrimeType] = useState("All");

  return (
    <div className="bg-slate-50 min-h-screen pb-12">
      <Topbar title="Cross Case Linker" subtitle="AI identifies connections between cases across districts" />

      <div className="p-8 max-w-7xl mx-auto space-y-6">
        {/* Top Control Bar */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-wrap flex-1">
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Select Base FIR</label>
              <select
                value={baseFir}
                onChange={(e) => setBaseFir(e.target.value)}
                className="input text-xs font-semibold py-1.5"
              >
                <option value="MRPS/2025/12345">MRPS/2025/12345</option>
                <option value="MRPS/2025/11234">MRPS/2025/11234</option>
                <option value="MRPS/2025/10876">MRPS/2025/10876</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Link Strength</label>
              <select
                value={linkStrength}
                onChange={(e) => setLinkStrength(e.target.value)}
                className="input text-xs font-semibold py-1.5"
              >
                <option value="All">All</option>
                <option value="High">High Only</option>
                <option value="Medium">Medium Only</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Crime Type</label>
              <select
                value={crimeType}
                onChange={(e) => setCrimeType(e.target.value)}
                className="input text-xs font-semibold py-1.5"
              >
                <option value="All">All</option>
                <option value="Chain Snatching">Chain Snatching</option>
                <option value="Theft">Theft</option>
              </select>
            </div>
          </div>

          <button className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors shadow-sm flex items-center gap-2">
            <Sparkles size={14} />
            <span>Analyze Connections</span>
          </button>
        </div>

        {/* Main Content Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Radial Graph Diagram */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between min-h-[460px] relative overflow-hidden">
            {/* Center Node & Radial Connections Canvas */}
            <div className="relative w-full h-[360px] flex items-center justify-center">
              {/* Connection Lines (SVG Overlay) */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                {LINKED_NODES.map((node) => {
                  const rad = (node.angle * Math.PI) / 180;
                  const r = 140; // radius
                  const cx = 260; // center X (approx)
                  const cy = 180; // center Y
                  const x = cx + r * Math.cos(rad);
                  const y = cy + r * Math.sin(rad);

                  return (
                    <g key={node.id}>
                      <line
                        x1={cx}
                        y1={cy}
                        x2={x}
                        y2={y}
                        stroke={node.color}
                        strokeWidth="2"
                        strokeDasharray={node.similarity === "medium" ? "4,4" : "none"}
                      />
                      {/* Similarity Badge on Line */}
                      <rect
                        x={(cx + x) / 2 - 25}
                        y={(cy + y) / 2 - 8}
                        width="50"
                        height="16"
                        rx="4"
                        fill="#ffffff"
                        stroke={node.color}
                        strokeWidth="1"
                      />
                      <text
                        x={(cx + x) / 2}
                        y={(cy + y) / 2 + 3}
                        fontSize="8"
                        fontWeight="bold"
                        fill={node.color}
                        textAnchor="middle"
                      >
                        {node.similarity === "high" ? "High Similarity" : "Low Similarity"}
                      </text>
                    </g>
                  );
                })}
              </svg>

              {/* Center Base FIR Node */}
              <div className="z-10 bg-emerald-600 text-white p-4 rounded-full shadow-lg text-center border-4 border-emerald-100 flex flex-col items-center justify-center w-28 h-28">
                <FileIcon size={20} className="mb-1" />
                <p className="text-[10px] font-mono font-bold leading-tight">{baseFir}</p>
                <p className="text-[9px] font-semibold text-emerald-200">Mysuru</p>
              </div>

              {/* Linked District Nodes */}
              {LINKED_NODES.map((node) => {
                const rad = (node.angle * Math.PI) / 180;
                const r = 140;
                const style = {
                  transform: `translate(${r * Math.cos(rad)}px, ${r * Math.sin(rad)}px)`,
                };

                return (
                  <div
                    key={node.id}
                    style={style}
                    className="absolute bg-white border border-slate-200 p-2.5 rounded-xl shadow-md text-center w-28 z-10 hover:scale-105 transition-transform cursor-pointer"
                  >
                    <p className="text-xs font-bold text-slate-900 leading-tight">{node.name}</p>
                    <p className="text-[10px] text-slate-500 font-semibold">{node.cases}</p>
                  </div>
                );
              })}
            </div>

            {/* Bottom Graph Legend */}
            <div className="flex items-center justify-center gap-6 pt-4 border-t border-slate-100 text-xs font-semibold text-slate-600">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-red-600" />
                <span>High Similarity</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-amber-500" />
                <span>Medium Similarity</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-lime-500" />
                <span>Low Similarity</span>
              </div>
            </div>
          </div>

          {/* Connection Insights Panel */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <h2 className="font-bold text-slate-900 text-sm">Connection Insights</h2>

              {/* Alert Box */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs font-semibold text-amber-900 flex items-start gap-2">
                <Sparkles size={16} className="text-amber-600 shrink-0 mt-0.5" />
                <span>AI has found 9 linked cases across 5 districts</span>
              </div>

              {/* Metric 1: Modus Operandi */}
              <div className="space-y-1.5 pt-2">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-600">Modus Operandi Match</span>
                  <span className="font-bold text-amber-600">92%</span>
                </div>
                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: "92%" }} />
                </div>
              </div>

              {/* Metric 2: Same Offender */}
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-bold text-red-700 uppercase">Same Offender</p>
                  <p className="text-xs font-bold text-red-900">High Probability</p>
                </div>
                <AlertTriangle size={18} className="text-red-600" />
              </div>

              {/* Metric 3: Time Pattern Match */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-600">Time Pattern Match</span>
                  <span className="font-bold text-emerald-600">89%</span>
                </div>
                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: "89%" }} />
                </div>
              </div>

              <button className="w-full mt-4 py-2.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-700 transition-colors border border-slate-200">
                View All Linked Cases
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FileIcon({ size, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}