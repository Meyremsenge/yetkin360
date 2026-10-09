import Link from "next/link";
import messages from "@/messages/tr.json";
import { StatusPageFrame, primaryLinkClass, outlineLinkClass } from "./status-page-frame";

export default function NotFound() {
  return (
    <StatusPageFrame>
      {/* Empty, dashed seal: nothing was issued here */}
      <span
        aria-hidden="true"
        className="flex h-16 w-16 items-center justify-center rounded-full border border-dashed border-muted-foreground text-muted-foreground"
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.5}>
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      </span>

      <h1 className="mt-6 font-serif text-3xl font-semibold text-foreground">
        {messages.notFound.title}
      </h1>

      <p className="mt-2 text-[15px] text-muted-foreground">{messages.notFound.description}</p>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link href="/" className={primaryLinkClass}>
          {messages.notFound.home}
        </Link>
        <Link href="/giris" className={outlineLinkClass}>
          {messages.notFound.login}
        </Link>
      </div>
    </StatusPageFrame>
  );
}
