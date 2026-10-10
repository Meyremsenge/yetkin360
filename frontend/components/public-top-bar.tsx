import Link from "next/link";
import messages from "@/messages/tr.json";
import { SealMark } from "@/components/brand/brand-mark";

export const publicFocusRing =
  "rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";

export function PublicTopBar({ label }: { label: string }) {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 md:px-8">
        <Link
          href="/"
          className={`inline-flex items-center gap-2 font-serif text-lg font-bold text-foreground ${publicFocusRing}`}
        >
          <SealMark className="h-6 w-6" />
          {messages.home.title}
        </Link>
        <span className="text-[13px] text-muted-foreground">{label}</span>
      </div>
    </header>
  );
}
