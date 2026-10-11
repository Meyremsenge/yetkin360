"use client";

import Link from "next/link";
import { AppShell, Icon } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { ADMIN_NAV_GROUPS } from "@/components/admin/admin-nav";
import messages from "@/messages/tr.json";

/** /admin overview: every admin screen as a card, grouped like the sidebar. */
export default function AdminHomePage() {
  return (
    <AppShell>
      <main>
        <PageHeader
          eyebrow={messages.shell.groupAdmin}
          title={messages.adminHome.title}
          description={messages.adminHome.description}
        />
        <PageBody className="space-y-10">
          {ADMIN_NAV_GROUPS.map((group, index) => (
            <section key={group.label} aria-labelledby={`admin-group-${index}`}>
              <div className="mb-4 border-b border-border pb-2">
                <h2
                  id={`admin-group-${index}`}
                  className="font-serif text-xl font-semibold text-foreground"
                >
                  {group.label}
                </h2>
                <p className="mt-0.5 text-sm text-muted-foreground">{group.description}</p>
              </div>
              <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {group.items.map((item) => (
                  <li key={item.href} className="flex">
                    <Link
                      href={item.href}
                      className="group flex w-full items-start gap-3 rounded-lg border border-border bg-card p-4 transition-colors duration-[120ms] hover:border-success/40 hover:bg-success/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground transition-colors group-hover:border-success/30 group-hover:text-success">
                        <Icon name={item.icon} />
                      </span>
                      <span className="min-w-0">
                        <span className="block font-medium text-foreground">{item.label}</span>
                        <span className="mt-0.5 block text-sm leading-5 text-muted-foreground">
                          {item.description}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </PageBody>
      </main>
    </AppShell>
  );
}
