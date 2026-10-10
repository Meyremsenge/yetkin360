import { SealMark } from "@/components/brand/brand-mark";
import type { PublicProfile } from "@/lib/api/public";
import messages from "@/messages/tr.json";
import { QrCode } from "./qr-code";
import { ShareActions } from "./share-actions";

const t = messages.publicProfile;

/**
 * Sticky "registry card" beside the profile: always-visible QR, the real
 * counts, copy link and print. Below the hero on narrow screens.
 */
export function ProfileCard({ profile, url }: { profile: PublicProfile; url: string }) {
  const hasExperiences = profile.verified_experiences.length > 0;
  const stats = [
    { value: profile.verified_experiences.length, label: t.statExperiences },
    { value: profile.skills?.length ?? 0, label: t.statSkills },
    { value: profile.attesting_organization_count ?? 0, label: t.statOrganizations },
  ];

  return (
    <div className="y360-rise rounded-xl border border-border bg-card print:hidden">
      <div className="flex items-center gap-2 border-b border-border px-5 py-3">
        <SealMark className="h-5 w-5" />
        <p className="font-mono text-xs text-muted-foreground">{t.cardTitle}</p>
      </div>

      {hasExperiences ? (
        <dl aria-label={t.statsLabel} className="grid grid-cols-3 divide-x divide-border border-b border-border lg:grid-cols-1 lg:divide-x-0 lg:divide-y">
          {stats.map((stat) => (
            <div key={stat.label} className="flex flex-col items-center gap-1 px-2 py-4 text-center lg:flex-row lg:items-baseline lg:gap-3 lg:px-5 lg:py-3 lg:text-left">
              <dd className="font-serif text-[28px] font-semibold leading-none tabular-nums text-foreground lg:w-10">
                {stat.value}
              </dd>
              <dt className="text-xs text-muted-foreground lg:text-[13px]">{stat.label}</dt>
            </div>
          ))}
        </dl>
      ) : null}

      <div className="flex items-center gap-4 px-5 py-4 lg:flex-col lg:items-stretch">
        <QrCode
          value={url}
          label={t.qrLabel.replace("{name}", profile.display_name)}
          className="h-24 w-24 shrink-0 rounded-md border border-border p-1 lg:mx-auto lg:h-40 lg:w-40"
        />
        <div className="min-w-0 lg:text-center">
          <p className="text-sm font-semibold text-foreground">{t.qrTitle}</p>
          <p className="mt-1 text-[13px] text-muted-foreground">{t.qrHint}</p>
        </div>
      </div>

      <div className="space-y-3 border-t border-border px-5 py-4">
        <ShareActions url={url} />
        <p className="break-all font-mono text-[11px] text-muted-foreground">{url}</p>
      </div>
    </div>
  );
}
