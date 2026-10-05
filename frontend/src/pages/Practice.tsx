import { useNavigate } from "react-router-dom";
import { PracticeLauncher } from "@/features/cybersecurity/practice/PracticeLauncher";

export default function Practice() {
  const navigate = useNavigate();
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">Cybersecurity Practice</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Scenario, troubleshooting and topic practice that adapts to your profile and results.
        </p>
      </div>
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
