import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">Yetkin360</h1>
      <p className="text-slate-600">beyan → kanıt → tanıklık → doğrulanmış deneyim</p>
      <Button>Başla</Button>
    </main>
  );
}
