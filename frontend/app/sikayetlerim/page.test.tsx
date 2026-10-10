import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SikayetlerimPage from "@/app/sikayetlerim/page";
import { listComplaints, type Complaint } from "@/lib/api/complaints";

vi.mock("@/components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/lib/api/complaints", () => ({ listComplaints: vi.fn() }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SikayetlerimPage />
    </QueryClientProvider>,
  );
}

const base: Complaint = {
  id: "c1",
  status_label: "IN_PROGRESS",
  subject_type: "ENGAGEMENT",
  subject_id: "e1",
  created_at: "2026-10-01T10:00:00Z",
};

describe("SikayetlerimPage", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("shows the loading state", () => {
    vi.mocked(listComplaints).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("Şikayetler yükleniyor...")).toBeTruthy();
  });

  it("shows an alert on error", async () => {
    vi.mocked(listComplaints).mockRejectedValue(new Error("x"));
    renderPage();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("yüklenemedi");
  });

  it("shows an actionable empty state", async () => {
    vi.mocked(listComplaints).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("Henüz şikayetiniz yok")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Çalışmalarım" })).toBeTruthy();
  });

  it("open complaint shows only 'İşlem devam etmekte', never internal status or admin note", async () => {
    vi.mocked(listComplaints).mockResolvedValue([
      { ...base, status: "ESCALATED", admin_note: "gizli yönetici notu", viewer_role: "OWNER" },
    ]);
    renderPage();
    expect(await screen.findByText("İşlem devam etmekte")).toBeTruthy();
    expect(screen.queryByText(/Yükseltildi/)).toBeNull();
    expect(screen.queryByText(/gizli yönetici notu/)).toBeNull();
  });

  it("terminal complaint shows its label", async () => {
    vi.mocked(listComplaints).mockResolvedValue([{ ...base, status_label: "UPHELD" }]);
    renderPage();
    expect(await screen.findByText("Haklı bulundu")).toBeTruthy();
  });

  it("is null-safe for missing dates and labels", async () => {
    vi.mocked(listComplaints).mockResolvedValue([
      { ...base, created_at: null, subject_label: null } as Complaint,
    ]);
    const { container } = renderPage();
    await waitFor(() => expect(screen.getByText("İşlem devam etmekte")).toBeTruthy());
    expect(container.textContent).not.toMatch(/null|Invalid Date|undefined/);
  });
});
