import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { useProfileStore } from "@/store/profileStore";

/** Loading / error placeholder shown until the profile has been fetched. */
export function ProfileLoadState() {
  const loadError = useProfileStore((s) => s.loadError);
  const loadProfile = useProfileStore((s) => s.loadProfile);

  if (loadError) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardContent className="space-y-3 py-8 text-center">
          <p role="alert" className="text-sm text-text-secondary">Unable to load your profile. Please try again.</p>
          <Button variant="secondary" onClick={() => void loadProfile()}>Retry</Button>
        </CardContent>
      </Card>
    );
  }
  return (
    <div role="status" className="mx-auto max-w-5xl space-y-4">
      <span className="sr-only">Loading your profile...</span>
      <Skeleton className="h-28 w-full rounded-[var(--radius-card)]" />
      <Skeleton className="h-64 w-full rounded-[var(--radius-card)]" />
    </div>
  );
}
