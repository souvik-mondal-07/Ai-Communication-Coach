import * as React from "react";
import { cn } from "@/lib/utils";

/** One source of truth for every text control. Also re-exported by features/profile/formStyles.ts. */
export const fieldClass =
  "w-full rounded-[var(--radius-panel)] border border-border-input bg-base/60 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted " +
  "transition-[border-color,box-shadow] duration-150 focus-visible:border-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/30 " +
  "disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-danger aria-[invalid=true]:focus-visible:ring-danger/30";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input ref={ref} className={cn(fieldClass, className)} {...props} />
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => <textarea ref={ref} className={cn(fieldClass, "resize-y", className)} {...props} />
);
Textarea.displayName = "Textarea";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => <select ref={ref} className={cn(fieldClass, "pr-8", className)} {...props} />
);
Select.displayName = "Select";

interface FieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: (a11y: { id: string; "aria-invalid": boolean | undefined; "aria-describedby": string | undefined }) => React.ReactNode;
}

/** Label + control + hint/error wired together with aria-describedby and aria-invalid. */
export function Field({ id, label, error, hint, children }: FieldProps) {
  const messageId = error || hint ? `${id}-msg` : undefined;
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-text-primary">
        {label}
      </label>
      {children({ id, "aria-invalid": error ? true : undefined, "aria-describedby": messageId })}
      {error ? (
        <p id={messageId} className="mt-1.5 text-xs text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={messageId} className="mt-1.5 text-xs text-text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
