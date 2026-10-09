import messages from "@/messages/tr.json";
import RegisterForm from "./form";
import { AuthLayout } from "@/components/ui/auth-layout";

export default function RegisterPage() {
  return (
    <AuthLayout
      brandSentence={messages.authLayout.brandSentence}
      links={[{ href: "/giris", label: messages.home.loginLink }]}
    >
        <h1 className="text-2xl font-bold mb-4 text-slate-900">
          {messages.kayit.title}
        </h1>

        <RegisterForm />
    </AuthLayout>
  );
}
