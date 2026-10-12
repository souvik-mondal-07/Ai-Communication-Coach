import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthShell, FormBanner } from "@/components/common/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
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
    <AuthShell
      title="Create an account"
      subtitle="Start tracking your progress across cybersecurity, communication, and interviews."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="text-link hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      {error && <FormBanner tone="error">{error}</FormBanner>}

      <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
        <Field id="name" label="Name" error={fieldErrors.name}>
          {(a11y) => <Input {...a11y} type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />}
        </Field>
        <Field id="email" label="Email" error={fieldErrors.email}>
          {(a11y) => (
            <Input {...a11y} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          )}
        </Field>
        <Field id="password" label="Password" error={fieldErrors.password} hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}>
          {(a11y) => (
            <Input {...a11y} type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          )}
        </Field>
        <Button type="submit" loading={isSubmitting} className="w-full">
          {isSubmitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
}
