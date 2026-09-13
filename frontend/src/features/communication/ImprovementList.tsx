interface ImprovementListProps {
  title: string;
  items: string[];
  variant: "positive" | "negative" | "neutral";
}

const BULLET: Record<string, string> = {
  positive: "✓",
  negative: "•",
  neutral: "→",
};

const COLOR: Record<string, string> = {
  positive: "text-signal",
  negative: "text-warn",
  neutral: "text-text-secondary",
};

export function ImprovementList({ title, items, variant }: ImprovementListProps) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-text-muted">{title}</p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-1.5 text-sm text-text-secondary">
            <span className={`mt-0.5 ${COLOR[variant]}`}>{BULLET[variant]}</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
