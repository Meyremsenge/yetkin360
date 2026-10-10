"use client";

import { DirectoryPage, formatDate } from "@/components/admin/directory-page";
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
        { header: m.headers.email, cell: (u) => u.email },
        { header: m.headers.status, cell: (u) => m.statusLabels[u.status] ?? u.status },
        { header: m.headers.role, cell: (u) => (u.is_platform_admin ? m.roleAdmin : m.roleUser) },
        { header: m.headers.emailVerified, cell: (u) => (u.email_verified ? m.yes : m.no) },
        { header: m.headers.createdAt, cell: (u) => formatDate(u.created_at) },
      ]}
    />
  );
}
