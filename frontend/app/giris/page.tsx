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
