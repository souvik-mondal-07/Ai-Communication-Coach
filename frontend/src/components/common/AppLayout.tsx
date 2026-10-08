import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "@/components/common/Sidebar";
import { Header } from "@/components/common/Header";
import { useReminderSync } from "@/hooks/useReminderSync";
import { useAuthStore } from "@/store/authStore";
import { useProfileStore } from "@/store/profileStore";
import { NAV_ITEMS } from "@/utils/constants";

function pageTitleForPath(pathname: string): string {
  const match = NAV_ITEMS.find((item) => pathname.startsWith(item.path));
  return match?.label ?? "AI Cybersecurity Mentor";
}

export function AppLayout() {
  const location = useLocation();
  const userId = useAuthStore((s) => s.user?.id);
  const loadProfile = useProfileStore((s) => s.loadProfile);

  // Load the profile once per signed-in user so the saved theme is applied
  // everywhere and Profile/Settings open instantly.
  useEffect(() => {
    if (userId) void loadProfile();
  }, [userId, loadProfile]);

  useReminderSync(userId);

  return (
    <div className="min-h-screen bg-base">
      <div className="mx-auto flex max-w-[1600px]">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header title={pageTitleForPath(location.pathname)} />
          <main className="flex-1 px-4 py-6 md:px-8 md:py-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
