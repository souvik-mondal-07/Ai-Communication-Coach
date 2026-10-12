import { useEffect, useRef } from "react";
import { ShieldHalf, X } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import { NAV_SECTIONS } from "@/components/common/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/appStore";
import { useAuthStore } from "@/store/authStore";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function SidebarContent({ closeButtonRef }: { closeButtonRef?: React.RefObject<HTMLButtonElement | null> }) {
  const closeMobileSidebar = useAppStore((s) => s.closeMobileSidebar);
  const user = useAuthStore((s) => s.user);

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center justify-between border-b border-border px-5 py-5">
        <Link to="/dashboard" onClick={closeMobileSidebar} className="flex items-center gap-2.5 rounded-[var(--radius-panel)]">
          <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-panel)] bg-brand text-white shadow-[0_6px_18px_-6px_rgb(91_141_255/0.7)]">
            <ShieldHalf size={18} strokeWidth={2.25} aria-hidden="true" />
          </div>
          <div className="leading-tight">
            <p className="font-display text-sm font-semibold text-text-primary">Mentor</p>
            <p className="text-[11px] text-text-muted">Cybersecurity &amp; Career</p>
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

      <nav aria-label="Main" className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {NAV_SECTIONS.map((section, idx) => (
          <div key={section.heading ?? `section-${idx}`}>
            {section.heading && <p className="mb-2 px-3 text-[11px] font-medium text-text-muted">{section.heading}</p>}
            <ul className="space-y-0.5">
              {section.items.map(({ label, path, icon: Icon }) => (
                <li key={path}>
                  <NavLink
                    to={path}
                    onClick={closeMobileSidebar}
                    className={({ isActive }) =>
                      cn(
                        "relative flex items-center gap-3 rounded-[var(--radius-panel)] px-3 py-2 text-sm transition-colors duration-150",
                        // Active indicator: a bar that grows in from the center.
                        "before:absolute before:-left-3 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-signal before:transition-transform before:duration-200",
                        isActive
                          ? "bg-signal/10 font-medium text-signal before:scale-y-100"
                          : "text-text-secondary before:scale-y-0 hover:bg-surface-raised hover:text-text-primary"
                      )
                    }
                  >
                    <Icon size={17} strokeWidth={2} aria-hidden="true" />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {user && (
        <div className="border-t border-border p-3">
          <Link
            to="/profile"
            onClick={closeMobileSidebar}
            className="flex items-center gap-3 rounded-[var(--radius-panel)] px-2 py-2 transition-colors hover:bg-surface-raised"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white" aria-hidden="true">
              {initials(user.name)}
            </span>
            <span className="min-w-0 leading-tight">
              <span className="block truncate text-sm text-text-primary">{user.name}</span>
              <span className="block truncate text-[11px] text-text-muted">{user.email}</span>
            </span>
          </Link>
        </div>
      )}
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
      <aside className="hidden w-60 shrink-0 border-r border-border md:block">
        <div className="sticky top-0 h-dvh w-60">
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
            "relative z-50 h-full w-64 border-r border-border shadow-pop transition-transform duration-250 ease-[var(--ease-out-quint)]",
            isOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <SidebarContent closeButtonRef={closeRef} />
        </aside>
      </div>
    </>
  );
}
