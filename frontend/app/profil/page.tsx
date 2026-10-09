"use client";

import { useState } from "react";
import Link from "next/link";
import { useSession } from "@/lib/session/use-session";
import { AppShell } from "@/components/app-shell";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabPanel } from "@/components/ui/tabs";
import ProfileForm from "./profile-form";
import SkillsSection from "./skills-section";
import EvidenceSection from "./evidence-section";
import InstitutionLinkSection from "./institution-link-section";
import messages from "@/messages/tr.json";

const TABS = [
  { id: "info", label: messages.profil.tabProfileInfo },
  { id: "skills", label: messages.profil.tabSkills },
  { id: "evidence", label: messages.profil.tabEvidence },
  { id: "institution", label: messages.profil.tabInstitution },
];

export default function ProfilePage() {
  const session = useSession();
  const [copied, setCopied] = useState(false);

  // AC-12: talent_profile null/eksik dönerse (AppShell zaten oturum/ağ hatalarını kendi
  // içinde yönetiyor — burada SADECE "oturum başarıyla yüklendi ama talent_profile
  // beklenmedik şekilde eksik" durumunu ele alıyoruz)
  const talentProfile = session?.data?.talent_profile;
  const hasValidProfile = talentProfile && typeof talentProfile === "object" && !Array.isArray(talentProfile);
  const profile = (hasValidProfile ? talentProfile : {}) as Record<string, unknown>;

  const displayName = (session?.data?.user?.full_name as string | undefined) || (session?.data?.user?.email as string | undefined) || "?";
  const metaParts = [profile.headline, profile.department, profile.city].filter(
    (v): v is string => typeof v === "string" && v.length > 0
  );
  const visibility = profile.visibility as string | null | undefined;
  const publicSlug = profile.public_slug as string | null | undefined;
  const isPublicWithSlug = visibility === "PUBLIC" && Boolean(publicSlug);
  const publicUrl = isPublicWithSlug && typeof window !== "undefined" ? `${window.location.origin}/p/${publicSlug}` : "";

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(publicUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Panoya erişim reddedilirse sessizce yok say — kritik bir aksiyon değil.
    }
  };

  return (
    <AppShell>
      <div className="p-6 max-w-4xl mx-auto">
        {hasValidProfile ? (
          <>
            <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
              <div className="flex items-center gap-4">
                <Avatar name={displayName} />
                <div>
                  <h1 className="font-serif text-2xl font-semibold text-foreground">{displayName}</h1>
                  {metaParts.length > 0 && (
                    <p className="text-sm text-muted-foreground mt-1">{metaParts.join(" · ")}</p>
                  )}
                  {visibility && (
                    <Badge className="mt-2" variant={visibility === "PUBLIC" ? "success" : "default"}>
                      {messages.profil.visibilityLabels[visibility as keyof typeof messages.profil.visibilityLabels] ?? visibility}
                    </Badge>
                  )}
                </div>
              </div>
              {isPublicWithSlug && (
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    href={`/p/${publicSlug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center rounded-md border border-success px-4 py-2 text-sm font-medium text-success hover:bg-success/10"
                  >
                    {messages.profil.viewPublicProfileButton}
                  </Link>
                  <Button
                    type="button"
                    onClick={handleCopyLink}
                    className="bg-transparent text-muted-foreground hover:text-foreground hover:bg-muted"
                  >
                    {copied ? messages.profil.linkCopiedMessage : messages.profil.copyLinkButton}
                  </Button>
                </div>
              )}
            </Card>

            <Tabs tabs={TABS} defaultTabId="info">
              {(activeTabId) => (
                <>
                  <TabPanel id="info" activeTabId={activeTabId}>
                    <ProfileForm initialData={profile} />
                  </TabPanel>
                  <TabPanel id="skills" activeTabId={activeTabId}>
                    <SkillsSection />
                  </TabPanel>
                  <TabPanel id="evidence" activeTabId={activeTabId}>
                    <EvidenceSection />
                  </TabPanel>
                  <TabPanel id="institution" activeTabId={activeTabId}>
                    <InstitutionLinkSection />
                  </TabPanel>
                </>
              )}
            </Tabs>
          </>
        ) : (
          /* AC-12: Error state when talent_profile is null/undefined */
          <div
            role="alert"
            className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
          >
            <div className="font-medium">{messages.profil.loadError}</div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
