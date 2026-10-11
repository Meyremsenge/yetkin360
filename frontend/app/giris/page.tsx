import Link from "next/link";
import messages from "@/messages/tr.json";
import LoginForm from "./form";
import { AuthLayout } from "@/components/ui/auth-layout";
import { demoAccountsEnabled } from "@/lib/demo-accounts";

const footerLinkClass =
  "underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success";

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

        <LoginForm
          nextPath={nextPath}
          showDemoAccounts={demoAccountsEnabled()}
          footer={
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-sm">
              <p className="text-muted-foreground">
                {messages.loginDialog.noAccount}{" "}
                <Link href="/kayit" className={`font-medium text-success ${footerLinkClass}`}>
                  {messages.home.registerLink}
                </Link>
              </p>
              <div className="flex items-center gap-4">
                <Link href="/sifre-unuttum" className={`text-muted-foreground hover:text-foreground ${footerLinkClass}`}>
                  {messages.authLayout.forgotPasswordLink}
                </Link>
                <Link href="/admin/giris" className={`text-muted-foreground hover:text-foreground ${footerLinkClass}`}>
                  {messages.adminGiris.linkFromLogin}
                </Link>
              </div>
            </div>
          }
        />
    </AuthLayout>
  );
}
