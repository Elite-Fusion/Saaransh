import React, { useState, useRef, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import Topbar from "../layout/Topbar";
import KarnatakaMap from "../components/KarnatakaMap";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../api/dashboard";
import { getAllCases } from "../utils/caseStore";
import { motion } from "framer-motion";
import {
  FileText, ShieldAlert, CheckCircle2, RotateCcw, MapPin,
  ArrowUpRight, ArrowDownRight, Search, ChevronDown, Check,
  Sparkles, Activity, AlertTriangle, RefreshCw, ArrowRight
} from "lucide-react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, AreaChart, Area
} from "recharts";

// Master List of Districts
const DISTRICT_OPTIONS = [
  "All Districts", "Bengaluru Urban", "Mysuru", "Chitradurga", "Tumakuru",
  "Belagavi", "Kalaburagi", "Ballari", "Uttara Kannada", "Hassan", "Mandya",
  "Chamarajanagar", "Davanagere", "Shivamogga", "Bagalkote", "Vijayapura",
  "Raichur", "Kolar", "Udupi", "Kodagu", "Dakshina Kannada", "Chikkaballapura"
];

// Time Periods
const PERIOD_OPTIONS = [
  "Today", "Last 7 Days", "Last 30 Days", "This Month", "Last Month", "This Year", "Custom Range"
];

// Priorities
const PRIORITY_OPTIONS = [
  "All Priorities", "Critical", "High", "Medium", "Low"
];

// Master Crime Types Dataset
const BASE_CRIME_TYPES = [
  { name: "Theft", baseValue: 3550, pct: "28.5%", color: "#2563EB" },
  { name: "Assault", baseValue: 2504, pct: "20.1%", color: "#8B5CF6" },
  { name: "Chain Snatching", baseValue: 1956, pct: "15.7%", color: "#10B981" },
  { name: "Robbery", baseValue: 1532, pct: "12.3%", color: "#F59E0B" },
  { name: "Cyber Crime", baseValue: 1245, pct: "10.0%", color: "#06B6D4" },
  { name: "Others", baseValue: 1671, pct: "13.4%", color: "#64748B" },
];

// Sparkline datasets
const SPARKLINE_DATA = {
  total: [{ v: 10 }, { v: 15 }, { v: 13 }, { v: 18 }, { v: 22 }, { v: 20 }, { v: 26 }],
  active: [{ v: 25 }, { v: 22 }, { v: 20 }, { v: 18 }, { v: 15 }, { v: 16 }, { v: 14 }],
  solved: [{ v: 12 }, { v: 14 }, { v: 18 }, { v: 17 }, { v: 22 }, { v: 25 }, { v: 28 }],
  repeat: [{ v: 8 }, { v: 10 }, { v: 9 }, { v: 12 }, { v: 14 }, { v: 13 }, { v: 16 }],
  districts: [{ v: 5 }, { v: 6 }, { v: 6 }, { v: 7 }, { v: 7 }, { v: 8 }, { v: 8 }],
};

// Master High Risk Districts List
const ALL_HIGH_RISK_DISTRICTS = [
  { name: "Chitradurga", score: 94, trend: "+4%", isUp: true, color: "bg-rose-500", priority: "Critical" },
  { name: "Tumakuru", score: 88, trend: "+2%", isUp: true, color: "bg-rose-500", priority: "Critical" },
  { name: "Bengaluru Urban", score: 87, trend: "+5%", isUp: true, color: "bg-rose-500", priority: "High" },
  { name: "Mysuru", score: 85, trend: "+3%", isUp: true, color: "bg-rose-500", priority: "High" },
  { name: "Chamarajanagar", score: 82, trend: "-1%", isUp: false, color: "bg-amber-500", priority: "Medium" },
  { name: "Uttara Kannada", score: 79, trend: "+1%", isUp: true, color: "bg-amber-500", priority: "Medium" },
  { name: "Ballari", score: 76, trend: "+2%", isUp: true, color: "bg-amber-500", priority: "Medium" },
];

// Master Critical Security Alerts Table Data
const ALL_ALERTS = [
  { id: 1, alert: "Chain Snatching Cluster Detected", district: "Mysuru", priority: "Critical", time: "12 mins ago", status: "Active", priorityColor: "bg-rose-100 text-rose-700 border-rose-200", statusColor: "bg-rose-50 text-rose-600 border-rose-200 animate-pulse" },
  { id: 2, alert: "Repeat Offender Presence Signal", district: "Chitradurga", priority: "High", time: "35 mins ago", status: "Investigating", priorityColor: "bg-amber-100 text-amber-700 border-amber-200", statusColor: "bg-amber-50 text-amber-700 border-amber-200" },
  { id: 3, alert: "Night Burglaries Spurt", district: "Tumakuru", priority: "High", time: "1 hour ago", status: "Investigating", priorityColor: "bg-amber-100 text-amber-700 border-amber-200", statusColor: "bg-amber-50 text-amber-700 border-amber-200" },
  { id: 4, alert: "Vehicle Theft Ring Activity", district: "Bengaluru Urban", priority: "Medium", time: "3 hours ago", status: "Patrol Dispatched", priorityColor: "bg-blue-100 text-blue-700 border-blue-200", statusColor: "bg-blue-50 text-blue-700 border-blue-200" },
  { id: 5, alert: "Cyber Fraud Anomaly", district: "Cyber Cell", priority: "Medium", time: "5 hours ago", status: "Resolved", priorityColor: "bg-emerald-100 text-emerald-700 border-emerald-200", statusColor: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { id: 6, alert: "Armed Robbery Warning", district: "Ballari", priority: "Critical", time: "6 hours ago", status: "Active", priorityColor: "bg-rose-100 text-rose-700 border-rose-200", statusColor: "bg-rose-50 text-rose-600 border-rose-200 animate-pulse" },
  { id: 7, alert: "Illegal Transit Spike", district: "Chamarajanagar", priority: "Low", time: "8 hours ago", status: "Resolved", priorityColor: "bg-slate-100 text-slate-700 border-slate-200", statusColor: "bg-emerald-50 text-emerald-700 border-emerald-200" },
];

export default function Dashboard() {
  // ---- React Filter States ----
  const [selectedControlRoom, setSelectedControlRoom] = useState("State Control Room (Bengaluru)");
  const [selectedDistrict, setSelectedDistrict] = useState("All Districts");
  const [selectedPeriod, setSelectedPeriod] = useState("This Month");
  const [selectedPriority, setSelectedPriority] = useState("All Priorities");
  const [searchQuery, setSearchQuery] = useState("");

  // Store cases
  const [storeCases, setStoreCases] = useState(() => getAllCases());

  // Dropdown open states
  const [districtDropdownOpen, setDistrictDropdownOpen] = useState(false);
  const [periodDropdownOpen, setPeriodDropdownOpen] = useState(false);
  const [priorityDropdownOpen, setPriorityDropdownOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Refs for outside click handlers
  const districtRef = useRef(null);
  const periodRef = useRef(null);
  const priorityRef = useRef(null);

  // Sync state with case creation events
  useEffect(() => {
    function handleCaseCreated() {
      setStoreCases(getAllCases());
    }
    window.addEventListener("saaransh_case_created", handleCaseCreated);
    return () => window.removeEventListener("saaransh_case_created", handleCaseCreated);
  }, []);

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (districtRef.current && !districtRef.current.contains(e.target)) setDistrictDropdownOpen(false);
      if (periodRef.current && !periodRef.current.contains(e.target)) setPeriodDropdownOpen(false);
      if (priorityRef.current && !priorityRef.current.contains(e.target)) setPriorityDropdownOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => dashboardApi.getSummary(),
  });

  // ---- DYNAMIC FILTERED DATA COMPUTATIONS ----

  // Period multiplier factor
  const periodMultiplier = useMemo(() => {
    switch (selectedPeriod) {
      case "Today": return 0.035;
      case "Last 7 Days": return 0.25;
      case "Last 30 Days": return 0.95;
      case "This Month": return 1.0;
      case "Last Month": return 0.92;
      case "This Year": return 11.5;
      default: return 1.0;
    }
  }, [selectedPeriod]);

  // District multiplier factor
  const districtMultiplier = useMemo(() => {
    if (selectedDistrict === "All Districts") return 1.0;
    if (["Bengaluru Urban", "Mysuru", "Chitradurga"].includes(selectedDistrict)) return 0.18;
    if (["Tumakuru", "Ballari", "Belagavi"].includes(selectedDistrict)) return 0.12;
    return 0.08;
  }, [selectedDistrict]);

  // Dynamic KPI Card Calculations
  const kpiStats = useMemo(() => {
    const mult = periodMultiplier * districtMultiplier;

    const baseTotal = (summary?.total_firs ?? 12458) + storeCases.length;
    const totalFirs = Math.round(baseTotal * mult);
    const activeCases = Math.round((summary?.active_cases ?? 5236) * mult);
    const solvedCases = Math.round((summary?.solved_cases ?? 6789) * mult);
    const repeatOffenders = Math.round((summary?.repeat_offenders ?? 1245) * mult);
    const highRiskDistricts = selectedDistrict === "All Districts" ? 8 : (["Chitradurga", "Tumakuru", "Bengaluru Urban", "Mysuru", "Chamarajanagar"].includes(selectedDistrict) ? 1 : 0);

    return [
      { key: "total_firs", label: `Total FIRs (${selectedPeriod})`, value: totalFirs.toLocaleString(), delta: "+12.5%", isUp: true, icon: FileText, sparkline: SPARKLINE_DATA.total, color: "#10B981" },
      { key: "active_cases", label: "Active Cases", value: activeCases.toLocaleString(), delta: "-8.7%", isUp: false, icon: ShieldAlert, sparkline: SPARKLINE_DATA.active, color: "#2563EB" },
      { key: "solved_cases", label: "Solved Cases", value: solvedCases.toLocaleString(), delta: "+15.2%", isUp: true, icon: CheckCircle2, sparkline: SPARKLINE_DATA.solved, color: "#10B981" },
      { key: "repeat_offenders", label: "Repeat Offenders", value: repeatOffenders.toLocaleString(), delta: "+10.1%", isUp: true, icon: RotateCcw, sparkline: SPARKLINE_DATA.repeat, color: "#F59E0B" },
      { key: "high_risk_districts", label: "High Risk Districts", value: highRiskDistricts.toString(), delta: selectedDistrict === "All Districts" ? "↑ 2 vs last month" : `${selectedDistrict} Selected`, isUp: false, isBadge: true, icon: MapPin, sparkline: SPARKLINE_DATA.districts, color: "#EF4444" },
    ];
  }, [summary, storeCases, periodMultiplier, districtMultiplier, selectedPeriod, selectedDistrict]);

  // Dynamic Donut Chart Data
  const crimeTypesData = useMemo(() => {
    return BASE_CRIME_TYPES.map((item) => ({
      ...item,
      value: Math.round(item.baseValue * periodMultiplier * districtMultiplier),
    }));
  }, [periodMultiplier, districtMultiplier]);

  const donutTotal = useMemo(() => {
    return crimeTypesData.reduce((acc, curr) => acc + curr.value, 0).toLocaleString();
  }, [crimeTypesData]);

  // Unified FIR Activity List
  const allActivityItems = useMemo(() => {
    const formattedStore = storeCases.map((c) => ({
      case_id: c.case_id,
      fir: c.fir_number || c.crime_no,
      crime: c.crime_category || c.crime_sub_category || "General Crime",
      officer: "PSI Mahesh",
      location: c.place_of_occurrence || c.district || "Mysuru",
      district: c.district || c.incident_district || "Mysuru",
      time: "Just now",
      priority: c.priority || "High",
      status: c.status || "Under Investigation",
      statusColor: "bg-amber-50 text-amber-700 border-amber-200"
    }));

    return [...formattedStore];
  }, [storeCases]);

  // Filtered Recent Activity List
  const filteredActivity = useMemo(() => {
    return allActivityItems.filter((item) => {
      // District filter
      const matchesDistrict = selectedDistrict === "All Districts" || item.district === selectedDistrict;
      // Priority filter
      const matchesPriority = selectedPriority === "All Priorities" || item.priority === selectedPriority;
      // Search query
      const matchesSearch = !searchQuery ||
        String(item.case_id).toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.fir.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.crime.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.officer.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.location.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesDistrict && matchesPriority && matchesSearch;
    });
  }, [allActivityItems, selectedDistrict, selectedPriority, searchQuery]);

  // Filtered High Risk Districts Ranking
  const filteredHighRiskDistricts = useMemo(() => {
    return ALL_HIGH_RISK_DISTRICTS.filter((item) => {
      const matchesDistrict = selectedDistrict === "All Districts" || item.name === selectedDistrict;
      const matchesPriority = selectedPriority === "All Priorities" || item.priority === selectedPriority;
      return matchesDistrict && matchesPriority;
    });
  }, [selectedDistrict, selectedPriority]);

  // Filtered Critical Security Alerts Table
  const filteredAlerts = useMemo(() => {
    return ALL_ALERTS.filter((item) => {
      const matchesDistrict = selectedDistrict === "All Districts" || item.district === selectedDistrict;
      const matchesPriority = selectedPriority === "All Priorities" || item.priority === selectedPriority;
      const matchesSearch = !searchQuery ||
        item.alert.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.district.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.status.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesDistrict && matchesPriority && matchesSearch;
    });
  }, [selectedDistrict, selectedPriority, searchQuery]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setStoreCases(getAllCases());
    setTimeout(() => setIsRefreshing(false), 500);
  };

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900 selection:bg-emerald-500 selection:text-white">
      {/* ---- Top Bar / Header with Functional Control Room Dropdown ---- */}
      <Topbar
        title="Dashboard Overview"
        subtitle="Real-time crime intelligence at a glance"
        selectedControlRoom={selectedControlRoom}
        onSelectControlRoom={(room) => setSelectedControlRoom(room)}
      />

      {/* Main Container */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="p-6 md:p-8 max-w-7xl mx-auto space-y-8"
      >
        {/* ---- Top Controls & Search Bar with Fully Working Dropdown Filters ---- */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-4 rounded-[20px] border border-slate-200/80 shadow-sm relative z-20">
          {/* Search Bar Input */}
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Case ID (e.g. 1, 101), FIRs, locations..."
              className="w-full bg-slate-50 border border-slate-200/80 rounded-xl pl-10 pr-4 py-2 text-xs font-semibold text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
            />
          </div>

          {/* Functional Filter Dropdowns */}
          <div className="flex items-center gap-3 overflow-visible w-full sm:w-auto">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap">Filter:</span>

            {/* 1. All Districts Dropdown */}
            <div className="relative" ref={districtRef}>
              <button
                onClick={() => {
                  setDistrictDropdownOpen(!districtDropdownOpen);
                  setPeriodDropdownOpen(false);
                  setPriorityDropdownOpen(false);
                }}
                className="px-3.5 py-2 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200/80 text-xs font-bold transition-all shadow-xs flex items-center gap-2 cursor-pointer hover:bg-emerald-100/60"
              >
                <span>{selectedDistrict}</span>
                <ChevronDown size={14} className={`transition-transform duration-200 ${districtDropdownOpen ? "rotate-180" : ""}`} />
              </button>

              {districtDropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-slate-200 shadow-xl py-1 z-50 text-xs max-h-64 overflow-y-auto thin-scroll">
                  <div className="px-3 py-1.5 font-bold text-[10px] uppercase text-slate-400 border-b border-slate-100 tracking-wider">
                    Select District
                  </div>
                  {DISTRICT_OPTIONS.map((d) => (
                    <button
                      key={d}
                      onClick={() => {
                        setSelectedDistrict(d);
                        setDistrictDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 font-semibold transition-colors ${
                        selectedDistrict === d ? "text-emerald-700 font-bold bg-emerald-50/50" : "text-slate-700"
                      }`}
                    >
                      <span>{d}</span>
                      {selectedDistrict === d && <Check size={14} className="text-emerald-600 shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 2. Time Period Filter Dropdown */}
            <div className="relative" ref={periodRef}>
              <button
                onClick={() => {
                  setPeriodDropdownOpen(!periodDropdownOpen);
                  setDistrictDropdownOpen(false);
                  setPriorityDropdownOpen(false);
                }}
                className="px-3.5 py-2 bg-slate-50 text-slate-700 hover:bg-slate-100 rounded-xl border border-slate-200/80 text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer"
              >
                <span>{selectedPeriod}</span>
                <ChevronDown size={14} className={`text-slate-500 transition-transform duration-200 ${periodDropdownOpen ? "rotate-180" : ""}`} />
              </button>

              {periodDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl border border-slate-200 shadow-xl py-1 z-50 text-xs">
                  <div className="px-3 py-1.5 font-bold text-[10px] uppercase text-slate-400 border-b border-slate-100 tracking-wider">
                    Time Period
                  </div>
                  {PERIOD_OPTIONS.map((p) => (
                    <button
                      key={p}
                      onClick={() => {
                        setSelectedPeriod(p);
                        setPeriodDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 font-semibold transition-colors ${
                        selectedPeriod === p ? "text-emerald-700 font-bold bg-emerald-50/50" : "text-slate-700"
                      }`}
                    >
                      <span>{p}</span>
                      {selectedPeriod === p && <Check size={14} className="text-emerald-600 shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 3. Priority Filter Dropdown */}
            <div className="relative" ref={priorityRef}>
              <button
                onClick={() => {
                  setPriorityDropdownOpen(!priorityDropdownOpen);
                  setDistrictDropdownOpen(false);
                  setPeriodDropdownOpen(false);
                }}
                className="px-3.5 py-2 bg-slate-50 text-slate-700 hover:bg-slate-100 rounded-xl border border-slate-200/80 text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer"
              >
                <span>{selectedPriority}</span>
                <ChevronDown size={14} className={`text-slate-500 transition-transform duration-200 ${priorityDropdownOpen ? "rotate-180" : ""}`} />
              </button>

              {priorityDropdownOpen && (
                <div className="absolute right-0 mt-2 w-44 bg-white rounded-xl border border-slate-200 shadow-xl py-1 z-50 text-xs">
                  <div className="px-3 py-1.5 font-bold text-[10px] uppercase text-slate-400 border-b border-slate-100 tracking-wider">
                    Priority Level
                  </div>
                  {PRIORITY_OPTIONS.map((pr) => (
                    <button
                      key={pr}
                      onClick={() => {
                        setSelectedPriority(pr);
                        setPriorityDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 font-semibold transition-colors ${
                        selectedPriority === pr ? "text-emerald-700 font-bold bg-emerald-50/50" : "text-slate-700"
                      }`}
                    >
                      <span>{pr}</span>
                      {selectedPriority === pr && <Check size={14} className="text-emerald-600 shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ---- KPI Statistic Cards Row ---- */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
          {kpiStats.map((card) => {
            const Icon = card.icon;

            return (
              <motion.div
                key={card.key}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className="bg-white p-5 rounded-[20px] border border-slate-200/80 shadow-sm hover:shadow-md transition-all flex flex-col justify-between relative overflow-hidden group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-500 tracking-tight">{card.label}</span>
                  <div className="h-8 w-8 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-700 group-hover:bg-emerald-50 group-hover:text-emerald-600 transition-colors">
                    <Icon size={16} />
                  </div>
                </div>

                <div className="mt-4">
                  <h3 className="text-3xl font-black text-slate-900 tracking-tight">{card.value}</h3>
                  <div className="flex items-center justify-between mt-2">
                    <span className={`text-[11px] font-bold flex items-center gap-0.5 ${
                      card.isUp ? "text-emerald-600" : "text-rose-500"
                    }`}>
                      {card.isUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                      {card.delta}
                    </span>

                    {/* Mini Sparkline Chart */}
                    <div className="w-16 h-8">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={card.sparkline}>
                          <defs>
                            <linearGradient id={`grad-${card.key}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor={card.color} stopOpacity={0.4} />
                              <stop offset="100%" stopColor={card.color} stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <Area type="monotone" dataKey="v" stroke={card.color} strokeWidth={2} fill={`url(#grad-${card.key})`} isAnimationActive={true} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* ---- Main Dashboard Grid (70% Left Map | 30% Right Charts) ---- */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left (70%): Large Crime Intelligence Map */}
          <div className="lg:col-span-2 bg-white rounded-[20px] border border-slate-200/80 p-2 shadow-sm flex flex-col min-h-[480px]">
            <KarnatakaMap
              selectedDistrict={selectedDistrict !== "All Districts" ? { id: selectedDistrict.toLowerCase().replace(/\s+/g, "_"), name: selectedDistrict } : null}
              className="flex-1 rounded-[18px]"
            />
          </div>

          {/* Right (30%): Donut Chart & AI Prediction Card */}
          <div className="space-y-6 flex flex-col justify-between">
            {/* Donut Chart: Top Crime Distribution */}
            <div className="bg-white rounded-[20px] border border-slate-200/80 p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="font-bold text-slate-900 text-sm">Crime Distribution <span className="text-xs font-medium text-slate-400">({selectedPeriod})</span></h3>
                <Link to="/analytics" className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1">
                  <span>View All</span>
                  <ArrowRight size={13} />
                </Link>
              </div>

              {/* Recharts Donut */}
              <div className="h-44 relative my-1">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={crimeTypesData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={54}
                      outerRadius={76}
                      paddingAngle={3}
                    >
                      {crimeTypesData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(val) => val.toLocaleString()} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <p className="text-2xl font-black text-slate-900 leading-tight">{donutTotal}</p>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Filtered FIRs</p>
                </div>
              </div>

              {/* Categories Grid Breakdown */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
                {crimeTypesData.map((item) => (
                  <div key={item.name} className="flex items-center justify-between text-xs font-semibold p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 truncate">
                      <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: item.color }} />
                      <span className="text-slate-700 truncate">{item.name}</span>
                    </div>
                    <span className="font-extrabold text-slate-900">{item.pct}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Prediction Card */}
            <div className="bg-gradient-to-br from-rose-50/80 via-orange-50/40 to-white border border-rose-200/80 rounded-[20px] p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-rose-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles size={15} className="text-rose-600 animate-pulse" />
                  AI Prediction ({selectedPeriod})
                </h3>
                <span className="text-[10px] font-extrabold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">High Alert</span>
              </div>

              <p className="text-xs font-bold text-slate-800 leading-relaxed">
                High probability of <span className="text-rose-700 font-extrabold">Chain Snatching</span> in {selectedDistrict !== "All Districts" ? selectedDistrict : "Mysuru, Mandya, Bengaluru City"}
              </p>

              <div className="flex items-center justify-between pt-2 border-t border-rose-100/80">
                <div className="flex items-center gap-3">
                  {/* Circular Gauge SVG */}
                  <div className="relative h-14 w-14">
                    <svg viewBox="0 0 64 64" className="h-14 w-14 -rotate-90">
                      <circle cx="32" cy="32" r="26" fill="none" stroke="#fecaca" strokeWidth="6" />
                      <circle
                        cx="32" cy="32" r="26" fill="none" stroke="#e11d48" strokeWidth="6"
                        strokeDasharray={163.3} strokeDashoffset={163.3 * (1 - 0.87)} strokeLinecap="round"
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-black text-slate-900">
                      87%
                    </span>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Confidence</p>
                    <p className="text-xs font-extrabold text-slate-800">87% AI Model</p>
                  </div>
                </div>

                <Link
                  to="/predictions"
                  className="px-3.5 py-2 rounded-xl bg-white border border-rose-200 text-xs font-extrabold text-slate-800 hover:bg-rose-50 transition-colors shadow-xs"
                >
                  View Details
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* ---- Lower Section: Two Equal Width Cards (Recent FIR Activity | High Risk Districts) ---- */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Card 1: Recent FIR Activity Timeline */}
          <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Activity size={18} className="text-emerald-600" />
                <h3 className="font-bold text-slate-900 text-sm">Recent FIR Activity</h3>
              </div>
              <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
                Live Stream ({filteredActivity.length})
              </span>
            </div>

            <div className="space-y-3">
              {filteredActivity.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <p className="text-xs font-semibold text-slate-500">No FIR activity matches current filter parameters.</p>
                </div>
              ) : (
                filteredActivity.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-slate-50/70 border border-slate-100 hover:bg-slate-50 transition-colors">
                    <div className="space-y-0.5 min-w-0 flex-1 pr-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-black text-slate-900">Case #{item.case_id} &middot; {item.fir}</span>
                        <span className="text-xs font-bold text-slate-700">• {item.crime}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 font-medium truncate">
                        Officer: <span className="font-semibold text-slate-700">{item.officer}</span> — {item.location}
                      </p>
                    </div>

                    <div className="text-right shrink-0">
                      <span className={`inline-block text-[10px] font-extrabold px-2.5 py-1 rounded-full border ${item.statusColor}`}>
                        {item.status}
                      </span>
                      <p className="text-[10px] font-semibold text-slate-400 mt-1">{item.time}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Card 2: High Risk Districts Ranking */}
          <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-rose-600" />
                <h3 className="font-bold text-slate-900 text-sm">High Risk Districts Ranking</h3>
              </div>
              <Link to="/map" className="text-xs font-bold text-emerald-600 hover:text-emerald-700">
                View Risk Map
              </Link>
            </div>

            <div className="space-y-4 pt-1">
              {filteredHighRiskDistricts.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <p className="text-xs font-semibold text-slate-500">No districts match the selected priority or district filter.</p>
                </div>
              ) : (
                filteredHighRiskDistricts.map((d, i) => (
                  <div key={d.name} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-black text-slate-400 w-4">#{i + 1}</span>
                        <span className="font-bold text-slate-800">{d.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-black text-slate-900">{d.score}% Risk</span>
                        <span className={`text-[10px] font-extrabold ${d.isUp ? "text-rose-600" : "text-emerald-600"}`}>
                          {d.trend}
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full ${d.color} rounded-full transition-all duration-500`} style={{ width: `${d.score}%` }} />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ---- Bottom Section: Recent Critical Security Alerts Table ---- */}
        <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-base tracking-tight">Critical Security Alerts</h3>
              <p className="text-xs text-slate-500 font-medium">Real-time crime triggers and automated AI alerts ({filteredAlerts.length})</p>
            </div>
            <button
              onClick={handleRefresh}
              className="px-3.5 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw size={13} className={isRefreshing ? "animate-spin text-emerald-600" : ""} />
              <span>Refresh Alerts</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Alert Name</th>
                  <th className="py-3 px-4">District</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Time</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500 font-semibold">
                      No security alerts match current filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredAlerts.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-rose-500 shrink-0" />
                        <span>{row.alert}</span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-700">{row.district}</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${row.priorityColor}`}>
                          {row.priority}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-500">{row.time}</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${row.statusColor}`}>
                          {row.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button className="text-xs font-bold text-emerald-600 hover:text-emerald-700 hover:underline">
                          Investigate
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
    </div>
  );
}