import messages from "@/messages/tr.json";
import RegisterForm from "./form";
import Link from "next/link";
import { AuthLayout } from "@/components/ui/auth-layout";
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
          <p className="mb-6 rounded-md border border-border bg-card px-3.5 py-3 text-sm text-muted-foreground">
            {messages.kayit.demoNotice}{" "}
            <Link href="/giris" className="font-medium text-foreground underline underline-offset-2">
              {messages.home.loginLink}
            </Link>
          </p>
        )}

        <RegisterForm showLocalEmailHint={demo} />
    </AuthLayout>
  );
}
