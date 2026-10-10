"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import {
  EmptyState,
  PanelIcon,
  StatusPill,
  actionClass,
  formatTemplate,
} from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import * as adminApi from "@/lib/api/admin";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const a = messages.adminSkills;

type StatusFilter = "ALL" | "ACTIVE" | "DEPRECATED" | "MERGED";
const STATUS_FILTERS: StatusFilter[] = ["ALL", "ACTIVE", "DEPRECATED", "MERGED"];
const STATUS_TONE: Record<string, "default" | "warning" | "success"> = {
  ACTIVE: "success",
  DEPRECATED: "warning",
  MERGED: "default",
};
const CATEGORIES = ["LANGUAGE", "DOMAIN", "TOOL", "FRAMEWORK"] as const;

const FIELD_CLASS =
  "block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25 disabled:bg-muted";
const LABEL_CLASS = "mb-1.5 block text-xs font-medium text-foreground";
const SM = "h-8 px-3 text-[13px]";

export default function SkillerPage() {
  const queryClient = useQueryClient();
  const SKILLS_KEY = ["admin", "skills"] as const;

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
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const { data: skillsList, isLoading, isError, error } = useQuery({
    queryKey: SKILLS_KEY,
    queryFn: () => adminApi.getSkills(),
  });

  const { mutate: createSkill, isPending: isCreating } = useMutation({
    mutationFn: () =>
      adminApi.createSkill(formData.slug, formData.name_tr, formData.category),
    onSuccess: (newSkill: adminApi.Skill | undefined) => {
      if (!newSkill) return;
      setFormError(null);
      setFormData({ slug: "", name_tr: "", category: "LANGUAGE" });
      setSuccessMessage(a.createSuccess);
      queryClient.setQueryData(SKILLS_KEY, (prev: adminApi.SkillsListResponse | undefined) => {
        if (!prev) return prev;
        return {
          items: [...prev.items, newSkill],
        };
      });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setFormError(a.slugConflict);
        } else if (err.status === 404) {
          setFormError(a.notFound);
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
          items: prev.items.map(s =>
            s.id === updated.id ? updated : s
          ),
        };
      });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setActionError(messages.errors.generic);
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
      queryClient.setQueryData(SKILLS_KEY, (prev: adminApi.SkillsListResponse | undefined) => {
        if (!prev) return prev;
        return {
          items: prev.items.map(s =>
            s.id === updated.id ? updated : s
          ),
        };
      });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setActionError(messages.errors.generic);
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
      setFormError(a.requiredError);
      return;
    }
    createSkill();
  };

  const getParentName = (parentId: string | null | undefined): string => {
    if (!parentId) return a.parentLabel;
    const parent = skillsList?.items.find((s) => s.id === parentId);
    return parent ? parent.name_tr : "-";
  };

  const getMergedIntoName = (mergedId: string | null | undefined): string => {
    if (!mergedId) return "-";
    const target = skillsList?.items.find((s) => s.id === mergedId);
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

  const allSkills = skillsList?.items ?? [];
  const countFor = (filter: StatusFilter) =>
    filter === "ALL" ? allSkills.length : allSkills.filter((s) => s.status === filter).length;
  const needle = search.trim().toLocaleLowerCase("tr-TR");
  const visibleSkills = allSkills.filter(
    (s) =>
      (statusFilter === "ALL" || s.status === statusFilter) &&
      (!needle ||
        s.slug.toLocaleLowerCase("tr-TR").includes(needle) ||
        s.name_tr.toLocaleLowerCase("tr-TR").includes(needle))
  );

  const statusLabel = (status: string) => (a.skillStatus as Record<string, string>)[status] ?? status;

  return (
    <AppShell>
      <main>
        <PageHeader eyebrow={messages.shell.groupAdmin} title={a.title} description={a.description} />

        <PageBody>
          {isLoading ? (
            <div role="status">
              <span className="sr-only">{messages.shell.loading}</span>
              <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
            </div>
          ) : isError ? (
            <Alert variant="error" className="text-sm">
              {error instanceof ApiError && error.status === 404
                ? a.notFound
                : error instanceof NetworkError && error.kind === "timeout"
                  ? messages.errors.timeout
                  : messages.errors.generic}
            </Alert>
          ) : (
            <div className="space-y-6">
              {
                <>
                  <section className="rounded-xl border border-border bg-card p-5">
                    <div className="mb-4 flex items-start gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success">
                        <PanelIcon name="tags" />
                      </span>
                      <div>
                        <h2 className="font-serif text-lg font-semibold text-foreground">{a.formTitle}</h2>
                        <p className="text-[13px] text-muted-foreground">{a.formHint}</p>
                      </div>
                    </div>
                    {successMessage ? (
                      <div
                        role="status"
                        // Stock green scale is mapped to pine in tailwind.config.ts.
                        className="mb-4 rounded-md border border-green-200 bg-green-50 px-3 py-2.5 text-sm text-green-700"
                      >
                        {successMessage}
                      </div>
                    ) : null}

                    {formError ? (
                      <div
                        aria-live="polite"
                        className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
                      >
                        {formError}
                      </div>
                    ) : null}

                    <form onSubmit={handleCreateSubmit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_180px_auto] md:items-end">
                      <div>
                        <label htmlFor="skill-slug" className={LABEL_CLASS}>
                          {a.form.slugLabel}
                        </label>
                        <input
                          id="skill-slug"
                          type="text"
                          placeholder="python, web-dev..."
                          value={formData.slug}
                          onChange={(e) => setFormData((p) => ({ ...p, slug: e.target.value }))}
                          disabled={isCreating}
                          className={cn(FIELD_CLASS, "font-mono")}
                        />
                      </div>

                      <div>
                        <label htmlFor="skill-name-tr" className={LABEL_CLASS}>
                          {a.form.nameLabel}
                        </label>
                        <input
                          id="skill-name-tr"
                          type="text"
                          placeholder="Python, Web Geliştirme..."
                          value={formData.name_tr}
                          onChange={(e) => setFormData((p) => ({ ...p, name_tr: e.target.value }))}
                          disabled={isCreating}
                          className={FIELD_CLASS}
                        />
                      </div>

                      <div>
                        <label htmlFor="skill-category" className={LABEL_CLASS}>
                          {a.form.categoryLabel}
                        </label>
                        <select
                          id="skill-category"
                          value={formData.category}
                          onChange={(e) => {
                            const newValue = e.target.value;
                            if ((CATEGORIES as readonly string[]).includes(newValue)) {
                              setFormData((p) => ({ ...p, category: newValue }));
                            }
                          }}
                          disabled={isCreating}
                          className={FIELD_CLASS}
                        >
                          {CATEGORIES.map((category) => (
                            <option key={category} value={category}>
                              {a.categoryLabels[category]}
                            </option>
                          ))}
                        </select>
                      </div>

                      <button
                        type="submit"
                        disabled={isCreating || !formData.slug || !formData.name_tr}
                        className={cn(actionClass.primary, "w-full md:w-auto")}
                      >
                        <PanelIcon name="plus" className="h-4 w-4" />
                        {isCreating ? a.form.creatingButton : a.form.createButton}
                      </button>
                    </form>
                  </section>
                  {actionError ? (
                    <Alert variant="error" className="text-sm">
                      {actionError}
                    </Alert>
                  ) : null}

                  {allSkills.length === 0 ? (
                    <section className="rounded-xl border border-border bg-card p-5">
                      <EmptyState icon="tags" title={a.empty} hint={a.emptyHint} />
                    </section>
                  ) : (
                    <>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="relative w-full sm:max-w-xs">
                          <label htmlFor="skill-search" className="sr-only">
                            {a.searchLabel}
                          </label>
                          <PanelIcon
                            name="search"
                            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                          />
                          <input
                            id="skill-search"
                            type="search"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder={a.searchPlaceholder}
                            className={cn(FIELD_CLASS, "pl-9")}
                          />
                        </div>
                        <div
                          role="group"
                          aria-label={a.filterLabel}
                          className="flex gap-1 overflow-x-auto rounded-lg border border-border bg-muted/60 p-1 [scrollbar-width:none]"
                        >
                          {STATUS_FILTERS.map((filter) => {
                            const selected = statusFilter === filter;
                            return (
                              <button
                                key={filter}
                                type="button"
                                aria-pressed={selected}
                                onClick={() => setStatusFilter(filter)}
                                className={cn(
                                  "flex h-8 shrink-0 items-center gap-1.5 rounded-md px-3 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
                                  selected
                                    ? "bg-card text-foreground shadow-[0_1px_3px_rgba(34,31,27,0.12)]"
                                    : "text-muted-foreground hover:text-foreground"
                                )}
                              >
                                {filter === "ALL" ? a.filterAll : statusLabel(filter)}
                                <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                                  {countFor(filter)}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="overflow-x-auto rounded-xl border border-border bg-card">
                        <table className="w-full min-w-[820px] border-collapse text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/70 text-left text-xs text-muted-foreground">
                              <th className="px-4 py-3 font-medium">{a.headers.slug}</th>
                              <th className="px-4 py-3 font-medium">{a.headers.name}</th>
                              <th className="px-4 py-3 font-medium">{a.headers.category}</th>
                              <th className="px-4 py-3 font-medium">{a.headers.status}</th>
                              <th className="px-4 py-3 font-medium">{a.headers.parent}</th>
                              <th className="px-4 py-3 font-medium">{a.headers.mergedInto}</th>
                              <th className="px-4 py-3 text-right font-medium">{a.actionsHeader}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {visibleSkills.length === 0 ? (
                              <tr>
                                <td colSpan={7} className="px-4 py-6 text-center text-sm text-muted-foreground">
                                  {a.noMatch}
                                </td>
                              </tr>
                            ) : (
                              visibleSkills.map((skill) => (
                                <tr
                                  key={skill.id}
                                  className={cn(
                                    "border-b border-border last:border-0 hover:bg-background",
                                    skill.status !== "ACTIVE" && "text-muted-foreground"
                                  )}
                                >
                                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[13px]">{skill.slug}</td>
                                  <td className="whitespace-nowrap px-4 py-3 font-medium text-foreground">{skill.name_tr}</td>
                                  <td className="px-4 py-3">
                                    {(a.categoryLabels as Record<string, string>)[skill.category] || skill.category}
                                  </td>
                                  <td className="px-4 py-3">
                                    <StatusPill tone={STATUS_TONE[skill.status] ?? "default"}>
                                      {statusLabel(skill.status)}
                                    </StatusPill>
                                  </td>
                                  <td className="whitespace-nowrap px-4 py-3">{getParentName(skill.parent_id)}</td>
                                  <td className="px-4 py-3">
                                    {skill.status === "MERGED" ? (
                                      <span className="inline-flex items-center gap-1 text-foreground">
                                        <PanelIcon name="arrowRight" className="h-3.5 w-3.5 text-muted-foreground" />
                                        {getMergedIntoName(skill.merged_into_id)}
                                      </span>
                                    ) : (
                                      "-"
                                    )}
                                  </td>
                                  <td className="px-4 py-3">
                                    <div className="flex justify-end gap-2">
                                      <button
                                        onClick={() =>
                                          setMergeDialog({ skillId: skill.id, skillName: skill.name_tr })
                                        }
                                        disabled={skill.status === "DEPRECATED" || skill.status === "MERGED"}
                                        aria-label={`Birleştir ${skill.name_tr}`}
                                        className={cn(actionClass.neutral, SM)}
                                      >
                                        {a.actions.merge}
                                      </button>
                                      <button
                                        onClick={() =>
                                          deprecateSkill(skill.id)
                                        }
                                        disabled={isDeprecating || skill.status === "DEPRECATED"}
                                        aria-label={`Devre Dışı Bırak ${skill.name_tr}`}
                                        className={cn(actionClass.dangerOutline, SM)}
                                      >
                                        {a.actions.deprecate}
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </>
              }
            </div>
          )}

          {/* Merge Dialog */}
          {mergeDialog ? (
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="merge-dialog-title"
              ref={dialogRef}
              className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/40 sm:items-center"
              onClick={(e) => {
                if (e.target === e.currentTarget) {
                  setMergeDialog(null);
                  setMergeTarget("");
                }
              }}
            >
              <div className="y360-rise w-full max-w-[480px] rounded-t-xl border border-border bg-card p-6 shadow-[0_8px_24px_-12px_rgba(34,31,27,0.25)] sm:mx-4 sm:rounded-lg">
                <h3 id="merge-dialog-title" className="font-serif text-xl font-medium text-foreground">
                  {a.mergeDialog.title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {formatTemplate(a.mergeHint, { name: mergeDialog.skillName })}
                </p>
                <div className="mt-5">
                  <label htmlFor="merge-target" className={LABEL_CLASS}>
                    {a.mergeDialog.label}
                  </label>
                  <select
                    id="merge-target"
                    value={mergeTarget}
                    onChange={(e) => setMergeTarget(e.target.value)}
                    className={FIELD_CLASS}
                  >
                    <option value="">{a.mergePlaceholder}</option>
                    {skillsList?.items
                      .filter((s) => s.id !== mergeDialog.skillId && s.status === "ACTIVE")
                      .map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name_tr}
                        </option>
                      ))}
                  </select>
                </div>
                <div className="mt-6 flex justify-end gap-2">
                  <button
                    onClick={() => {
                      setMergeDialog(null);
                      setMergeTarget("");
                    }}
                    className="inline-flex h-10 items-center rounded-md px-4 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                  >
                    {a.mergeDialog.cancel}
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
                    className={actionClass.primary}
                  >
                    {a.mergeDialog.confirm}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </PageBody>
      </main>
    </AppShell>
  );
}
