"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TabDefinition {
  id: string;
  label: string;
}

/**
 * Brif §2.9: sola hizalı sekmeler, altında tam genişlik çizgi, seçili sekme
 * 2px pine alt çizgi. Panel'lerin hepsi DOM'da kalır (yalnız CSS ile
 * gizlenir) ki içindeki bileşenler mount/unmount olmasın.
 */
export function Tabs({
  tabs,
  defaultTabId,
  children,
}: {
  tabs: TabDefinition[];
  defaultTabId: string;
  children: (activeTabId: string) => ReactNode;
}) {
  const [activeTabId, setActiveTabId] = useState(defaultTabId);

  return (
    <div>
      <div role="tablist" className="flex gap-6 border-b border-border overflow-x-auto">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTabId;
          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              aria-selected={isActive}
              onClick={() => setActiveTabId(tab.id)}
              className={cn(
                "shrink-0 px-1 pb-3 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors",
                isActive
                  ? "border-success text-foreground font-medium"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div className="pt-6">{children(activeTabId)}</div>
    </div>
  );
}

export function TabPanel({
  id,
  activeTabId,
  children,
}: {
  id: string;
  activeTabId: string;
  children: ReactNode;
}) {
  return (
    <div role="tabpanel" hidden={id !== activeTabId}>
      {children}
    </div>
  );
}
