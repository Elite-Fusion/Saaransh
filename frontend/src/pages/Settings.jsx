import React, { useState } from "react";
import Topbar from "../layout/Topbar";
import {
  User, Building, Bell, Shield, KeyRound, Sliders, CheckCircle2,
  Lock, Save, RefreshCw, Moon, Sun, Monitor, AlertCircle
} from "lucide-react";

export default function Settings() {
  const [activeTab, setActiveTab] = useState("profile");
  const [toastMsg, setToastMsg] = useState(null);

  // Profile Settings State
  const [profile, setProfile] = useState({
    name: "PSI Mahesh",
    rank: "Police Sub-Inspector",
    badge: "KSP-4891",
    station: "Mysuru City PS",
    phone: "9876543210",
    email: "mahesh@ksp.gov.in",
  });

  // Department State
  const [department, setDepartment] = useState({
    controlRoom: "State Control Room (Bengaluru)",
    range: "Southern Range Mysuru",
    division: "Law & Order",
    emergencyContact: "+91 821 2418300",
  });

  // Notifications Toggles
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    smsTriggers: true,
    desktopPush: true,
    soundAlerts: false,
  });

  // Password State
  const [passwords, setPasswords] = useState({
    current: "",
    newPass: "",
    confirmPass: "",
  });
  const [passError, setPassError] = useState(null);

  // Application Preferences
  const [preferences, setPreferences] = useState({
    defaultDistrict: "Mysuru",
    refreshInterval: "30s",
    theme: "light",
  });

  function handleSaveProfile(e) {
    e.preventDefault();
    setToastMsg("Profile settings saved successfully!");
    setTimeout(() => setToastMsg(null), 3000);
  }

  function handleSaveDepartment(e) {
    e.preventDefault();
    setToastMsg("Department information updated successfully!");
    setTimeout(() => setToastMsg(null), 3000);
  }

  function handleChangePassword(e) {
    e.preventDefault();
    setPassError(null);

    if (!passwords.current) {
      setPassError("Current password is required");
      return;
    }
    if (!passwords.newPass || passwords.newPass.length < 6) {
      setPassError("New password must be at least 6 characters");
      return;
    }
    if (passwords.newPass !== passwords.confirmPass) {
      setPassError("New passwords do not match");
      return;
    }

    setPasswords({ current: "", newPass: "", confirmPass: "" });
    setToastMsg("Password changed successfully!");
    setTimeout(() => setToastMsg(null), 3000);
  }

  function handleReset() {
    setProfile({
      name: "PSI Mahesh",
      rank: "Police Sub-Inspector",
      badge: "KSP-4891",
      station: "Mysuru City PS",
      phone: "9876543210",
      email: "mahesh@ksp.gov.in",
    });
    setToastMsg("Settings reset to defaults.");
    setTimeout(() => setToastMsg(null), 3000);
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900">
      {/* Toast Alert */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-4 bg-emerald-600 text-white font-bold text-xs rounded-2xl shadow-xl flex items-center gap-2 border border-emerald-400 animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 size={18} />
          <span>{toastMsg}</span>
        </div>
      )}

      <Topbar title="System Settings" subtitle="Configure system preferences, department profile, notifications, and security" />

      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Settings Tab Navigation Side Bar */}
          <div className="bg-white rounded-[20px] border border-slate-200/80 p-3 shadow-sm space-y-1">
            {[
              { id: "profile", label: "Profile Settings", icon: User },
              { id: "department", label: "Department Info", icon: Building },
              { id: "notifications", label: "Notifications", icon: Bell },
              { id: "security", label: "Security & Password", icon: KeyRound },
              { id: "roles", label: "Roles & Permissions", icon: Shield },
              { id: "preferences", label: "Preferences", icon: Sliders },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all text-left cursor-pointer ${
                    isActive ? "bg-emerald-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <Icon size={16} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Settings Tab Content Main Area */}
          <div className="md:col-span-3 bg-white rounded-[20px] border border-slate-200/80 p-6 md:p-8 shadow-sm space-y-6">
            {/* 1. Profile Settings */}
            {activeTab === "profile" && (
              <form onSubmit={handleSaveProfile} className="space-y-6">
                <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
                  <h2 className="font-bold text-slate-900 text-base">Officer Profile Settings</h2>
                  <button type="button" onClick={handleReset} className="text-xs font-bold text-slate-500 hover:text-slate-800 flex items-center gap-1">
                    <RefreshCw size={13} /> Reset Defaults
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Full Name</label>
                    <input
                      type="text"
                      value={profile.name}
                      onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Rank / Designation</label>
                    <input
                      type="text"
                      value={profile.rank}
                      onChange={(e) => setProfile({ ...profile, rank: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Badge Number</label>
                    <input
                      type="text"
                      value={profile.badge}
                      readOnly
                      className="input w-full bg-slate-50 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Police Station Unit</label>
                    <input
                      type="text"
                      value={profile.station}
                      onChange={(e) => setProfile({ ...profile, station: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Contact Phone</label>
                    <input
                      type="text"
                      value={profile.phone}
                      onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Official Email</label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      className="input w-full"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button type="submit" className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-xs flex items-center gap-1.5 cursor-pointer">
                    <Save size={15} /> Save Changes
                  </button>
                </div>
              </form>
            )}

            {/* 2. Department Info */}
            {activeTab === "department" && (
              <form onSubmit={handleSaveDepartment} className="space-y-6">
                <div className="border-b border-slate-100 pb-3">
                  <h2 className="font-bold text-slate-900 text-base">Department & Unit Information</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Control Room Jurisdiction</label>
                    <input
                      type="text"
                      value={department.controlRoom}
                      onChange={(e) => setDepartment({ ...department, controlRoom: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Police Range</label>
                    <input
                      type="text"
                      value={department.range}
                      onChange={(e) => setDepartment({ ...department, range: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">State Division</label>
                    <input
                      type="text"
                      value={department.division}
                      onChange={(e) => setDepartment({ ...department, division: e.target.value })}
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Emergency Hotline Contact</label>
                    <input
                      type="text"
                      value={department.emergencyContact}
                      onChange={(e) => setDepartment({ ...department, emergencyContact: e.target.value })}
                      className="input w-full"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button type="submit" className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-xs flex items-center gap-1.5 cursor-pointer">
                    <Save size={15} /> Save Department Info
                  </button>
                </div>
              </form>
            )}

            {/* 3. Notifications */}
            {activeTab === "notifications" && (
              <div className="space-y-6">
                <div className="border-b border-slate-100 pb-3">
                  <h2 className="font-bold text-slate-900 text-base">Notification Preferences</h2>
                </div>

                <div className="space-y-4 text-xs">
                  {[
                    { key: "emailAlerts", label: "Email Critical Alert Reports", desc: "Receive automated email summaries for Critical security alerts." },
                    { key: "smsTriggers", label: "SMS Emergency Dispatches", desc: "Send SMS alerts for immediate high priority crime triggers." },
                    { key: "desktopPush", label: "Desktop Push Notifications", desc: "Show browser push popups when new FIR or alert is logged." },
                    { key: "soundAlerts", label: "Audible Alarm Sound", desc: "Play sound prompt for incoming emergency notifications." },
                  ].map((item) => (
                    <div key={item.key} className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                      <div>
                        <p className="font-bold text-slate-900">{item.label}</p>
                        <p className="text-[11px] text-slate-500">{item.desc}</p>
                      </div>

                      <button
                        type="button"
                        onClick={() => {
                          setNotifications((prev) => ({ ...prev, [item.key]: !prev[item.key] }));
                          setToastMsg(`Updated ${item.label} setting.`);
                          setTimeout(() => setToastMsg(null), 2000);
                        }}
                        className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
                          notifications[item.key] ? "bg-emerald-600" : "bg-slate-300"
                        }`}
                      >
                        <span className={`absolute top-1 left-1 h-4 w-4 bg-white rounded-full transition-transform ${
                          notifications[item.key] ? "translate-x-6" : ""
                        }`} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. Security & Password */}
            {activeTab === "security" && (
              <form onSubmit={handleChangePassword} className="space-y-6">
                <div className="border-b border-slate-100 pb-3">
                  <h2 className="font-bold text-slate-900 text-base">Security & Password Management</h2>
                </div>

                {passError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-bold flex items-center gap-2">
                    <AlertCircle size={16} />
                    <span>{passError}</span>
                  </div>
                )}

                <div className="space-y-4 max-w-md text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Current Password *</label>
                    <input
                      type="password"
                      value={passwords.current}
                      onChange={(e) => setPasswords({ ...passwords, current: e.target.value })}
                      placeholder="Enter current password..."
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">New Password *</label>
                    <input
                      type="password"
                      value={passwords.newPass}
                      onChange={(e) => setPasswords({ ...passwords, newPass: e.target.value })}
                      placeholder="Min 6 characters..."
                      className="input w-full"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Confirm New Password *</label>
                    <input
                      type="password"
                      value={passwords.confirmPass}
                      onChange={(e) => setPasswords({ ...passwords, confirmPass: e.target.value })}
                      placeholder="Re-enter new password..."
                      className="input w-full"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button type="submit" className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-xs flex items-center gap-1.5 cursor-pointer">
                    <Lock size={15} /> Change Password
                  </button>
                </div>
              </form>
            )}

            {/* 5. Roles & Permissions */}
            {activeTab === "roles" && (
              <div className="space-y-6">
                <div className="border-b border-slate-100 pb-3">
                  <h2 className="font-bold text-slate-900 text-base">Roles & Permissions Matrix</h2>
                </div>

                <div className="overflow-x-auto text-xs">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px] font-bold">
                        <th className="py-2.5 px-3">System Role</th>
                        <th className="py-2.5 px-3">Dashboard</th>
                        <th className="py-2.5 px-3">FIR Register</th>
                        <th className="py-2.5 px-3">Predictions</th>
                        <th className="py-2.5 px-3">User Admin</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      <tr>
                        <td className="py-3 px-3 font-bold text-slate-900">Control Room Officer</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ Full Access</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ Full Access</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ Full Access</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ Admin</td>
                      </tr>
                      <tr>
                        <td className="py-3 px-3 font-bold text-slate-900">Police Station Officer</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ View</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ Create / Edit</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ View</td>
                        <td className="py-3 px-3 text-slate-400">✕ None</td>
                      </tr>
                      <tr>
                        <td className="py-3 px-3 font-bold text-slate-900">Data Center Analyst</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ View</td>
                        <td className="py-3 px-3 text-slate-400">✕ Read-only</td>
                        <td className="py-3 px-3 text-emerald-600 font-bold">✓ Full Analytics</td>
                        <td className="py-3 px-3 text-slate-400">✕ None</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 6. Preferences */}
            {activeTab === "preferences" && (
              <div className="space-y-6">
                <div className="border-b border-slate-100 pb-3">
                  <h2 className="font-bold text-slate-900 text-base">Application Preferences</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Default District Focus</label>
                    <select
                      value={preferences.defaultDistrict}
                      onChange={(e) => setPreferences({ ...preferences, defaultDistrict: e.target.value })}
                      className="input w-full"
                    >
                      <option value="Mysuru">Mysuru</option>
                      <option value="Bengaluru Urban">Bengaluru Urban</option>
                      <option value="Chitradurga">Chitradurga</option>
                      <option value="Tumakuru">Tumakuru</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Auto Refresh Interval</label>
                    <select
                      value={preferences.refreshInterval}
                      onChange={(e) => setPreferences({ ...preferences, refreshInterval: e.target.value })}
                      className="input w-full"
                    >
                      <option value="15s">15 Seconds</option>
                      <option value="30s">30 Seconds</option>
                      <option value="60s">1 Minute</option>
                      <option value="off">Off</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={() => {
                      setToastMsg("Preferences saved!");
                      setTimeout(() => setToastMsg(null), 2500);
                    }}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    <Save size={15} /> Save Preferences
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
