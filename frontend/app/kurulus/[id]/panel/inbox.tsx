"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ActionLink, CopyButton, EmptyState, PanelSection, StatusPill, TimeAgo, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { transitionEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import type { OrgMember } from "@/lib/api/organizations";
import { STATUS_TONE } from "@/lib/ui/engagement-chain";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { fill, groupInbox, isAssignedTo, rowAction, type InboxGroup, type PanelEngagement } from "./panel-data";

const t = messages.kurulusPanel;
const ti = t.inbox;
const c = messages.calismalar;

/** Rows per group in the panel; the full list lives at /calismalar (#60 view). */
export const INBOX_ROWS_PER_GROUP = 8;

type Tab = "mine" | "all";

export function Inbox({
  organizationId,
  items,
  members,
  isAdmin,
  userId,
  startLink,
  onChanged,
}: {
  organizationId: string;
  items: PanelEngagement[];
  members: OrgMember[];
  isAdmin: boolean;
  userId: string | undefined;
  startLink: () => string;
  onChanged: () => void;
}) {
  const mine = items.filter((item) => isAssignedTo(item, userId));
  // Nothing assigned to me → open on "all".
  const [tab, setTab] = useState<Tab>(() => (mine.length > 0 ? "mine" : "all"));
  const [showDone, setShowDone] = useState(false);
  const [announcement, setAnnouncement] = useState<{ tone: "error" | "info"; text: string } | null>(null);

  const visible = tab === "mine" ? mine : items;
  const groups = groupInbox(visible, organizationId, isAdmin);
  const shown = groups.action.length + groups.ongoing.length + groups.done.length;
  const membersById = new Map(members.map((member) => [member.user_id, member]));

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "mine", label: ti.tabMine, count: mine.length },
    { id: "all", label: ti.tabAll, count: items.length },
  ];

  return (
    <PanelSection
      id="kurulus-calismalar"
      icon="inbox"
      title={ti.title}
      hint={ti.hint}
      count={groups.action.length}
      actions={
        <ActionLink href="/calismalar" variant="neutral" className="h-8 px-3">
          {ti.seeAll}
        </ActionLink>
      }
      flush
    >
      <div role="tablist" aria-label={ti.tabsLabel} className="flex gap-1 border-b border-border px-5">
        {tabs.map((entry) => (
          <button
            key={entry.id}
            type="button"
            role="tab"
            id={`inbox-tab-${entry.id}`}
            aria-selected={tab === entry.id}
            aria-controls="inbox-panel"
            onClick={() => setTab(entry.id)}
            className={cn(
              "-mb-px h-10 border-b-2 px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
              tab === entry.id
                ? "border-success text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {entry.label} <span className="font-mono text-xs text-muted-foreground">{entry.count}</span>
          </button>
        ))}
      </div>

      <div aria-live="polite" className="empty:hidden">
        {announcement ? (
          <Alert variant={announcement.tone === "error" ? "error" : "info"} className="mx-5 mt-4 text-sm">
            {announcement.text}
          </Alert>
        ) : null}
      </div>

      <div id="inbox-panel" role="tabpanel" aria-labelledby={`inbox-tab-${tab}`}>
        {shown === 0 ? (
          tab === "mine" ? (
            <EmptyState icon="inbox" title={ti.mineEmptyTitle} hint={ti.mineEmptyHint} />
          ) : (
            <EmptyState
              icon="link"
              title={ti.emptyTitle}
              hint={ti.emptyHint}
              action={<CopyButton value={startLink} label={t.startLinkButton} variant="neutral" />}
            />
          )
        ) : (
          <>
            <InboxGroupList
              group="action"
              title={ti.groupAction}
              rows={groups.action}
              {...{ organizationId, isAdmin, membersById, onChanged, setAnnouncement }}
            />
            <InboxGroupList
              group="ongoing"
              title={ti.groupOngoing}
              rows={groups.ongoing}
              {...{ organizationId, isAdmin, membersById, onChanged, setAnnouncement }}
            />
            {groups.done.length > 0 ? (
              <div className="border-t border-border px-5 py-3">
                <button
                  type="button"
                  aria-expanded={showDone}
                  aria-controls="inbox-done"
                  onClick={() => setShowDone((open) => !open)}
                  className={cn(actionClass.neutral, "h-8 px-3 text-xs")}
                >
                  {showDone ? ti.hideDone : fill(ti.showDone, { count: groups.done.length })}
                </button>
              </div>
            ) : null}
            {showDone ? (
              <div id="inbox-done">
                <InboxGroupList
                  group="done"
                  title={ti.groupDone}
                  rows={groups.done}
                  {...{ organizationId, isAdmin, membersById, onChanged, setAnnouncement }}
                />
              </div>
            ) : null}
          </>
        )}
      </div>
    </PanelSection>
  );
}

type Announce = (value: { tone: "error" | "info"; text: string } | null) => void;

function InboxGroupList({
  group,
  title,
  rows,
  organizationId,
  isAdmin,
  membersById,
  onChanged,
  setAnnouncement,
}: {
  group: InboxGroup;
  title: string;
  rows: PanelEngagement[];
  organizationId: string;
  isAdmin: boolean;
  membersById: Map<string, OrgMember>;
  onChanged: () => void;
  setAnnouncement: Announce;
}) {
  if (rows.length === 0 && group !== "action") return null;
  const headingId = `inbox-group-${group}`;
  return (
    <section aria-labelledby={headingId} className="border-t border-border first:border-t-0">
      <h4 id={headingId} className="flex items-center gap-2 px-5 pb-1 pt-4 text-xs font-medium text-muted-foreground">
        {title} <span className="font-mono">{rows.length}</span>
      </h4>
      {rows.length === 0 ? (
        <p className="px-5 pb-4 text-sm text-muted-foreground">{messages.kurulusPanel.inbox.groupEmpty}</p>
      ) : (
        <ul className="divide-y divide-border">
          {rows.slice(0, INBOX_ROWS_PER_GROUP).map((item) => (
            <InboxRow
              key={item.id}
              item={item}
              organizationId={organizationId}
              isAdmin={isAdmin}
              approver={item.supervisor_user_id ? membersById.get(item.supervisor_user_id) : undefined}
              onChanged={onChanged}
              setAnnouncement={setAnnouncement}
            />
          ))}
        </ul>
      )}
      {rows.length > INBOX_ROWS_PER_GROUP ? (
        <p className="px-5 pb-3 font-mono text-xs text-muted-foreground">
          {fill(ti.shownOf, { shown: INBOX_ROWS_PER_GROUP, total: rows.length })}
        </p>
      ) : null}
    </section>
  );
}

function InboxRow({
  item,
  organizationId,
  isAdmin,
  approver,
  onChanged,
  setAnnouncement,
}: {
  item: PanelEngagement;
  organizationId: string;
  isAdmin: boolean;
  approver: OrgMember | undefined;
  onChanged: () => void;
  setAnnouncement: Announce;
}) {
  const action = rowAction(item, organizationId, isAdmin);
  const tone = STATUS_TONE[item.status] ?? "default";
  const university = item.institution_id === null ? ti.individual : (item.institution_name ?? ti.universityUnknown);

  const startEvaluation = useMutation({
    mutationFn: () => transitionEngagement(item.id, { to_status: "PENDING_EVALUATION", version: item.version }),
    onSuccess: () => {
      setAnnouncement(null);
      onChanged();
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === "PRECONDITION_FAILED") {
        setAnnouncement({ tone: "error", text: ti.preconditionFailed });
      } else if (error instanceof ApiError && error.status === 409) {
        setAnnouncement({ tone: "info", text: ti.conflict });
        onChanged();
      } else {
        setAnnouncement({ tone: "error", text: ti.actionError });
      }
    },
  });

  return (
    <li
      className={cn(
        "flex flex-col gap-3 px-5 py-3.5 transition-colors hover:bg-background sm:flex-row sm:items-center",
        action === "evaluate" && "bg-warning/[0.04]"
      )}
    >
      <Link
        href={`/calismalar/${item.id}`}
        className="group min-w-0 flex-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
      >
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-foreground group-hover:underline group-hover:underline-offset-4">
            {item.talent_name}
          </span>
          <span className="text-muted-foreground">·</span>
          <span className="text-foreground">{item.title}</span>
          <StatusPill tone={tone}>{c.status[item.status]}</StatusPill>
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-muted-foreground">
          <span>{c.kind[item.kind]}</span>
          <span>{university}</span>
          {approver ? (
            <span className="rounded-full border border-border px-2 py-0.5 text-xs">
              {fill(ti.approverChip, {
                name: approver.unit ? `${approver.display_name} · ${approver.unit}` : approver.display_name,
              })}
            </span>
          ) : null}
          <TimeAgo iso={item.updated_at} />
        </span>
      </Link>
      <div className="flex shrink-0 flex-wrap items-center gap-2 empty:hidden">
        {action === "evaluate" ? (
          <ActionLink href={`/calismalar/${item.id}/degerlendirme`} variant="outline" className="h-8 px-3">
            {ti.evaluate}
          </ActionLink>
        ) : null}
        {action === "startEvaluation" ? (
          <button
            type="button"
            onClick={() => startEvaluation.mutate()}
            disabled={startEvaluation.isPending}
            className={cn(actionClass.neutral, "h-8 px-3")}
          >
            {startEvaluation.isPending ? ti.starting : ti.startEvaluation}
          </button>
        ) : null}
        {action === "seal" ? (
          <ActionLink href={`/calismalar/${item.id}#taniklik`} variant="primary" className="h-8 px-3">
            {ti.seal}
          </ActionLink>
        ) : null}
        {action === "awaitingUniversitySeal" ? (
          <StatusPill tone="default">{ti.awaitingUniversitySeal}</StatusPill>
        ) : null}
      </div>
    </li>
  );
}
