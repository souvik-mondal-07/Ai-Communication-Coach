import { useAuthStore } from "@/store/authStore";

/**
 * Placeholder hook exposing auth state to components.
 * Real login/logout actions are added with the authentication feature.
 */
export function useAuth() {
  const { isAuthenticated, user } = useAuthStore();
  return { isAuthenticated, user };
}
