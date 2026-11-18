import { Hourglass } from "lucide-react";
import type { NavItem } from "../components/Layout";
import { Card, PageHeader } from "../components/ui";

/** Empty state for views whose evidence does not exist yet (FR-10: no placeholder numbers). */
export default function PlannedView({ item }: { item: NavItem }) {
  return (
    <>
      <PageHeader title={item.label} requirement={item.requirement}>
        {item.summary}
      </PageHeader>
      <Card>
        <div className="flex flex-col items-center gap-2 py-10 text-center">
          <Hourglass className="size-8 text-slate-400" aria-hidden />
          <p className="font-medium">No data yet</p>
          <p className="max-w-md text-sm text-slate-600">
            This view is populated by roadmap {item.phase.toLowerCase()}. It will show real results once that
            component produces them.
          </p>
        </div>
      </Card>
    </>
  );
}
