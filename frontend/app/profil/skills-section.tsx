"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getMySkills,
  listSkills,
  addSkill,
  removeSkill,
} from "@/lib/api/client";
import messages from "@/messages/tr.json";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function SkillsSection() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [claimedLevel, setClaimedLevel] = useState("INTERMEDIATE");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);
  const [isAddingSkill, setIsAddingSkill] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // AC-4: Fetch current user's skills on mount using TanStack Query
  const SKILLS_QUERY_KEY = ["talent-skills"] as const;
  const queryClient = useQueryClient();
  const { data: mySkillsData, isLoading: mySkillsLoading, isError: mySkillsError } = useQuery({
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
      setSearchResults(null);
      setIsSearching(false);
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

  // Get list of current skill IDs for filtering
  const currentSkillIds = new Set(
    mySkills.map((item) => item.skill.id as string)
  );

  // AC-6: Filter out already-claimed skills from search results
  const filteredSearchResults = (searchResults as Array<Record<string, unknown>> | null)?.filter(
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

      // AC-5: Refetch skills list after successful add
      await queryClient.invalidateQueries({ queryKey: SKILLS_QUERY_KEY });

      // Clear selection
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

  // Handle removing skill
  const handleRemoveSkill = async (skillId: string) => {
    setRemoveError(null);

    try {
      await removeSkill(skillId);

      // AC-8: Refetch skills list after successful remove
      await queryClient.invalidateQueries({ queryKey: SKILLS_QUERY_KEY });
    } catch (error) {
      if (error && typeof error === "object") {
        const errObj = error as Record<string, unknown>;

        // AC-9: 404 → silent refetch, no error shown
        if (errObj.status === 404) {
          await queryClient.invalidateQueries({ queryKey: SKILLS_QUERY_KEY });
          // No error message shown
          return;
        }
      }

      setRemoveError(messages.errors.generic);
    }
  };


  return (
    <div className="rounded-md bg-slate-50 p-6 border border-slate-200">
      <h2 className="text-xl font-bold mb-4">{messages.profil.skillsSection}</h2>

      {/* Current skills list */}
      {mySkillsLoading ? (
        <p className="text-slate-600">{messages.shell.loading}</p>
      ) : mySkillsError ? (
        <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
          {messages.errors.generic}
        </div>
      ) : mySkills.length === 0 ? (
        /* AC-4: Empty state message */
        <p className="text-slate-600 mb-6">{messages.profil.emptySkillsMessage}</p>
      ) : (
        <div className="mb-6 space-y-2">
          {mySkills.map((item) => (
            <div
              key={String(item.skill.id)}
              className="flex items-center justify-between bg-white p-3 rounded-md border border-slate-200"
            >
              <div className="flex-1">
                <div className="font-medium text-slate-900">
                  {/* AC-S2: No dangerouslySetInnerHTML — safe text render */}
                  {String(item.skill.name_tr || "")}
                </div>
                <div className="text-xs text-slate-600">
                  {`${messages.profil.claimedLevel}: ${String(item.claimed_level || "")}`}
                </div>
              </div>
              <Button
                onClick={() => handleRemoveSkill(String(item.skill.id))}
                className="bg-red-600 hover:bg-red-700 px-3 py-1 text-sm"
              >
                {messages.profil.removeSkillButton}
              </Button>
            </div>
          ))}
        </div>
      )}

      {removeError && (
        <div
          role="alert"
          aria-live="polite"
          className="mb-4 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
        >
          {removeError}
        </div>
      )}

      {/* Add skill section */}
      <div className="border-t pt-6">
        {/* Search input with debounce */}
        <div className="mb-4">
          <Label htmlFor="skill-search">{messages.profil.skillSearchPlaceholder}</Label>
          <Input
            id="skill-search"
            type="text"
            placeholder={messages.profil.skillSearchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Search results */}
        {isSearching && <p className="text-sm text-slate-600 mb-4">{messages.shell.loading}</p>}

        {filteredSearchResults && filteredSearchResults.length > 0 && (
          <div className="mb-4 space-y-2 max-h-48 overflow-y-auto">
            {filteredSearchResults.map((skill) => (
              <button
                key={String(skill.id)}
                onClick={() => handleSelectSkill(String(skill.id))}
                className={`block w-full text-left px-3 py-2 rounded-md text-sm ${
                  selectedSkillId === skill.id
                    ? "bg-slate-900 text-white"
                    : "bg-white border border-slate-200 hover:bg-slate-100 text-slate-900"
                }`}
              >
                {/* AC-S1: No dangerouslySetInnerHTML — safe text render */}
                {String(skill.name_tr || "")}
              </button>
            ))}
          </div>
        )}

        {searchResults !== null && filteredSearchResults?.length === 0 && !isSearching && (
          <p className="text-xs text-slate-600 mb-4">
            {searchQuery.trim() ? "Sonuç bulunamadı" : "Bir yetkinlik arayın"}
          </p>
        )}

        {/* Claimed level selector */}
        {selectedSkillId && (
          <div className="mb-4">
            <Label htmlFor="claimed-level">{messages.profil.claimedLevel}</Label>
            <select
              id="claimed-level"
              value={claimedLevel}
              onChange={(e) => setClaimedLevel(e.target.value)}
              className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
            >
              <option value="BEGINNER">Başlangıç</option>
              <option value="INTERMEDIATE">Orta</option>
              <option value="ADVANCED">İleri</option>
            </select>
          </div>
        )}

        {/* Add button */}
        {selectedSkillId && (
          <Button
            onClick={handleAddSkill}
            disabled={isAddingSkill}
            className="w-full mb-4"
          >
            {isAddingSkill ? "Ekleniyor..." : messages.profil.addSkillButton}
          </Button>
        )}

        {/* Add error message */}
        {addError && (
          <div
            role="alert"
            aria-live="polite"
            className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600 mb-4"
          >
            {addError}
          </div>
        )}

        {/* Add success message */}
        {addSuccess && (
          <div
            role="status"
            aria-live="polite"
            className="rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-600"
          >
            {addSuccess}
          </div>
        )}
      </div>
    </div>
  );
}
