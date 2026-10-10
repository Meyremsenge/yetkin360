import type { Metadata } from "next";
import type { ReactNode } from "react";
import messages from "@/messages/tr.json";

const t = messages.publicProfile;
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Title / description / Open Graph for shared profile links. Uses only the
 * public, auth-free endpoint; any failure falls back to a generic title so the
 * page itself (client-rendered) is never blocked by metadata.
 */
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  let name: string | null = null;
  try {
    const response = await fetch(`${BASE_URL}/public/talents/${encodeURIComponent(slug)}`, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(3000),
    });
    if (response.ok) {
      const body = (await response.json()) as { display_name?: unknown };
      if (typeof body.display_name === "string" && body.display_name.trim()) name = body.display_name;
    }
  } catch {
    name = null;
  }

  if (!name) {
    return { title: t.metaFallbackTitle, robots: { index: false } };
  }
  const title = t.metaTitle.replace("{name}", name);
  const description = t.metaDescription.replace("{name}", name);
  return {
    title,
    description,
    openGraph: { title, description, type: "profile", locale: "tr_TR", siteName: messages.home.title },
    twitter: { card: "summary", title, description },
  };
}

export default function PublicProfileLayout({ children }: { children: ReactNode }) {
  return children;
}
