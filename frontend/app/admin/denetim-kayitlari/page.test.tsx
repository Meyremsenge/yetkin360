import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DenetimKayitlariPage from "@/app/admin/denetim-kayitlari/page";
import { useSession } from "@/lib/session/use-session";
import { ApiError } from "@/lib/api/errors";
import * as auditApi from "@/lib/api/admin-audit";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin-audit", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin-audit")>();
  return { ...actual, getAuditEvents: vi.fn() };
});

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DenetimKayitlariPage />
    </QueryClientProvider>
  );
}

const event = {
  id: 2,
  actor_user_id: "11111111-2222-3333-4444-555555555555",
  actor_ip: "203.0.113.7",
  action: "ADMIN_SET_VERIFICATION_LEVEL",
  subject_type: "organization",
  subject_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  result: "SUCCESS",
  metadata: { verification_level: "T3" },
  created_at: "2026-10-01T10:00:00Z",
};

describe("DenetimKayitlariPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: "admin-1", email: "a@test.com", is_platform_admin: true },
        organizations: [],
        institutions: [],
        talent_profile: null,
      },
      error: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
  });
  afterEach(cleanup);

  it("shows loading state", () => {
    vi.mocked(auditApi.getAuditEvents).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("Denetim kayıtları yükleniyor...")).toBeTruthy();
  });

  it("renders rows and tolerates null fields", async () => {
    vi.mocked(auditApi.getAuditEvents).mockResolvedValue({
      items: [
        event,
        {
          ...event,
          id: 1,
          actor_user_id: null,
          actor_ip: null,
          subject_id: null,
          metadata: null,
          created_at: "not-a-date",
        },
      ],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(screen.getAllByText("ADMIN_SET_VERIFICATION_LEVEL").length).toBe(2);
    expect(screen.getByText("Sistem / anonim")).toBeTruthy();
    expect(screen.getByText("203.0.113.7")).toBeTruthy();
    expect(document.body.textContent).not.toContain("null");
    expect(document.body.textContent).not.toContain("Invalid Date");
  });

  it("shows empty state with guidance", async () => {
    vi.mocked(auditApi.getAuditEvents).mockResolvedValue({
      items: [],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/eşleşen kayıt yok/)).toBeTruthy());
  });

  it("shows error alert with retry", async () => {
    vi.mocked(auditApi.getAuditEvents).mockRejectedValue(
      new ApiError({ status: 500, code: "INTERNAL_ERROR", message: "x", requestId: null })
    );
    renderPage();
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(screen.getByRole("button", { name: "Tekrar dene" })).toBeTruthy();
  });

  it("next page requests offset 50 when has_more", async () => {
    vi.mocked(auditApi.getAuditEvents).mockResolvedValue({
      items: [event],
      limit: 50,
      offset: 0,
      has_more: true,
    });
    renderPage();
    const next = await screen.findByRole("button", { name: "Sonraki" });
    await userEvent.click(next);
    await waitFor(() =>
      expect(auditApi.getAuditEvents).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: 50, limit: 50 })
      )
    );
  });

  it("rejects a non-UUID actor filter without calling the API again", async () => {
    vi.mocked(auditApi.getAuditEvents).mockResolvedValue({
      items: [event],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    await screen.findByRole("table");
    const calls = vi.mocked(auditApi.getAuditEvents).mock.calls.length;
    await userEvent.type(screen.getByLabelText("İşlemi yapan kullanıcı kimliği"), "abc");
    await userEvent.click(screen.getByRole("button", { name: "Filtrele" }));
    expect(screen.getByRole("alert").textContent).toContain("UUID");
    expect(vi.mocked(auditApi.getAuditEvents).mock.calls.length).toBe(calls);
  });
});
