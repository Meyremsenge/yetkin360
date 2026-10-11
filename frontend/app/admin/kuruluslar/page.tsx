"use client";

import { useState } from "react";
import { DirectoryPage, NONE, formatDate } from "@/components/admin/directory-page";
import { FIELD_CLASS, Field, statusTone } from "@/components/admin/admin-ui";
import { StatusPill } from "@/components/panel-kit";
import { listOrganizations, type AdminOrganization } from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

const m = messages.adminOrganizations;
const LEVELS = ["T1", "T2", "T3", "T4"];

export default function KuruluslarPage() {
  const [level, setLevel] = useState("");

  return (
    <DirectoryPage<AdminOrganization>
      kind="organizations"
      m={m}
      fetchPage={listOrganizations}
      rowLabel={(o) => o.name}
      statusOptions={["ACTIVE", "SUSPENDED"]}
      extraParams={{ verification_level: level || undefined }}
      extraFilters={
        <Field label={m.filterLevel} htmlFor="organizations-level">
          <select
            id="organizations-level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className={FIELD_CLASS}
          >
            <option value="">{m.filterAll}</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </Field>
      }
      columns={[
        { header: m.headers.name, cell: (o) => <span className="font-medium">{o.name}</span> },
        { header: m.headers.legalId, cell: (o) => o.legal_id || NONE },
        { header: m.headers.domain, cell: (o) => o.domain || NONE },
        { header: m.headers.verificationLevel, cell: (o) => <span className="rounded-md border border-border bg-background px-1.5 py-0.5 font-mono text-xs">{o.verification_level}</span> },
        { header: m.headers.verifiedAt, cell: (o) => (o.verified_at ? formatDate(o.verified_at) : m.notVerified) },
        {
          header: m.headers.status,
          cell: (o) => (
            <StatusPill tone={statusTone(o.status)}>
              {m.statusLabels[o.status as keyof typeof m.statusLabels] ?? o.status}
            </StatusPill>
          ),
        },
        { header: m.headers.createdAt, cell: (o) => formatDate(o.created_at) },
      ]}
    />
  );
}
