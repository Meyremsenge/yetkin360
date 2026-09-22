"use client";

import { useSession } from "@/lib/session/use-session";
import { AppShell } from "@/components/app-shell";
import ProfileForm from "./profile-form";
import SkillsSection from "./skills-section";
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
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.profil.title}</h1>

        {/* AC-1: Render ProfileForm + SkillsSection if talent_profile is valid */}
        {hasValidProfile ? (
          <>
            <ProfileForm initialData={talentProfile as Record<string, unknown>} />
            <div className="mt-8">
              <SkillsSection />
            </div>
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
