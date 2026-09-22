import messages from "@/messages/tr.json";

export default async function LoginPlaceholderPage({
  searchParams,
}: {
  searchParams: Promise<{ neden?: string }>;
}) {
  const params = await searchParams;
  const showExpiredMessage = params.neden === "oturum-bitti";

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full">
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

        <div className="rounded-md bg-slate-50 p-6 border border-slate-200">
          <p className="text-slate-600 text-center">
            {messages.giris.formComingSoon}
          </p>
        </div>
      </div>
    </div>
  );
}
