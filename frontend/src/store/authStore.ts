import { create } from "zustand";
import * as authService from "@/services/authService";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/services/tokenStorage";
import type { User } from "@/types/auth";
import { getApiErrorMessage } from "@/utils/apiError";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  /** True while the initial "do we already have a session?" check is running. */
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadCurrentUser: () => Promise<void>;
  clearError: () => void;
}

/**
 * All authentication API calls happen here, never inside components —
 * components call these actions and read `user` / `isAuthenticated` back out.
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  login: async (email, password) => {
    set({ error: null });
    try {
      const { user, accessToken } = await authService.login({ email, password });
      setStoredToken(accessToken);
      set({ user, accessToken, isAuthenticated: true });
    } catch (err) {
      const message = getApiErrorMessage(err, "Invalid email or password.");
      set({ error: message });
      throw new Error(message);
    }
  },

  register: async (name, email, password) => {
    set({ error: null });
    try {
      await authService.register({ name, email, password });
      // Registration intentionally does not sign the user in automatically —
      // they log in explicitly afterwards.
    } catch (err) {
      const message = getApiErrorMessage(err, "Could not create your account.");
      set({ error: message });
      throw new Error(message);
    }
  },

  logout: async () => {
    try {
      await authService.logout();
    } catch {
      // Logout must always succeed from the user's point of view, even if
      // the network call fails — the token is discarded either way.
    } finally {
      clearStoredToken();
      set({ user: null, accessToken: null, isAuthenticated: false });
    }
  },

  loadCurrentUser: async () => {
    const token = getStoredToken();
    if (!token) {
      set({ isLoading: false });
      return;
    }

    set({ accessToken: token, isLoading: true });
    try {
      const user = await authService.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      clearStoredToken();
      set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
