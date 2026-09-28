import Link from "next/link";
import messages from "@/messages/tr.json";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">{messages.home.title}</h1>
      <p className="text-slate-600">{messages.home.tagline}</p>
      <Link
        href="/giris"
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
      >
        {messages.home.cta}
      </Link>
    </main>
  );
}
