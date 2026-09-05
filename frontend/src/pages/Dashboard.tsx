import { Bot, ShieldHalf, Mic, TrendingUp, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  Tooltip,
} from "recharts";

const STATS = [
  { label: "Cybersecurity topics", value: "0 / 42", icon: ShieldHalf },
  { label: "Interview sessions", value: "0", icon: Mic },
  { label: "Mentor conversations", value: "0", icon: Bot },
  { label: "Weekly progress", value: "—", icon: TrendingUp },
];

const QUICK_LINKS = [
  { label: "Talk to your AI Mentor", to: "/mentor" },
  { label: "Start a cybersecurity lab", to: "/cybersecurity" },
  { label: "Practice an interview", to: "/interview" },
  { label: "Review your progress", to: "/progress" },
];

// Placeholder sample data — replaced once real progress tracking exists.
const SAMPLE_TREND = [
  { week: "W1", score: 0 },
  { week: "W2", score: 0 },
  { week: "W3", score: 0 },
  { week: "W4", score: 0 },
];

export default function Dashboard() {
  return (
    <div className="space-y-8">
      <section className="rounded-[var(--radius-panel)] border border-border bg-surface px-6 py-7 md:px-8 md:py-9">
        <p className="text-xs font-medium text-signal">Foundation build</p>
        <h2 className="mt-2 max-w-xl font-display text-2xl font-semibold text-text-primary md:text-3xl">
          Your mentor is set up and ready to grow.
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-text-secondary">
          This dashboard will track your cybersecurity progress, interview
          practice, and communication skills as those features come online.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="flex items-center justify-between py-5">
              <div>
                <p className="text-xs text-text-muted">{label}</p>
                <p className="mt-1.5 font-display text-xl font-semibold text-text-primary">
                  {value}
                </p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-panel)] bg-surface-raised text-text-secondary">
                <Icon size={16} />
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="py-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">
                Progress trend
              </h3>
              <span className="text-[11px] text-text-muted">Sample data</span>
            </div>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={SAMPLE_TREND}>
                  <defs>
                    <linearGradient id="trend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#35d0ba" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#35d0ba" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="week"
                    stroke="#6c7889"
                    tickLine={false}
                    axisLine={false}
                    fontSize={12}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#19212c",
                      border: "1px solid #2f3b4d",
                      borderRadius: 6,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="#35d0ba"
                    strokeWidth={2}
                    fill="url(#trend)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-5">
            <h3 className="mb-4 text-sm font-semibold text-text-primary">
              Quick links
            </h3>
            <ul className="space-y-1">
              {QUICK_LINKS.map(({ label, to }) => (
                <li key={to}>
                  <Link
                    to={to}
                    className="flex items-center justify-between rounded-[var(--radius-panel)] px-3 py-2.5 text-sm text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
                  >
                    {label}
                    <ArrowUpRight size={15} className="text-text-muted" />
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
