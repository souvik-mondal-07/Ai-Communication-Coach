import { Settings as SettingsIcon } from "lucide-react";
import { PlaceholderPage } from "@/components/common/PlaceholderPage";

export default function Settings() {
  return (
    <PlaceholderPage
      icon={SettingsIcon}
      title="Settings"
      description="Configure app preferences, notification settings, and connected AI providers."
    />
  );
}
