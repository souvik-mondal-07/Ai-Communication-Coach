import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/common/AppLayout";
import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import Dashboard from "@/pages/Dashboard";
import Mentor from "@/pages/Mentor";
import Cybersecurity from "@/pages/Cybersecurity";
import Communication from "@/pages/Communication";
import Interview from "@/pages/Interview";
import Practice from "@/pages/Practice";
import Progress from "@/pages/Progress";
import History from "@/pages/History";
import Profile from "@/pages/Profile";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Application routes */}
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/mentor" element={<Mentor />} />
        <Route path="/cybersecurity" element={<Cybersecurity />} />
        <Route path="/communication" element={<Communication />} />
        <Route path="/interview" element={<Interview />} />
        <Route path="/practice" element={<Practice />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/history" element={<History />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
