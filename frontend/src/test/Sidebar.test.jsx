import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../layout/Sidebar';

// Per-test factory pattern: each test sets the role on the mock.
const mockUseAuth = vi.fn();

// Mock AuthContext — only useAuth is consumed by the Sidebar.
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// WebSocketContext is not under test; provide a stub so useNotifications
// and usePresence don't reach for a real socket.
vi.mock('../contexts/WebSocketContext', () => ({
  useWs: () => ({ status: 'disconnected', disconnect: vi.fn() }),
}));

// useNotifications / usePresence are derived from the socket — stub them.
vi.mock('../hooks/useNotifications', () => ({
  useNotifications: () => ({ unreadCount: 0, notifications: [] }),
}));
vi.mock('../hooks/usePresence', () => ({
  usePresence: () => ({ onlineCount: 0, onlineUsers: [] }),
}));

// The set of menu labels the spec requires each role to see.
const ALL_LABELS = [
  'Dashboard',
  'FIR / Cases',
  'Map Intelligence',
  'Predictions',
  'AI Assistant',
  'Cross Case Linker',
  'Analytics',
  'Alerts',
  'Reports',
  'Users',
  'Settings',
];

const POLICE_STATION_LABELS = ['Dashboard', 'FIR / Cases', 'AI Assistant'];
const DATA_CENTER_LABELS = ['Dashboard', 'Analytics', 'Predictions', 'Reports'];
const CONTROL_CENTER_LABELS = ALL_LABELS;

const renderSidebar = (user) => {
  mockUseAuth.mockReturnValue({
    user,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  });
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>
  );
};

const visibleLabels = () => {
  const nav = screen.getByRole('navigation');
  return within(nav)
    .getAllByRole('link')
    .map((link) => link.textContent.replace(/Sign out.*$/i, '').trim())
    .filter((label) => label.length > 0);
};

describe('Sidebar — role-based menu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows Dashboard, FIR / Cases, AI Assistant for police_station_officer', () => {
    renderSidebar({ email: 'officer@ksp.gov.in', role: 'police_station_officer' });
    const labels = visibleLabels();
    for (const expected of POLICE_STATION_LABELS) {
      expect(labels).toContain(expected);
    }
    for (const label of ALL_LABELS) {
      if (!POLICE_STATION_LABELS.includes(label)) {
        expect(labels).not.toContain(label);
      }
    }
  });

  it('shows Dashboard, Analytics, Predictions, Reports for data_center_officer', () => {
    renderSidebar({ email: 'analyst@ksp.gov.in', role: 'data_center_officer' });
    const labels = visibleLabels();
    for (const expected of DATA_CENTER_LABELS) {
      expect(labels).toContain(expected);
    }
    for (const label of ALL_LABELS) {
      if (!DATA_CENTER_LABELS.includes(label)) {
        expect(labels).not.toContain(label);
      }
    }
  });

  it('shows every menu item for control_center_officer', () => {
    renderSidebar({ email: 'admin@ksp.gov.in', role: 'control_center_officer' });
    const labels = visibleLabels();
    for (const expected of CONTROL_CENTER_LABELS) {
      expect(labels).toContain(expected);
    }
  });

  it('renders no menu links when user is null', () => {
    renderSidebar(null);
    const nav = screen.getByRole('navigation');
    expect(within(nav).queryAllByRole('link')).toHaveLength(0);
  });

  it('always shows the Sign out button when the sidebar renders', () => {
    for (const role of ['police_station_officer', 'data_center_officer', 'control_center_officer']) {
      const { unmount } = renderSidebar({ email: 'u@ksp.gov.in', role });
      expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();
      unmount();
    }
  });
});
