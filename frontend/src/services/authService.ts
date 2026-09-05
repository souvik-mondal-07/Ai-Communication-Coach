import { api } from "@/services/api";
import type { User } from "@/types/auth";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

interface LoginResponseData {
  access_token: string;
  token_type: string;
  user: User;
}

/**
 * Register a new account. Does not log the user in — they sign in
 * separately afterwards via `login()`.
 */
export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<ApiEnvelope<{ user: User }>>(
    "/auth/register",
    payload
  );
  return data.data.user;
}

export async function login(
  payload: LoginPayload
): Promise<{ user: User; accessToken: string }> {
  const { data } = await api.post<ApiEnvelope<LoginResponseData>>(
    "/auth/login",
    payload
  );
  return { user: data.data.user, accessToken: data.data.access_token };
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get<ApiEnvelope<{ user: User }>>("/auth/me");
  return data.data.user;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}
