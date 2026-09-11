import {
  LayoutDashboard,
  Bot,
  ShieldHalf,
  Flag,
  MessagesSquare,
  Mic,
  Target,
  TrendingUp,
  History,
  UserRound,
  Settings,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/appStore";

const NAV_SECTIONS = [
  {
    items: [
      { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
      { label: "AI Mentor", path: "/mentor", icon: Bot },
    ],
  },
  {
    heading: "Train",
    items: [
      { label: "Cybersecurity", path: "/cybersecurity", icon: ShieldHalf },
      { label: "CTF & Labs", path: "/ctf", icon: Flag },
      { label: "Communication", path: "/communication", icon: MessagesSquare },
      { label: "Interview", path: "/interview", icon: Mic },
      { label: "Practice", path: "/practice", icon: Target },
    ],
  },
  {
    heading: "Track",
    items: [
      { label: "Progress", path: "/progress", icon: TrendingUp },
      { label: "History", path: "/history", icon: History },
    ],
  },
  {
    heading: "Account",
    items: [
      { label: "Profile", path: "/profile", icon: UserRound },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

function SidebarContent() {
  const closeMobileSidebar = useAppStore((s) => s.closeMobileSidebar);

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center justify-between border-b border-border px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
            <ShieldHalf size={18} strokeWidth={2.25} />
          </div>
          <div className="leading-tight">
            <p className="font-display text-sm font-semibold text-text-primary">
              Mentor
            </p>
            <p className="text-[11px] text-text-muted">Cybersecurity &amp; Career</p>
          </div>
        </div>
        <button
          type="button"
          onClick={closeMobileSidebar}
          className="rounded-[var(--radius-panel)] p-1.5 text-text-muted hover:bg-surface-raised hover:text-text-primary md:hidden"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {NAV_SECTIONS.map((section, idx) => (
          <div key={section.heading ?? `section-${idx}`}>
            {section.heading && (
              <p className="mb-2 px-2 text-[11px] font-medium text-text-muted">
                {section.heading}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map(({ label, path, icon: Icon }) => (
                <li key={path}>
                  <NavLink
                    to={path}
                    onClick={closeMobileSidebar}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-[var(--radius-panel)] px-3 py-2 text-sm transition-colors",
                        isActive
                          ? "bg-signal/10 text-signal"
                          : "text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                      )
                    }
                  >
                    <Icon size={17} strokeWidth={2} />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-5 py-4">
        <p className="text-[11px] text-text-muted">v0.1.0 · Foundation build</p>
      </div>
    </div>
  );
}

export function Sidebar() {
  const isMobileSidebarOpen = useAppStore((s) => s.isMobileSidebarOpen);
  const closeMobileSidebar = useAppStore((s) => s.closeMobileSidebar);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 border-r border-border md:block">
        <div className="fixed h-screen w-60">
          <SidebarContent />
        </div>
      </aside>

      {/* Mobile sidebar drawer */}
      {isMobileSidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={closeMobileSidebar}
            aria-hidden="true"
          />
          <aside className="relative z-50 h-full w-64 border-r border-border">
            <SidebarContent />
          </aside>
        </div>
      )}
    </>
  );
}
