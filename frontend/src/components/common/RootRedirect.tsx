import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

/** "/" sends signed-in users to their dashboard and everyone else to the public news. */
export function RootRedirect() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return <Navigate to={isAuthenticated ? "/dashboard" : "/news"} replace />;
}
