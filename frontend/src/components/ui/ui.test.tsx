import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Badge } from "./badge";
import { Button } from "./button";
import { EmptyState, ErrorState } from "./empty-state";
import { Field, Input } from "./input";
import { PageHeader } from "./page-header";
import { ProgressBar, ProgressRing } from "./progress";
import { Skeleton } from "./skeleton";
import { StatCard } from "./stat-card";

describe("design-system primitives", () => {
  it("ProgressBar exposes accessible values, clamps, and keeps final width in markup", () => {
    const html = renderToStaticMarkup(<ProgressBar value={53.4} label="Daily practice progress" />);
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('aria-valuenow="53"');
    expect(html).toContain('aria-label="Daily practice progress"');
    expect(html).toContain("width:53%");
    expect(renderToStaticMarkup(<ProgressBar value={140} label="x" />)).toContain('aria-valuenow="100"');
    expect(renderToStaticMarkup(<ProgressBar value={-5} label="x" />)).toContain('aria-valuenow="0"');
  });

  it("ProgressRing is a labelled progressbar and renders its center content", () => {
    const html = renderToStaticMarkup(<ProgressRing value={25} label="Goal"><span>25%</span></ProgressRing>);
    expect(html).toContain('aria-valuenow="25"');
    expect(html).toContain("25%");
  });

  it("Button in loading state is disabled and marked busy", () => {
    const html = renderToStaticMarkup(<Button loading>Save</Button>);
    expect(html).toContain("disabled");
    expect(html).toContain('aria-busy="true"');
    expect(html).toContain("Save");
  });

  it("Field wires label, aria-invalid and aria-describedby to the error message", () => {
    const html = renderToStaticMarkup(
      <Field id="email" label="Email" error="Email is required.">
        {(a11y) => <Input {...a11y} />}
      </Field>
    );
    expect(html).toContain('for="email"');
    expect(html).toContain('aria-invalid="true"');
    expect(html).toContain('aria-describedby="email-msg"');
    expect(html).toContain('id="email-msg"');
    expect(html).toContain("Email is required.");
  });

  it("Field shows a hint when there is no error, and no aria-invalid", () => {
    const html = renderToStaticMarkup(
      <Field id="pw" label="Password" hint="At least 8 characters.">
        {(a11y) => <Input {...a11y} />}
      </Field>
    );
    expect(html).toContain("At least 8 characters.");
    expect(html).not.toContain("aria-invalid");
  });

  it("ErrorState is announced and offers Retry only when a handler exists", () => {
    expect(renderToStaticMarkup(<ErrorState message="Boom" onRetry={() => {}} />)).toContain("Retry");
    const without = renderToStaticMarkup(<ErrorState message="Boom" />);
    expect(without).toContain('role="alert"');
    expect(without).not.toContain("Retry");
  });

  it("EmptyState renders title, description and action", () => {
    const html = renderToStaticMarkup(<EmptyState title="Nothing yet" description="Do a thing." action={<a href="/x">Go</a>} />);
    expect(html).toContain("Nothing yet");
    expect(html).toContain("Do a thing.");
    expect(html).toContain('href="/x"');
  });

  it("PageHeader renders exactly one h1 with description and actions", () => {
    const html = renderToStaticMarkup(<PageHeader title="History" description="All sessions." actions={<button>Go</button>} />);
    expect(html.match(/<h1/g)).toHaveLength(1);
    expect(html).toContain("History");
    expect(html).toContain("All sessions.");
  });

  it("StatCard shows a labelled loading status, then the real value", () => {
    expect(renderToStaticMarkup(<StatCard label="Sessions" value={3} loading />)).toContain('aria-label="Loading Sessions"');
    const ready = renderToStaticMarkup(<StatCard label="Sessions" value={3} hint="of 5" />);
    expect(ready).toContain(">3<");
    expect(ready).toContain("of 5");
  });

  it("Skeleton is hidden from assistive tech and Badge renders its text", () => {
    expect(renderToStaticMarkup(<Skeleton />)).toContain('aria-hidden="true"');
    expect(renderToStaticMarkup(<Badge tone="success">Done</Badge>)).toContain("Done");
  });
});
