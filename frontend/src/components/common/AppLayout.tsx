import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "@/components/common/Sidebar";
import { Header } from "@/components/common/Header";
import { NAV_ITEMS } from "@/utils/constants";

function pageTitleForPath(pathname: string): string {
  const match = NAV_ITEMS.find((item) => pathname.startsWith(item.path));
  return match?.label ?? "AI Cybersecurity Mentor";
}

export function AppLayout() {
  const location = useLocation();

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
