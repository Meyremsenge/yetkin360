import messages from "@/messages/tr.json";

/**
 * Single source for admin navigation: the admin sidebar (AppShell) and the
 * /admin overview cards both render these groups. To add a screen, append an
 * item here (plus its i18n strings).
 */

export type AdminNavIcon =
  | "overview"
  | "shield"
  | "inbox"
  | "flag"
  | "history"
  | "users"
  | "building"
  | "landmark"
  | "tag"
  | "scroll";

export type AdminNavItem = {
  href: string;
  label: string;
  description: string;
  icon: AdminNavIcon;
};

export type AdminNavGroup = { label: string; description: string; items: AdminNavItem[] };

export const ADMIN_HOME_HREF = "/admin";

export const ADMIN_OVERVIEW: AdminNavItem = {
  href: ADMIN_HOME_HREF,
  label: messages.shell.adminOverviewLink,
  description: messages.adminHome.description,
  icon: "overview",
};

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    label: messages.shell.adminGroupReview,
    description: messages.adminHome.reviewDescription,
    items: [
      {
        href: "/admin/dogrulama-kuyrugu",
        label: messages.shell.adminVerificationQueueLink,
        description: messages.adminHome.verificationQueueDescription,
        icon: "shield",
      },
      {
        href: "/admin/sikayetler",
        label: messages.adminComplaints.navLink,
        description: messages.adminHome.complaintsDescription,
        icon: "inbox",
      },
      {
        href: "/admin/sahtekarlik-isaretleri",
        label: messages.shell.adminFraudQueueLink,
        description: messages.adminHome.fraudQueueDescription,
        icon: "flag",
      },
      {
        href: "/admin/sahtekarlik-isaretleri/gecmis",
        label: messages.shell.adminFraudHistoryLink,
        description: messages.adminHome.fraudHistoryDescription,
        icon: "history",
      },
    ],
  },
  {
    label: messages.shell.adminGroupDirectory,
    description: messages.adminHome.directoryDescription,
    items: [
      {
        href: "/admin/kullanicilar",
        label: messages.shell.adminUsersLink,
        description: messages.adminUsers.intro,
        icon: "users",
      },
      {
        href: "/admin/kuruluslar",
        label: messages.shell.adminOrganizationsLink,
        description: messages.adminOrganizations.intro,
        icon: "building",
      },
      {
        href: "/admin/kurumlar",
        label: messages.shell.adminInstitutionsLink,
        description: messages.adminInstitutions.intro,
        icon: "landmark",
      },
    ],
  },
  {
    label: messages.shell.adminGroupSystem,
    description: messages.adminHome.systemDescription,
    items: [
      {
        href: "/admin/skiller",
        label: messages.shell.adminSkillsLink,
        description: messages.adminHome.skillsDescription,
        icon: "tag",
      },
      {
        href: "/admin/denetim-kayitlari",
        label: messages.shell.adminAuditLink,
        description: messages.adminHome.auditDescription,
        icon: "scroll",
      },
    ],
  },
];

/**
 * The nav item to highlight for `pathname`: the longest matching href, so
 * /admin/sahtekarlik-isaretleri/gecmis highlights "İşaret Geçmişi" only.
 * The overview matches /admin exactly.
 */
export function activeAdminHref(pathname: string): string | null {
  if (pathname === ADMIN_HOME_HREF || pathname === `${ADMIN_HOME_HREF}/`) return ADMIN_HOME_HREF;
  let best: string | null = null;
  for (const group of ADMIN_NAV_GROUPS) {
    for (const item of group.items) {
      const matches = pathname === item.href || pathname.startsWith(`${item.href}/`);
      if (matches && (best === null || item.href.length > best.length)) best = item.href;
    }
  }
  return best;
}
