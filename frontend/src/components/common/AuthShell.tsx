import { Newspaper } from "lucide-react";
import { Link } from "react-router-dom";
import { BrandMark } from "@/components/common/BrandMark";
import type { ReactNode } from "react";
import { APP_NAME } from "@/utils/constants";

/** Shared frame for the sign-in and register pages: brand, glass card, faint grid and glow. */
export function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0" />
      <main className="relative w-full max-w-sm animate-rise-in">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <BrandMark size={44} />
          <span className="font-display text-base font-semibold text-text-primary">{APP_NAME}</span>
        </div>
        <div className="glass rounded-[var(--radius-card)] border border-border-strong/70 px-7 py-8 shadow-pop">
          <h1 className="font-display text-xl font-semibold text-text-primary">{title}</h1>
          <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>
          {children}
        </div>
        <p className="mt-5 text-center text-sm text-text-secondary">{footer}</p>
        <p className="mt-3 text-center text-sm">
          <Link to="/news" className="inline-flex items-center gap-1.5 rounded-sm font-medium text-link hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal">
            <Newspaper size={14} aria-hidden="true" /> Read cybersecurity news — no account needed
          </Link>
        </p>
      </main>
    </div>
  );
}

export function FormBanner({ tone, children }: { tone: "error" | "success"; children: ReactNode }) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={
        tone === "error"
          ? "mt-5 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger"
          : "mt-5 rounded-[var(--radius-panel)] border border-success/40 bg-success/10 px-3 py-2 text-sm text-success"
      }
    >
      {children}
    </p>
  );
}
