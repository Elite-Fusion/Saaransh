import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Register from '../pages/Register';

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import { api } from '../api/client';

const renderRegister = () => {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <Register />
    </MemoryRouter>
  );
};

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the registration form', () => {
    renderRegister();
    expect(screen.getByText('Request Registration')).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument();
  });

  it('renders role dropdown with exactly 3 options', () => {
    renderRegister();
    const select = screen.getByLabelText(/role/i);
    const options = select.querySelectorAll('option');
    // Including the placeholder "Select role"
    expect(options.length).toBe(4);
    expect(options[1]).toHaveTextContent('Police Station Officer');
    expect(options[2]).toHaveTextContent('Data Center Officer');
    expect(options[3]).toHaveTextContent('Police Control Center Officer');
  });

  it('shows error when passwords do not match', async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@ksp.gov.in' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'different123' } });
    fireEvent.change(screen.getByLabelText(/role/i), { target: { value: 'control_center_officer' } });
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });

  it('shows error when no role is selected', async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@ksp.gov.in' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    expect(screen.getByText('Please select a role.')).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });

  it('submits registration successfully', async () => {
    api.post.mockResolvedValueOnce({ message: 'Registration submitted successfully.', user_id: 1 });
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@ksp.gov.in' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/role/i), { target: { value: 'control_center_officer' } });
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/register', {
        name: 'Test User',
        email: 'test@ksp.gov.in',
        password: 'password123',
        confirm_password: 'password123',
        role: 'control_center_officer',
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/registration submitted successfully/i)).toBeInTheDocument();
    });
  });

  it('shows error message on API failure', async () => {
    api.post.mockRejectedValueOnce(new Error('Registration is closed.'));
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@ksp.gov.in' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/role/i), { target: { value: 'control_center_officer' } });
    fireEvent.click(screen.getByRole('button', { name: /submit registration/i }));

    await waitFor(() => {
      expect(screen.getByText('Registration is closed.')).toBeInTheDocument();
    });
  });

  it('has a link back to login', () => {
    renderRegister();
    const backLink = screen.getByText('Back to Sign In');
    expect(backLink).toBeInTheDocument();
    expect(backLink.closest('a')).toHaveAttribute('href', '/login');
  });
});
