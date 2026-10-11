"use client";

import { DirectoryPage, formatDate } from "@/components/admin/directory-page";
import { statusTone } from "@/components/admin/admin-ui";
import { StatusPill } from "@/components/panel-kit";
import { listUsers, type AdminUser } from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

const m = messages.adminUsers;

export default function KullanicilarPage() {
  return (
    <DirectoryPage<AdminUser>
      kind="users"
      m={m}
      fetchPage={listUsers}
      rowLabel={(u) => u.email}
      statusOptions={["ACTIVE", "PENDING", "SUSPENDED", "DELETED"]}
      inactionableStatuses={["DELETED"]}
      conflictMessage={(err) => (err.code === "LAST_ADMIN_PROTECTED" ? m.lastAdmin : null)}
      columns={[
        { header: m.headers.email, cell: (u) => <span className="font-medium">{u.email}</span> },
        {
          header: m.headers.status,
          cell: (u) => <StatusPill tone={statusTone(u.status)}>{m.statusLabels[u.status] ?? u.status}</StatusPill>,
        },
        { header: m.headers.role, cell: (u) => (u.is_platform_admin ? m.roleAdmin : m.roleUser) },
        {
          header: m.headers.emailVerified,
          cell: (u) => <span className={u.email_verified ? undefined : "text-muted-foreground"}>{u.email_verified ? m.yes : m.no}</span>,
        },
        { header: m.headers.createdAt, cell: (u) => formatDate(u.created_at) },
      ]}
    />
  );
}
