import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Yetkin360",
  description: "Kanıta dayalı yetkinlik platformu",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
