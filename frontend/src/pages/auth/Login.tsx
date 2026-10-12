import { type FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthShell, FormBanner } from "@/components/common/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
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
    <AuthShell
      title="Sign in"
      subtitle="Welcome back. Enter your details to continue."
      footer={
        <>
          No account?{" "}
          <Link to="/register" className="text-link hover:underline">
            Register
          </Link>
        </>
      }
    >
      {location.state?.justRegistered && <FormBanner tone="success">Account created — sign in to continue.</FormBanner>}
      {error && <FormBanner tone="error">{error}</FormBanner>}

      <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
        <Field id="email" label="Email" error={fieldErrors.email}>
          {(a11y) => (
            <Input {...a11y} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          )}
        </Field>
        <Field id="password" label="Password" error={fieldErrors.password}>
          {(a11y) => (
            <Input {...a11y} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          )}
        </Field>
        <Button type="submit" loading={isSubmitting} className="w-full">
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}
