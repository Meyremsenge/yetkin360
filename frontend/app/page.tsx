import Link from "next/link";
import messages from "@/messages/tr.json";
import { Card } from "@/components/ui/card";
import { ChainProgress } from "@/components/ui/chain-progress";
import { VerifiedSeal } from "@/components/ui/verified-seal";

const { home } = messages;

const chainSteps = [
  { label: home.chain.claim, completed: false },
  { label: home.chain.evidence, completed: false },
  { label: home.chain.attestation, completed: false },
  { label: home.chain.verified, completed: true },
];

const personas = [home.personas.student, home.personas.organization, home.personas.institution];

const linkClass =
  "rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success";

export default function Home() {
  return (
    <>
      <header className="mx-auto flex max-w-6xl items-center justify-between border-b border-border px-4 py-5 md:px-8">
        <span className="font-serif text-xl font-bold">{home.title}</span>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/giris" className={`${linkClass} text-muted-foreground hover:text-foreground`}>
            {home.loginLink}
          </Link>
          <Link href="/kayit" className={`${linkClass} font-medium hover:text-success`}>
            {home.registerLink}
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 md:px-8">
        <section className="grid grid-cols-1 items-center gap-12 py-16 md:grid-cols-[7fr_5fr]">
          <div>
            <h1 className="font-serif text-4xl leading-tight md:text-5xl">{home.heroTitle}</h1>
            <p className="mt-6 text-lg text-muted-foreground">{home.heroDescription}</p>
            <p className="mt-4 font-mono text-sm text-muted-foreground">{home.tagline}</p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                href="/kayit"
                className={`${linkClass} inline-block bg-success px-6 py-3 text-base font-medium text-background hover:opacity-90`}
              >
                {home.registerLink}
              </Link>
              <Link
                href="/giris"
                className={`${linkClass} inline-block border border-success px-6 py-3 text-base font-medium text-success hover:bg-success/10`}
              >
                {home.secondaryCta}
              </Link>
            </div>
          </div>
          <div>
            <Card className="-rotate-1 p-8">
              <VerifiedSeal />
            </Card>
            <p className="mt-4 text-sm text-muted-foreground">{home.sealCaption}</p>
          </div>
        </section>

        <section className="border-t border-border py-16">
          <h2 className="font-serif text-2xl">{home.chainTitle}</h2>
          <div className="mt-8">
            <ChainProgress steps={chainSteps} />
          </div>
        </section>

        <section className="max-w-3xl border-t border-border py-16">
          <h2 className="font-serif text-2xl">{home.comparisonTitle}</h2>
          <p className="mt-6 text-lg text-muted-foreground">{home.comparisonClaim}</p>
          <p className="mt-4 text-lg">{home.comparisonVerified}</p>
        </section>

        <section className="border-t border-border py-16">
          <h2 className="font-serif text-2xl">{home.personasTitle}</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {personas.map((persona) => (
              <Card key={persona.title}>
                <h3 className="font-serif text-xl">{persona.title}</h3>
                <p className="mt-3 text-muted-foreground">{persona.description}</p>
              </Card>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-4 py-8 text-sm text-muted-foreground md:px-8">
        <p className="mx-auto max-w-6xl">{home.footerNote}</p>
      </footer>
    </>
  );
}
