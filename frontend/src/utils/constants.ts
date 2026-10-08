export const APP_NAME = "AI Cybersecurity Mentor";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const NAV_ITEMS = [
  { label: "Dashboard", path: "/dashboard" },
  { label: "AI Mentor", path: "/mentor" },
  { label: "Cybersecurity", path: "/cybersecurity" },
  { label: "CTF & Labs", path: "/ctf" },
  { label: "Communication", path: "/communication" },
  { label: "Interview", path: "/interview" },
  { label: "Pressure Training", path: "/pressure-training" },
  { label: "Practice", path: "/practice" },
  { label: "Daily Practice", path: "/daily-practice" },
  { label: "Notifications", path: "/notifications" },
  { label: "Progress", path: "/progress" },
  { label: "History", path: "/history" },
  { label: "Profile", path: "/profile" },
  { label: "Settings", path: "/settings" },
] as const;
