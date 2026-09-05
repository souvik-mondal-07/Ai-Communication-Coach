import { ShieldHalf } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function Login() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm rounded-[var(--radius-panel)] border border-border bg-surface px-7 py-8">
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
            <ShieldHalf size={18} />
          </div>
          <span className="font-display text-base font-semibold text-text-primary">
            AI Cybersecurity Mentor
          </span>
        </div>

        <h1 className="text-lg font-semibold text-text-primary">Sign in</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Authentication isn&apos;t wired up yet — this is a layout placeholder.
        </p>

        <form className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-text-secondary">
              Email
            </label>
            <input
              id="email"
              type="email"
              disabled
              placeholder="you@example.com"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-text-secondary">
              Password
            </label>
            <input
              id="password"
              type="password"
              disabled
              placeholder="••••••••"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>
          <Button type="button" disabled className="w-full">
            Sign in
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-text-secondary">
          No account?{" "}
          <Link to="/register" className="text-link hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
