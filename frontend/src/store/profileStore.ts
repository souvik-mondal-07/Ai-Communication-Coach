import { create } from "zustand";
import * as profileService from "@/services/profileService";
import { useAuthStore } from "@/store/authStore";
import type { PreferencesUpdate, ProfileUpdate, UserProfile } from "@/types/profile";
import { applyTheme } from "@/utils/theme";

interface ProfileState {
  profile: UserProfile | null;
  isLoading: boolean;
  loadError: boolean;

  loadProfile: () => Promise<void>;
  /** Rejects on failure; the caller decides which message to show. */
  saveProfile: (update: ProfileUpdate) => Promise<void>;
  savePreferences: (update: PreferencesUpdate) => Promise<void>;
}

/**
 * Holds the profile/preferences read from `/users/me`. Authentication state
 * stays in the auth store — the only thing synced across is the display name,
 * which the header and the rest of the app already read from `authStore.user`.
 */
export const useProfileStore = create<ProfileState>((set) => ({
  profile: null,
  isLoading: false,
  loadError: false,

  loadProfile: async () => {
    set({ isLoading: true, loadError: false });
    try {
      const profile = await profileService.getProfile();
      set({ profile, isLoading: false });
      applyTheme(profile.preferences.theme);
    } catch {
      set({ isLoading: false, loadError: true });
    }
  },

  saveProfile: async (update) => {
    const profile = await profileService.updateProfile(update);
    set({ profile });
    useAuthStore.getState().patchUser({ name: profile.full_name });
  },

  savePreferences: async (update) => {
    const preferences = await profileService.updatePreferences(update);
    set((state) => (state.profile ? { profile: { ...state.profile, preferences } } : state));
    applyTheme(preferences.theme);
  },
}));
