"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { listEngagements } from "@/lib/api/engagements";
import messages from "@/messages/tr.json";

const STATUS_BADGE_CLASS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  PENDING_APPROVAL: "bg-amber-100 text-amber-700",
  ACTIVE: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
  CANCELLED: "bg-red-100 text-red-700",
  PENDING_EVALUATION: "bg-blue-100 text-blue-700",
  EVALUATED: "bg-indigo-100 text-indigo-700",
  VERIFIED: "bg-emerald-100 text-emerald-700",
  DISPUTED: "bg-orange-100 text-orange-700",
  RESOLVED: "bg-slate-200 text-slate-700",
};

export default function CalismalarPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["engagements"],
    queryFn: listEngagements,
  });

  const items = data?.items ?? [];

  return (
    <AppShell>
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.calismalar.listTitle}</h1>

        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {messages.calismalar.loadError}
          </div>
        ) : items.length === 0 ? (
          <p className="text-slate-600">{messages.calismalar.emptyMessage}</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/calismalar/${item.id}`}
                  className="flex items-center justify-between bg-white p-4 rounded-md border border-slate-200 hover:bg-slate-50"
                >
                  <div>
                    <div className="font-medium text-slate-900">{item.title}</div>
                    <div className="text-xs text-slate-600">
                      {messages.calismalar.kind[item.kind]} · {item.organization_name}
                    </div>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded-full ${
                      STATUS_BADGE_CLASS[item.status] ?? "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {messages.calismalar.status[item.status]}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
