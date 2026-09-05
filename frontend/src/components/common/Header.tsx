import { useState } from "react";
import { LogOut, Menu, UserCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/store/appStore";
import { useAuth } from "@/hooks/useAuth";

interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  const openMobileSidebar = useAppStore((s) => s.openMobileSidebar);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  async function handleLogout() {
    setIsMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-base/95 px-4 backdrop-blur md:px-8">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={openMobileSidebar}
          className="rounded-[var(--radius-panel)] p-1.5 text-text-secondary hover:bg-surface-raised hover:text-text-primary md:hidden"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-base font-semibold text-text-primary">{title}</h1>
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={() => setIsMenuOpen((open) => !open)}
          className="flex items-center gap-2 rounded-[var(--radius-panel)] px-2 py-1 text-text-secondary hover:bg-surface-raised hover:text-text-primary"
          aria-label="Account menu"
        >
          <UserCircle2 size={26} strokeWidth={1.5} />
          {user && <span className="hidden text-sm sm:inline">{user.name}</span>}
        </button>

        {isMenuOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setIsMenuOpen(false)}
              aria-hidden="true"
            />
            <div className="absolute right-0 z-20 mt-2 w-48 rounded-[var(--radius-panel)] border border-border bg-surface py-1 shadow-lg">
              {user && (
                <div className="border-b border-border px-3 py-2">
                  <p className="truncate text-sm text-text-primary">{user.name}</p>
                  <p className="truncate text-xs text-text-muted">{user.email}</p>
                </div>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-raised hover:text-text-primary"
              >
                <LogOut size={15} />
                Log out
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
