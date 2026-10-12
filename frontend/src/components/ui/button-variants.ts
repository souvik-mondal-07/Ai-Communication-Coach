import { cva } from "class-variance-authority";

/** Exported so links can look like buttons without nesting a <button> inside an <a>. */
export const buttonVariants = cva(
  [
    "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-panel)] text-sm font-medium",
    "transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-out",
    "active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100",
  ],
  {
    variants: {
      variant: {
        primary:
          "bg-signal text-on-signal shadow-[inset_0_1px_0_0_rgb(255_255_255/0.22)] hover:bg-signal/90 hover:shadow-glow",
        secondary:
          "border border-border-strong bg-surface-raised text-text-primary hover:border-border-input hover:bg-surface-raised/70",
        ghost: "text-text-secondary hover:bg-surface-raised hover:text-text-primary",
        danger: "bg-danger text-on-danger hover:bg-danger/90",
      },
      size: {
        sm: "h-8 px-3",
        md: "h-9 px-4",
        lg: "h-11 px-6 text-base",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);
