import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { formatPeriod } from "@/features/analytics/analyticsUtils";
import type { TrendSeries } from "@/types/progress";
import { chartColors, chartLabelStyle, chartTooltipStyle } from "@/utils/chartTheme";

/** Overall score trend from /progress/trends. The caller handles the not-enough-data case. */
export function OverallTrendChart({ series }: { series: TrendSeries }) {
  const reduce = usePrefersReducedMotion();
  return (
    <div className="h-52" role="img" aria-label="Overall score trend over the last 30 days">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series.points} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="overall-trend" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={chartColors.signal} stopOpacity={0.4} />
              <stop offset="100%" stopColor={chartColors.signal} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="period" tickFormatter={formatPeriod} stroke={chartColors.muted} tickLine={false} axisLine={false} fontSize={12} />
          <YAxis hide domain={[0, 100]} />
          <Tooltip labelFormatter={(l) => formatPeriod(String(l))} contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} cursor={{ stroke: chartColors.gridStrong }} />
          <Area
            type="monotone"
            dataKey="average_score"
            name="Average score"
            stroke={chartColors.signal}
            strokeWidth={2}
            fill="url(#overall-trend)"
            isAnimationActive={!reduce}
            animationDuration={800}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
