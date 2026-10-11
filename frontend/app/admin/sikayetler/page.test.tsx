import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminSikayetlerPage from "@/app/admin/sikayetler/page";
import { adminListComplaints, type AdminComplaint } from "@/lib/api/complaints";

vi.mock("@/components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/lib/api/complaints", () => ({ adminListComplaints: vi.fn() }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AdminSikayetlerPage />
    </QueryClientProvider>,
  );
}

const item = (id: string): AdminComplaint => ({
  id,
  status: "UNDER_REVIEW",
  status_label: "IN_PROGRESS",
  subject_type: "ENGAGEMENT",
  subject_id: "e",
  created_at: "2026-10-01T10:00:00Z",
});

describe("AdminSikayetlerPage", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("status tabs: open queue by default, a tab filters by status and resets paging", async () => {
    vi.mocked(adminListComplaints).mockResolvedValue({ items: [], limit: 50, offset: 0, has_more: false });
    renderPage();
    const open = await screen.findByRole("tab", { name: "Açık" });
    expect(open.getAttribute("aria-selected")).toBe("true");
    await waitFor(() => expect(adminListComplaints).toHaveBeenCalledWith({ limit: 50, offset: 0 }));

    fireEvent.click(screen.getByRole("tab", { name: "Haklı bulunan" }));
    await waitFor(() =>
      expect(adminListComplaints).toHaveBeenCalledWith({ limit: 50, offset: 0, status: "UPHELD" })
    );
    expect(screen.getByRole("tab", { name: "Haklı bulunan" }).getAttribute("aria-selected")).toBe("true");
    expect(await screen.findByText('"Haklı bulunan" sekmesinde şikayet yok.')).toBeTruthy();
  });

  it("shows empty state", async () => {
    vi.mocked(adminListComplaints).mockResolvedValue({ items: [], limit: 50, offset: 0, has_more: false });
    renderPage();
    expect(await screen.findByText("Bekleyen şikayet yok")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Sonraki" })).toBeNull();
  });

  it("shows error alert", async () => {
    vi.mocked(adminListComplaints).mockRejectedValue(new Error("x"));
    renderPage();
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("paginates with has_more and offset", async () => {
    vi.mocked(adminListComplaints).mockImplementation(async ({ offset } = {}) =>
      offset === 50
        ? { items: [item("c2")], limit: 50, offset: 50, has_more: false }
        : { items: [item("c1")], limit: 50, offset: 0, has_more: true },
    );
    renderPage();
    const next = await screen.findByRole("button", { name: "Sonraki" });
    expect((screen.getByRole("button", { name: "Önceki" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(next);
    await waitFor(() => expect(adminListComplaints).toHaveBeenCalledWith({ limit: 50, offset: 50 }));
    await waitFor(() =>
      expect((screen.getByRole("button", { name: "Sonraki" }) as HTMLButtonElement).disabled).toBe(true),
    );
    expect((screen.getByRole("button", { name: "Önceki" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("flags complaints whose subject is no longer pending (AC-21)", async () => {
    vi.mocked(adminListComplaints).mockResolvedValue({
      items: [{ ...item("c1"), subject_still_pending: false }],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    expect(await screen.findByText("Konu artık beklemiyor")).toBeTruthy();
  });
});
