import messages from "@/messages/tr.json";
import RegisterForm from "./form";

export default function RegisterPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full px-4">
        <h1 className="text-2xl font-bold mb-4 text-slate-900">
          {messages.kayit.title}
        </h1>

        <RegisterForm />
      </div>
    </div>
  );
}
