import { Menu, UserCircle2 } from "lucide-react";
import { useAppStore } from "@/store/appStore";

interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  const openMobileSidebar = useAppStore((s) => s.openMobileSidebar);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-base/95 px-4 backdrop-blur md:px-8">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={openMobileSidebar}
          className="rounded-[var(--radius-panel)] p-1.5 text-text-secondary hover:bg-surface-raised hover:text-text-primary md:hidden"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-base font-semibold text-text-primary">{title}</h1>
      </div>

      <div className="flex items-center gap-3 text-text-secondary">
        <UserCircle2 size={26} strokeWidth={1.5} />
      </div>
    </header>
  );
}
