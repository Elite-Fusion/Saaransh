/**
 * WebSocketProvider — provides WebSocket context to the entire app.
 *
 * Wraps the app with a WebSocket connection that is active only when
 * a user is authenticated.  All hooks (useNotifications, useLiveDashboard,
 * usePresence) consume this context.
 */
import { createContext, useContext } from "react";
import { useWebSocket } from "../hooks/useWebSocket";

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const ws = useWebSocket();

  return (
    <WebSocketContext.Provider value={ws}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWs() {
  return useContext(WebSocketContext);
}
