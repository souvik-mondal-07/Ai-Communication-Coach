import { cn } from "@/lib/utils";

interface Props {
  code: string;
  label?: string;
  className?: string;
}

/** Read-only, monospaced code. Scrolls sideways inside its own box (keyboard-focusable) so the page never scrolls sideways. */
export function CodeBlock({ code, label = "Code", className }: Props) {
  return (
    <pre
      tabIndex={0}
      aria-label={label}
      className={cn("max-w-full overflow-x-auto rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3 font-mono text-xs leading-relaxed text-text-primary", className)}
    >
      <code>{code}</code>
    </pre>
  );
}
