import { useCallback, useEffect, useState } from "react";
import { RefreshCw, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import * as progressService from "@/services/progressService";
import { getApiErrorMessage } from "@/utils/apiError";
import { CtfActivityOverview, SkillOverview } from "@/features/progress/SkillOverview";
import { SkillTrendChart } from "@/features/progress/SkillTrendChart";
import { StrengthsCard } from "@/features/progress/StrengthsCard";
import { WeaknessesCard } from "@/features/progress/WeaknessesCard";
import { RecommendationsCard } from "@/features/progress/RecommendationsCard";
import { RecentActivity } from "@/features/progress/RecentActivity";
import { PersonalProfileCard } from "@/features/progress/PersonalProfileCard";
import type {
  PersonalProfile,
  ProgressOverview as ProgressOverviewData,
  SkillsResponse,
  TrendsResponse,
} from "@/types/progress";

type Section<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function SectionBody<T>({
  section,
  render,
}: {
  section: Section<T>;
  render: (data: T) => React.ReactNode;
}) {
  if (section.status === "loading") {
    return <p className="text-sm text-text-muted">Loading…</p>;
  }
  if (section.status === "error") {
    return <p className="text-sm text-danger">{section.message}</p>;
  }
  return <>{render(section.data)}</>;
}

export default function ProgressPage() {
  const [overview, setOverview] = useState<Section<ProgressOverviewData>>({ status: "loading" });
  const [skills, setSkills] = useState<Section<SkillsResponse>>({ status: "loading" });
  const [trends, setTrends] = useState<Section<TrendsResponse>>({ status: "loading" });
  const [profile, setProfile] = useState<Section<PersonalProfile>>({ status: "loading" });
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [recalcError, setRecalcError] = useState<string | null>(null);

  const loadAll = useCallback(() => {
    setOverview({ status: "loading" });
    setSkills({ status: "loading" });
    setTrends({ status: "loading" });
    setProfile({ status: "loading" });

    // Each section fetches and fails independently -- a problem loading one
    // (e.g. trends) never blocks the rest of the dashboard from rendering.
    progressService
      .getOverview()
      .then((data) => setOverview({ status: "ready", data }))
      .catch((err) => setOverview({ status: "error", message: getApiErrorMessage(err, "Couldn't load overview.") }));

    progressService
      .getSkills()
      .then((data) => setSkills({ status: "ready", data }))
      .catch((err) => setSkills({ status: "error", message: getApiErrorMessage(err, "Couldn't load skills.") }));

    progressService
      .getTrends("30d")
      .then((data) => setTrends({ status: "ready", data }))
      .catch((err) => setTrends({ status: "error", message: getApiErrorMessage(err, "Couldn't load trends.") }));

    progressService
      .getProfile()
      .then((data) => setProfile({ status: "ready", data }))
      .catch((err) => setProfile({ status: "error", message: getApiErrorMessage(err, "Couldn't load profile.") }));
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function handleComplete(id: string) {
    setCompletingId(id);
    try {
      await progressService.completeRecommendation(id);
      const recs = await progressService.getRecommendations();
      setOverview((prev) => (prev.status === "ready" ? { status: "ready", data: { ...prev.data, recommendations: recs } } : prev));
    } catch {
      /* leave the list as-is; the button re-enables so the user can retry */
    } finally {
      setCompletingId(null);
    }
  }

  async function handleRecalculate() {
    setIsRecalculating(true);
    setRecalcError(null);
    try {
      await progressService.recalculateProgress();
      loadAll();
    } catch (err) {
      setRecalcError(getApiErrorMessage(err, "Couldn't recalculate progress. Please try again."));
    } finally {
      setIsRecalculating(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 font-display text-xl font-semibold text-text-primary">
            <TrendingUp size={20} className="text-signal" />
            Progress
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Track strengths, weaknesses, and improvement over time across every skill area.
          </p>
        </div>
        <div className="text-right">
          <Button variant="secondary" size="sm" onClick={handleRecalculate} disabled={isRecalculating}>
            <RefreshCw size={14} className={isRecalculating ? "animate-spin" : ""} />
            {isRecalculating ? "Recalculating…" : "Recalculate"}
          </Button>
          {recalcError && <p className="mt-1 text-xs text-danger">{recalcError}</p>}
        </div>
      </div>

      {overview.status === "ready" && !overview.data.has_activity && (
        <Card>
          <CardContent className="py-5 text-sm text-text-secondary">
            Start practicing to build your personal progress profile. Once you've completed a few sessions across
            cybersecurity practice, CTF, communication, interviews, or pressure training, your skills, strengths,
            weaknesses, and recommendations will show up here.
          </CardContent>
        </Card>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {overview.status === "ready" &&
          (
            [
              ["Practice", overview.data.session_counts.practice_sessions],
              ["CTF", overview.data.session_counts.ctf_sessions],
              ["Communication", overview.data.session_counts.communication_sessions],
              ["Interview", overview.data.session_counts.interview_sessions],
              ["Pressure", overview.data.session_counts.pressure_sessions],
            ] as const
          ).map(([label, counts]) => (
            <Card key={label}>
              <CardContent className="py-4">
                <p className="text-xs text-text-muted">{label} Sessions</p>
                <p className="mt-1 font-display text-lg font-semibold text-text-primary">
                  {counts.completed}
                  <span className="text-sm font-normal text-text-muted"> / {counts.total}</span>
                </p>
              </CardContent>
            </Card>
          ))}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <SectionCard title="Cybersecurity Skills">
          <SectionBody section={skills} render={(data) => <SkillOverview skills={data.cybersecurity_skills} />} />
        </SectionCard>

        <SectionCard title="Strengths">
          <SectionBody section={overview} render={(data) => <StrengthsCard strengths={data.strengths} />} />
        </SectionCard>

        <SectionCard title="Areas to Improve">
          <SectionBody section={overview} render={(data) => <WeaknessesCard weaknesses={data.weaknesses} />} />
        </SectionCard>
      </section>

      <SectionCard title="Trends (last 30 days)">
        <SectionBody
          section={trends}
          render={(data) => (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <SkillTrendChart title="Technical" series={data.dimensions.technical} />
              <SkillTrendChart title="Communication" series={data.dimensions.communication} />
              <SkillTrendChart title="Interview" series={data.dimensions.interview} />
              <SkillTrendChart title="Pressure" series={data.dimensions.pressure} />
            </div>
          )}
        />
      </SectionCard>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionCard title="Recommendations">
          <SectionBody
            section={overview}
            render={(data) => (
              <RecommendationsCard
                recommendations={data.recommendations}
                onComplete={handleComplete}
                completingId={completingId}
              />
            )}
          />
        </SectionCard>

        <SectionCard title="Recent Activity">
          <SectionBody section={overview} render={(data) => <RecentActivity activity={data.recent_activity} />} />
        </SectionCard>
      </section>

      {skills.status === "ready" && skills.data.ctf_activity.length > 0 && (
        <SectionCard title="CTF Activity">
          <CtfActivityOverview activity={skills.data.ctf_activity} />
        </SectionCard>
      )}

      <SectionCard title="Your Personal AI Profile">
        <SectionBody section={profile} render={(data) => <PersonalProfileCard profile={data} />} />
      </SectionCard>
    </div>
  );
}
