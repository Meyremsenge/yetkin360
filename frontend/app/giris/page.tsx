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
        <h1 className="text-2xl font-bold mb-4 text-slate-900">
          {messages.giris.title}
        </h1>

        {showExpiredMessage && (
          <div
            aria-live="polite"
            className="mb-4 rounded-md bg-yellow-50 border border-yellow-200 p-3 text-sm text-yellow-700"
          >
            {messages.session.expired}
          </div>
        )}

        <LoginForm nextPath={nextPath} />
    </AuthLayout>
  );
}
