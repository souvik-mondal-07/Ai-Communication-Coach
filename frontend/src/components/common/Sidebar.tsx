import { useEffect, useRef } from "react";
import { ArrowRight, Star, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { BrandMark } from "@/components/common/BrandMark";
import { isNavItemActive, NAV_SECTIONS } from "@/components/common/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/appStore";
import { useNotificationStore } from "@/store/notificationStore";

function SidebarContent({ closeButtonRef }: { closeButtonRef?: React.RefObject<HTMLButtonElement | null> }) {
  const closeMobileSidebar = useAppStore((s) => s.closeMobileSidebar);
  const unread = useNotificationStore((s) => s.unreadCount);
  const { pathname } = useLocation();

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex h-[68px] shrink-0 items-center justify-between border-b border-border px-5">
        <Link to="/dashboard" onClick={closeMobileSidebar} className="flex items-center gap-3 rounded-[var(--radius-panel)]">
          <BrandMark size={40} />
          <div className="leading-tight">
            <p className="whitespace-nowrap font-display text-[15.5px] font-semibold text-text-primary">AI CyberSec Mentor</p>
            <p className="text-[11px] text-text-muted">Learn · Practice · Grow</p>
          </div>
        </Link>
        <button
          ref={closeButtonRef}
          type="button"
          onClick={closeMobileSidebar}
          className="rounded-[var(--radius-panel)] p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-text-primary md:hidden"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      <nav aria-label="Main" className="flex-1 overflow-y-auto px-3.5 py-4">
        {NAV_SECTIONS.map((section, idx) => (
          <ul key={section.heading ?? `section-${idx}`} className="space-y-1">
            {section.items.map((item) => {
              const { label, path, icon: Icon } = item;
              const active = isNavItemActive(item, pathname);
              const count = item.badge === "notifications" ? unread : 0;
              return (
                <li key={path}>
                  <Link
                    to={path}
                    onClick={closeMobileSidebar}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group flex items-center gap-3 rounded-[var(--radius-panel)] px-3.5 py-2 text-sm transition-[background-color,color,box-shadow,transform] duration-200",
                      active
                        ? "bg-nav-active font-medium text-white shadow-[0_8px_22px_-10px_rgb(47_107_255/0.9)]"
                        : "text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                    )}
                  >
                    <Icon size={19} strokeWidth={1.75} aria-hidden="true" className={cn("shrink-0 transition-transform duration-200", !active && "group-hover:scale-110")} />
                    <span className="min-w-0 flex-1 truncate">{label}</span>
                    {count > 0 && (
                      <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1.5 text-[11px] font-semibold text-on-danger" aria-label={`${count} unread`}>
                        {count > 99 ? "99+" : count}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        ))}
      </nav>

      <div className="hidden shrink-0 p-3.5 [@media(min-height:860px)]:block">
        <div className="rounded-[var(--radius-card)] border border-[#2c3aa8]/60 bg-promo p-4 text-white shadow-[0_14px_34px_-18px_rgb(60_70_240/0.8)]">
          <Star size={20} className="fill-[#ff8fd8] text-[#ff8fd8]" aria-hidden="true" />
          <p className="mt-2 font-display text-[15px] font-semibold">Level Up Your Skills</p>
          <p className="mt-1.5 text-[13px] leading-relaxed text-white/75">Stay consistent, build your skills, and achieve your goals with your AI mentor.</p>
          <Link
            to="/progress"
            onClick={closeMobileSidebar}
            className="mt-3 inline-flex h-9 items-center gap-2 rounded-[var(--radius-panel)] bg-cta px-4 text-sm font-medium text-white transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.98]"
          >
            View Progress <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export function Sidebar() {
  const isOpen = useAppStore((s) => s.isMobileSidebarOpen);
  const closeMobileSidebar = useAppStore((s) => s.closeMobileSidebar);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Mobile drawer: Escape closes, page scroll is locked, focus moves into the drawer.
  useEffect(() => {
    if (!isOpen) return;
    closeRef.current?.focus();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeMobileSidebar();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKey);
    };
  }, [isOpen, closeMobileSidebar]);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-[272px] shrink-0 border-r border-border md:block">
        <div className="sticky top-0 h-dvh w-[272px]">
          <SidebarContent />
        </div>
      </aside>

      {/*
        Mobile drawer stays mounted so it can slide in and out. `inert` removes it
        from tab order and the accessibility tree while closed.
      */}
      <div className={cn("fixed inset-0 z-40 md:hidden", !isOpen && "pointer-events-none")} inert={!isOpen}>
        <div
          className={cn("absolute inset-0 bg-black/60 transition-opacity duration-200", isOpen ? "opacity-100" : "opacity-0")}
          onClick={closeMobileSidebar}
          aria-hidden="true"
        />
        <aside
          aria-label="Navigation menu"
          className={cn(
            "relative z-50 h-full w-72 border-r border-border shadow-pop transition-transform duration-250 ease-[var(--ease-out-quint)]",
            isOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <SidebarContent closeButtonRef={closeRef} />
        </aside>
      </div>
    </>
  );
}
