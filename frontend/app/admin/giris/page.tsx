import messages from "@/messages/tr.json";
import LoginForm from "@/app/giris/form";
import { AuthLayout } from "@/components/ui/auth-layout";

/**
 * Separate sign-in entry for platform admins. It calls the same
 * POST /auth/login as /giris; the form's `adminOnly` mode signs a non-admin
 * straight back out. Not a security boundary — /admin/* is gated on the server.
 */
export default async function AdminLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ neden?: string; next?: string }>;
}) {
  const params = await searchParams;
  const showExpiredMessage = params.neden === "oturum-bitti";

  return (
    <AuthLayout
      brandSentence={messages.adminGiris.brandSentence}
      links={[{ href: "/giris", label: messages.adminGiris.userLoginLink }]}
    >
      <h1 className="font-serif text-[32px] font-semibold leading-tight text-foreground">
        {messages.adminGiris.title}
      </h1>
      <p className="mb-8 mt-2 text-[15px] text-muted-foreground">{messages.adminGiris.subtitle}</p>

      {showExpiredMessage && (
        <div
          aria-live="polite"
          className="mb-6 rounded-md border border-warning/30 bg-warning/10 px-3.5 py-3 text-sm text-warning"
        >
          {messages.session.expired}
        </div>
      )}

      <LoginForm nextPath={params.next} adminOnly />
    </AuthLayout>
  );
}
