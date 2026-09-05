import { type FormEvent, useState } from "react";
import { ShieldHalf } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { isValidEmail } from "@/utils/validators";

interface FieldErrors {
  email?: string;
  password?: string;
}

export default function Login() {
  const { login, error, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { justRegistered?: boolean } };

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate(): boolean {
    const errors: FieldErrors = {};
    if (!email.trim()) errors.email = "Email is required.";
    else if (!isValidEmail(email)) errors.email = "Enter a valid email address.";
    if (!password) errors.password = "Password is required.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard", { replace: true });
    } catch {
      // Error message is already surfaced via the store's `error` state.
    } finally {
      setIsSubmitting(false);
    }
  }

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
          Welcome back. Enter your details to continue.
        </p>

        {location.state?.justRegistered && (
          <p className="mt-4 rounded-[var(--radius-panel)] border border-signal-dim/40 bg-signal/10 px-3 py-2 text-sm text-signal">
            Account created — sign in to continue.
          </p>
        )}

        {error && (
          <p className="mt-4 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-text-secondary">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
            {fieldErrors.email && (
              <p className="mt-1 text-xs text-danger">{fieldErrors.email}</p>
            )}
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-text-secondary">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
            {fieldErrors.password && (
              <p className="mt-1 text-xs text-danger">{fieldErrors.password}</p>
            )}
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Signing in…" : "Sign in"}
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
