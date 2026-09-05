import { History as HistoryIcon } from "lucide-react";
import { PlaceholderPage } from "@/components/common/PlaceholderPage";

export default function History() {
  return (
    <PlaceholderPage
      icon={HistoryIcon}
      title="History"
      description="A full log of past sessions — mentor conversations, interviews, and practice attempts."
    />
  );
}
