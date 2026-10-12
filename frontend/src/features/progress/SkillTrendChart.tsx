import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import type { TrendSeries } from "@/types/progress";
import { chartColors, chartLabelStyle, chartTooltipStyle } from "@/utils/chartTheme";

const TREND_LABEL: Record<TrendSeries["trend"], string> = {
  improving: "Improving",
  stable: "Stable",
  declining: "Declining",
  insufficient_data: "Not enough data yet",
};

const TREND_COLOR: Record<TrendSeries["trend"], string> = {
  improving: chartColors.success,
  stable: chartColors.warn,
  declining: chartColors.danger,
  insufficient_data: chartColors.muted,
};

export function SkillTrendChart({ title, series }: { title: string; series: TrendSeries }) {
  const color = TREND_COLOR[series.trend];
  const reduceMotion = usePrefersReducedMotion();

  if (series.trend === "insufficient_data" || series.points.length < 2) {
    return (
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-xs font-medium text-text-secondary">{title}</h4>
          <span className="text-[11px] text-text-muted">{TREND_LABEL[series.trend]}</span>
        </div>
        <p className="text-sm text-text-muted">
          Not enough data yet. Complete a few more sessions to see your {title.toLowerCase()} trend.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-medium text-text-secondary">{title}</h4>
        <span className="text-[11px] font-medium" style={{ color }}>
          {TREND_LABEL[series.trend]}
        </span>
      </div>
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series.points}>
            <defs>
              <linearGradient id={`trend-${title}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="period" stroke={chartColors.muted} tickLine={false} axisLine={false} fontSize={11} />
            <YAxis hide domain={[0, 100]} />
            <Tooltip
              contentStyle={chartTooltipStyle}
              labelStyle={chartLabelStyle}
            />
            <Area
              type="monotone"
              dataKey="average_score"
              stroke={color}
              strokeWidth={2}
              fill={`url(#trend-${title})`}
              isAnimationActive={!reduceMotion}
              animationDuration={700}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
