import Link from "next/link";
import messages from "@/messages/tr.json";
import LoginForm from "./form";
import { AuthLayout } from "@/components/ui/auth-layout";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ neden?: string; next?: string }>;
}) {
  const params = await searchParams;
  const showExpiredMessage = params.neden === "oturum-bitti";
  const nextPath = params.next;

  return (
    <AuthLayout
      brandSentence={messages.authLayout.brandSentence}
      links={[
        { href: "/kayit", label: messages.home.registerLink },
        { href: "/sifre-unuttum", label: messages.authLayout.forgotPasswordLink },
      ]}
    >
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
            <path d="M19 12H5M11 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {messages.giris.backHome}
        </Link>
        <h1 className="font-serif text-[32px] font-semibold leading-tight text-foreground">
          {messages.giris.title}
        </h1>
        <p className="mb-8 mt-2 text-[15px] text-muted-foreground">{messages.giris.subtitle}</p>

        {showExpiredMessage && (
          <div
            aria-live="polite"
            className="mb-6 rounded-md border border-warning/30 bg-warning/10 px-3.5 py-3 text-sm text-warning"
          >
            {messages.session.expired}
          </div>
        )}

        <LoginForm nextPath={nextPath} />
    </AuthLayout>
  );
}
