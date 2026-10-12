import { useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "@/components/common/Sidebar";
import { Header } from "@/components/common/Header";
import { documentTitleFor } from "@/components/common/navigation";
import { useReminderSync } from "@/hooks/useReminderSync";
import { useAuthStore } from "@/store/authStore";
import { useProfileStore } from "@/store/profileStore";

export function AppLayout() {
  const { pathname } = useLocation();
  const userId = useAuthStore((s) => s.user?.id);
  const loadProfile = useProfileStore((s) => s.loadProfile);
  const mainRef = useRef<HTMLElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  // Last pathname we handled. Comparing (instead of a "first render" flag) also
  // survives React StrictMode replaying effects in development.
  const handledPath = useRef(pathname);

  // Load the profile once per signed-in user so the saved theme is applied
  // everywhere and Profile/Settings open instantly.
  useEffect(() => {
    if (userId) void loadProfile();
  }, [userId, loadProfile]);

  useReminderSync(userId);

  // On every navigation: update the tab title, move focus to the page so screen
  // readers announce it, and play a short fade/rise. The animation runs through
  // the Web Animations API on a wrapper, so page components are never remounted
  // and keep their state.
  useEffect(() => {
    document.title = documentTitleFor(pathname);
    if (handledPath.current === pathname) return;
    handledPath.current = pathname;
    mainRef.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) {
      pageRef.current?.animate(
        [
          { opacity: 0, transform: "translateY(8px)" },
          { opacity: 1, transform: "none" },
        ],
        { duration: 240, easing: "cubic-bezier(0.22, 1, 0.36, 1)" }
      );
    }
  }, [pathname]);

  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="skip-link rounded-[var(--radius-panel)] bg-signal px-4 py-2 text-sm font-medium text-on-signal"
        onClick={(e) => {
          e.preventDefault();
          mainRef.current?.focus();
        }}
      >
        Skip to content
      </a>
      <div className="mx-auto flex max-w-[1600px]">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main id="main-content" ref={mainRef} tabIndex={-1} className="flex-1 px-4 py-6 focus:outline-none md:px-8 md:py-8">
            <div ref={pageRef}>
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
