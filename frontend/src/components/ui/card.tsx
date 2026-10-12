import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva("rounded-[var(--radius-card)] border", {
  variants: {
    variant: {
      default: "border-border bg-surface shadow-card",
      raised: "border-border bg-surface-raised",
      glass: "glass border-border-strong/70 shadow-card",
    },
    /** Only for cards that are themselves a link/button. Static cards must not look clickable. */
    interactive: {
      true: "transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-px hover:border-border-input hover:shadow-pop focus-within:border-border-input",
      false: "",
    },
  },
  defaultVariants: { variant: "default", interactive: false },
});

export interface CardProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

export function Card({ className, variant, interactive, ...props }: CardProps) {
  return <div className={cn(cardVariants({ variant, interactive }), className)} {...props} />;
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("border-b border-border px-5 py-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-sm font-semibold text-text-primary", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("mt-1 text-xs text-text-muted", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("border-t border-border px-5 py-3", className)} {...props} />;
}
