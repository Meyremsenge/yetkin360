"use client";

import { KeyboardEvent, ReactNode, useId, useRef, useSyncExternalStore } from "react";
import { useSession } from "@/lib/session/use-session";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { Alert } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import ProfileForm from "./profile-form";
import ProfileHero from "./profile-hero";
import EvidenceSection from "./evidence-section";
import AboutSection from "./about-section";
import PortfolioSection from "./portfolio-section";
import InstitutionLinkSection from "./institution-link-section";
import messages from "@/messages/tr.json";

type TabKey = keyof typeof messages.profil.tabs;

// Follows the chain: who you are → claim vs evidence → verified → own uploads.
const TABS: TabKey[] = ["hakkimda", "yetkinlik", "deneyimler", "sertifikalar"];
const TAB_PARAM = "sekme";

// The active tab lives in ?sekme= so it can be linked and survives a reload.
// Read without next/navigation (page tests mock that module partially).
const tabListeners = new Set<() => void>();

function subscribeTab(onChange: () => void) {
  tabListeners.add(onChange);
  window.addEventListener("popstate", onChange);
  return () => {
    tabListeners.delete(onChange);
    window.removeEventListener("popstate", onChange);
  };
}

function readTab(): TabKey {
  const value = new URLSearchParams(window.location.search).get(TAB_PARAM);
  return TABS.includes(value as TabKey) ? (value as TabKey) : "hakkimda";
}

function selectTab(tab: TabKey) {
  const url = new URL(window.location.href);
  if (tab === "hakkimda") url.searchParams.delete(TAB_PARAM);
  else url.searchParams.set(TAB_PARAM, tab);
  window.history.replaceState(window.history.state, "", url);
  tabListeners.forEach((listener) => listener());
}

function useActiveTab(): TabKey {
  return useSyncExternalStore(subscribeTab, readTab, () => "hakkimda");
}

function ProfileTabs({ active, idPrefix }: { active: TabKey; idPrefix: string }) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Arrow keys move between tabs (WAI-ARIA tabs pattern).
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = TABS[(TABS.indexOf(active) + step + TABS.length) % TABS.length];
    selectTab(next);
    refs.current[next]?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label={messages.profil.tabsLabel}
      onKeyDown={onKeyDown}
      className="mt-8 flex gap-1 overflow-x-auto overflow-y-hidden rounded-lg border border-border bg-muted/60 p-1 [scrollbar-width:none] sm:inline-flex [&::-webkit-scrollbar]:hidden"
    >
      {TABS.map((key) => {
        const selected = active === key;
        return (
          <button
            key={key}
            ref={(node) => {
              refs.current[key] = node;
            }}
            id={`${idPrefix}-tab-${key}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel-${key}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => selectTab(key)}
            className={cn(
              "flex h-9 shrink-0 items-center rounded-md px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
              selected
                ? "bg-card text-foreground shadow-[0_1px_3px_rgba(34,31,27,0.12)]"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {messages.profil.tabs[key]}
          </button>
        );
      })}
    </div>
  );
}

export default function ProfilePage() {
  const session = useSession();
  const activeTab = useActiveTab();
  const idPrefix = useId();

  // AC-12: talent_profile null/eksik dönerse (AppShell zaten oturum/ağ hatalarını kendi
  // içinde yönetiyor — burada SADECE "oturum başarıyla yüklendi ama talent_profile
  // beklenmedik şekilde eksik" durumunu ele alıyoruz)
  const talentProfile = session?.data?.talent_profile;
  const hasValidProfile = talentProfile && typeof talentProfile === "object" && !Array.isArray(talentProfile);

  // Every panel stays mounted (hidden when inactive) so unsaved form input
  // survives a tab switch.
  const panel = (key: TabKey, children: ReactNode) => (
    <div
      key={key}
      id={`${idPrefix}-panel-${key}`}
      role="tabpanel"
      aria-labelledby={`${idPrefix}-tab-${key}`}
      hidden={activeTab !== key}
    >
      {children}
    </div>
  );

  return (
    <AppShell>
      <PageHeader
        eyebrow={messages.shell.groupWork}
        title={messages.profil.title}
        description={messages.profil.pageDescription}
      />
      <PageBody>

        {/* AC-1: Render ProfileForm + SkillsSection if talent_profile is valid */}
        {hasValidProfile ? (
          <>
            <ProfileHero profile={talentProfile as Record<string, unknown>} />
            <ProfileTabs active={activeTab} idPrefix={idPrefix} />

            {panel(
              "hakkimda",
              <div className="grid grid-cols-1 items-start gap-x-6 xl:grid-cols-2">
                <ProfileForm initialData={talentProfile as Record<string, unknown>} />
                <div>
                  <AboutSection
                    initialAbout={((talentProfile as Record<string, unknown>).about as string | null) ?? null}
                  />
                  <InstitutionLinkSection />
                </div>
              </div>
            )}

            {/* One list: grey self-claims and sealed, evidence-backed skills. */}
            {panel("yetkinlik", <EvidenceSection part="signals" />)}

            {panel("deneyimler", <EvidenceSection part="experiences" />)}

            {panel("sertifikalar", <PortfolioSection />)}
          </>
        ) : (
          /* AC-12: Error state when talent_profile is null/undefined */
          <Alert variant="error">
            <div className="font-medium">{messages.profil.loadError}</div>
          </Alert>
        )}
      </PageBody>
    </AppShell>
  );
}
