"use client";

import { EmptyState, PanelIcon, PanelSection, StatusPill } from "@/components/panel-kit";
import messages from "@/messages/tr.json";
import { aggregatePartners, fill, type PanelEngagement } from "./panel-data";

const t = messages.kurulusPanel;
const tp = t.partners;

/** Universities the organization works with, computed from the "all" list. */
export function PartnersSection({ items }: { items: PanelEngagement[] }) {
  const rows = aggregatePartners(items);
  const universities = rows.filter((row) => row.institutionId !== null);

  return (
    <PanelSection
      id="kurulus-is-birlikleri"
      icon="landmark"
      title={tp.title}
      hint={tp.hint}
      count={universities.length}
      flush={rows.length > 0}
    >
      {rows.length === 0 ? (
        <EmptyState icon="landmark" title={tp.emptyTitle} hint={tp.emptyHint} />
      ) : (
        <ul className="divide-y divide-border">
          {rows.map((row) => (
            <li key={row.institutionId ?? "__individual"} className="flex items-center gap-3 px-5 py-3 text-sm">
              <PanelIcon
                name={row.institutionId === null ? "users" : "landmark"}
                className="h-4 w-4 shrink-0 text-muted-foreground"
              />
              <span className="min-w-0 flex-1 truncate font-medium text-foreground">
                {row.institutionId === null ? tp.individual : (row.name ?? t.inbox.universityUnknown)}
              </span>
              <span className="font-mono text-xs text-muted-foreground">{fill(tp.people, { count: row.people })}</span>
              {row.sealed > 0 ? <StatusPill tone="success">{fill(tp.sealed, { count: row.sealed })}</StatusPill> : null}
            </li>
          ))}
        </ul>
      )}
    </PanelSection>
  );
}
