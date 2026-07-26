// Auth-related API helpers. Thin wrappers around the shared axios client
// so the calling code does not have to know the exact endpoint paths.

import { api } from "./client";

/**
 * Create a new user via the admin-only POST /auth/users endpoint.
 *
 * Used by the public "Request Registration" page to submit a registration
 * request. The backend route is restricted to authenticated
 * control_center_officer callers; the unauthenticated first-admin
 * bootstrap lives on POST /auth/register and is not exposed here.
 *
 * @param {{ name: string, email: string, password: string, role: string }} payload
 * @returns {Promise<object>} The created user record.
 */
export function requestRegistration(payload) {
  return api.post("/auth/users", {
    name: payload.name,
    email: payload.email,
    password: payload.password,
    role: payload.role,
  });
}
