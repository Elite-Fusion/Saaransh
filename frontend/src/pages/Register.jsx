import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldHalf } from "lucide-react";
import { requestRegistration } from "../api/auth";

const ROLE_OPTIONS = [
  { value: "police_station_officer", label: "Police Station Officer" },
  { value: "data_center_officer", label: "Data Center Officer" },
  { value: "control_center_officer", label: "Police Control Center Officer" },
];

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (!role) {
      setError("Please select a role.");
      return;
    }

    setSubmitting(true);
    try {
      await requestRegistration({
        name,
        email,
        password,
        role,
      });
      setSuccess("Registration submitted successfully. Please sign in.");
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-ink-100">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="h-14 w-14 rounded-full bg-brand-50 flex items-center justify-center text-brand-600 mb-3">
            <ShieldHalf size={28} />
          </div>
          <h1 className="text-xl font-bold text-ink-900">Request Registration</h1>
          <p className="text-sm text-ink-500">Create your account</p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="input"
              placeholder="Enter full name"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="input"
              placeholder="officer@ksp.gov.in"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="input"
              placeholder="Minimum 8 characters"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className="input"
              placeholder="Re-enter password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">
              Role
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              required
              className="input"
            >
              <option value="">Select role</option>
              {ROLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit Registration"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <Link
            to="/login"
            className="text-sm text-brand-600 hover:text-brand-700 font-medium"
          >
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
