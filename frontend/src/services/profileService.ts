import { api } from "@/services/api";
import { setStoredToken } from "@/services/tokenStorage";
import type {
  ChangePasswordPayload,
  PreferencesUpdate,
  ProfileUpdate,
  UserPreferences,
  UserProfile,
} from "@/types/profile";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

// Identity always comes from the bearer token — no user id is ever sent.

export async function getProfile(): Promise<UserProfile> {
  const { data } = await api.get<ApiEnvelope<{ user: UserProfile }>>("/users/me");
  return data.data.user;
}

export async function updateProfile(payload: ProfileUpdate): Promise<UserProfile> {
  const { data } = await api.patch<ApiEnvelope<{ user: UserProfile }>>("/users/me", payload);
  return data.data.user;
}

export async function getPreferences(): Promise<UserPreferences> {
  const { data } = await api.get<ApiEnvelope<{ preferences: UserPreferences }>>("/users/me/preferences");
  return data.data.preferences;
}

export async function updatePreferences(payload: PreferencesUpdate): Promise<UserPreferences> {
  const { data } = await api.patch<ApiEnvelope<{ preferences: UserPreferences }>>(
    "/users/me/preferences",
    payload
  );
  return data.data.preferences;
}

/**
 * Changing the password invalidates every token issued before the change, so the backend
 * returns a fresh one for this device. It is stored immediately (the request interceptor
 * reads it from storage), which keeps the user signed in here while any other session —
 * or a stolen token — stops working. Resolves to the new token so callers can sync state.
 */
export async function changePassword(payload: ChangePasswordPayload): Promise<string | null> {
  const { data } = await api.post<ApiEnvelope<{ access_token?: string }>>("/users/me/change-password", payload);
  const token = data.data?.access_token ?? null;
  if (token) {
    setStoredToken(token);
  }
  return token;
}
