"use client";

import { useSession } from "@/lib/session/use-session";
import { AppShell } from "@/components/app-shell";
import { Alert } from "@/components/ui/alert";
import ProfileForm from "./profile-form";
import ProfileHero from "./profile-hero";
import SkillsSection from "./skills-section";
import EvidenceSection from "./evidence-section";
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
      <div className="max-w-[960px] px-4 py-8 md:px-6 lg:px-10">
        <h1 className="font-serif text-3xl font-semibold text-foreground">{messages.profil.title}</h1>

        {/* AC-1: Render ProfileForm + SkillsSection if talent_profile is valid */}
        {hasValidProfile ? (
          <>
            <ProfileHero profile={talentProfile as Record<string, unknown>} />
            <ProfileForm initialData={talentProfile as Record<string, unknown>} />
            <SkillsSection />
            <EvidenceSection />
            <InstitutionLinkSection />
          </>
        ) : (
          /* AC-12: Error state when talent_profile is null/undefined */
          <Alert variant="error" className="mt-6">
            <div className="font-medium">{messages.profil.loadError}</div>
          </Alert>
        )}
      </div>
    </AppShell>
  );
}
