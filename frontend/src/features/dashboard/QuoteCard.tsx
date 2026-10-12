import { ShieldCheck } from "lucide-react";
import { MountainArt } from "@/features/dashboard/DashboardArt";
import { reveal } from "@/lib/motion";

export function QuoteCard() {
  const r = reveal(1);
  return (
    <figure className={`${r.className} relative flex min-h-44 flex-col justify-between overflow-hidden rounded-[var(--radius-card)] border border-[#6d5bff]/50 bg-quote p-6 text-white shadow-[0_18px_40px_-20px_rgb(91_61_240/0.8)]`} style={r.style}>
      <MountainArt className="pointer-events-none absolute -bottom-1 right-0 h-32 w-auto" />
      <div className="relative">
        <span aria-hidden="true" className="block font-display text-5xl font-bold leading-none text-white/80">“</span>
        <blockquote className="-mt-1 font-display text-xl font-semibold leading-snug">Progress, not perfection, is the goal.</blockquote>
      </div>
      <ShieldCheck size={26} className="relative mt-4 text-white/80" aria-hidden="true" />
    </figure>
  );
}
