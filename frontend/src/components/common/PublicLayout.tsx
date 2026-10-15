import { Link, NavLink, Outlet } from "react-router-dom";
import { Newspaper } from "lucide-react";
import { BrandMark } from "@/components/common/BrandMark";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { buttonVariants } from "@/components/ui/button-variants";
import { cn } from "@/lib/utils";
import { APP_NAME } from "@/utils/constants";

/**
 * Frame for pages anyone can open without an account (today: /news). It deliberately holds no
 * auth logic and no private data: just brand, a link back to the news, theme, and sign-in /
 * sign-up calls to action that never block reading.
 */
export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main-content" className="skip-link rounded-[var(--radius-panel)] bg-signal px-4 py-2 text-sm font-medium text-on-signal">
        Skip to content
      </a>
      <header className="glass sticky top-0 z-30 border-b border-border">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 md:px-8">
          <Link to="/news" className="flex min-w-0 items-center gap-2.5 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal">
            <BrandMark size={30} />
            <span className="hidden truncate font-display text-sm font-semibold text-text-primary sm:inline">{APP_NAME}</span>
          </Link>
          <nav aria-label="Public" className="ml-2 flex items-center">
            <NavLink
              to="/news"
              className={({ isActive }) =>
                cn("inline-flex items-center gap-1.5 rounded-[var(--radius-panel)] px-3 py-1.5 text-sm font-medium transition-colors",
                  isActive ? "bg-signal/10 text-signal" : "text-text-secondary hover:text-text-primary")
              }
            >
              <Newspaper size={15} aria-hidden="true" /> Cybersecurity News
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <Link to="/login" className={buttonVariants({ variant: "ghost", size: "sm" })}>Log in</Link>
            <Link to="/register" className={buttonVariants({ variant: "primary", size: "sm" })}>Sign up</Link>
          </div>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 focus:outline-none md:px-8 md:py-8">
        <Outlet />
      </main>
      <footer className="border-t border-border px-4 py-5 text-center text-xs text-text-muted">
        Headlines and short excerpts link to their original publishers, who own the articles.
      </footer>
    </div>
  );
}
