import messages from "@/messages/tr.json";
import LoginForm from "./form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ neden?: string; next?: string }>;
}) {
  const params = await searchParams;
  const showExpiredMessage = params.neden === "oturum-bitti";
  const nextPath = params.next;

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full px-4">
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
      </div>
    </div>
  );
}
