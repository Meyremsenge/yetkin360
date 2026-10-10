"use client";

import { useSession } from "@/lib/session/use-session";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { Alert } from "@/components/ui/alert";
import ProfileForm from "./profile-form";
import ProfileHero from "./profile-hero";
import SkillsSection from "./skills-section";
import EvidenceSection from "./evidence-section";
import AboutSection from "./about-section";
import PortfolioSection from "./portfolio-section";
import InstitutionLinkSection from "./institution-link-section";
import messages from "@/messages/tr.json";

export default function ProfilePage() {
  const session = useSession();

  // AC-12: talent_profile null/eksik dönerse (AppShell zaten oturum/ağ hatalarını kendi
  // içinde yönetiyor — burada SADECE "oturum başarıyla yüklendi ama talent_profile
  // beklenmedik şekilde eksik" durumunu ele alıyoruz)
  const talentProfile = session?.data?.talent_profile;
  const hasValidProfile = talentProfile && typeof talentProfile === "object" && !Array.isArray(talentProfile);

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
            {/* Two columns on wide screens: editable identity left, evidence right. */}
            <div className="grid grid-cols-1 items-start gap-x-6 xl:grid-cols-2">
              <div>
                <ProfileForm initialData={talentProfile as Record<string, unknown>} />
                <AboutSection initialAbout={((talentProfile as Record<string, unknown>).about as string | null) ?? null} />
                <SkillsSection />
              </div>
              <div>
                <EvidenceSection />
                <PortfolioSection />
                <InstitutionLinkSection />
              </div>
            </div>
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
