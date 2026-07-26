import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileText, Map, Sparkles, Share2, BarChart3,
  Bell, ClipboardList, Users, Settings, LogOut, ShieldAlert,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useWs } from "../contexts/WebSocketContext";
import { useNotifications } from "../hooks/useNotifications";

// Navigation items configured by role
const getNavItems = (userRole) => {
  // Base items visible to all authenticated users
  const baseItems = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
  ];

  // Role-specific items
  if (userRole === "police_station_officer") {
    return [
      ...baseItems,
      { to: "/cases/new", label: "FIR Registration", icon: FileText },
      { to: "/cases", label: "My FIR Cases", icon: FileText },
      { to: "/map", label: "Nearby Crime Map", icon: Map },
      { to: "/assistant", label: "AI Assistant", icon: Sparkles },
      { to: "/alerts", label: "Alerts", icon: Bell },
    ];
  } else if (userRole === "data_center_officer") {
    return [
      ...baseItems,
      { to: "/cases", label: "All FIR Cases", icon: FileText },
      { to: "/users", label: "Users", icon: Users },
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/reports", label: "Reports", icon: ClipboardList },
      { to: "/cross-case-linker", label: "Cross Case Linker", icon: Share2 },
      { to: "/alerts", label: "Alerts", icon: Bell },
      { to: "/assistant", label: "AI Assistant", icon: Sparkles },
    ];
  } else if (userRole === "control_center_officer") {
    return [
      ...baseItems,
      { to: "/map", label: "Live Map", icon: Map },
      { to: "/alerts", label: "Alerts", icon: Bell },
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/reports", label: "Reports", icon: ClipboardList },
      { to: "/cross-case-linker", label: "Cross Case Linker", icon: Share2 },
      { to: "/assistant", label: "AI Assistant", icon: Sparkles },
    ];
  } else {
    // Default fallback (should not happen with proper auth)
    return baseItems;
  }
};

export default function Sidebar() {
  const { user, logout } = useAuth();
  const ws = useWs();
  const { unreadCount } = useNotifications(ws);
  const navigate = useNavigate();

  const handleLogout = async () => {
    ws?.disconnect?.();
    await logout();
    navigate("/login", { replace: true });
  };

  
  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 bg-white border-r border-slate-200 flex flex-col z-20 shadow-sm">
      {/* Brand Header with KSP Emblem */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100">
        <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center text-white shadow-md p-1 shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full fill-current text-white">
            <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="6" />
            <path d="M 50 15 L 60 40 L 85 40 L 65 55 L 75 80 L 50 65 L 25 80 L 35 55 L 15 40 L 40 40 Z" />
          </svg>
        </div>
        <div>
          <h1 className="font-bold text-slate-900 text-lg leading-tight tracking-tight">Saaransh</h1>
          <p className="text-[10px] text-slate-500 font-medium leading-tight">AI Powered Crime Intelligence System</p>
        </div>
      </div>

      <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 px-5 pt-4 pb-1">Main Menu</p>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto thin-scroll px-3 py-1 space-y-1">
        {getNavItems(user?.role).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? "bg-emerald-50 text-emerald-700 shadow-sm border-l-4 border-emerald-600 font-bold"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            <Icon size={18} className="shrink-0" />
            <span className="flex-1">{label}</span>
            {label === "Alerts" && unreadCount > 0 && (
              <span className="h-4 min-w-4 px-1.5 rounded-full bg-red-500 text-white text-[10px] font-extrabold flex items-center justify-center">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Officer Footer Card */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-3 p-2 bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="relative">
            <div className="h-9 w-9 rounded-full bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800 font-bold text-xs">
              PSI
            </div>
            <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-white" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold text-slate-900 truncate">
              {user?.email ? user.email.split("@")[0].toUpperCase() : "PSI Mahesh"}
            </p>
            <p className="text-[10px] text-slate-500 truncate">
              Mysuru City PS
            </p>
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
