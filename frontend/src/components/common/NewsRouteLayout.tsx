import { AppLayout } from "@/components/common/AppLayout";
import { PublicLayout } from "@/components/common/PublicLayout";
import { useAuthStore } from "@/store/authStore";

/**
 * Chooses the frame for routes that anyone may open. It never redirects and never blocks:
 * signed-in users get the normal app shell (sidebar, header, notifications), visitors get the
 * public shell. Either way the page inside is the same.
 */
export function NewsRouteLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <AppLayout /> : <PublicLayout />;
}
