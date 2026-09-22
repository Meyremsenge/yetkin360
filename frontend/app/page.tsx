import { Button } from "@/components/ui/button";
import messages from "@/messages/tr.json";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">{messages.home.title}</h1>
      <p className="text-slate-600">{messages.home.tagline}</p>
      <Button>{messages.home.cta}</Button>
    </main>
  );
}
