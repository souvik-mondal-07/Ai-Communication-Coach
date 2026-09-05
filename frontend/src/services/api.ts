import axios from "axios";
import { API_BASE_URL } from "@/utils/constants";

/**
 * Single Axios instance for the whole app. All feature services import this
 * instead of creating their own client, so base URL, headers, and future
 * interceptors (auth token attachment, error normalization) live in one place.
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});
