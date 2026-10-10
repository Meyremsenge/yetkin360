"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AdminPagination } from "@/components/admin-pagination";
import * as adminApi from "@/lib/api/admin";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export default function SkillerPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const limit = adminApi.ADMIN_PAGE_SIZE;
  const SKILLS_KEY = ["admin", "skills", { limit, offset }] as const;

  const [formData, setFormData] = useState<{ slug: string; name_tr: string; category: string }>({
    slug: "",
    name_tr: "",
    category: "LANGUAGE"
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [mergeDialog, setMergeDialog] = useState<{ skillId: string; skillName: string } | null>(null);
  const [mergeTarget, setMergeTarget] = useState<string>("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const { data: skillsList, isLoading, isError, error, refetch } = useQuery({
    queryKey: SKILLS_KEY,
    queryFn: () => adminApi.getSkills({ limit, offset }),
  });

  // Merge targets: every skill across all pages, fetched only while the dialog
  // is open (the visible page alone would hide targets beyond it).
  const {
    data: allSkills,
    isLoading: isLoadingTargets,
    isError: isTargetsError,
  } = useQuery({
    queryKey: ["admin", "skills-all"] as const,
    queryFn: () => adminApi.getAllSkills(),
    enabled: mergeDialog !== null,
    staleTime: 0,
  });

  const { mutate: createSkill, isPending: isCreating } = useMutation({
    mutationFn: () =>
      adminApi.createSkill(formData.slug, formData.name_tr, formData.category),
    onSuccess: (newSkill: adminApi.Skill | undefined) => {
      if (!newSkill) return;
      setFormError(null);
      setFormData({ slug: "", name_tr: "", category: "LANGUAGE" });
      setSuccessMessage(messages.adminSkills.createSuccess);
      // Sorted server-side: the new skill may land on any page, so refetch.
      void queryClient.invalidateQueries({ queryKey: ["admin", "skills"] });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setFormError(messages.adminSkills.slugConflict);
        } else if (err.status === 404) {
          setFormError(messages.adminSkills.notFound);
        } else {
          setFormError(messages.errors.generic);
        }
      } else if (err instanceof NetworkError) {
        setFormError(
          err.message === "timeout" ? messages.errors.timeout : messages.errors.network
        );
      }
    },
  });

  const { mutate: deprecateSkill, isPending: isDeprecating } = useMutation({
    mutationFn: (skillId: string) => adminApi.deprecateSkill(skillId),
    onSuccess: (updated: adminApi.Skill | undefined) => {
      if (!updated) return;
      setActionError(null);
      queryClient.setQueryData(SKILLS_KEY, (prev: adminApi.SkillsListResponse | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map(s =>
            s.id === updated.id ? updated : s
          ),
        };
      });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 500) {
          setActionError(messages.errors.generic);
        } else {
          setActionError(messages.errors.generic);
        }
      } else if (err instanceof NetworkError) {
        setActionError(
          err.message === "timeout" ? messages.errors.timeout : messages.errors.network
        );
      }
    },
  });

  const { mutate: mergeSkillMutation, isPending: isMerging } = useMutation({
    mutationFn: (vars: { skillId: string; targetId: string }) =>
      adminApi.mergeSkill(vars.skillId, vars.targetId),
    onSuccess: (updated: adminApi.Skill | undefined) => {
      if (!updated) return;
      setActionError(null);
      setMergeDialog(null);
      setMergeTarget("");
      void queryClient.invalidateQueries({ queryKey: ["admin", "skills-all"] });
      queryClient.setQueryData(SKILLS_KEY, (prev: adminApi.SkillsListResponse | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map(s =>
            s.id === updated.id ? updated : s
          ),
        };
      });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 500) {
          setActionError(messages.errors.generic);
        } else {
          setActionError(messages.errors.generic);
        }
      } else if (err instanceof NetworkError) {
        setActionError(
          err.message === "timeout" ? messages.errors.timeout : messages.errors.network
        );
      }
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formData.slug || !formData.name_tr) {
      setFormError("Slug ve ad zorunludur");
      return;
    }
    createSkill();
  };

  const getParentName = (parentId: string | null | undefined): string => {
    if (!parentId) return messages.adminSkills.parentLabel;
    const parent = (allSkills ?? skillsList?.items)?.find((s) => s.id === parentId);
    return parent ? parent.name_tr : "-";
  };

  const getMergedIntoName = (mergedId: string | null | undefined): string => {
    if (!mergedId) return "-";
    const target = (allSkills ?? skillsList?.items)?.find((s) => s.id === mergedId);
    return target ? target.name_tr : "-";
  };

  useEffect(() => {
    if (!mergeDialog) return;

    const triggerEl = document.activeElement as HTMLElement;
    triggerRef.current = triggerEl;

    // Setup focus trap (first focus) after paint
    const rafId = requestAnimationFrame(() => {
      if (!dialogRef.current) return;

      const focusables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button, select, input, [tabindex]'
        )
      ).filter(el => {
        const disabled = el.getAttribute('disabled');
        const tabindex = el.getAttribute('tabindex');
        return !disabled && tabindex !== '-1';
      });

      if (focusables.length > 0) {
        focusables[0].focus();
      }
    });

    // Setup event listener
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!dialogRef.current) return;

      if (e.key === "Escape") {
        e.preventDefault();
        setMergeDialog(null);
        setMergeTarget("");
        triggerEl?.focus();
        return;
      }

      if (e.key === "Tab") {
        const getFocusable = () => {
          if (!dialogRef.current) return [];
          return Array.from(
            dialogRef.current.querySelectorAll<HTMLElement>(
              'button, select, input, [tabindex]'
            )
          ).filter(el => {
            const disabled = el.getAttribute('disabled');
            const tabindex = el.getAttribute('tabindex');
            return !disabled && tabindex !== '-1';
          });
        };

        const items = getFocusable();
        if (items.length === 0) return;

        const active = document.activeElement as HTMLElement;
        const isInsideDialog = dialogRef.current.contains(active);
        const currentIndex = items.indexOf(active);

        if (e.shiftKey) {
          if (!isInsideDialog || currentIndex <= 0) {
            e.preventDefault();
            items[items.length - 1].focus();
          }
        } else {
          if (!isInsideDialog || currentIndex === items.length - 1) {
            e.preventDefault();
            items[0].focus();
          }
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      cancelAnimationFrame(rafId);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [mergeDialog]);

  return (
    <AppShell>
      <main className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">{messages.adminSkills.title}</h1>

        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div
            role="alert"
            className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
          >
            {error instanceof ApiError && error.status === 404
              ? messages.adminSkills.notFound
              : error instanceof NetworkError && error.kind === "timeout"
                ? messages.errors.timeout
                : messages.errors.generic}
            <button
              type="button"
              onClick={() => refetch()}
              className="ml-3 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            >
              {messages.errors.retry}
            </button>
          </div>
        ) : (
          <>
            {/* Action Error Alert */}
            {actionError && (
              <div
                role="alert"
                className="mb-6 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
              >
                {actionError}
              </div>
            )}

            {/* Create Form */}
            <div className="mb-8 rounded-md border border-slate-200 bg-white p-6">
              <h2 className="text-lg font-bold mb-4">{messages.adminSkills.formTitle}</h2>

              {successMessage && (
                <div
                  role="status"
                  className="mb-4 rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-700"
                >
                  {successMessage}
                </div>
              )}

              {formError && (
                <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
                  {formError}
                </div>
              )}

              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div>
                  <label htmlFor="skill-slug" className="block text-sm font-medium text-slate-700 mb-1">
                    {messages.adminSkills.form.slugLabel}
                  </label>
                  <input
                    id="skill-slug"
                    type="text"
                    placeholder="python, web-dev..."
                    value={formData.slug}
                    onChange={(e) => setFormData((p) => ({ ...p, slug: e.target.value }))}
                    disabled={isCreating}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm disabled:bg-slate-100"
                  />
                </div>

                <div>
                  <label htmlFor="skill-name-tr" className="block text-sm font-medium text-slate-700 mb-1">
                    {messages.adminSkills.form.nameLabel}
                  </label>
                  <input
                    id="skill-name-tr"
                    type="text"
                    placeholder="Python, Web Geliştirme..."
                    value={formData.name_tr}
                    onChange={(e) => setFormData((p) => ({ ...p, name_tr: e.target.value }))}
                    disabled={isCreating}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm disabled:bg-slate-100"
                  />
                </div>

                <div>
                  <label htmlFor="skill-category" className="block text-sm font-medium text-slate-700 mb-1">
                    {messages.adminSkills.form.categoryLabel}
                  </label>
                  <select
                    id="skill-category"
                    value={formData.category}
                    onChange={(e) => {
                      const validCategories = ["LANGUAGE", "DOMAIN", "TOOL", "FRAMEWORK", "SOFT"];
                      const newValue = e.target.value;
                      if (validCategories.includes(newValue)) {
                        setFormData((p) => ({
                          ...p,
                          category: newValue as adminApi.Skill["category"],
                        }));
                      }
                    }}
                    disabled={isCreating}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm disabled:bg-slate-100"
                  >
                    <option value="LANGUAGE">LANGUAGE</option>
                    <option value="DOMAIN">DOMAIN</option>
                    <option value="TOOL">TOOL</option>
                    <option value="FRAMEWORK">FRAMEWORK</option>
                    <option value="SOFT">SOFT</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={isCreating || !formData.slug || !formData.name_tr}
                  className="px-4 py-2 bg-slate-900 text-white text-sm rounded-md hover:bg-slate-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
                >
                  {isCreating
                    ? messages.adminSkills.form.creatingButton
                    : messages.adminSkills.form.createButton}
                </button>
              </form>
            </div>

            {/* Skills List */}
            {!skillsList || skillsList.items.length === 0 ? (
              <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
                {messages.adminSkills.empty}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left p-3 font-medium text-slate-700">İşlemler</th>
                      <th className="text-left p-3 font-medium text-slate-700">
                        {messages.adminSkills.headers.slug}
                      </th>
                      <th className="text-left p-3 font-medium text-slate-700">
                        {messages.adminSkills.headers.name}
                      </th>
                      <th className="text-left p-3 font-medium text-slate-700">
                        {messages.adminSkills.headers.category}
                      </th>
                      <th className="text-left p-3 font-medium text-slate-700">
                        {messages.adminSkills.headers.status}
                      </th>
                      <th className="text-left p-3 font-medium text-slate-700">
                        {messages.adminSkills.headers.parent}
                      </th>
                      <th className="text-left p-3 font-medium text-slate-700">
                        {messages.adminSkills.headers.mergedInto}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {skillsList.items.map((skill) => (
                      <tr key={skill.id} className="border-b border-slate-200 hover:bg-slate-50">
                        <td className="p-3 space-x-2">
                          <button
                            onClick={() =>
                              deprecateSkill(skill.id)
                            }
                            disabled={isDeprecating || skill.status === "DEPRECATED"}
                            aria-label={`Devre Dışı Bırak ${skill.name_tr}`}
                            className="px-2 py-1 text-xs bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
                          >
                            {messages.adminSkills.actions.deprecate}
                          </button>
                          <button
                            onClick={() =>
                              setMergeDialog({ skillId: skill.id, skillName: skill.name_tr })
                            }
                            disabled={skill.status === "DEPRECATED" || skill.status === "MERGED"}
                            aria-label={`Birleştir ${skill.name_tr}`}
                            className="px-2 py-1 text-xs bg-slate-600 text-white rounded-md hover:bg-slate-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
                          >
                            {messages.adminSkills.actions.merge}
                          </button>
                        </td>
                        <td className="p-3 text-slate-700">{skill.slug}</td>
                        <td className="p-3 text-slate-700">{skill.name_tr}</td>
                        <td className="p-3 text-slate-600">
                          {(messages.adminSkills.categoryLabels as Record<string, string>)[skill.category] || skill.category}
                        </td>
                        <td className="p-3">
                          <span
                            className={`inline-block px-2 py-1 rounded-md text-xs font-medium ${
                              skill.status === "ACTIVE"
                                ? "bg-green-100 text-green-800"
                                : skill.status === "DEPRECATED"
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-slate-100 text-slate-800"
                            }`}
                          >
                            {skill.status}
                          </span>
                        </td>
                        <td className="p-3 text-slate-600">{getParentName(skill.parent_id)}</td>
                        <td className="p-3 text-slate-600">
                          {skill.status === "MERGED" ? getMergedIntoName(skill.merged_into_id) : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {skillsList && (
              <AdminPagination
                offset={offset}
                limit={limit}
                hasMore={skillsList.has_more}
                disabled={isDeprecating || isMerging}
                onChange={setOffset}
              />
            )}

            {/* Merge Dialog */}
            {mergeDialog && (
              <div
                role="dialog"
                aria-modal="true"
                ref={dialogRef}
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                onClick={(e) => {
                  if (e.target === e.currentTarget) {
                    setMergeDialog(null);
                    setMergeTarget("");
                  }
                }}
              >
                <div className="bg-white rounded-md p-6 max-w-md w-full mx-4">
                  <h3 className="text-lg font-bold mb-4">
                    {messages.adminSkills.mergeDialog.title}
                  </h3>
                  <div className="mb-4">
                    <label htmlFor="merge-target" className="block text-sm font-medium text-slate-700 mb-2">
                      {messages.adminSkills.mergeDialog.label}
                    </label>
                    <select
                      id="merge-target"
                      value={mergeTarget}
                      onChange={(e) => setMergeTarget(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                    >
                      <option value="">Seçiniz...</option>
                      {allSkills
                        ?.filter((s) => s.id !== mergeDialog.skillId && s.status === "ACTIVE")
                        .map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name_tr}
                          </option>
                        ))}
                    </select>
                    {isLoadingTargets && (
                      <p role="status" className="mt-2 text-xs text-slate-600">{messages.shell.loading}</p>
                    )}
                    {isTargetsError && (
                      <p role="alert" className="mt-2 text-xs text-red-700">{messages.errors.generic}</p>
                    )}
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => {
                        setMergeDialog(null);
                        setMergeTarget("");
                      }}
                      className="px-4 py-2 text-sm border border-slate-300 rounded-md hover:bg-slate-50"
                    >
                      {messages.adminSkills.mergeDialog.cancel}
                    </button>
                    <button
                      onClick={() => {
                        if (mergeTarget) {
                          mergeSkillMutation({
                            skillId: mergeDialog.skillId,
                            targetId: mergeTarget,
                          });
                        }
                      }}
                      disabled={!mergeTarget || isMerging}
                      className="px-4 py-2 bg-slate-900 text-white text-sm rounded-md hover:bg-slate-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
                    >
                      {messages.adminSkills.mergeDialog.confirm}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </AppShell>
  );
}
