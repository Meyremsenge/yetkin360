import Link from "next/link";
import messages from "@/messages/tr.json";

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md text-center">
        <h1 className="text-3xl font-bold mb-4 text-slate-900">
          {messages.notFound.title}
        </h1>

        <p className="text-slate-600 mb-6">
          {messages.notFound.description}
        </p>

        <div className="flex flex-col gap-3">
          <Link
            href="/"
            className="inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            {messages.notFound.home}
          </Link>
          <Link
            href="/giris"
            className="inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            {messages.notFound.login}
          </Link>
        </div>
      </div>
    </div>
  );
}
