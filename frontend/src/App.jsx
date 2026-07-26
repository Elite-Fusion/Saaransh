import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { WebSocketProvider, useWs } from "./contexts/WebSocketContext";
import { useNotifications } from "./hooks/useNotifications";
import { useLiveDashboard } from "./hooks/useLiveDashboard";
import { usePresence } from "./hooks/usePresence";
import ProtectedRoute from "./components/ProtectedRoute";
import Sidebar from "./layout/Sidebar";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Cases from "./pages/Cases";
import FirIntake from "./pages/FirIntake";
import MapIntelligence from "./pages/MapIntelligence";
import Predictions from "./pages/Predictions";
import AIAssistant from "./pages/AIAssistant";
import CrossCaseLinker from "./pages/CrossCaseLinker";
import Analytics from "./pages/Analytics";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import Users from "./pages/Users";
import Settings from "./pages/Settings";

/**
 * Inner component that initializes real-time hooks once authenticated.
 * Must be inside both AuthProvider and WebSocketProvider.
 */
function RealTimeHooks() {
  const ws = useWs();
  useNotifications(ws);
  useLiveDashboard(ws);
  usePresence(ws);
  return null;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <p className="text-slate-500 text-sm font-semibold">Loading Saaransh AI...</p>
      </div>
    );
  }

  // Not logged in — show only the login page
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Logged in — show sidebar + protected routes
  return (
    <WebSocketProvider>
      <RealTimeHooks />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 min-w-0">
          <Routes>
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="/register" element={<Navigate to="/" replace />} />
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/cases" element={<ProtectedRoute><Cases /></ProtectedRoute>} />
            <Route path="/cases/new" element={<ProtectedRoute><FirIntake /></ProtectedRoute>} />
            <Route path="/map" element={<ProtectedRoute><MapIntelligence /></ProtectedRoute>} />
            <Route path="/predictions" element={<ProtectedRoute><Predictions /></ProtectedRoute>} />
            <Route path="/assistant" element={<ProtectedRoute><AIAssistant /></ProtectedRoute>} />
            <Route path="/cross-case-linker" element={<ProtectedRoute><CrossCaseLinker /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
            <Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
            <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </WebSocketProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
