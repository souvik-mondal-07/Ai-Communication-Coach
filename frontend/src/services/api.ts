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

// If the token is rejected as invalid/expired, drop it. The auth store
// notices on its next `/auth/me` check or protected navigation.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      clearStoredToken();
    }
    return Promise.reject(error);
  }
);
