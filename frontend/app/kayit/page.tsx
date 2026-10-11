import messages from "@/messages/tr.json";
import RegisterForm from "./form";
import { AuthLayout } from "@/components/ui/auth-layout";
import { DemoAccountsLink } from "@/components/ui/demo-accounts-link";
import { demoAccountsEnabled } from "@/lib/demo-accounts";

export default function RegisterPage() {
  const demo = demoAccountsEnabled();
  return (
    <AuthLayout
      brandSentence={messages.authLayout.brandSentence}
      links={[{ href: "/giris", label: messages.home.loginLink }]}
    >
        <h1 className="text-2xl font-bold mb-4 text-slate-900">
          {messages.kayit.title}
        </h1>

        {demo && (
          <div className="mb-6">
            <p className="mb-2 text-sm text-muted-foreground">{messages.kayit.demoNotice}</p>
            <DemoAccountsLink />
          </div>
        )}

        <RegisterForm showLocalEmailHint={demo} />
    </AuthLayout>
  );
}
