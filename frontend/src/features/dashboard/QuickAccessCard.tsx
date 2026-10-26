import { BookOpen, Database, Flag, MessageCircle, Mic } from "lucide-react";
import { Link } from "react-router-dom";
import { reveal } from "@/lib/motion";

const LINKS = [
  { label: "Start Learning", to: "/cybersecurity", icon: BookOpen },
  { label: "Open CTF Lab", to: "/ctf", icon: Flag },
  { label: "Chat with Mentor", to: "/mentor", icon: MessageCircle },
  { label: "Voice Practice", to: "/voice-conversation", icon: Mic },
  { label: "DBMS & SQL Lab", to: "/dbms-sql", icon: Database },
];

export function QuickAccessCard() {
  const r = reveal(4);
  return (
    <section aria-labelledby="quick-title" className={`${r.className} rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card`} style={r.style}>
      <h2 id="quick-title" className="font-display text-[15px] font-semibold text-text-primary">Quick Access</h2>
      <ul className="mt-3.5 space-y-2.5">
        {LINKS.map(({ label, to, icon: Icon }) => (
          <li key={to}>
            <Link to={to} className="group flex h-11 items-center gap-4 rounded-[var(--radius-panel)] border border-border-strong bg-surface-raised/50 px-4 text-sm font-medium text-text-primary transition-[border-color,background-color,transform] duration-200 hover:translate-x-0.5 hover:border-signal/60 hover:bg-surface-raised active:scale-[0.99]">
              <Icon size={20} strokeWidth={1.75} className="text-text-secondary transition-colors group-hover:text-signal" aria-hidden="true" />
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
