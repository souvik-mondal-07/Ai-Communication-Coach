import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CtfSessionForm } from "@/features/cybersecurity/ctf/CtfSessionForm";
import { CtfSessionList } from "@/features/cybersecurity/ctf/CtfSessionList";
import type { CtfSessionSummary } from "@/features/cybersecurity/ctf/ctfTypes";
import * as ctfService from "@/services/ctfService";
import { getApiErrorMessage } from "@/utils/apiError";

export default function CTF() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<CtfSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    ctfService
      .getSessions()
      .then((result) => {
        if (!cancelled) setSessions(result.sessions);
      })
      .catch((err) => {
        if (!cancelled) setError(getApiErrorMessage(err, "Unable to load your challenge sessions."));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(payload: Parameters<typeof ctfService.createSession>[0]) {
    const result = await ctfService.createSession(payload);
    navigate(`/ctf/${result.session_id}`);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-xl font-semibold text-text-primary">
            CTF &amp; Lab Mentor
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            AI guidance for CTFs and lab challenges you're already working on — it never scans,
            attacks, or accesses anything itself.
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)} className="gap-1.5">
            <Plus size={15} />
            New Challenge
          </Button>
        )}
      </div>

      {showForm && (
        <Card>
          <CardContent className="py-5">
            <CtfSessionForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-text-primary">Previous Sessions</h2>
        {isLoading ? (
          <p className="py-10 text-center text-sm text-text-muted">Loading sessions…</p>
        ) : (
          <CtfSessionList sessions={sessions} />
        )}
      </div>
    </div>
  );
}
