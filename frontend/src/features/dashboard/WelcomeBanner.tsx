import { Eye, Hammer, Lightbulb } from "lucide-react";
import { HeroArt } from "@/features/dashboard/DashboardArt";
import { firstName, greetingFor, plural } from "@/features/dashboard/dashboardUtils";
import { reveal } from "@/lib/motion";
import type { Resource } from "@/features/dashboard/useAsyncResource";
import type { ProgressOverview } from "@/types/progress";

const CHIPS = [
  { label: "Think Secure", icon: Eye },
  { label: "Build Skills", icon: Hammer },
  { label: "Create Opportunities", icon: Lightbulb },
];

function progressLine(overview: Resource<ProgressOverview>, completed: number): string {
  if (overview.status !== "ready") return "Your learning progress, practice plan and next steps in one place.";
  return overview.data.has_activity
    ? `You've completed ${plural(completed, "session")} so far. Keep the momentum going.`
    : "Complete your first practice session and this page will start tracking your skills and progress.";
}

/** Welcome hero. Greeting follows the visitor's local time; chips are labels, not controls. */
export function WelcomeBanner({ name, overview, completed }: { name: string | undefined; overview: Resource<ProgressOverview>; completed: number }) {
  const greeting = greetingFor(new Date().getHours());
  const [lead, ...rest] = greeting.split(" ");
  const r = reveal(0);
  return (
    <section aria-labelledby="welcome-heading" className={`${r.className} relative overflow-hidden rounded-[var(--radius-card)] border border-[#1d2f78]/70 bg-hero px-6 py-6 text-white shadow-card md:px-8 md:py-7`} style={r.style}>
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0 opacity-60" />
      <HeroArt className="animate-float-slow pointer-events-none absolute -right-6 top-1/2 hidden h-[115%] -translate-y-1/2 md:block lg:right-2" />
      <div className="relative max-w-xl">
        <h1 id="welcome-heading" className="font-display text-[1.75rem] font-semibold leading-tight md:text-[2rem]">
          {lead} <span className="text-[#5b8dff]">{rest.length ? `${rest.join(" ")}, ` : ", "}</span>
          <span className="bg-gradient-to-r from-[#7c8cff] to-[#b46bff] bg-clip-text text-transparent">{firstName(name)}</span>
          <span aria-hidden="true"> 👋</span>
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-white/85">{progressLine(overview, completed)}</p>
        <p className="text-[15px] leading-relaxed text-white/85">Keep learning, stay curious, and build the skills for your future.</p>
        <ul className="mt-5 flex flex-wrap gap-2.5" aria-label="Principles">
          {CHIPS.map(({ label, icon: Icon }) => (
            <li key={label} className="flex items-center gap-2 rounded-full border border-[#3b6bff]/60 bg-[#0c1b57]/70 px-3.5 py-1.5 text-xs text-white/90">
              <Icon size={13} className="text-[#6ea8ff]" aria-hidden="true" />
              {label}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
