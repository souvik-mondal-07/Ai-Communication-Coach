import { useMemo } from "react";
import { Radar as RadarIcon } from "lucide-react";
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { buildSkillAxes, type SkillAxis } from "@/features/dashboard/dashboardUtils";
import type { Resource } from "@/features/dashboard/useAsyncResource";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { reveal } from "@/lib/motion";
import type { ProgressOverview } from "@/types/progress";

interface TickProps {
  x?: number | string;
  y?: number | string;
  textAnchor?: "start" | "middle" | "end" | "inherit";
  payload?: { value: string };
}

export function SkillsRadarCard({ overview, onRetry }: { overview: Resource<ProgressOverview>; onRetry: () => void }) {
  const reduce = usePrefersReducedMotion();
  const axes = useMemo(() => (overview.status === "ready" ? buildSkillAxes(overview.data) : []), [overview]);
  const measured = axes.filter((a) => a.value !== null).length;
  const byLabel = useMemo(() => Object.fromEntries(axes.map((a) => [a.label, a])) as Record<string, SkillAxis>, [axes]);
  const data = axes.map((a) => ({ label: a.label, value: a.value ?? 0 }));
  const r = reveal(8);
  const summary = axes.map((a) => `${a.label} ${a.value == null ? "no data" : `${a.value}%`}`).join(", ");

  function renderTick({ x = 0, y = 0, textAnchor = "middle", payload }: TickProps) {
    const a = payload ? byLabel[payload.value] : undefined;
    return (
      <text x={Number(x)} y={Number(y)} textAnchor={textAnchor} fontSize={11} fill="var(--color-text-secondary)">
        <tspan x={Number(x)} dy="0">{payload?.value}</tspan>
        <tspan x={Number(x)} dy="14" fill="var(--color-text-primary)" fontWeight={500}>{a?.value == null ? "—" : `${a.value}%`}</tspan>
      </text>
    );
  }

  return (
    <section aria-labelledby="skills-title" className={`${r.className} rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card`} style={r.style}>
      <h2 id="skills-title" className="font-display text-[15px] font-semibold text-text-primary">Skills Overview</h2>
      <div className="mt-2">
        {overview.status === "loading" && <div role="status" aria-label="Loading skills"><Skeleton className="h-52 w-full rounded-[var(--radius-panel)]" /></div>}
        {overview.status === "error" && <ErrorState message={overview.message} onRetry={onRetry} />}
        {overview.status === "ready" && measured < 3 && (
          <EmptyState icon={RadarIcon} title="Not enough results yet" description="Complete practice in at least three areas (security, communication, interview, pressure) to see your skill shape." />
        )}
        {overview.status === "ready" && measured >= 3 && (
          <>
            <div className="h-52" role="img" aria-label={`Skills overview. ${summary}.`}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={data} outerRadius="62%" margin={{ top: 12, right: 32, bottom: 12, left: 32 }}>
                  <defs>
                    <linearGradient id="radar-fill" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#4d86ff" stopOpacity={0.65} />
                      <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.55} />
                    </linearGradient>
                  </defs>
                  <PolarGrid stroke="var(--color-border-strong)" />
                  <PolarAngleAxis dataKey="label" tick={renderTick} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar dataKey="value" stroke="#7da2ff" strokeWidth={2} fill="url(#radar-fill)" dot={{ r: 3, fill: "#c7d6ff", strokeWidth: 0 }} isAnimationActive={!reduce} animationDuration={900} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            {measured < axes.length && <p className="text-center text-xs text-text-muted">Axes marked “—” have no results yet.</p>}
          </>
        )}
      </div>
    </section>
  );
}
