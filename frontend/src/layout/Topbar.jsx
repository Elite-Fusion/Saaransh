import React, { useState, useRef, useEffect } from "react";
import { Bell, ChevronDown, Shield, User, Check } from "lucide-react";
import { useWs } from "../contexts/WebSocketContext";
import { useNotifications } from "../hooks/useNotifications";

const CONTROL_ROOMS = [
  "State Control Room (Bengaluru)",
  "Mysuru Range Control Room",
  "Belagavi Range Control Room",
  "Kalaburagi Range Control Room",
  "Coastal Security Control Room",
];

export default function Topbar({ title, subtitle, right, selectedControlRoom, onSelectControlRoom }) {
  const ws = useWs();
  const { unreadCount } = useNotifications(ws);
  const [isOpen, setIsOpen] = useState(false);
  const [currentRoom, setCurrentRoom] = useState(selectedControlRoom || "Control Room");
  const dropdownRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (room) => {
    setCurrentRoom(room);
    setIsOpen(false);
    if (onSelectControlRoom) {
      onSelectControlRoom(room);
    }
  };

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200 px-8 py-3 flex items-center justify-between shadow-sm">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 font-medium">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        {/* Live Status Indicator */}
        {ws?.status === "connected" && (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-emerald-700">Live Network</span>
          </div>
        )}

        {/* Control Room / Station Selector Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 transition-colors border border-slate-200 cursor-pointer"
          >
            <span className="truncate max-w-[180px]">{currentRoom}</span>
            <ChevronDown size={14} className={`text-slate-500 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
          </button>

          {isOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl border border-slate-200 shadow-lg py-1 z-50 text-xs animate-in fade-in zoom-in-95">
              <div className="px-3 py-1.5 font-bold text-[10px] uppercase text-slate-400 border-b border-slate-100 tracking-wider">
                Select Control Room
              </div>
              {CONTROL_ROOMS.map((room) => (
                <button
                  key={room}
                  onClick={() => handleSelect(room)}
                  className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-50 font-medium transition-colors ${
                    currentRoom === room ? "text-emerald-700 font-bold bg-emerald-50/50" : "text-slate-700"
                  }`}
                >
                  <span className="truncate">{room}</span>
                  {currentRoom === room && <Check size={14} className="text-emerald-600 shrink-0 ml-1" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notification Bell */}
        <button className="relative p-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors border border-slate-200 cursor-pointer">
          <Bell size={18} />
          <span className="absolute -top-1 -right-1 h-4 min-w-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-extrabold flex items-center justify-center border-2 border-white shadow-sm">
            {unreadCount > 0 ? unreadCount : 3}
          </span>
        </button>

        {/* Custom Actions */}
        {right}

        {/* Profile Officer Avatar */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="h-8 w-8 rounded-full bg-emerald-600 border-2 border-emerald-200 text-white flex items-center justify-center shadow-sm">
            <User size={16} />
          </div>
        </div>
      </div>
    </header>
  );
}
