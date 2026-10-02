import { Check, Circle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types/profile";

export function CompletionCard({ user }: { user: UserProfile }) {
  const { percentage, items } = user.completion;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Complete your profile</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          {percentage === 100
            ? "All done — your mentor has what it needs to personalize your practice."
            : "The more your mentor knows, the better it can personalize your practice."}
        </p>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.key} className="flex items-center gap-2.5 text-sm">
              {item.done ? (
                <Check size={16} className="shrink-0 text-signal" aria-label="Completed" />
              ) : (
                <Circle size={16} className="shrink-0 text-text-muted" aria-label="Not completed" />
              )}
              <span className={cn(item.done ? "text-text-primary" : "text-text-secondary")}>{item.label}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
