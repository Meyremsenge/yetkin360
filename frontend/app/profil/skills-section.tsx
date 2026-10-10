"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getMySkills, listSkills, addSkill } from "@/lib/api/client";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { ProfileFormDialog, fieldClass, labelClass, focusRingClass, primaryButtonClass } from "./profile-ui";

/**
 * "+ Yeni yetkinlik": claim a skill from the taxonomy in a modal. A claim
 * becomes a SELF_CLAIM signal, so it shows (unsealed) in the skills list
 * next to evidence-backed skills; removal lives on that list.
 */
export default function SkillsSection() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [claimedLevel, setClaimedLevel] = useState("INTERMEDIATE");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);
  const [isAddingSkill, setIsAddingSkill] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // AC-4: Current claims, used to hide already-claimed skills from search
  const SKILLS_QUERY_KEY = ["talent-skills"] as const;
  const queryClient = useQueryClient();
  const { data: mySkillsData } = useQuery({
    queryKey: SKILLS_QUERY_KEY,
    queryFn: getMySkills,
  });
  const mySkills = (mySkillsData?.items as Array<{ skill: { id: string; name_tr: string }; claimed_level: string }>) ?? [];

  // AC-S1: Debounce search (≥300ms)
  const [searchResults, setSearchResults] = useState<unknown[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (!searchQuery.trim()) {
      return;
    }

    // Set new timeout for debounce
    const timeout = setTimeout(async () => {
      setIsSearching(true);
      try {
        const result = await listSkills(searchQuery);
        setSearchResults(result?.items ?? []);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    searchTimeoutRef.current = timeout;

    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, [searchQuery]);

  // Boş sorguda sonuç/arama göstergesi her zaman gizli olmalı — effect'te
  // reset yerine render'da türetilir (react-hooks/set-state-in-effect).
  const effectiveSearchResults = searchQuery.trim() ? searchResults : null;
  const effectiveIsSearching = searchQuery.trim() ? isSearching : false;

  // Get list of current skill IDs for filtering
  const currentSkillIds = new Set(mySkills.map((item) => item.skill.id as string));

  // AC-6: Filter out already-claimed skills from search results
  const filteredSearchResults = (effectiveSearchResults as Array<Record<string, unknown>> | null)?.filter(
    (skill) => !currentSkillIds.has(skill.id as string)
  );

  // Handle skill selection
  const handleSelectSkill = (skillId: string) => {
    setSelectedSkillId(skillId);
    setAddError(null);
    setAddSuccess(null);
  };

  // Handle adding skill
  const handleAddSkill = async () => {
    if (!selectedSkillId) return;

    setIsAddingSkill(true);
    setAddError(null);
    setAddSuccess(null);

    try {
      await addSkill(selectedSkillId, claimedLevel);

      // AC-5: Refetch claims (search filter) and signals (the skills list)
      await queryClient.invalidateQueries({ queryKey: SKILLS_QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: ["talent-signals"] });

      // Clear selection; the dialog stays open so several skills can be added
      setSelectedSkillId(null);
      setSearchQuery("");
      setSearchResults(null);
      setClaimedLevel("INTERMEDIATE");

      setAddSuccess(messages.profil.skillAddedMessage);
      setTimeout(() => setAddSuccess(null), 2000);
    } catch (error) {
      if (error && typeof error === "object") {
        const errObj = error as Record<string, unknown>;

        // AC-6: 409 ALREADY_CLAIMED → reactive fallback
        if (errObj.status === 409 && errObj.code === "ALREADY_CLAIMED") {
          setAddError(messages.errors.skillAlreadyClaimed);
        }
        // AC-7: 404 SKILL_NOT_FOUND → refetch taxonomy + info message
        else if (errObj.status === 404 && errObj.code === "SKILL_NOT_FOUND") {
          // Refetch taxonomy
          try {
            const updated = await listSkills(searchQuery);
            setSearchResults(updated?.items ?? []);
          } catch {
            // Ignore refetch error
          }
          setAddError(messages.errors.skillNotFound);
        } else {
          setAddError(messages.errors.generic);
        }
      } else {
        setAddError(messages.errors.network);
      }
    } finally {
      setIsAddingSkill(false);
    }
  };

  return (
    <ProfileFormDialog
      triggerLabel={messages.profil.skillAddButton}
      title={messages.profil.skillAddTitle}
      description={messages.profil.skillAddHint}
      closeLabel={messages.profil.sheetClose}
    >
      {() => (
        <div className="space-y-4">
          <div>
            <label htmlFor="skill-search" className={labelClass}>
              {messages.profil.skillSearchLabel}
            </label>
            <input
              id="skill-search"
              type="text"
              placeholder={messages.profil.skillSearchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={fieldClass}
            />

            {effectiveIsSearching && (
              <p className="mt-3 text-sm text-muted-foreground">{messages.profil.searching}</p>
            )}

            {filteredSearchResults && filteredSearchResults.length > 0 && (
              <div className="mt-3 max-h-56 space-y-1 overflow-y-auto rounded-md border border-border bg-card p-1">
                {filteredSearchResults.map((skill) => (
                  <button
                    key={String(skill.id)}
                    type="button"
                    onClick={() => handleSelectSkill(String(skill.id))}
                    aria-pressed={selectedSkillId === skill.id}
                    className={`block h-9 w-full rounded-md px-3 text-left text-sm ${focusRingClass} ${
                      selectedSkillId === skill.id
                        ? "border border-success bg-success/10 text-success"
                        : "text-foreground hover:bg-muted"
                    }`}
                  >
                    {/* AC-S1: No dangerouslySetInnerHTML — safe text render */}
                    {String(skill.name_tr || "")}
                  </button>
                ))}
              </div>
            )}

            {effectiveSearchResults !== null && filteredSearchResults?.length === 0 && !effectiveIsSearching && (
              <p className="mt-3 text-[13px] text-muted-foreground">
                {searchQuery.trim() ? "Sonuç bulunamadı" : "Bir yetkinlik arayın"}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="claimed-level" className={labelClass}>
              {messages.profil.claimedLevel}
            </label>
            <select
              id="claimed-level"
              value={claimedLevel}
              onChange={(e) => setClaimedLevel(e.target.value)}
              className={fieldClass}
            >
              <option value="BEGINNER">Başlangıç</option>
              <option value="INTERMEDIATE">Orta</option>
              <option value="ADVANCED">İleri</option>
            </select>
          </div>

          <Button
            onClick={handleAddSkill}
            disabled={isAddingSkill || !selectedSkillId}
            className={`h-10 ${primaryButtonClass}`}
          >
            {isAddingSkill ? "Ekleniyor..." : messages.profil.addSkillButton}
          </Button>

          {addError && (
            <div
              role="alert"
              aria-live="polite"
              className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            >
              {addError}
            </div>
          )}

          {addSuccess && (
            <div
              role="status"
              aria-live="polite"
              className="rounded-md border border-success/30 bg-success/10 px-4 py-3 text-sm text-success"
            >
              {addSuccess}
            </div>
          )}
        </div>
      )}
    </ProfileFormDialog>
  );
}
