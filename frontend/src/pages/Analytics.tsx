import { useCallback, useEffect, useRef, useState } from "react";
import { BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import * as analyticsService from "@/services/analyticsService";
import { getApiErrorMessage } from "@/utils/apiError";
import { DataBanner, SectionCard } from "@/features/analytics/AnalyticsStates";
import { OverviewSection } from "@/features/analytics/OverviewSection";
import { TrendsSection } from "@/features/analytics/TrendsSection";
import { DomainsSection, ModesSection } from "@/features/analytics/BreakdownSection";
import { CommunicationSection, SpeakingSection, WeaknessList } from "@/features/analytics/CommunicationSection";
import { InsightsSection, PressureSection, StrengthsList } from "@/features/analytics/PressureAndInsights";
import { RANGE_OPTIONS, type LoadState } from "@/features/analytics/analyticsUtils";
import type {
  AnalyticsRange, CommunicationData, DomainsData, InsightsData, OverviewData, PressureData, SpeakingData, TrendsData,
} from "@/types/analytics";

/**
 * Analytics page. Each section loads independently (one failing endpoint never blanks
 * the page) and reloads when the range changes; stale responses are ignored.
 */
function useSection<T>(load: (range: AnalyticsRange) => Promise<T>, range: AnalyticsRange) {
  const [state, setState] = useState<LoadState<T>>({ status: "loading" });
  const token = useRef(0);
  const run = useCallback(() => {
    const mine = ++token.current;
    setState({ status: "loading" });
    load(range).then(
      (data) => { if (mine === token.current) setState({ status: "ready", data }); },
      (error) => { if (mine === token.current) setState({ status: "error", message: getApiErrorMessage(error, "Could not load this section.") }); },
    );
  }, [load, range]);
  useEffect(run, [run]);
  return [state, run] as const;
}

export default function AnalyticsPage() {
  const [range, setRange] = useState<AnalyticsRange>("30d");
  const [overview, reloadOverview] = useSection<OverviewData>(analyticsService.getOverview, range);
  const [trends, reloadTrends] = useSection<TrendsData>(analyticsService.getTrends, range);
  const [domains, reloadDomains] = useSection<DomainsData>(analyticsService.getDomains, range);
  const [communication, reloadCommunication] = useSection<CommunicationData>(analyticsService.getCommunication, range);
  const [speaking, reloadSpeaking] = useSection<SpeakingData>(analyticsService.getSpeaking, range);
  const [pressure, reloadPressure] = useSection<PressureData>(analyticsService.getPressure, range);
  const [insights, reloadInsights] = useSection<InsightsData>(analyticsService.getInsights, range);

  const meta = overview.status === "ready" ? overview.data : null;
  const noData = meta?.data.status === "none";

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-text-primary">
            <BarChart3 size={22} className="text-signal" aria-hidden="true" /> Analytics
          </h1>
          <p className="text-sm text-text-secondary">How you are improving as a cybersecurity candidate and communicator.</p>
        </div>
        <div role="group" aria-label="Date range" className="flex gap-1">
          {RANGE_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              aria-pressed={range === o.value}
              onClick={() => setRange(o.value)}
              className={`rounded-full border px-3 py-1 text-xs ${
                range === o.value ? "border-signal text-signal" : "border-border text-text-secondary hover:border-border-strong"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </header>

      <DataBanner meta={meta} />

      {overview.status === "error" ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-danger">
          {overview.message}
          <Button variant="secondary" size="sm" onClick={reloadOverview}>Retry</Button>
        </div>
      ) : overview.status === "loading" ? (
        <div role="status" aria-label="Loading overview" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <div key={i} aria-hidden="true" className="h-24 animate-pulse rounded-[var(--radius-panel)] bg-surface-raised" />)}
        </div>
      ) : (
        <OverviewSection data={overview.data} />
      )}

      {noData ? null : (
        <>
          <SectionCard title="Performance trends" state={trends} onRetry={reloadTrends} render={(d) => <TrendsSection data={d} />} />
          <div className="grid gap-4 lg:grid-cols-2">
            <SectionCard title="Interview performance" description="By interview type" state={domains} onRetry={reloadDomains} render={(d) => <ModesSection modes={d.modes} />} />
            <SectionCard title="Cybersecurity domains" state={domains} onRetry={reloadDomains} render={(d) => <DomainsSection data={d} />} />
          </div>
          <SectionCard title="Communication" state={communication} onRetry={reloadCommunication} render={(d) => <CommunicationSection data={d} />} />
          <div className="grid gap-4 lg:grid-cols-2">
            <SectionCard title="Speaking" state={speaking} onRetry={reloadSpeaking} render={(d) => <SpeakingSection data={d} />} />
            <SectionCard title="Pressure performance" state={pressure} onRetry={reloadPressure} render={(d) => <PressureSection data={d} />} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <SectionCard title="Strengths" state={insights} onRetry={reloadInsights} render={(d) => <StrengthsList items={d.strengths} />} />
            <SectionCard title="Recurring weaknesses" state={communication} onRetry={reloadCommunication} render={(d) => <WeaknessList items={d.weaknesses} />} />
          </div>
          <SectionCard title="Insights & next steps" state={insights} onRetry={reloadInsights} render={(d) => <InsightsSection data={d} />} />
        </>
      )}
    </div>
  );
}
