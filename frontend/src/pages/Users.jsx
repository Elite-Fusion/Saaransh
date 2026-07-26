import React, { useState, useMemo } from "react";
import Topbar from "../layout/Topbar";
import {
  Users as UsersIcon, UserPlus, Search, Filter, Edit3, Trash2,
  CheckCircle2, Shield, Phone, Mail, UserCheck, UserX, Eye, AlertTriangle
} from "lucide-react";

// Master Officers / Users Dataset
const INITIAL_USERS = [
  { id: 1, name: "PSI Mahesh", badge: "KSP-4891", role: "Police Station Officer", station: "Mysuru City PS", phone: "9876543210", email: "mahesh@ksp.gov.in", status: "Active" },
  { id: 2, name: "Inspector Rao", badge: "KSP-3210", role: "Control Room Officer", station: "Mysuru Rural PS", phone: "9448123456", email: "rao@ksp.gov.in", status: "Active" },
  { id: 3, name: "PSI Kumar", badge: "KSP-2041", role: "Police Station Officer", station: "Tumakuru PS", phone: "9900112233", email: "kumar@ksp.gov.in", status: "Active" },
  { id: 4, name: "Inspector Ananya Sen", badge: "KSP-7712", role: "Data Center Officer", station: "Cyber Cell Bengaluru", phone: "9731045678", email: "ananya@ksp.gov.in", status: "Active" },
  { id: 5, name: "PSI Gowda", badge: "KSP-5412", role: "Police Station Officer", station: "Ballari Central PS", phone: "9880234567", email: "gowda@ksp.gov.in", status: "Inactive" },
];

const ROLES = ["Police Station Officer", "Control Room Officer", "Data Center Officer", "Inspector", "Sub-Inspector"];
const STATIONS = ["Mysuru City PS", "Mysuru Rural PS", "Tumakuru PS", "Cyber Cell Bengaluru", "Bengaluru Central PS", "Ballari Central PS"];

export default function Users() {
  const [userList, setUserList] = useState(INITIAL_USERS);
  const [searchQ, setSearchQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");
  const [stationFilter, setStationFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");

  // Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [viewingUser, setViewingUser] = useState(null);
  const [toastMsg, setToastMsg] = useState(null);

  // Form State for Add / Edit
  const [form, setForm] = useState({
    name: "", badge: "", role: "Police Station Officer", station: "Mysuru City PS",
    phone: "", email: "", status: "Active"
  });
  const [formErrors, setFormErrors] = useState({});

  // Filter Logic
  const filteredUsers = useMemo(() => {
    return userList.filter((u) => {
      const matchesSearch = !searchQ ||
        u.name.toLowerCase().includes(searchQ.toLowerCase()) ||
        u.badge.toLowerCase().includes(searchQ.toLowerCase()) ||
        u.station.toLowerCase().includes(searchQ.toLowerCase()) ||
        u.email.toLowerCase().includes(searchQ.toLowerCase());

      const matchesRole = roleFilter === "All" || u.role === roleFilter;
      const matchesStation = stationFilter === "All" || u.station === stationFilter;
      const matchesStatus = statusFilter === "All" || u.status === statusFilter;

      return matchesSearch && matchesRole && matchesStation && matchesStatus;
    });
  }, [userList, searchQ, roleFilter, stationFilter, statusFilter]);

  function handleOpenAddModal() {
    setForm({
      name: "", badge: `KSP-${Math.floor(1000 + Math.random() * 9000)}`,
      role: "Police Station Officer", station: "Mysuru City PS",
      phone: "", email: "", status: "Active"
    });
    setFormErrors({});
    setIsAddModalOpen(true);
  }

  function validateForm() {
    const errs = {};
    if (!form.name.trim()) errs.name = "Full Name is required";
    if (!form.badge.trim()) errs.badge = "Badge Number is required";
    if (!form.phone || form.phone.length < 10) errs.phone = "Valid 10-digit Phone Number is required";
    if (!form.email || !form.email.includes("@")) errs.email = "Valid Email Address is required";
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSaveUser(e) {
    e.preventDefault();
    if (!validateForm()) return;

    if (editingUser) {
      setUserList((prev) => prev.map((u) => (u.id === editingUser.id ? { ...u, ...form } : u)));
      setToastMsg(`User ${form.name} updated successfully!`);
    } else {
      const newUser = { id: Date.now(), ...form };
      setUserList((prev) => [newUser, ...prev]);
      setToastMsg(`Officer ${form.name} added successfully!`);
    }

    setIsAddModalOpen(false);
    setEditingUser(null);
    setTimeout(() => setToastMsg(null), 3000);
  }

  function toggleUserStatus(id) {
    setUserList((prev) =>
      prev.map((u) => (u.id === id ? { ...u, status: u.status === "Active" ? "Inactive" : "Active" } : u))
    );
  }

  function deleteUser(id) {
    setUserList((prev) => prev.filter((u) => u.id !== id));
    setToastMsg("User deleted successfully.");
    setTimeout(() => setToastMsg(null), 3000);
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-4 bg-emerald-600 text-white font-bold text-xs rounded-2xl shadow-xl flex items-center gap-2 border border-emerald-400 animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 size={18} />
          <span>{toastMsg}</span>
        </div>
      )}

      <Topbar title="User Management" subtitle="Manage police officers, station personnel, and access roles" />

      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
        {/* Top Action & Search Bar */}
        <div className="bg-white rounded-[20px] border border-slate-200/80 p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Search Input */}
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Search name, badge number, station..."
                className="input w-full pl-10 text-xs"
              />
            </div>

            {/* Filters & Add User Button */}
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto text-xs">
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
                <span className="font-bold text-slate-400">Role:</span>
                <select
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All">All Roles</option>
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
                <span className="font-bold text-slate-400">Station:</span>
                <select
                  value={stationFilter}
                  onChange={(e) => setStationFilter(e.target.value)}
                  className="bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="All">All Stations</option>
                  {STATIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <button
                onClick={handleOpenAddModal}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl flex items-center gap-1.5 transition-all shadow-xs cursor-pointer ml-auto md:ml-0"
              >
                <UserPlus size={16} />
                <span>Add User</span>
              </button>
            </div>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="font-bold text-slate-900 text-sm">Police Personnel Directory ({filteredUsers.length})</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Profile</th>
                  <th className="py-3 px-4">Officer Name</th>
                  <th className="py-3 px-4">Badge Number</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Police Station</th>
                  <th className="py-3 px-4">Contact</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400 font-semibold">
                      No officers match the search or filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="h-8 w-8 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 flex items-center justify-center font-bold text-xs">
                          {u.name.slice(0, 2).toUpperCase()}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">{u.name}</td>
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-700">{u.badge}</td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800">{u.role}</td>
                      <td className="py-3.5 px-4 font-medium text-slate-600">{u.station}</td>
                      <td className="py-3.5 px-4">
                        <p className="font-semibold text-slate-800">{u.phone}</p>
                        <p className="text-[10px] text-slate-400">{u.email}</p>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${
                          u.status === "Active" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-500 border-slate-200"
                        }`}>
                          {u.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setViewingUser(u)}
                            title="View Officer Details"
                            className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
                          >
                            <Eye size={15} />
                          </button>

                          <button
                            onClick={() => {
                              setEditingUser(u);
                              setForm({ ...u });
                              setIsAddModalOpen(true);
                            }}
                            title="Edit User"
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg"
                          >
                            <Edit3 size={15} />
                          </button>

                          <button
                            onClick={() => toggleUserStatus(u.id)}
                            title={u.status === "Active" ? "Deactivate User" : "Activate User"}
                            className={`p-1.5 rounded-lg ${u.status === "Active" ? "text-amber-600 hover:bg-amber-50" : "text-emerald-600 hover:bg-emerald-50"}`}
                          >
                            {u.status === "Active" ? <UserX size={15} /> : <UserCheck size={15} />}
                          </button>

                          <button
                            onClick={() => deleteUser(u.id)}
                            title="Delete User"
                            className="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg"
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
        </div>
      </div>

      {/* Add / Edit User Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">{editingUser ? "Edit User Details" : "Add New Officer"}</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600 font-bold">✕</button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g. Inspector Ramesh"
                    className="input w-full"
                  />
                  {formErrors.name && <p className="text-rose-500 font-bold mt-1">{formErrors.name}</p>}
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Badge Number *</label>
                  <input
                    type="text"
                    value={form.badge}
                    onChange={(e) => setForm({ ...form, badge: e.target.value })}
                    placeholder="e.g. KSP-1234"
                    className="input w-full"
                  />
                  {formErrors.badge && <p className="text-rose-500 font-bold mt-1">{formErrors.badge}</p>}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">System Role</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                    className="input w-full"
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Police Station Unit</label>
                  <select
                    value={form.station}
                    onChange={(e) => setForm({ ...form, station: e.target.value })}
                    className="input w-full"
                  >
                    {STATIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Phone Number *</label>
                  <input
                    type="text"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="10-digit mobile"
                    className="input w-full"
                  />
                  {formErrors.phone && <p className="text-rose-500 font-bold mt-1">{formErrors.phone}</p>}
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Email Address *</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="officer@ksp.gov.in"
                    className="input w-full"
                  />
                  {formErrors.email && <p className="text-rose-500 font-bold mt-1">{formErrors.email}</p>}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl font-bold text-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-xs"
                >
                  {editingUser ? "Save Changes" : "Create Officer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View User Profile Modal */}
      {viewingUser && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-sm w-full p-6 space-y-4 text-center">
            <div className="h-16 w-16 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-black text-xl mx-auto border-2 border-emerald-300 shadow-sm">
              {viewingUser.name.slice(0, 2).toUpperCase()}
            </div>

            <div>
              <h3 className="font-bold text-slate-900 text-base">{viewingUser.name}</h3>
              <p className="text-xs font-mono font-bold text-emerald-700">{viewingUser.badge}</p>
              <p className="text-xs text-slate-500 font-medium mt-0.5">{viewingUser.role} &middot; {viewingUser.station}</p>
            </div>

            <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80 space-y-1 text-left">
              <p><span className="font-bold">Phone:</span> {viewingUser.phone}</p>
              <p><span className="font-bold">Email:</span> {viewingUser.email}</p>
              <p><span className="font-bold">Status:</span> {viewingUser.status}</p>
            </div>

            <button
              onClick={() => setViewingUser(null)}
              className="w-full py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-bold text-slate-700"
            >
              Close Profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
