"use client";

import { useState } from "react";
import { DirectoryPage, NONE, formatDate } from "@/components/admin/directory-page";
import { FIELD_CLASS, SM, statusTone } from "@/components/admin/admin-ui";
import { StatusPill, actionClass } from "@/components/panel-kit";
import { cn } from "@/lib/utils";
import {
  listInstitutions,
  setInstitutionVerificationLevel,
  type AdminInstitution,
  type VerificationLevel,
} from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

const m = messages.adminInstitutions;
const LEVELS: VerificationLevel[] = ["T1", "T2", "T3", "T4"];

function LevelControl({
  inst,
  onChanged,
  onError,
}: {
  inst: AdminInstitution;
  onChanged: (msg: string) => void;
  onError: (err: unknown) => void;
}) {
  const [level, setLevel] = useState<string>(inst.verification_level);
  const [busy, setBusy] = useState(false);
  const selectId = `level-${inst.id}`;

  const save = async () => {
    setBusy(true);
    try {
      await setInstitutionVerificationLevel(inst.id, level as VerificationLevel);
      onChanged(m.levelUpdated);
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="flex items-center gap-1.5">
      <label htmlFor={selectId} className="sr-only">
        {`${m.levelLabel}: ${inst.name}`}
      </label>
      <select
        id={selectId}
        value={level}
        onChange={(e) => setLevel(e.target.value)}
        disabled={busy}
        className={cn(FIELD_CLASS, "h-8 w-auto px-2 text-xs")}
      >
        {LEVELS.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={save}
        disabled={busy || level === inst.verification_level}
        className={cn(actionClass.primary, SM)}
      >
        {m.saveLevel}
      </button>
    </span>
  );
}

export default function KurumlarPage() {
  return (
    <DirectoryPage<AdminInstitution>
      kind="institutions"
      m={m}
      fetchPage={listInstitutions}
      rowLabel={(i) => i.name}
      statusOptions={[]}
      extraActions={(inst, onChanged, onError) => (
        <LevelControl key={`${inst.id}-${inst.verification_level}`} inst={inst} onChanged={onChanged} onError={onError} />
      )}
      columns={[
        { header: m.headers.name, cell: (i) => <span className="font-medium">{i.name}</span> },
        { header: m.headers.domain, cell: (i) => i.domain || NONE },
        { header: m.headers.verificationLevel, cell: (i) => <span className="rounded-md border border-border bg-background px-1.5 py-0.5 font-mono text-xs">{i.verification_level}</span> },
        {
          header: m.headers.status,
          cell: (i) => (
            <StatusPill tone={statusTone(i.status)}>
              {m.statusLabels[i.status as keyof typeof m.statusLabels] ?? i.status}
            </StatusPill>
          ),
        },
        { header: m.headers.createdAt, cell: (i) => formatDate(i.created_at) },
      ]}
    />
  );
}
