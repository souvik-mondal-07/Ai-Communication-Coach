import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { getPersonalizationProfile } from "@/services/personalizationService";
import type { PersonalizationProfile } from "@/types/personalization";

const EMPTY_TEXT = "None identified yet";

function TopicList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{title}</p>
      <p className="mt-1 text-sm text-text-secondary">{items.length ? items.join(", ") : EMPTY_TEXT}</p>
    </div>
  );
}

/** Dashboard "Your Learning Focus" card -- every value comes from the personalization API. */
export function LearningFocusCard() {
  const [data, setData] = useState<PersonalizationProfile | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    getPersonalizationProfile()
      .then((profile) => active && setData(profile))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, []);

  const top = data?.recommended_activity ?? null;

  return (
    <Card>
      <CardContent className="space-y-4 py-5">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-signal" />
          <h3 className="text-sm font-semibold text-text-primary">Your Learning Focus</h3>
        </div>

        {failed && <p className="text-sm text-text-muted">Personalization is unavailable right now.</p>}
        {!data && !failed && <p className="text-sm text-text-muted">Loading your focus…</p>}

        {data && (
          <>
            {data.message && <p className="text-sm text-text-secondary">{data.message}</p>}

            {data.current_focus && top ? (
              <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised p-4">
                <p className="text-[11px] text-text-muted">
                  {data.current_focus.basis === "performance" ? "Based on your recent performance" : "Based on your profile"}
                </p>
                <p className="mt-1 font-display text-base font-semibold text-text-primary">{top.title}</p>
                {top.difficulty && (
                  <p className="mt-0.5 text-xs capitalize text-text-muted">{top.difficulty} difficulty</p>
                )}
                <p className="mt-3 text-[11px] font-medium text-text-muted">Recommended because</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-text-secondary">
                  {top.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                <Link
                  to={top.route}
                  className="mt-4 inline-flex rounded-[var(--radius-panel)] bg-signal px-3 py-1.5 text-xs font-medium text-canvas hover:opacity-90"
                >
                  {top.type === "practice" ? "Start practice" : "Open"}
                </Link>
              </div>
            ) : (
              !data.message && <p className="text-sm text-text-secondary">No recommendation right now.</p>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TopicList title="Strengths" items={data.strengths.map((s) => s.topic)} />
              <TopicList title="Weak areas" items={data.weaknesses.map((w) => w.topic)} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
