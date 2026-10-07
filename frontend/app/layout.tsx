import type { Metadata } from "next";
import { IBM_Plex_Sans, Source_Serif_4, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin", "latin-ext"],
  weight: ["500", "600"],
  variable: "--font-source-serif",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin", "latin-ext"],
  weight: ["400"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Yetkin360",
  description: "Kanıta dayalı yetkinlik platformu",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body className={`${plexSans.className} ${plexSans.variable} ${sourceSerif.variable} ${plexMono.variable} bg-background text-foreground antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
