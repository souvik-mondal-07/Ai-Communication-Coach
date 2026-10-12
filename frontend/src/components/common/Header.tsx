import { type KeyboardEvent, useCallback, useRef, useState } from "react";
import { ChevronRight, LogOut, Menu, Settings, UserRound } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { breadcrumbsFor } from "@/components/common/navigation";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { useAuth } from "@/hooks/useAuth";
import { useDismiss } from "@/hooks/useDismiss";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/appStore";

const MENU_ITEM =
  "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary focus-visible:bg-surface-raised focus-visible:text-text-primary focus-visible:outline-none";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function Breadcrumbs() {
  const crumbs = breadcrumbsFor(useLocation().pathname);
  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        {crumbs.map((c, i) => {
          const isLast = i === crumbs.length - 1;
          return (
            <li key={c.label} className={cn("flex min-w-0 items-center gap-1.5", !isLast && "hidden sm:flex")}>
              {c.to && !isLast ? (
                <Link to={c.to} className="rounded text-text-muted transition-colors hover:text-text-primary">
                  {c.label}
                </Link>
              ) : (
                <span aria-current="page" className="truncate font-medium text-text-primary">
                  {c.label}
                </span>
              )}
              {!isLast && <ChevronRight size={14} className="shrink-0 text-text-muted" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function Header() {
  const openMobileSidebar = useAppStore((s) => s.openMobileSidebar);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setIsMenuOpen(false), []);
  useDismiss(wrapRef, isMenuOpen, close);

  async function handleLogout() {
    close();
    await logout();
    navigate("/login", { replace: true });
  }

  // Arrow keys move between menu items; Escape (handled by useDismiss) closes, then focus returns to the trigger.
  function onMenuKey(e: KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
    const idx = items.indexOf(document.activeElement as HTMLElement);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      items[(idx + 1) % items.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      items[(idx - 1 + items.length) % items.length]?.focus();
    } else if (e.key === "Escape") {
      triggerRef.current?.focus();
    }
  }

  function toggleMenu() {
    const next = !isMenuOpen;
    setIsMenuOpen(next);
    if (next) requestAnimationFrame(() => menuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus());
  }

  return (
    <header className="glass sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border px-4 md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={openMobileSidebar}
          className="rounded-[var(--radius-panel)] p-1.5 text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary md:hidden"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <Breadcrumbs />
      </div>

      <div className="flex items-center gap-1">
        <NotificationBell />
        <div ref={wrapRef} className="relative">
          <button
            ref={triggerRef}
            type="button"
            onClick={toggleMenu}
            className="flex items-center gap-2 rounded-[var(--radius-panel)] px-1.5 py-1 text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
            aria-label="Account menu"
            aria-haspopup="menu"
            aria-expanded={isMenuOpen}
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand text-[11px] font-semibold text-white" aria-hidden="true">
              {user ? initials(user.name) : "?"}
            </span>
            {user && <span className="hidden max-w-32 truncate text-sm sm:inline">{user.name}</span>}
          </button>

          {isMenuOpen && (
            <div
              ref={menuRef}
              role="menu"
              aria-label="Account"
              onKeyDown={onMenuKey}
              className="glass absolute right-0 z-20 mt-2 w-56 origin-top-right animate-pop-in rounded-[var(--radius-card)] border border-border-strong p-1.5 shadow-pop"
            >
              {user && (
                <div className="mb-1 border-b border-border px-2.5 pb-2.5 pt-1.5">
                  <p className="truncate text-sm font-medium text-text-primary">{user.name}</p>
                  <p className="truncate text-xs text-text-muted">{user.email}</p>
                </div>
              )}
              <Link role="menuitem" to="/profile" onClick={close} className={MENU_ITEM}>
                <UserRound size={15} aria-hidden="true" />
                Profile
              </Link>
              <Link role="menuitem" to="/settings" onClick={close} className={MENU_ITEM}>
                <Settings size={15} aria-hidden="true" />
                Settings
              </Link>
              <button role="menuitem" type="button" onClick={() => void handleLogout()} className={MENU_ITEM}>
                <LogOut size={15} aria-hidden="true" />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
