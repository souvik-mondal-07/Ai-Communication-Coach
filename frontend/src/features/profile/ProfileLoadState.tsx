import { Button } from "@/components/ui/button";
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
  return <p role="status" className="py-10 text-center text-sm text-text-muted">Loading your profile...</p>;
}
