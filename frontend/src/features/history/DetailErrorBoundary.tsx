import { Component, type ErrorInfo, type ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  children: ReactNode;
}

/**
 * History reopens sessions written over many releases, so one older or
 * unexpectedly shaped record must never blank the whole page. If rendering a
 * detail fails, the header and navigation stay usable and this message shows.
 */
export class DetailErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Technical detail goes to the console only, never to the screen.
    console.error("History detail failed to render", error, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return (
        <Card>
          <CardContent className="space-y-1 py-8 text-center" role="alert">
            <p className="text-sm font-medium text-text-primary">We couldn't display the details of this activity.</p>
            <p className="text-sm text-text-muted">It is still saved. The summary above shows what was recorded.</p>
          </CardContent>
        </Card>
      );
    }
    return this.props.children;
  }
}
