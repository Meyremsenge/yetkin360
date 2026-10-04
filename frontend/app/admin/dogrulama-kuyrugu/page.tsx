"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import * as adminApi from "@/lib/api/admin";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export default function DogrulamaKuyruguPage() {
  const queryClient = useQueryClient();
  const QUEUE_KEY = ["admin", "verification-queue"] as const;

  const [selectedLevels, setSelectedLevels] = useState<Record<string, string>>({});
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: queue, isLoading, isError, error } = useQuery({
    queryKey: QUEUE_KEY,
    queryFn: () => adminApi.getVerificationQueue(),
  });

  const { mutate: updateLevel, isPending: isUpdating } = useMutation({
    mutationFn: (vars: { orgId: string; level: string }) =>
      adminApi.updateVerificationLevel(vars.orgId, vars.level),
    onSuccess: (updated: adminApi.Organization | undefined) => {
      if (!updated) return;
      setMutationError(null);
      setSuccessMessage(messages.adminVerificationQueue.updated);
      queryClient.setQueryData(QUEUE_KEY, (prev: adminApi.VerificationQueueResponse | undefined) => {
        if (!prev) return prev;
        return {
          items: prev.items.map(org =>
            org.id === updated.id ? updated : org
          ),
        };
      });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setMutationError(
          err.status === 404 ? messages.adminVerificationQueue.notFound : messages.errors.generic
        );
      } else if (err instanceof NetworkError) {
        setMutationError(
          err.kind === "timeout" ? messages.errors.timeout : messages.errors.network
        );
      }
    },
  });

  const { mutate: reject, isPending: isRejecting } = useMutation({
    mutationFn: (orgId: string) => adminApi.rejectVerification(orgId),
    onSuccess: (rejected: adminApi.Organization | undefined) => {
      if (!rejected) return;
      setMutationError(null);
      setSuccessMessage(messages.adminVerificationQueue.rejected);
      queryClient.setQueryData(QUEUE_KEY, (prev: adminApi.VerificationQueueResponse | undefined) => {
        if (!prev) return prev;
        return { items: prev.items.filter(org => org.id !== rejected.id) };
      });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setMutationError(
          err.status === 404
            ? messages.adminVerificationQueue.notFound
            : err.status === 409
              ? messages.adminVerificationQueue.notPending
              : messages.errors.generic
        );
      } else if (err instanceof NetworkError) {
        setMutationError(
          err.kind === "timeout" ? messages.errors.timeout : messages.errors.network
        );
      }
    },
  });

  const handleLevelChange = (orgId: string, newLevel: string) => {
    setSelectedLevels((prev) => ({ ...prev, [orgId]: newLevel }));
    setMutationError(null);
  };

  const handleSubmit = (orgId: string) => {
    const level = selectedLevels[orgId];
    if (!level) return;
    updateLevel({ orgId, level });
  };

  return (
    <AppShell>
      <main className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.adminVerificationQueue.title}</h1>

        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div
            role="alert"
            className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
          >
            {error instanceof ApiError && error.status === 404
              ? messages.adminVerificationQueue.notFound
              : error instanceof NetworkError && error.kind === "timeout"
                ? messages.errors.timeout
                : messages.errors.generic}
          </div>
        ) : !queue || queue.items.length === 0 ? (
          <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.adminVerificationQueue.empty}
          </div>
        ) : (
          <>
            {successMessage && (
              <div role="status" className="mb-4 rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-700">
                {successMessage}
              </div>
            )}

            {mutationError && (
              <div
                role="alert"
                className="mb-4 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
              >
                {mutationError}
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left p-3 font-medium text-slate-700">
                      {messages.adminVerificationQueue.headers.name}
                    </th>
                    <th className="text-left p-3 font-medium text-slate-700">
                      {messages.adminVerificationQueue.headers.legalId}
                    </th>
                    <th className="text-left p-3 font-medium text-slate-700">
                      {messages.adminVerificationQueue.headers.domain}
                    </th>
                    <th className="text-left p-3 font-medium text-slate-700">
                      {messages.adminVerificationQueue.headers.verificationLevel}
                    </th>
                    <th className="text-left p-3 font-medium text-slate-700">
                      {messages.adminVerificationQueue.headers.createdAt}
                    </th>
                    <th className="text-left p-3 font-medium text-slate-700">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {queue.items.map((org) => (
                    <tr key={org.id} className="border-b border-slate-200 hover:bg-slate-50">
                      <td className="p-3">{org.name}</td>
                      <td className="p-3 text-slate-600">{org.legal_id || "-"}</td>
                      <td className="p-3 text-slate-600">{org.domain || "-"}</td>
                      <td className="p-3">
                        <span className="font-medium mr-2">{selectedLevels[org.id] || org.verification_level}</span>
                        <select
                          value={selectedLevels[org.id] || org.verification_level}
                          onChange={(e) => handleLevelChange(org.id, e.target.value)}
                          disabled={isUpdating}
                          className="px-2 py-1 border border-slate-300 rounded-md text-sm"
                        >
                          <option value="T0">T0</option>
                          <option value="T1">T1</option>
                          <option value="T2">T2</option>
                          <option value="T3">T3</option>
                        </select>
                      </td>
                      <td className="p-3 text-slate-600">
                        {org.verified_at
                          ? new Date(org.verified_at).toLocaleString("tr-TR")
                          : "-"}
                      </td>
                      <td className="p-3">
                        <button
                          onClick={() => handleSubmit(org.id)}
                          disabled={isUpdating || isRejecting || selectedLevels[org.id] === org.verification_level}
                          aria-label={`Onayla ${org.name}`}
                          className="px-3 py-1 bg-slate-900 text-white text-xs rounded-md hover:bg-slate-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
                        >
                          {messages.adminVerificationQueue.form.confirm}
                        </button>
                        <button
                          onClick={() => reject(org.id)}
                          disabled={isUpdating || isRejecting}
                          aria-label={`Reddet ${org.name}`}
                          className="ml-2 px-3 py-1 border border-slate-300 text-slate-700 text-xs rounded-md hover:bg-slate-100 disabled:bg-slate-100 disabled:cursor-not-allowed"
                        >
                          {messages.adminVerificationQueue.form.reject}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </AppShell>
  );
}
