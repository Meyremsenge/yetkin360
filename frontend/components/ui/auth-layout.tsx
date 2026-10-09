import Link from "next/link";
import messages from "@/messages/tr.json";
import { ChainProgress } from "./chain-progress";

const { home } = messages;

const CHAIN_STEPS = [
  { label: home.chain.claim, completed: false },
  { label: home.chain.evidence, completed: false },
  { label: home.chain.attestation, completed: false },
  { label: home.chain.verified, completed: true },
];

interface AuthLayoutProps {
  brandSentence: string;
  links?: { href: string; label: string }[];
  children: React.ReactNode;
}

export function AuthLayout({ brandSentence, links, children }: AuthLayoutProps) {
  return (
    <div className="grid grid-cols-1 min-h-screen md:grid-cols-[2fr_3fr]">
      <div className="flex flex-col gap-8 bg-sand p-6 md:p-10">
        <p className="font-serif text-2xl">{home.title}</p>
        <p className="font-serif text-lg md:text-xl">{brandSentence}</p>
        <div className="hidden md:block">
          <ChainProgress steps={CHAIN_STEPS} />
        </div>
        {links && links.length > 0 && (
          <nav aria-label="Auth bağlantıları" className="flex flex-wrap gap-4 text-sm">
            {links.map((link) => (
              <Link key={link.href} href={link.href} className="underline underline-offset-4">
                {link.label}
              </Link>
            ))}
          </nav>
        )}
      </div>
      <div className="flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
