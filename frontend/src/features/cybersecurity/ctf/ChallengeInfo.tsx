import { Card, CardContent } from "@/components/ui/card";
import {
  CATEGORY_LABELS,
  DIFFICULTY_LABELS,
  type CtfSessionDetail,
} from "@/features/cybersecurity/ctf/ctfTypes";

interface ChallengeInfoProps {
  session: CtfSessionDetail;
}

export function ChallengeInfo({ session }: ChallengeInfoProps) {
  return (
    <Card>
      <CardContent className="space-y-3 py-4">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">{session.title}</h2>
          <p className="mt-0.5 text-xs text-text-muted">
            {session.platform} · {CATEGORY_LABELS[session.category]} ·{" "}
            {DIFFICULTY_LABELS[session.difficulty]}
          </p>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
          {session.description}
        </p>
        {session.user_notes && (
          <div>
            <p className="mb-1 text-xs font-medium text-text-muted">What I tried</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
              {session.user_notes}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
