import axios from "axios";
import { API_BASE_URL } from "@/utils/constants";
import { clearStoredToken, getStoredToken } from "@/services/tokenStorage";

/**
 * Single Axios instance for the whole app. All feature services import this
 * instead of creating their own client, so base URL, headers, and
 * interceptors (auth token attachment, error normalization) live in one place.
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach the bearer token to every request, centrally — no route or
// component ever handles the token directly.
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// The auth store registers a callback here so a rejected token also resets
// in-memory auth state (avoids importing the store from this module, which
// would be a circular dependency: store -> authService -> api -> store).
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

// If the token is rejected as invalid/expired, drop it and reset auth state so
// ProtectedRoute redirects to /login instead of leaving a dead session on screen.
// Login/register 401s (wrong password) are not a session expiry, so they're skipped.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const url = error.config?.url ?? "";
      const isCredentialCheck = url.includes("/auth/login") || url.includes("/auth/register");
      if (!isCredentialCheck) {
        clearStoredToken();
        onUnauthorized?.();
      }
    }
    return Promise.reject(error);
  }
);
