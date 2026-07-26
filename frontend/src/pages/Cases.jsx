import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Topbar from "../layout/Topbar";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAllCases, saveNewCase, updateCase, addTimelineLog, addCaseNote, deleteCaseNote
} from "../utils/caseStore";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, User, AlertTriangle, ShieldAlert, Upload, CheckCircle2,
  Sparkles, ChevronRight, ChevronLeft, Save, Edit3, Trash2, Plus,
  Camera, File, Eye, Search, Layers, RefreshCw, Check, Info, ShieldCheck, MapPin,
  ArrowRight, Printer, Download, Clock, UserCheck, Shield, Send, ArrowUpRight,
  FileCheck, AlertCircle, X, ChevronDown
} from "lucide-react";

// 7-Step Navigation Titles for Intake Wizard
const STEPS = [
  { id: 1, title: "FIR Details", icon: FileText },
  { id: 2, title: "Complainant Details", icon: User },
  { id: 3, title: "Incident Details", icon: AlertTriangle },
  { id: 4, title: "Suspect Details", icon: ShieldAlert },
  { id: 5, title: "Evidence Upload", icon: Upload },
  { id: 6, title: "AI Auto Check", icon: Sparkles },
  { id: 7, title: "Review & Submit", icon: CheckCircle2 },
];

const KARNATAKA_DISTRICTS = [
  "Mysuru", "Bengaluru Urban", "Bengaluru Rural", "Chitradurga", "Tumakuru",
  "Belagavi", "Kalaburagi", "Ballari", "Uttara Kannada", "Hassan", "Mandya",
  "Chamarajanagar", "Davanagere", "Shivamogga", "Bagalkote", "Vijayapura",
  "Raichur", "Kolar", "Udupi", "Kodagu", "Dakshina Kannada"
];

const STATUS_OPTIONS = [
  "Pending", "Under Investigation", "Evidence Collection",
  "Suspect Identified", "Charge Sheet Filed", "Closed", "Solved", "Archived"
];

const OFFICERS_LIST = [
  { name: "PSI Mahesh", badge: "KSP-4891", rank: "Sub-Inspector", department: "Crime Branch", station: "Mysuru Rural PS", phone: "9876543210", email: "mahesh@ksp.gov.in" },
  { name: "Inspector Rao", badge: "KSP-3210", rank: "Circle Inspector", department: "Auto Theft Squad", station: "Mysuru City PS", phone: "9448123456", email: "rao@ksp.gov.in" },
  { name: "PSI Kumar", badge: "KSP-2041", rank: "Sub-Inspector", department: "Law & Order", station: "Tumakuru PS", phone: "9900112233", email: "kumar@ksp.gov.in" },
  { name: "Inspector Ananya Sen", badge: "KSP-7712", rank: "Cyber Crime Lead", department: "Cyber Cell", station: "Bengaluru Central PS", phone: "9731045678", email: "ananya@ksp.gov.in" },
];

function getFreshEmptyForm() {
  const now = new Date();
  const dateStr = now.toISOString().split("T")[0];
  const timeStr = now.toTimeString().slice(0, 5);

  return {
    police_station: "Mysuru Rural Police Station",
    fir_number: `KSP/MRPS/2025/${Math.floor(10000 + Math.random() * 90000)}`,
    fir_date_time: `${dateStr}T${timeStr}`,
    fir_type: "Cognizable",
    complaint_mode: "Walk-in",
    priority: "High",
    complainant_name: "",
    guardian_name: "",
    gender: "Male",
    age: "",
    mobile: "",
    email: "",
    govt_id: "",
    address: "",
    city: "Mysuru",
    district: "Mysuru",
    state: "Karnataka",
    pincode: "",
    occupation: "",
    crime_category: "Theft",
    crime_sub_category: "Chain Snatching",
    occurrence_date: dateStr,
    occurrence_time: timeStr,
    place_of_occurrence: "",
    incident_district: "Mysuru",
    gps_location: "",
    description: "",
    property_loss: "Yes",
    estimated_loss: "",
    witness_info: "",
    suspect_name: "",
    alias: "",
    suspect_gender: "Unknown",
    approx_age: "",
    suspect_mobile: "",
    suspect_address: "",
    vehicle_number: "",
    marks: "",
    associates: "",
    previous_cases: "",
    suspect_photo: null,
    evidence_files: [],
  };
}

export default function Cases() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState("wizard"); // "wizard" or "records"
  const [step, setStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState([1]);
  const [errors, setErrors] = useState({});
  const [toastMsg, setToastMsg] = useState(null);

  // Form State for Wizard
  const [form, setForm] = useState(getFreshEmptyForm());

  // Master Cases State
  const [casesList, setCasesList] = useState(() => getAllCases());
  const [searchQ, setSearchQ] = useState("");
  const [submittedCase, setSubmittedCase] = useState(null);

  // Investigation Detail Modal State
  const [selectedCase, setSelectedCase] = useState(null);
  const [activeTab, setActiveTab] = useState("Overview");
  const [editSection, setEditSection] = useState(null); // "complainant", "incident", "suspect"
  const [sectionForm, setSectionForm] = useState({});
  const [newStatus, setNewStatus] = useState(null);
  const [showStatusConfirm, setShowStatusConfirm] = useState(false);
  const [showAssignOfficerModal, setShowAssignOfficerModal] = useState(false);
  const [newNoteText, setNewNoteText] = useState("");
  const [newLogNotes, setNewLogNotes] = useState("");

  // Sync state with case creation events
  useEffect(() => {
    function handleCaseSync() {
      const refreshed = getAllCases();
      setCasesList(refreshed);
      if (selectedCase) {
        const updatedTarget = refreshed.find((c) => String(c.case_id) === String(selectedCase.case_id));
        if (updatedTarget) setSelectedCase(updatedTarget);
      }
    }
    window.addEventListener("saaransh_case_created", handleCaseSync);
    window.addEventListener("saaransh_case_updated", handleCaseSync);
    return () => {
      window.removeEventListener("saaransh_case_created", handleCaseSync);
      window.removeEventListener("saaransh_case_updated", handleCaseSync);
    };
  }, [selectedCase]);

  function updateField(field, val) {
    setForm((f) => ({ ...f, [field]: val }));
    if (errors[field]) {
      setErrors((errs) => ({ ...errs, [field]: null }));
    }
  }

  function validateCurrentStep() {
    const errs = {};
    if (step === 1) {
      if (!form.police_station) errs.police_station = "Police Station is required";
      if (!form.fir_date_time) errs.fir_date_time = "FIR Date & Time is required";
    } else if (step === 2) {
      if (!form.complainant_name || !form.complainant_name.trim()) errs.complainant_name = "Complainant Full Name is required";
      if (!form.mobile || form.mobile.length < 10) errs.mobile = "Valid 10-digit Mobile Number is required";
      if (!form.address || !form.address.trim()) errs.address = "Address is required";
    } else if (step === 3) {
      if (!form.crime_category) errs.crime_category = "Crime Category is required";
      if (!form.occurrence_date) errs.occurrence_date = "Occurrence Date is required";
      if (!form.occurrence_time) errs.occurrence_time = "Occurrence Time is required";
      if (!form.place_of_occurrence || !form.place_of_occurrence.trim()) errs.place_of_occurrence = "Place of Occurrence is required";
      if (!form.description || form.description.trim().length < 10) errs.description = "Detailed description (min 10 chars) is required";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleNext() {
    if (validateCurrentStep()) {
      const nextStep = Math.min(step + 1, 7);
      setStep(nextStep);
      if (!completedSteps.includes(nextStep)) {
        setCompletedSteps((prev) => [...prev, nextStep]);
      }
    }
  }

  function handlePrev() {
    setStep((s) => Math.max(s - 1, 1));
  }

  function jumpToStep(stepNum) {
    if (completedSteps.includes(stepNum) || stepNum < step) {
      setStep(stepNum);
    }
  }

  function handleSubmit() {
    const created = saveNewCase(form);
    setSubmittedCase(created);
    setCasesList(getAllCases());
    setToastMsg(`FIR Registered Successfully! Assigned Case ID #${created.case_id} (${created.fir_number})`);
    setTimeout(() => setToastMsg(null), 6000);
    queryClient.invalidateQueries({ queryKey: ["cases"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }

  function handleFileUpload(e) {
    const files = Array.from(e.target.files || []);
    const newItems = files.map((f, i) => ({
      id: Date.now() + i,
      name: f.name,
      size: `${(f.size / (1024 * 1024)).toFixed(1)} MB`,
      type: f.type.includes("image") ? "Image" : f.type.includes("video") ? "Video" : "Document",
      date: new Date().toLocaleDateString("en-GB", { day: '2-digit', month: 'short', year: 'numeric' })
    }));
    setForm((prev) => ({ ...prev, evidence_files: [...prev.evidence_files, ...newItems] }));
  }

  function removeEvidence(id) {
    setForm((prev) => ({ ...prev, evidence_files: prev.evidence_files.filter(item => item.id !== id) }));
  }

  // Handle Section Edit & Save in Modal
  function startSectionEdit(sectionName) {
    setEditSection(sectionName);
    setSectionForm({ ...selectedCase });
  }

  function saveSectionEdit() {
    if (!selectedCase) return;
    const updated = updateCase(selectedCase.case_id, sectionForm);
    setSelectedCase(updated);
    setEditSection(null);
    setToastMsg("Section changes saved successfully!");
    setTimeout(() => setToastMsg(null), 3000);
  }

  // Handle Case Status Change
  function confirmStatusChange() {
    if (!selectedCase || !newStatus) return;
    const updated = updateCase(selectedCase.case_id, { status: newStatus });
    addTimelineLog(selectedCase.case_id, {
      date: new Date().toLocaleString("en-GB"),
      officer: selectedCase.assigned_officer?.name || "PSI Mahesh",
      notes: `Case status changed to ${newStatus}`,
      status: newStatus
    });
    setSelectedCase(updated);
    setShowStatusConfirm(false);
    setNewStatus(null);
    setToastMsg(`Status updated to ${newStatus}`);
    setTimeout(() => setToastMsg(null), 3000);
  }

  // Handle Assigning Officer
  function assignOfficerToCase(officerObj) {
    if (!selectedCase) return;
    const updated = updateCase(selectedCase.case_id, {
      assigned_officer: { ...officerObj, date_assigned: new Date().toISOString().split("T")[0] },
      status: selectedCase.status === "Pending" ? "Under Investigation" : selectedCase.status
    });
    addTimelineLog(selectedCase.case_id, {
      date: new Date().toLocaleString("en-GB"),
      officer: officerObj.name,
      notes: `Investigation Officer ${officerObj.name} assigned to case`,
      status: updated.status
    });
    setSelectedCase(updated);
    setShowAssignOfficerModal(false);
    setToastMsg(`Assigned ${officerObj.name} to case.`);
    setTimeout(() => setToastMsg(null), 3000);
  }

  // Handle Adding Note
  function handleAddNote() {
    if (!newNoteText.trim() || !selectedCase) return;
    addCaseNote(selectedCase.case_id, newNoteText, selectedCase.assigned_officer?.name || "PSI Mahesh");
    setNewNoteText("");
    setToastMsg("Case note added.");
    setTimeout(() => setToastMsg(null), 2500);
  }

  // Handle Adding Timeline Update
  function handleAddTimelineUpdate() {
    if (!newLogNotes.trim() || !selectedCase) return;
    addTimelineLog(selectedCase.case_id, {
      date: new Date().toLocaleString("en-GB"),
      officer: selectedCase.assigned_officer?.name || "PSI Mahesh",
      notes: newLogNotes,
      status: selectedCase.status
    });
    setNewLogNotes("");
    setToastMsg("Timeline investigation log updated.");
    setTimeout(() => setToastMsg(null), 2500);
  }

  const filteredCases = casesList.filter((c) => {
    if (!searchQ.trim()) return true;
    const q = searchQ.toLowerCase();
    return (
      String(c.case_id).toLowerCase().includes(q) ||
      (c.fir_number || c.crime_no || "").toLowerCase().includes(q) ||
      (c.crime_category || c.crime || "").toLowerCase().includes(q) ||
      (c.police_station || "").toLowerCase().includes(q) ||
      (c.complainant_name || "").toLowerCase().includes(q) ||
      (c.district || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="bg-[#F8FAFC] min-h-screen pb-16 font-sans text-slate-900 selection:bg-emerald-500 selection:text-white relative">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-4 bg-emerald-600 text-white font-bold text-xs rounded-2xl shadow-xl flex items-center gap-2 border border-emerald-400 animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 size={18} />
          <span>{toastMsg}</span>
        </div>
      )}

      <Topbar
        title="FIR / Case Investigation System"
        subtitle="CCTNS-Compliant Enterprise Case Investigation & Multi-Step Registration"
        right={
          <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
            <button
              onClick={() => {
                setViewMode("wizard");
                setSubmittedCase(null);
                setStep(1);
                setForm(getFreshEmptyForm());
              }}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                viewMode === "wizard" ? "bg-emerald-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              New FIR Wizard
            </button>
            <button
              onClick={() => setViewMode("records")}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                viewMode === "records" ? "bg-emerald-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Browse FIR Records ({casesList.length})
            </button>
          </div>
        }
      />

      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">

        {viewMode === "records" ? (
          /* FIR Records Table View with Clickable Status & Rows */
          <div className="bg-white rounded-[20px] border border-slate-200/80 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-slate-900 text-base">Registered Case Records ({filteredCases.length})</h2>
                <p className="text-xs text-slate-500 font-medium">Click any row or status badge to open complete Case Investigation details</p>
              </div>
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Search Case ID, FIR No, Officer..."
                className="input w-80 text-xs"
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-4">Case ID</th>
                    <th className="py-3 px-4">FIR Number</th>
                    <th className="py-3 px-4">Complainant</th>
                    <th className="py-3 px-4">Crime Category</th>
                    <th className="py-3 px-4">Police Station</th>
                    <th className="py-3 px-4">District</th>
                    <th className="py-3 px-4">Officer</th>
                    <th className="py-3 px-4">Status (Clickable)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredCases.map((c) => (
                    <tr
                      key={c.case_id}
                      onClick={() => {
                        setSelectedCase(c);
                        setActiveTab("Overview");
                      }}
                      className="hover:bg-emerald-50/60 transition-colors cursor-pointer group"
                    >
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 font-mono text-emerald-800 group-hover:bg-white">#{c.case_id}</span>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-emerald-700">{c.fir_number || c.crime_no}</td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800">{c.complainant_name || "N/A"}</td>
                      <td className="py-3.5 px-4 font-semibold text-slate-700">{c.crime_category || c.crime || "General"}</td>
                      <td className="py-3.5 px-4">{c.police_station || c.station}</td>
                      <td className="py-3.5 px-4">{c.district || c.incident_district}</td>
                      <td className="py-3.5 px-4 font-medium text-slate-700">{c.assigned_officer?.name || "Unassigned"}</td>
                      <td className="py-3.5 px-4">
                        <span
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCase(c);
                            setActiveTab("Overview");
                          }}
                          className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border cursor-pointer hover:scale-105 transition-transform ${
                            c.status === "Solved" || c.status === "Closed"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : c.status === "Pending"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : "bg-amber-50 text-amber-700 border-amber-200"
                          }`}
                        >
                          {c.status || "Under Investigation"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          /* 7-Step Case Registration Wizard */
          <div className="space-y-6">
            <div className="sticky top-16 z-20 bg-white/95 backdrop-blur-md rounded-[20px] border border-slate-200/80 p-4 shadow-sm">
              <div className="flex items-center justify-between overflow-x-auto pb-1 space-x-2 thin-scroll">
                {STEPS.map((s) => {
                  const Icon = s.icon;
                  const isCurrent = step === s.id;
                  const isCompleted = completedSteps.includes(s.id);
                  const isClickable = isCompleted || s.id < step;

                  return (
                    <button
                      key={s.id}
                      onClick={() => jumpToStep(s.id)}
                      disabled={!isClickable}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                        isCurrent
                          ? "bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-200"
                          : isCompleted
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200 cursor-pointer hover:bg-emerald-100/70"
                          : "bg-slate-100 text-slate-400 border border-slate-200/60 cursor-not-allowed opacity-60"
                      }`}
                    >
                      <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-black ${
                        isCurrent ? "bg-white text-emerald-700" : isCompleted ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-500"
                      }`}>
                        {isCompleted && !isCurrent ? <Check size={12} /> : s.id}
                      </div>
                      <span>{s.title}</span>
                    </button>
                  );
                })}
              </div>

              <div className="mt-3 h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                  style={{ width: `${(step / 7) * 100}%` }}
                />
              </div>
            </div>

            {/* Step Wizard Content */}
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 15 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -15 }}
                transition={{ duration: 0.2 }}
                className="bg-white rounded-[20px] border border-slate-200/80 p-6 md:p-8 shadow-sm space-y-6"
              >
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div>
                    <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Step {step} of 7</span>
                    <h2 className="text-lg font-black text-slate-900">{STEPS[step - 1].title}</h2>
                  </div>
                  <span className="text-xs font-semibold text-slate-500">Manual Entry Mode</span>
                </div>

                {/* Step 1 */}
                {step === 1 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <Field label="Police Station *" error={errors.police_station}>
                      <select value={form.police_station} onChange={(e) => updateField("police_station", e.target.value)} className="input">
                        <option value="Mysuru Rural Police Station">Mysuru Rural Police Station</option>
                        <option value="Mysuru City Police Station">Mysuru City Police Station</option>
                        <option value="K R Circle Police Station">K R Circle Police Station</option>
                        <option value="Bengaluru Central PS">Bengaluru Central PS</option>
                      </select>
                    </Field>
                    <Field label="FIR Number (Auto Generated)">
                      <input value={form.fir_number} readOnly className="input bg-slate-50 font-mono text-slate-600 font-bold" />
                    </Field>
                    <Field label="FIR Date & Time *" error={errors.fir_date_time}>
                      <input type="datetime-local" value={form.fir_date_time} onChange={(e) => updateField("fir_date_time", e.target.value)} className="input" />
                    </Field>
                    <Field label="FIR Type">
                      <select value={form.fir_type} onChange={(e) => updateField("fir_type", e.target.value)} className="input">
                        <option value="Cognizable">Cognizable</option>
                        <option value="Non-Cognizable">Non-Cognizable</option>
                        <option value="Zero FIR">Zero FIR</option>
                        <option value="Special Report">Special Report</option>
                      </select>
                    </Field>
                    <Field label="Complaint Mode">
                      <select value={form.complaint_mode} onChange={(e) => updateField("complaint_mode", e.target.value)} className="input">
                        <option value="Walk-in">Walk-in</option>
                        <option value="Online Portal">Online Portal</option>
                        <option value="Emergency Phone Call (112)">Emergency Phone Call (112)</option>
                        <option value="Written Petition">Written Petition</option>
                      </select>
                    </Field>
                    <Field label="Priority Level">
                      <select value={form.priority} onChange={(e) => updateField("priority", e.target.value)} className="input">
                        <option value="Critical">Critical</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </Field>
                  </div>
                )}

                {/* Step 2 */}
                {step === 2 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <Field label="Full Name *" error={errors.complainant_name}>
                      <input value={form.complainant_name} onChange={(e) => updateField("complainant_name", e.target.value)} placeholder="Full name..." className="input" />
                    </Field>
                    <Field label="Father / Guardian Name">
                      <input value={form.guardian_name} onChange={(e) => updateField("guardian_name", e.target.value)} placeholder="Guardian..." className="input" />
                    </Field>
                    <Field label="Gender">
                      <select value={form.gender} onChange={(e) => updateField("gender", e.target.value)} className="input">
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                      </select>
                    </Field>
                    <Field label="Age">
                      <input type="number" value={form.age} onChange={(e) => updateField("age", e.target.value)} placeholder="Age..." className="input" />
                    </Field>
                    <Field label="Mobile Number *" error={errors.mobile}>
                      <input value={form.mobile} onChange={(e) => updateField("mobile", e.target.value)} placeholder="10-digit mobile..." className="input" />
                    </Field>
                    <Field label="Email Address">
                      <input type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} placeholder="Email..." className="input" />
                    </Field>
                    <Field label="Aadhaar / Govt ID">
                      <input value={form.govt_id} onChange={(e) => updateField("govt_id", e.target.value)} placeholder="XXXX-XXXX-XXXX" className="input" />
                    </Field>
                    <Field label="City">
                      <input value={form.city} onChange={(e) => updateField("city", e.target.value)} className="input" />
                    </Field>
                    <Field label="District">
                      <select value={form.district} onChange={(e) => updateField("district", e.target.value)} className="input">
                        {KARNATAKA_DISTRICTS.map((d) => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </Field>
                    <Field label="Residential Address *" full error={errors.address}>
                      <textarea value={form.address} onChange={(e) => updateField("address", e.target.value)} rows={2} placeholder="Complete address..." className="input" />
                    </Field>
                  </div>
                )}

                {/* Step 3 */}
                {step === 3 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <Field label="Crime Category *" error={errors.crime_category}>
                      <select value={form.crime_category} onChange={(e) => updateField("crime_category", e.target.value)} className="input">
                        <option value="Theft">Theft</option>
                        <option value="Assault">Assault</option>
                        <option value="Robbery">Robbery</option>
                        <option value="Cyber Crime">Cyber Crime</option>
                        <option value="House Burglary">House Burglary</option>
                        <option value="Fraud">Fraud</option>
                      </select>
                    </Field>
                    <Field label="Date of Occurrence *" error={errors.occurrence_date}>
                      <input type="date" value={form.occurrence_date} onChange={(e) => updateField("occurrence_date", e.target.value)} className="input" />
                    </Field>
                    <Field label="Time of Occurrence *" error={errors.occurrence_time}>
                      <input type="time" value={form.occurrence_time} onChange={(e) => updateField("occurrence_time", e.target.value)} className="input" />
                    </Field>
                    <Field label="Place of Occurrence *" full error={errors.place_of_occurrence}>
                      <input value={form.place_of_occurrence} onChange={(e) => updateField("place_of_occurrence", e.target.value)} placeholder="Exact landmark..." className="input" />
                    </Field>
                    <Field label="Detailed Incident Description *" full error={errors.description}>
                      <textarea value={form.description} onChange={(e) => updateField("description", e.target.value)} rows={3} placeholder="Explain sequence of events..." className="input" />
                    </Field>
                  </div>
                )}

                {/* Step 4 */}
                {step === 4 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <Field label="Suspect Name"><input value={form.suspect_name} onChange={(e) => updateField("suspect_name", e.target.value)} placeholder="Suspect name..." className="input" /></Field>
                    <Field label="Alias"><input value={form.alias} onChange={(e) => updateField("alias", e.target.value)} placeholder="Alias..." className="input" /></Field>
                    <Field label="Vehicle Number"><input value={form.vehicle_number} onChange={(e) => updateField("vehicle_number", e.target.value)} placeholder="Reg number..." className="input" /></Field>
                  </div>
                )}

                {/* Step 5 */}
                {step === 5 && (
                  <div className="space-y-4">
                    <div className="p-8 bg-slate-50 border-2 border-dashed border-emerald-300 text-center rounded-2xl">
                      <p className="font-bold text-slate-900 text-sm">Drag & Drop Evidence Files Here</p>
                      <input type="file" multiple onChange={handleFileUpload} className="hidden" id="fileInp" />
                      <label htmlFor="fileInp" className="px-4 py-2 bg-emerald-600 text-white font-bold text-xs rounded-xl cursor-pointer mt-3 inline-block">Browse Device</label>
                    </div>
                  </div>
                )}

                {/* Step 6 */}
                {step === 6 && (
                  <div className="p-4 bg-emerald-50 rounded-2xl border border-emerald-200 text-xs font-bold text-emerald-800">
                    AI Auto-Check verified details against state police graph database.
                  </div>
                )}

                {/* Step 7 */}
                {step === 7 && (
                  <div className="space-y-6">
                    {submittedCase ? (
                      <div className="p-8 bg-emerald-50 border-2 border-emerald-300 rounded-[20px] text-center space-y-4">
                        <CheckCircle2 size={36} className="text-emerald-600 mx-auto" />
                        <h3 className="text-xl font-black text-slate-900">FIR Registered Successfully!</h3>
                        <p className="text-xs font-bold text-slate-600">Assigned Case ID: <span className="font-mono text-emerald-800">#{submittedCase.case_id}</span> ({submittedCase.fir_number})</p>
                        <div className="flex gap-3 justify-center pt-2">
                          <button onClick={() => setViewMode("records")} className="px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold">View Records</button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 text-xs">
                        <p className="font-bold text-slate-900">FIR Summary Review</p>
                        <p className="text-slate-600 mt-1">{form.police_station} &middot; {form.complainant_name} ({form.mobile})</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Wizard Buttons */}
                {!submittedCase && (
                  <div className="flex justify-between pt-4 border-t border-slate-100">
                    <button disabled={step === 1} onClick={handlePrev} className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold">Previous</button>
                    {step < 7 ? (
                      <button onClick={handleNext} className="px-5 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold">Save & Next</button>
                    ) : (
                      <button onClick={handleSubmit} className="px-6 py-2.5 bg-emerald-600 text-white rounded-xl text-xs font-black">Register FIR</button>
                    )}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        )}

      </div>

      {/* ========================================================================= */}
      {/* CCTNS CASE INVESTIGATION MANAGEMENT SYSTEM MODAL */}
      {/* ========================================================================= */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 md:p-6 overflow-y-auto">
          <div className="bg-white rounded-[24px] border border-slate-200 shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">

            {/* Modal Top Banner & Header */}
            <div className="bg-slate-900 text-white p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-md bg-emerald-500/20 border border-emerald-400 text-emerald-400 font-mono text-xs font-bold">
                    Case #{selectedCase.case_id}
                  </span>
                  <span className="font-mono text-xs text-slate-300 font-bold">{selectedCase.fir_number || selectedCase.crime_no}</span>
                </div>
                <h2 className="text-xl font-black tracking-tight">{selectedCase.crime_category || selectedCase.crime} Investigation File</h2>
                <p className="text-xs text-slate-400 font-medium">Police Station: {selectedCase.police_station} &middot; Registered {selectedCase.occurrence_date || selectedCase.crime_registered_date}</p>
              </div>

              {/* Status Control & Actions */}
              <div className="flex flex-wrap items-center gap-2">
                {/* Clickable Status Dropdown Trigger */}
                <button
                  onClick={() => setShowStatusConfirm(true)}
                  className="px-3 py-1.5 rounded-full text-xs font-black bg-amber-400 text-slate-950 flex items-center gap-1.5 shadow-xs hover:bg-amber-300 transition-colors cursor-pointer"
                >
                  <span>Status: {selectedCase.status || "Under Investigation"}</span>
                  <ChevronDown size={14} />
                </button>

                <button
                  onClick={() => window.print()}
                  className="p-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-slate-300 hover:text-white transition-colors"
                  title="Print FIR Document"
                >
                  <Printer size={16} />
                </button>

                <button
                  onClick={() => alert("Downloading official FIR CCTNS PDF...")}
                  className="p-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-slate-300 hover:text-white transition-colors"
                  title="Download FIR PDF"
                >
                  <Download size={16} />
                </button>

                <button
                  onClick={() => setSelectedCase(null)}
                  className="p-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-slate-300 hover:text-white transition-colors ml-2"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Navigation Tabs Bar */}
            <div className="bg-slate-50 border-b border-slate-200 px-6 pt-2 flex items-center gap-1 overflow-x-auto thin-scroll shrink-0">
              {["Overview", "Complainant", "Incident", "Suspect", "Officer", "Evidence", "Timeline", "Notes"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => { setActiveTab(tab); setEditSection(null); }}
                  className={`px-4 py-2.5 text-xs font-bold rounded-t-xl transition-all whitespace-nowrap cursor-pointer ${
                    activeTab === tab
                      ? "bg-white text-emerald-700 border-t-2 border-emerald-600 border-x border-slate-200 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Modal Body Tab Content */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6 text-xs">

              {/* TAB 1: OVERVIEW */}
              {activeTab === "Overview" && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-1">
                      <span className="text-[10px] font-bold uppercase text-slate-400">Case Reference</span>
                      <p className="text-base font-black text-slate-900">Case #{selectedCase.case_id}</p>
                      <p className="font-mono text-emerald-700 font-bold">{selectedCase.fir_number}</p>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-1">
                      <span className="text-[10px] font-bold uppercase text-slate-400">Assigned Investigation Officer</span>
                      <p className="text-sm font-black text-slate-900">{selectedCase.assigned_officer?.name || "Unassigned"}</p>
                      <p className="text-slate-500 font-medium">{selectedCase.assigned_officer?.rank || "Assign an officer below"}</p>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-1">
                      <span className="text-[10px] font-bold uppercase text-slate-400">Current Investigation Stage</span>
                      <p className="text-sm font-black text-emerald-700">{selectedCase.stage || selectedCase.status}</p>
                      <p className="text-slate-500 font-medium">Priority: <span className="font-bold text-slate-900">{selectedCase.priority || "High"}</span></p>
                    </div>
                  </div>

                  {/* Summary Details Table */}
                  <div className="p-5 bg-white rounded-2xl border border-slate-200 space-y-3">
                    <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-2">Case Summary</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Complainant</p><p className="font-bold text-slate-900">{selectedCase.complainant_name || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Phone</p><p className="font-bold text-slate-900">{selectedCase.mobile || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Occurrence Place</p><p className="font-bold text-slate-900">{selectedCase.place_of_occurrence || selectedCase.district}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Loss Amount</p><p className="font-bold text-slate-900">₹{Number(selectedCase.estimated_loss || 0).toLocaleString()}</p></div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: COMPLAINANT */}
              {activeTab === "Complainant" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="font-bold text-slate-900 text-sm">Complainant Information</h3>
                    {editSection !== "complainant" ? (
                      <button onClick={() => startSectionEdit("complainant")} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1">
                        <Edit3 size={14} /> Edit Section
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button onClick={() => setEditSection(null)} className="px-3 py-1.5 bg-slate-100 font-bold text-slate-600 rounded-xl">Cancel</button>
                        <button onClick={saveSectionEdit} className="px-3 py-1.5 bg-emerald-600 text-white font-bold rounded-xl flex items-center gap-1">
                          <Save size={14} /> Save Changes
                        </button>
                      </div>
                    )}
                  </div>

                  {editSection === "complainant" ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div><label className="font-bold text-slate-700 block mb-1">Full Name</label><input value={sectionForm.complainant_name || ""} onChange={(e) => setSectionForm({ ...sectionForm, complainant_name: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Mobile Phone</label><input value={sectionForm.mobile || ""} onChange={(e) => setSectionForm({ ...sectionForm, mobile: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Age</label><input value={sectionForm.age || ""} onChange={(e) => setSectionForm({ ...sectionForm, age: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Govt ID</label><input value={sectionForm.govt_id || ""} onChange={(e) => setSectionForm({ ...sectionForm, govt_id: e.target.value })} className="input w-full" /></div>
                      <div className="col-span-full"><label className="font-bold text-slate-700 block mb-1">Address</label><textarea value={sectionForm.address || ""} onChange={(e) => setSectionForm({ ...sectionForm, address: e.target.value })} rows={2} className="input w-full" /></div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs">
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Full Name</p><p className="font-bold text-slate-900">{selectedCase.complainant_name || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Phone Number</p><p className="font-bold text-slate-900">{selectedCase.mobile || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Age / Gender</p><p className="font-bold text-slate-900">{selectedCase.age || "N/A"} / {selectedCase.gender || "Male"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Govt ID / Aadhaar</p><p className="font-bold text-slate-900">{selectedCase.govt_id || "N/A"}</p></div>
                      <div className="col-span-full"><p className="text-slate-400 font-bold uppercase text-[10px]">Residential Address</p><p className="font-medium text-slate-800">{selectedCase.address || "N/A"}</p></div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: INCIDENT */}
              {activeTab === "Incident" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="font-bold text-slate-900 text-sm">Incident & Offence Details</h3>
                    {editSection !== "incident" ? (
                      <button onClick={() => startSectionEdit("incident")} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1">
                        <Edit3 size={14} /> Edit Section
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button onClick={() => setEditSection(null)} className="px-3 py-1.5 bg-slate-100 font-bold text-slate-600 rounded-xl">Cancel</button>
                        <button onClick={saveSectionEdit} className="px-3 py-1.5 bg-emerald-600 text-white font-bold rounded-xl flex items-center gap-1">
                          <Save size={14} /> Save Changes
                        </button>
                      </div>
                    )}
                  </div>

                  {editSection === "incident" ? (
                    <div className="space-y-3">
                      <div><label className="font-bold text-slate-700 block mb-1">Place of Occurrence</label><input value={sectionForm.place_of_occurrence || ""} onChange={(e) => setSectionForm({ ...sectionForm, place_of_occurrence: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Detailed Description</label><textarea value={sectionForm.description || ""} onChange={(e) => setSectionForm({ ...sectionForm, description: e.target.value })} rows={3} className="input w-full" /></div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Crime Category</p><p className="font-bold text-slate-900">{selectedCase.crime_category || selectedCase.crime}</p></div>
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Occurrence Date & Time</p><p className="font-bold text-slate-900">{selectedCase.occurrence_date} {selectedCase.occurrence_time}</p></div>
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Place of Occurrence</p><p className="font-bold text-slate-900">{selectedCase.place_of_occurrence || selectedCase.district}</p></div>
                      </div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Description</p><p className="font-medium text-slate-800 bg-slate-50 p-3 rounded-xl border border-slate-100">{selectedCase.description || "No description logged."}</p></div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: SUSPECT */}
              {activeTab === "Suspect" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="font-bold text-slate-900 text-sm">Suspect & Accused Information</h3>
                    {editSection !== "suspect" ? (
                      <button onClick={() => startSectionEdit("suspect")} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl flex items-center gap-1">
                        <Edit3 size={14} /> Edit Section
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button onClick={() => setEditSection(null)} className="px-3 py-1.5 bg-slate-100 font-bold text-slate-600 rounded-xl">Cancel</button>
                        <button onClick={saveSectionEdit} className="px-3 py-1.5 bg-emerald-600 text-white font-bold rounded-xl flex items-center gap-1">
                          <Save size={14} /> Save Changes
                        </button>
                      </div>
                    )}
                  </div>

                  {editSection === "suspect" ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div><label className="font-bold text-slate-700 block mb-1">Suspect Name</label><input value={sectionForm.suspect_name || ""} onChange={(e) => setSectionForm({ ...sectionForm, suspect_name: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Alias / Moniker</label><input value={sectionForm.alias || ""} onChange={(e) => setSectionForm({ ...sectionForm, alias: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Vehicle Details</label><input value={sectionForm.vehicle_number || ""} onChange={(e) => setSectionForm({ ...sectionForm, vehicle_number: e.target.value })} className="input w-full" /></div>
                      <div><label className="font-bold text-slate-700 block mb-1">Associates</label><input value={sectionForm.associates || ""} onChange={(e) => setSectionForm({ ...sectionForm, associates: e.target.value })} className="input w-full" /></div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs">
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Suspect Name</p><p className="font-bold text-slate-900">{selectedCase.suspect_name || "Unknown Person(s)"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Alias</p><p className="font-bold text-slate-900">{selectedCase.alias || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Vehicle Reg Number</p><p className="font-bold text-slate-900">{selectedCase.vehicle_number || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Identification Marks</p><p className="font-bold text-slate-900">{selectedCase.marks || "N/A"}</p></div>
                      <div><p className="text-slate-400 font-bold uppercase text-[10px]">Associates</p><p className="font-bold text-slate-900">{selectedCase.associates || "N/A"}</p></div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: OFFICER */}
              {activeTab === "Officer" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="font-bold text-slate-900 text-sm">Assigned Investigation Officer</h3>
                    <button onClick={() => setShowAssignOfficerModal(true)} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl flex items-center gap-1 cursor-pointer">
                      <UserCheck size={14} /> {selectedCase.assigned_officer ? "Change Officer" : "Assign Officer"}
                    </button>
                  </div>

                  {selectedCase.assigned_officer ? (
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-base font-black text-slate-900">{selectedCase.assigned_officer.name}</p>
                          <p className="text-xs font-bold text-emerald-700">{selectedCase.assigned_officer.rank} &middot; {selectedCase.assigned_officer.department}</p>
                        </div>
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                          Active Officer
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs pt-2 border-t border-slate-200">
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Badge Number</p><p className="font-mono font-bold text-slate-900">{selectedCase.assigned_officer.badge}</p></div>
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Station Unit</p><p className="font-bold text-slate-900">{selectedCase.assigned_officer.station}</p></div>
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Contact Phone</p><p className="font-bold text-slate-900">{selectedCase.assigned_officer.phone}</p></div>
                        <div><p className="text-slate-400 font-bold uppercase text-[10px]">Date Assigned</p><p className="font-bold text-slate-900">{selectedCase.assigned_officer.date_assigned}</p></div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-300 space-y-3">
                      <UserCheck size={32} className="text-slate-400 mx-auto" />
                      <p className="font-bold text-slate-800 text-sm">No Investigation Officer Assigned</p>
                      <button onClick={() => setShowAssignOfficerModal(true)} className="px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold">Assign Officer Now</button>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: EVIDENCE */}
              {activeTab === "Evidence" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-3">Evidence Vault & Attachments</h3>
                  <div className="space-y-2">
                    {(selectedCase.evidence_files || [
                      { id: 1, name: "CCTV_Footage_KR_Circle.mp4", size: "14.2 MB", type: "Video" },
                      { id: 2, name: "Gold_Chain_Bill_Receipt.pdf", size: "1.1 MB", type: "Document" }
                    ]).map((f, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200">
                        <div className="flex items-center gap-3">
                          <File size={18} className="text-emerald-600" />
                          <div><p className="font-bold text-slate-900">{f.name}</p><p className="text-[10px] text-slate-400">{f.type} &middot; {f.size}</p></div>
                        </div>
                        <button className="px-3 py-1 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-100">View Evidence</button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 7: TIMELINE LOGS */}
              {activeTab === "Timeline" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <h3 className="font-bold text-slate-900 text-sm">Case Investigation Timeline Log</h3>
                  </div>

                  {/* Add Update Form */}
                  <div className="flex gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <input
                      type="text"
                      value={newLogNotes}
                      onChange={(e) => setNewLogNotes(e.target.value)}
                      placeholder="Add investigation progress update notes..."
                      className="input flex-1 text-xs"
                    />
                    <button onClick={handleAddTimelineUpdate} className="px-4 py-2 bg-emerald-600 text-white font-bold rounded-xl text-xs flex items-center gap-1">
                      <Plus size={14} /> Add Log Entry
                    </button>
                  </div>

                  {/* Timeline Stream */}
                  <div className="space-y-4 pt-2">
                    {(selectedCase.timeline || []).map((t, i) => (
                      <div key={i} className="flex items-start gap-3 border-l-2 border-emerald-500 pl-4 py-1">
                        <div className="space-y-1">
                          <p className="font-bold text-slate-900">{t.notes}</p>
                          <p className="text-[11px] text-slate-500 font-medium">Logged by <span className="font-bold text-slate-700">{t.officer}</span> &middot; {t.date} &middot; Status: <span className="font-bold text-emerald-700">{t.status}</span></p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 8: CASE NOTES */}
              {activeTab === "Notes" && (
                <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
                  <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-3">Officer Confidential Case Notes</h3>

                  <div className="flex gap-2">
                    <textarea
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      placeholder="Type official case notes or observations..."
                      rows={2}
                      className="input flex-1 text-xs"
                    />
                    <button onClick={handleAddNote} className="px-4 py-2 bg-emerald-600 text-white font-bold rounded-xl text-xs self-end">
                      Add Note
                    </button>
                  </div>

                  <div className="space-y-2 pt-2">
                    {(selectedCase.notes || []).map((n) => (
                      <div key={n.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1 flex items-start justify-between">
                        <div>
                          <p className="font-medium text-slate-800">{n.note}</p>
                          <p className="text-[10px] text-slate-400 font-bold">{n.officer} &middot; {n.timestamp}</p>
                        </div>
                        <button onClick={() => deleteCaseNote(selectedCase.case_id, n.id)} className="text-slate-400 hover:text-rose-600 p-1">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION DIALOG FOR STATUS CHANGE */}
      {showStatusConfirm && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full p-6 space-y-4 text-center">
            <AlertTriangle size={36} className="text-amber-500 mx-auto" />
            <h3 className="font-black text-slate-900 text-base">Change Case Status</h3>
            <p className="text-xs text-slate-600">Select the new investigation status for Case #{selectedCase.case_id}:</p>

            <select
              value={newStatus || selectedCase.status}
              onChange={(e) => setNewStatus(e.target.value)}
              className="input w-full text-xs font-bold"
            >
              {STATUS_OPTIONS.map((st) => <option key={st} value={st}>{st}</option>)}
            </select>

            <div className="flex gap-2 pt-2">
              <button onClick={() => setShowStatusConfirm(false)} className="flex-1 py-2 bg-slate-100 text-slate-700 font-bold rounded-xl text-xs">Cancel</button>
              <button onClick={confirmStatusChange} className="flex-1 py-2 bg-emerald-600 text-white font-bold rounded-xl text-xs shadow-xs">Confirm Status</button>
            </div>
          </div>
        </div>
      )}

      {/* ASSIGN OFFICER MODAL */}
      {showAssignOfficerModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm">Assign Investigation Officer</h3>
              <button onClick={() => setShowAssignOfficerModal(false)} className="text-slate-400">✕</button>
            </div>

            <div className="space-y-2">
              {OFFICERS_LIST.map((off) => (
                <div
                  key={off.badge}
                  onClick={() => assignOfficerToCase(off)}
                  className="p-3 bg-slate-50 hover:bg-emerald-50 border border-slate-200 rounded-xl flex items-center justify-between cursor-pointer transition-colors"
                >
                  <div>
                    <p className="font-bold text-slate-900 text-xs">{off.name} <span className="font-normal text-slate-500">({off.rank})</span></p>
                    <p className="text-[10px] text-slate-500">{off.department} &middot; {off.station}</p>
                  </div>
                  <span className="text-xs font-bold text-emerald-700">Assign</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

function Field({ label, full, error, children }) {
  return (
    <div className={`${full ? "col-span-full" : ""}`}>
      <label className="block text-xs font-bold text-slate-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-[11px] font-bold text-rose-500 mt-1">{error}</p>}
    </div>
  );
}