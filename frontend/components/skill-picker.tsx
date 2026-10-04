"use client";

import { useEffect, useRef, useState } from "react";
import { listSkills } from "@/lib/api/client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import messages from "@/messages/tr.json";

interface SkillOption {
  id: string;
  name_tr: string;
}

/**
 * YET-202/ENT-01: Opsiyonel yetkinlik seçimi (teslim/tanıklık formlarında SkillSignal
 * üretimi için). skills-section.tsx'teki debounce+arama desenini taklit eder, ama
 * burada "kendi yetkinliklerim" listesi yok — herhangi bir skill seçilebilir.
 */
export function SkillPicker({
  value,
  onChange,
  label,
}: {
  value: string | null;
  onChange: (skillId: string | null) => void;
  label: string;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SkillOption[] | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    if (!searchQuery.trim()) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }

    const timeout = setTimeout(async () => {
      setIsSearching(true);
      try {
        const result = await listSkills(searchQuery);
        setSearchResults((result?.items as SkillOption[] | undefined) ?? []);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    searchTimeoutRef.current = timeout;
    return () => clearTimeout(timeout);
  }, [searchQuery]);

  const handleSelect = (skill: SkillOption) => {
    setSelectedLabel(skill.name_tr);
    setSearchQuery("");
    setSearchResults(null);
    onChange(skill.id);
  };

  const handleClear = () => {
    setSelectedLabel(null);
    onChange(null);
  };

  return (
    <div>
      <Label>{label}</Label>

      {value && selectedLabel ? (
        <div className="flex items-center justify-between bg-slate-100 rounded-md px-3 py-2 text-sm">
          <span>{selectedLabel}</span>
          <Button type="button" onClick={handleClear} className="bg-slate-500 hover:bg-slate-600 px-2 py-0.5 text-xs">
            {messages.calismalar.clearSkillButton}
          </Button>
        </div>
      ) : (
        <>
          <Input
            type="text"
            placeholder={messages.calismalar.skillSearchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />

          {isSearching && <p className="text-xs text-slate-600 mt-1">{messages.shell.loading}</p>}

          {searchResults && searchResults.length > 0 && (
            <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
              {searchResults.map((skill) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={() => handleSelect(skill)}
                  className="block w-full text-left px-3 py-2 rounded-md text-sm bg-white border border-slate-200 hover:bg-slate-100 text-slate-900"
                >
                  {skill.name_tr}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
