import { type FormEvent, useState } from "react";
import { ShieldHalf } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { isValidEmail, isValidPassword, MIN_PASSWORD_LENGTH } from "@/utils/validators";

interface FieldErrors {
  name?: string;
  email?: string;
  password?: string;
}

export default function Register() {
  const { register, error, clearError } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate(): boolean {
    const errors: FieldErrors = {};
    if (!name.trim()) errors.name = "Name is required.";
    if (!email.trim()) errors.email = "Email is required.";
    else if (!isValidEmail(email)) errors.email = "Enter a valid email address.";
    if (!password) errors.password = "Password is required.";
    else if (!isValidPassword(password))
      errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await register(name, email, password);
      navigate("/login", { state: { justRegistered: true }, replace: true });
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

        <h1 className="text-lg font-semibold text-text-primary">Create an account</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Start tracking your progress across cybersecurity, communication, and interviews.
        </p>

        {error && (
          <p className="mt-4 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
          <div>
            <label htmlFor="name" className="mb-1.5 block text-xs font-medium text-text-secondary">
              Name
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
            {fieldErrors.name && <p className="mt-1 text-xs text-danger">{fieldErrors.name}</p>}
          </div>
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
            {fieldErrors.email && <p className="mt-1 text-xs text-danger">{fieldErrors.email}</p>}
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-text-secondary">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
            {fieldErrors.password ? (
              <p className="mt-1 text-xs text-danger">{fieldErrors.password}</p>
            ) : (
              <p className="mt-1 text-xs text-text-muted">
                At least {MIN_PASSWORD_LENGTH} characters.
              </p>
            )}
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-text-secondary">
          Already have an account?{" "}
          <Link to="/login" className="text-link hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
