import { LearningProgressCard } from "@/features/dashboard/LearningProgressCard";
import { NextStepsCard } from "@/features/dashboard/NextStepsCard";
import { QuickAccessCard } from "@/features/dashboard/QuickAccessCard";
import { QuoteCard } from "@/features/dashboard/QuoteCard";
import { RecentActivityCard } from "@/features/dashboard/RecentActivityCard";
import { SkillsRadarCard } from "@/features/dashboard/SkillsRadarCard";
import { SummaryCards } from "@/features/dashboard/SummaryCards";
import { TodayPracticeCard } from "@/features/dashboard/TodayPracticeCard";
import { WelcomeBanner } from "@/features/dashboard/WelcomeBanner";
import { totalCompleted } from "@/features/dashboard/dashboardUtils";
import { useAsyncResource } from "@/features/dashboard/useAsyncResource";
import * as progressService from "@/services/progressService";
import { useAuthStore } from "@/store/authStore";

/**
 * Dashboard (Phase 21). Real data only: /progress/overview, /progress/trends and
 * /daily-practice. Each card owns its loading, empty and error state.
 *
 * Grid: banner | quote on the first row, then the main stack | the side stack.
 * Below `xl` everything becomes one column in reading order.
 */
export default function Dashboard() {
  const name = useAuthStore((s) => s.user?.name);
  const [overview, reloadOverview] = useAsyncResource(progressService.getOverview, "Couldn't load your progress.");
  const completed = overview.status === "ready" ? totalCompleted(overview.data.session_counts) : 0;

  return (
    <div className="mx-auto grid max-w-[1500px] grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <WelcomeBanner name={name} overview={overview} completed={completed} />
      <QuoteCard />

      <div className="min-w-0 space-y-5">
        <SummaryCards overview={overview} onRetry={reloadOverview} />
        <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[1.35fr_1fr]">
          <LearningProgressCard />
          <NextStepsCard overview={overview} onRetry={reloadOverview} />
        </div>
        <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[1.35fr_1fr]">
          <TodayPracticeCard />
          <SkillsRadarCard overview={overview} onRetry={reloadOverview} />
        </div>
      </div>

      <div className="min-w-0 space-y-5">
        <RecentActivityCard overview={overview} onRetry={reloadOverview} />
        <QuickAccessCard />
      </div>
    </div>
  );
}
