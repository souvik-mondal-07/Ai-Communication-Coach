import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/common/AppLayout";
import { FullScreenLoader } from "@/components/common/FullScreenLoader";
import { ProtectedRoute } from "@/components/common/ProtectedRoute";
import { PublicOnlyRoute } from "@/components/common/PublicOnlyRoute";
import { useAuthStore } from "@/store/authStore";

// Each page is its own chunk so the first load doesn't ship the whole app.
const Login = lazy(() => import("@/pages/auth/Login"));
const Register = lazy(() => import("@/pages/auth/Register"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Mentor = lazy(() => import("@/pages/Mentor"));
const Cybersecurity = lazy(() => import("@/pages/Cybersecurity"));
const Practice = lazy(() => import("@/pages/Practice"));
const CybersecurityTopic = lazy(() => import("@/pages/CybersecurityTopic"));
const CybersecurityPractice = lazy(() => import("@/pages/CybersecurityPractice"));
const CTF = lazy(() => import("@/pages/CTF"));
const CtfSession = lazy(() => import("@/pages/CtfSession"));
const Communication = lazy(() => import("@/pages/Communication"));
const CommunicationSessionPage = lazy(() => import("@/pages/CommunicationSessionPage"));
const Interview = lazy(() => import("@/pages/Interview"));
const InterviewSessionPage = lazy(() => import("@/pages/InterviewSessionPage"));
const PressureTraining = lazy(() => import("@/pages/PressureTraining"));
const PressureSessionPage = lazy(() => import("@/pages/PressureSessionPage"));
const VoiceConversation = lazy(() => import("@/pages/VoiceConversation"));
const VoiceConversationSessionPage = lazy(() => import("@/pages/VoiceConversationSessionPage"));
const History = lazy(() => import("@/pages/History"));
const HistoryDetail = lazy(() => import("@/pages/HistoryDetail"));
const Progress = lazy(() => import("@/pages/Progress"));
const Profile = lazy(() => import("@/pages/Profile"));
const Settings = lazy(() => import("@/pages/Settings"));

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
    <Suspense fallback={<FullScreenLoader />}>
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
          <Route path="/communication/:sessionId" element={<CommunicationSessionPage />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/interview/:sessionId" element={<InterviewSessionPage />} />
          <Route path="/pressure-training" element={<PressureTraining />} />
          <Route path="/pressure-training/:sessionId" element={<PressureSessionPage />} />
          {/* Placeholder-only pages are not linked in the nav; old URLs go to the real feature. */}
          <Route path="/voice-conversation" element={<VoiceConversation />} />
          <Route path="/voice-conversation/:sessionId" element={<VoiceConversationSessionPage />} />

          <Route path="/practice" element={<Practice />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/history" element={<History />} />
          <Route path="/history/:type/:id" element={<HistoryDetail />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
    </Suspense>
  );
}
