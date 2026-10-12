import { useNavigate } from "react-router-dom";
import { PracticeLauncher } from "@/features/cybersecurity/practice/PracticeLauncher";
import { PageHeader } from "@/components/ui/page-header";

export default function Practice() {
  const navigate = useNavigate();
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title="Cybersecurity Practice" description="Scenario, troubleshooting and topic practice that adapts to your profile and results." />
      <PracticeLauncher />
      <p className="text-center text-xs text-text-muted">
        Want to study first?{" "}
        <button type="button" onClick={() => navigate("/cybersecurity")} className="text-link hover:underline">
          Browse topics
        </button>
      </p>
    </div>
  );
}
