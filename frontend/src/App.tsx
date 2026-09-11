import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/common/AppLayout";
import { FullScreenLoader } from "@/components/common/FullScreenLoader";
import { ProtectedRoute } from "@/components/common/ProtectedRoute";
import { PublicOnlyRoute } from "@/components/common/PublicOnlyRoute";
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import Dashboard from "@/pages/Dashboard";
import Mentor from "@/pages/Mentor";
import Cybersecurity from "@/pages/Cybersecurity";
import CybersecurityTopic from "@/pages/CybersecurityTopic";
import CybersecurityPractice from "@/pages/CybersecurityPractice";
import CTF from "@/pages/CTF";
import CtfSession from "@/pages/CtfSession";
import Communication from "@/pages/Communication";
import Interview from "@/pages/Interview";
import Practice from "@/pages/Practice";
import Progress from "@/pages/Progress";
import History from "@/pages/History";
import Profile from "@/pages/Profile";
import Settings from "@/pages/Settings";
import { useAuthStore } from "@/store/authStore";

export default function App() {
  const isLoading = useAuthStore((s) => s.isLoading);
  const loadCurrentUser = useAuthStore((s) => s.loadCurrentUser);

  // On app start: check for a stored token and validate it against the
  // backend before rendering any route, so an authenticated user never
  // flashes the login page and an unauthenticated one never flashes a
  // protected page.
  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  if (isLoading) {
    return <FullScreenLoader />;
  }

  return (
    <Routes>
      {/* Public routes — redirect to /dashboard if already authenticated */}
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Application routes — redirect to /login if not authenticated */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/mentor" element={<Mentor />} />
          <Route path="/cybersecurity" element={<Cybersecurity />} />
          <Route path="/cybersecurity/practice/:sessionId" element={<CybersecurityPractice />} />
          <Route path="/cybersecurity/:slug" element={<CybersecurityTopic />} />
          <Route path="/ctf" element={<CTF />} />
          <Route path="/ctf/:sessionId" element={<CtfSession />} />
          <Route path="/communication" element={<Communication />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/practice" element={<Practice />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/history" element={<History />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
