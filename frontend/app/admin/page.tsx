"use client";

import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import messages from "@/messages/tr.json";

/**
 * Admin screens listed on the /admin landing page. To add a screen, append a
 * row here (plus its i18n strings) — nothing else on this page changes.
 */
const ADMIN_LINKS: { href: string; label: string; description: string }[] = [
  {
    href: "/admin/dogrulama-kuyrugu",
    label: messages.shell.adminVerificationQueueLink,
    description: messages.adminHome.verificationQueueDescription,
  },
  {
    href: "/admin/skiller",
    label: messages.shell.adminSkillsLink,
    description: messages.adminHome.skillsDescription,
  },
  {
    href: "/admin/sahtekarlik-isaretleri",
    label: messages.shell.adminFraudQueueLink,
    description: messages.adminHome.fraudQueueDescription,
  },
  {
    href: "/admin/sahtekarlik-isaretleri/gecmis",
    label: messages.shell.adminFraudHistoryLink,
    description: messages.adminHome.fraudHistoryDescription,
  },
  {
    href: "/admin/denetim-kayitlari",
    label: messages.shell.adminAuditLink,
    description: messages.adminHome.auditDescription,
  },
  {
    href: "/admin/kullanicilar",
    label: messages.shell.adminUsersLink,
    description: messages.adminUsers.intro,
  },
  {
    href: "/admin/kuruluslar",
    label: messages.shell.adminOrganizationsLink,
    description: messages.adminOrganizations.intro,
  },
  {
    href: "/admin/kurumlar",
    label: messages.shell.adminInstitutionsLink,
    description: messages.adminInstitutions.intro,
  },
];

export default function AdminHomePage() {
  return (
    <AppShell>
      <main className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">{messages.adminHome.title}</h1>
        <p className="text-sm text-slate-600 mb-6">{messages.adminHome.description}</p>
        <ul className="space-y-3">
          {ADMIN_LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="block rounded-lg border border-slate-200 p-4 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
              >
                <span className="block font-medium text-slate-900">{link.label}</span>
                <span className="block text-sm text-slate-600">{link.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      </main>
    </AppShell>
  );
}
