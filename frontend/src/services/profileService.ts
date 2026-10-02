import { api } from "@/services/api";
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

export async function changePassword(payload: ChangePasswordPayload): Promise<void> {
  await api.post("/users/me/change-password", payload);
}
