// Axios-based API client. Every screen goes through this — no component
// is allowed to hardcode data. If the backend call fails, callers get
// a typed error and must render an error/empty state, never fake rows.

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const STORAGE_KEY_ACCESS = "saaransh_access_token";
const STORAGE_KEY_REFRESH = "saaransh_refresh_token";

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

const axiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---- Request interceptor: attach access token ----
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_KEY_ACCESS);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---- Response interceptor: auto-refresh on 401 ----
let isRefreshing = false;
let failedQueue = [];

function processQueue(error, token) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
}

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Skip refresh for login/refresh endpoints or if already retried
    if (
      originalRequest._retry ||
      originalRequest.url === "/auth/login" ||
      originalRequest.url === "/auth/refresh"
    ) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem(STORAGE_KEY_REFRESH);
      if (!refreshToken) {
        // No refresh token — clear and redirect to login
        localStorage.removeItem(STORAGE_KEY_ACCESS);
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue this request while refresh is in progress
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return axiosInstance(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        localStorage.setItem(STORAGE_KEY_ACCESS, data.access_token);
        localStorage.setItem(STORAGE_KEY_REFRESH, data.refresh_token);

        processQueue(null, data.access_token);

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem(STORAGE_KEY_ACCESS);
        localStorage.removeItem(STORAGE_KEY_REFRESH);
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Wrapper around axios to throw ApiError on non-2xx responses.
 * @param {Object} config - Axios request config
 * @param {AbortSignal} signal - Optional abort signal
 * @returns {Promise<any>} Resolved with response data
 */
async function request(config, signal) {
  if (signal) {
    config.signal = signal;
  }

  try {
    const response = await axiosInstance(config);
    return response.data;
  } catch (err) {
    // Axios error
    let payload = null;
    if (err.response) {
      payload = err.response.data;
    } else if (err.request) {
      payload = err.request;
    } else {
      payload = err.message;
    }

    throw new ApiError(
      payload?.detail || payload?.message || `Request failed`,
      err.response ? err.response.status : 0,
      payload
    );
  }
}

export const api = {
  get: (path, params, signal) => request({ method: "GET", url: path, params }, signal),
  post: (path, body, signal) => request({ method: "POST", url: path, data: body }, signal),
  patch: (path, body, signal) => request({ method: "PATCH", url: path, data: body }, signal),
};
