import messages from "@/messages/tr.json";

const t = messages.publicProfile;

/**
 * "Hakkımda" under the hero. The owner's own words: plain text (line breaks kept),
 * a dashed "Kendi beyanı" chip and no seal, so it never reads as a verified record.
 */
export function AboutBlock({ about }: { about: string }) {
  return (
    <section aria-labelledby="about-title" className="y360-rise mt-8 max-w-[640px] print:break-inside-avoid">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="about-title" className="font-serif text-xl font-semibold text-foreground">
          {t.aboutTitle}
        </h2>
        <span className="inline-flex items-center rounded-full border border-dashed border-border bg-sand/60 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
          {t.selfDeclared}
        </span>
      </div>
      <p className="mt-3 whitespace-pre-line text-[16px] leading-relaxed text-foreground">{about}</p>
      <p className="mt-2 text-xs text-muted-foreground">{t.aboutNote}</p>
    </section>
  );
}
