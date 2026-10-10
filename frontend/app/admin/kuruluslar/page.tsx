"use client";

import { useState } from "react";
import { DirectoryPage, NONE, formatDate } from "@/components/admin/directory-page";
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
        <div className="flex flex-col">
          <label htmlFor="organizations-level" className="text-sm font-medium text-slate-700">
            {m.filterLevel}
          </label>
          <select
            id="organizations-level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            <option value="">{m.filterAll}</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
      }
      columns={[
        { header: m.headers.name, cell: (o) => o.name },
        { header: m.headers.legalId, cell: (o) => o.legal_id || NONE },
        { header: m.headers.domain, cell: (o) => o.domain || NONE },
        { header: m.headers.verificationLevel, cell: (o) => o.verification_level },
        { header: m.headers.verifiedAt, cell: (o) => (o.verified_at ? formatDate(o.verified_at) : m.notVerified) },
        { header: m.headers.status, cell: (o) => m.statusLabels[o.status as keyof typeof m.statusLabels] ?? o.status },
        { header: m.headers.createdAt, cell: (o) => formatDate(o.created_at) },
      ]}
    />
  );
}
