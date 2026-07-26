import React, { useState, useMemo } from "react";
import Topbar from "../layout/Topbar";
import {
  Bell, Search, Filter, ShieldAlert, CheckCircle2, UserPlus,
  Trash2, Eye, RefreshCw, ChevronLeft, ChevronRight, AlertTriangle, Check
} from "lucide-react";

// Master Alerts Dataset
const INITIAL_ALERTS = [
  { id: "ALT-2025-001", alert: "Chain Snatching Cluster Detected", crimeType: "Chain Snatching", district: "Mysuru", priority: "Critical", officer: "PSI Mahesh", date: "2025-05-30 14:15", status: "Open" },
  { id: "ALT-2025-002", alert: "Repeat Offender Presence Signal", crimeType: "Robbery", district: "Chitradurga", priority: "High", officer: "Inspector Naik", date: "2025-05-30 13:40", status: "Investigating" },
  { id: "ALT-2025-003", alert: "Night Burglaries Spurt Warning", crimeType: "House Burglary", district: "Tumakuru", priority: "High", officer: "PSI Kumar", date: "2025-05-30 11:20", status: "Investigating" },
  { id: "ALT-2025-004", alert: "Vehicle Theft Ring Activity", crimeType: "Vehicle Theft", district: "Bengaluru Urban", priority: "Medium", officer: "Inspector Rao", date: "2025-05-30 09:50", status: "Open" },
  { id: "ALT-2025-005", alert: "Cyber Fraud Anomaly Trigger", crimeType: "Cyber Fraud", district: "Bengaluru Urban", priority: "Medium", officer: "Inspector Ananya", date: "2025-05-29 18:30", status: "Resolved" },
  { id: "ALT-2025-006", alert: "Armed Robbery Movement Alert", crimeType: "Robbery", district: "Ballari", priority: "Critical", officer: "PSI Gowda", date: "2025-05-29 16:10", status: "Open" },
  { id: "ALT-2025-007", alert: "Illegal Transit Spike Detected", crimeType: "Smuggling", district: "Chamarajanagar", priority: "Low", officer: "PSI Ramesh", date: "2025-05-29 12:00", status: "Resolved" },
  { id: "ALT-2025-008", alert: "High Density Assault Warning", crimeType: "Assault", district: "Belagavi", priority: "High", officer: "Inspector Patil", date: "2025-05-28 20:45", status: "Open" },
];

const OFFICERS = ["PSI Mahesh", "Inspector Rao", "PSI Kumar", "Inspector Naik", "Inspector Ananya", "PSI Gowda"];

export default function Alerts() {
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [searchQ, setSearchQ] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("All");
  const [districtFilter, setDistrictFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [page, setPage] = useState(1);
  const pageSize = 5;

  const [assigningAlertId, setAssigningAlertId] = useState(null);
  const [selectedAlertModal, setSelectedAlertModal] = useState(null);

  // Filter Logic
  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      const matchesSearch = !searchQ ||
        a.id.toLowerCase().includes(searchQ.toLowerCase()) ||
        a.alert.toLowerCase().includes(searchQ.toLowerCase()) ||
        a.crimeType.toLowerCase().includes(searchQ.toLowerCase()) ||
        a.district.toLowerCase().includes(searchQ.toLowerCase()) ||
        a.officer.toLowerCase().includes(searchQ.toLowerCase());

      const matchesPriority = priorityFilter === "All" || a.priority === priorityFilter;
      const matchesDistrict = districtFilter === "All" || a.district === districtFilter;
      const matchesStatus = statusFilter === "All" || a.status === statusFilter;

      return matchesSearch && matchesPriority && matchesDistrict && matchesStatus;
    });
  }, [alerts, searchQ, priorityFilter, districtFilter, statusFilter]);

  const totalPages = Math.ceil(filteredAlerts.length / pageSize) || 1;
  const paginatedAlerts = filteredAlerts.slice((page - 1) * pageSize, page * pageSize);

  // Actions
  function markResolved(id) {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: "Resolved" } : a))
    );
  }

  function deleteAlert(id) {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  function assignOfficer(id, officerName) {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, officer: officerName, status: "Investigating" } : a))
    );
    setAssigningAlertId(null);
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900">
      <Topbar title="Alerts Management" subtitle="Real-time security triggers, threat alerts, and automated dispatches" />

      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
        {/* Top Control Header Card */}
        <div className="bg-white rounded-[20px] border border-slate-200/80 p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Search Input */}
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                value={searchQ}
                onChange={(e) => { setSearchQ(e.target.value); setPage(1); }}
                placeholder="Search Alert ID, crime type, officer..."
                className="input w-full pl-10 text-xs"
              />
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto text-xs">
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl">
                <span className="font-bold text-slate-400">Priority:</span>
                <select
                  value={priorityFilter}
                  onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All">All Priorities</option>
                  <option value="Critical">Critical</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl">
                <span className="font-bold text-slate-400">District:</span>
                <select
                  value={districtFilter}
                  onChange={(e) => { setDistrictFilter(e.target.value); setPage(1); }}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All">All Districts</option>
                  <option value="Mysuru">Mysuru</option>
                  <option value="Bengaluru Urban">Bengaluru Urban</option>
                  <option value="Chitradurga">Chitradurga</option>
                  <option value="Tumakuru">Tumakuru</option>
                  <option value="Ballari">Ballari</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl">
                <span className="font-bold text-slate-400">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All">All Status</option>
                  <option value="Open">Open</option>
                  <option value="Investigating">Investigating</option>
                  <option value="Resolved">Resolved</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Alerts Table Card */}
        <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="font-bold text-slate-900 text-sm">Security Alerts Feed ({filteredAlerts.length})</h2>
            <span className="text-xs font-semibold text-slate-500">Showing page {page} of {totalPages}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Alert ID</th>
                  <th className="py-3 px-4">Crime / Trigger</th>
                  <th className="py-3 px-4">District</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Assigned Officer</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400 font-semibold">
                      No security alerts match the selected criteria.
                    </td>
                  </tr>
                ) : (
                  paginatedAlerts.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{a.id}</td>
                      <td className="py-3.5 px-4">
                        <p className="font-bold text-slate-900">{a.alert}</p>
                        <p className="text-[10px] text-slate-500">{a.crimeType}</p>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-700">{a.district}</td>
                      <td className="py-3.5 px-4">
                        <PriorityBadge priority={a.priority} />
                      </td>
                      <td className="py-3.5 px-4">
                        {assigningAlertId === a.id ? (
                          <select
                            autoFocus
                            onChange={(e) => assignOfficer(a.id, e.target.value)}
                            onBlur={() => setAssigningAlertId(null)}
                            className="bg-white border border-emerald-300 rounded px-2 py-1 text-xs font-semibold text-slate-800"
                          >
                            <option value="">Select Officer...</option>
                            {OFFICERS.map((o) => (
                              <option key={o} value={o}>{o}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                            {a.officer}
                            <button
                              onClick={() => setAssigningAlertId(a.id)}
                              className="text-[10px] text-emerald-600 hover:underline font-bold"
                            >
                              (Change)
                            </button>
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-500">{a.date}</td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={a.status} />
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedAlertModal(a)}
                            title="View Alert"
                            className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
                          >
                            <Eye size={15} />
                          </button>

                          {a.status !== "Resolved" && (
                            <button
                              onClick={() => markResolved(a.id)}
                              title="Mark Resolved"
                              className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-[11px] font-bold hover:bg-emerald-100"
                            >
                              Resolve
                            </button>
                          )}

                          <button
                            onClick={() => deleteAlert(a.id)}
                            title="Delete Alert"
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
            <p className="text-slate-500 font-semibold">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filteredAlerts.length)} of {filteredAlerts.length} alerts
            </p>

            <div className="flex items-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="p-2 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50 font-bold"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="font-bold text-slate-700">Page {page} / {totalPages}</span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="p-2 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50 font-bold"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* View Alert Details Modal */}
      {selectedAlertModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Alert Details</h3>
              <button onClick={() => setSelectedAlertModal(null)} className="text-slate-400 hover:text-slate-600 font-bold">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <p><span className="font-bold text-slate-500">Alert ID:</span> <span className="font-mono font-bold text-slate-900">{selectedAlertModal.id}</span></p>
              <p><span className="font-bold text-slate-500">Trigger:</span> <span className="font-bold text-slate-900">{selectedAlertModal.alert}</span></p>
              <p><span className="font-bold text-slate-500">Crime Type:</span> {selectedAlertModal.crimeType}</p>
              <p><span className="font-bold text-slate-500">District:</span> {selectedAlertModal.district}</p>
              <p><span className="font-bold text-slate-500">Assigned Officer:</span> {selectedAlertModal.officer}</p>
              <p><span className="font-bold text-slate-500">Timestamp:</span> {selectedAlertModal.date}</p>
            </div>

            <div className="pt-3 border-t border-slate-100 text-right">
              <button
                onClick={() => setSelectedAlertModal(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-bold text-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PriorityBadge({ priority }) {
  const styles = {
    Critical: "bg-rose-100 text-rose-700 border-rose-200",
    High: "bg-amber-100 text-amber-700 border-amber-200",
    Medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
    Low: "bg-emerald-100 text-emerald-700 border-emerald-200",
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${styles[priority] || styles.Medium}`}>
      {priority}
    </span>
  );
}

function StatusBadge({ status }) {
  const styles = {
    Open: "bg-rose-50 text-rose-600 border-rose-200 animate-pulse",
    Investigating: "bg-amber-50 text-amber-700 border-amber-200",
    Resolved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${styles[status] || styles.Open}`}>
      {status}
    </span>
  );
}
