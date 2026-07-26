import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Register from '../pages/Register';

// Register.jsx now imports requestRegistration from ../api/auth.
const mockRequestRegistration = vi.fn();
vi.mock('../api/auth', () => ({
  requestRegistration: (...args) => mockRequestRegistration(...args),
}));

const renderRegister = (initialPath = '/register') =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Register />
    </MemoryRouter>
  );

// The Register form's <label> tags are not associated with their inputs
// via htmlFor/id in the current implementation, so we use placeholder +
// type selectors rather than getByLabelText.
const fillForm = (overrides = {}) => {
  fireEvent.change(screen.getByPlaceholderText(/enter full name/i), {
    target: { value: overrides.name ?? 'Test User' },
  });
  fireEvent.change(screen.getByPlaceholderText(/officer@ksp.gov.in/i), {
    target: { value: overrides.email ?? 'test@ksp.gov.in' },
  });
  const passwordInputs = document.querySelectorAll('input[type="password"]');
  fireEvent.change(passwordInputs[0], {
    target: { value: overrides.password ?? 'password123' },
  });
  fireEvent.change(passwordInputs[1], {
    target: { value: overrides.confirmPassword ?? 'password123' },
  });
  fireEvent.change(screen.getByRole('combobox'), {
    target: { value: overrides.role ?? 'control_center_officer' },
  });
};

describe('Register Page — /auth/users submission path', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('submits the form to the admin /auth/users endpoint with the spec body shape', async () => {
    mockRequestRegistration.mockResolvedValueOnce({ user_id: 1 });
    renderRegister();

    fillForm();
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    await waitFor(() => {
      expect(mockRequestRegistration).toHaveBeenCalledWith({
        name: 'Test User',
        email: 'test@ksp.gov.in',
        password: 'password123',
        role: 'control_center_officer',
      });
    });
  });

  it('shows the success banner after a successful submission', async () => {
    mockRequestRegistration.mockResolvedValueOnce({ user_id: 1 });
    renderRegister();

    fillForm();
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/registration submitted successfully\. please sign in\./i)
      ).toBeInTheDocument();
    });
    // The Submit button must not be called twice.
    expect(mockRequestRegistration).toHaveBeenCalledTimes(1);
  });

  it('surfaces API errors from /auth/users', async () => {
    mockRequestRegistration.mockRejectedValueOnce(
      new Error('Email already registered')
    );
    renderRegister();

    fillForm();
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    await waitFor(() => {
      expect(screen.getByText('Email already registered')).toBeInTheDocument();
    });
    // The success banner must not appear on failure.
    expect(
      screen.queryByText(/registration submitted successfully/i)
    ).not.toBeInTheDocument();
  });

  it('does not call requestRegistration when passwords do not match', async () => {
    renderRegister();
    fillForm({ password: 'password123', confirmPassword: 'different123' });
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    expect(mockRequestRegistration).not.toHaveBeenCalled();
  });
});
