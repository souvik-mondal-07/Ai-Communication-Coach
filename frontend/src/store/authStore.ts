import { create } from "zustand";

/**
 * Placeholder auth store.
 *
 * Step 1 only establishes the shape of this store so future features
 * (login, register, JWT session handling) can plug in without a rewrite.
 * No authentication logic is implemented yet.
 */
interface AuthState {
  isAuthenticated: boolean;
  user: null;
}

export const useAuthStore = create<AuthState>(() => ({
  isAuthenticated: false,
  user: null,
}));
