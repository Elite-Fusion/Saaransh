import React, { useState } from "react";
import Topbar from "../layout/Topbar";
import {
  ClipboardList, Download, FileSpreadsheet, FileText, Printer,
  RefreshCw, Filter, BarChart2, PieChart as PieIcon, CheckCircle2, TrendingUp
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell
} from "recharts";

const MONTHLY_CRIME_DATA = [
  { month: "Jan", cases: 940, solved: 720 },
  { month: "Feb", cases: 1020, solved: 790 },
  { month: "Mar", cases: 1150, solved: 880 },
  { month: "Apr", cases: 1080, solved: 810 },
  { month: "May", cases: 1240, solved: 950 },
];

const STATUS_SUMMARY = [
  { name: "Solved Cases", value: 6789, color: "#10B981" },
  { name: "Under Investigation", value: 5236, color: "#2563EB" },
  { name: "Pending Action", value: 1245, color: "#F59E0B" },
];

export default function Reports() {
  const [dateRange, setDateRange] = useState("This Month");
  const [district, setDistrict] = useState("All Districts");
  const [crimeType, setCrimeType] = useState("All Types");
  const [isGenerating, setIsGenerating] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  function triggerDownload(type) {
    setToastMsg(`Exporting ${type} report for ${district} (${dateRange})...`);
    setTimeout(() => setToastMsg(null), 3500);

    if (type === "Print") {
      window.print();
    }
  }

  function handleGenerateReport() {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setToastMsg("Report generated successfully with latest dataset!");
      setTimeout(() => setToastMsg(null), 3000);
    }, 600);
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900">
      {/* Toast alert */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-4 bg-emerald-600 text-white font-bold text-xs rounded-2xl shadow-xl flex items-center gap-2 border border-emerald-400 animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 size={18} />
          <span>{toastMsg}</span>
        </div>
      )}

      <Topbar title="Reports & Crime Analytics" subtitle="Generate official police reports, export CSV/Excel, and print summaries" />

      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
        {/* Filter & Export Action Bar */}
        <div className="bg-white rounded-[20px] border border-slate-200/80 p-5 shadow-sm space-y-4">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
            {/* Filter Inputs */}
            <div className="flex flex-wrap items-center gap-3 text-xs w-full lg:w-auto">
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
                <span className="font-bold text-slate-400">Date Range:</span>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="Today">Today</option>
                  <option value="Last 7 Days">Last 7 Days</option>
                  <option value="This Month">This Month</option>
                  <option value="Last Month">Last Month</option>
                  <option value="This Year">This Year</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
                <span className="font-bold text-slate-400">District:</span>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All Districts">All Districts</option>
                  <option value="Mysuru">Mysuru</option>
                  <option value="Bengaluru Urban">Bengaluru Urban</option>
                  <option value="Chitradurga">Chitradurga</option>
                  <option value="Tumakuru">Tumakuru</option>
                  <option value="Belagavi">Belagavi</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
                <span className="font-bold text-slate-400">Crime Type:</span>
                <select
                  value={crimeType}
                  onChange={(e) => setCrimeType(e.target.value)}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All Types">All Types</option>
                  <option value="Chain Snatching">Chain Snatching</option>
                  <option value="Vehicle Theft">Vehicle Theft</option>
                  <option value="House Burglary">House Burglary</option>
                  <option value="Cyber Crime">Cyber Crime</option>
                  <option value="Assault">Assault</option>
                </select>
              </div>

              <button
                onClick={handleGenerateReport}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
              >
                <RefreshCw size={14} className={isGenerating ? "animate-spin" : ""} />
                <span>Generate Report</span>
              </button>
            </div>

            {/* Export Buttons */}
            <div className="flex flex-wrap items-center gap-2 text-xs w-full lg:w-auto">
              <button
                onClick={() => triggerDownload("PDF")}
                className="px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <FileText size={14} className="text-rose-600" />
                <span>Download PDF</span>
              </button>

              <button
                onClick={() => triggerDownload("Excel")}
                className="px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <FileSpreadsheet size={14} className="text-emerald-600" />
                <span>Export Excel</span>
              </button>

              <button
                onClick={() => triggerDownload("CSV")}
                className="px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Download size={14} className="text-blue-600" />
                <span>Export CSV</span>
              </button>

              <button
                onClick={() => triggerDownload("Print")}
                className="px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Printer size={14} className="text-slate-700" />
                <span>Print Report</span>
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-white p-5 rounded-[20px] border border-slate-200/80 shadow-sm space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total FIR Reports</span>
            <p className="text-3xl font-black text-slate-900">12,458</p>
            <p className="text-xs font-bold text-emerald-600">+12.5% vs last month</p>
          </div>

          <div className="bg-white p-5 rounded-[20px] border border-slate-200/80 shadow-sm space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Case Clearance Rate</span>
            <p className="text-3xl font-black text-slate-900">54.5%</p>
            <p className="text-xs font-bold text-emerald-600">+4.2% efficiency score</p>
          </div>

          <div className="bg-white p-5 rounded-[20px] border border-slate-200/80 shadow-sm space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Avg Resolution Time</span>
            <p className="text-3xl font-black text-slate-900">4.8 Days</p>
            <p className="text-xs font-bold text-blue-600">-1.2 days faster</p>
          </div>

          <div className="bg-white p-5 rounded-[20px] border border-slate-200/80 shadow-sm space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">High Risk Zones</span>
            <p className="text-3xl font-black text-slate-900">8 Districts</p>
            <p className="text-xs font-bold text-rose-600">Active Alert Level</p>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Monthly Trend Bar Chart */}
          <div className="lg:col-span-2 bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm">Monthly Crime & Solved Cases Report</h3>
              <span className="text-xs font-semibold text-slate-500">{district} &middot; {dateRange}</span>
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={MONTHLY_CRIME_DATA} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ borderRadius: "0.75rem", border: "1px solid #e2e8f0" }} />
                  <Bar dataKey="cases" name="Total FIRs" fill="#2563EB" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="solved" name="Solved Cases" fill="#10B981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Case Status Breakdown Pie Chart */}
          <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm">Case Status Summary</h3>
            </div>

            <div className="h-44 relative my-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={STATUS_SUMMARY}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={74}
                    paddingAngle={3}
                  >
                    {STATUS_SUMMARY.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <p className="text-xl font-black text-slate-900">13,270</p>
                <p className="text-[10px] font-bold text-slate-400 uppercase">Total Cases</p>
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
              {STATUS_SUMMARY.map((s) => (
                <div key={s.name} className="flex items-center justify-between font-semibold">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
                    <span className="text-slate-700">{s.name}</span>
                  </div>
                  <span className="font-bold text-slate-900">{s.value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
