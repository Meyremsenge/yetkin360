/**
 * Accounts created by backend/scripts/seed.py (never in production: the seed
 * refuses to run there). The login page lists them only in development or when
 * NEXT_PUBLIC_DEMO_ACCOUNTS=1, so a first-time visitor does not have to register
 * and verify an email address to see the product.
 */
export const DEMO_PASSWORD = "SeedTest123!";

export type DemoRole = "talent" | "orgAdmin" | "approver" | "candidateVerifier" | "institutionAdmin" | "coordinator";

export const DEMO_ACCOUNTS: ReadonlyArray<{ role: DemoRole; email: string }> = [
  { role: "talent", email: "ayse.yilmaz@posta.test" },
  { role: "orgAdmin", email: "murat.demirci@yelkovanyazilim.test" },
  { role: "approver", email: "mehmet.karaca@yelkovanyazilim.test" },
  { role: "candidateVerifier", email: "seda.gurbuz@gundogusuenerji.test" },
  { role: "institutionAdmin", email: "nermin.basaran@cinaralti.edu.test" },
  { role: "coordinator", email: "kerem.taskin@cinaralti.edu.test" },
];

export function demoAccountsEnabled(): boolean {
  return process.env.NODE_ENV === "development" || process.env.NEXT_PUBLIC_DEMO_ACCOUNTS === "1";
}
