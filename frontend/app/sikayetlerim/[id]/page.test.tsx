import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SikayetDetayPage from "@/app/sikayetlerim/[id]/page";
import { getComplaint, submitExplanation, type Complaint } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "c1" }) }));
vi.mock("@/components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/lib/api/complaints", async (orig) => {
  const actual = await orig<typeof import("@/lib/api/complaints")>();
  return { ...actual, getComplaint: vi.fn(), submitExplanation: vi.fn() };
});

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SikayetDetayPage />
    </QueryClientProvider>,
  );
}

const base: Complaint = {
  id: "c1",
  status_label: "IN_PROGRESS",
  subject_type: "ENGAGEMENT",
  subject_id: "e1",
  created_at: "2026-10-01T10:00:00Z",
  description: "Yanıt yok",
};

describe("SikayetDetayPage", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("shows not-found on 404 without leaking details", async () => {
    vi.mocked(getComplaint).mockRejectedValue(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null }),
    );
    renderPage();
    expect((await screen.findByRole("alert")).textContent).toContain("bulunamadı");
  });

  it("student sees in-progress note and attachment link; no admin note", async () => {
    vi.mocked(getComplaint).mockResolvedValue({
      ...base,
      viewer_role: "OWNER",
      admin_note: "gizli",
      attachments: [{ id: "f1", filename: "kanit.pdf" }],
    });
    renderPage();
    expect(await screen.findByText(/İşleminiz inceleniyor/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "kanit.pdf" })).toBeTruthy();
    expect(screen.queryByText("gizli")).toBeNull();
  });

  it("terminal complaint shows result and the admin reason", async () => {
    vi.mocked(getComplaint).mockResolvedValue({
      ...base,
      status_label: "UPHELD",
      result_reason: "Yetkili yanıt vermedi.",
      closed_at: null,
    });
    renderPage();
    expect(await screen.findByText("Yetkili yanıt vermedi.")).toBeTruthy();
    expect(screen.getAllByText("Haklı bulundu").length).toBeGreaterThan(0);
  });

  it("respondent sees admin note, writes an explanation, and gets no attachment links", async () => {
    vi.mocked(getComplaint).mockResolvedValue({
      ...base,
      viewer_role: "RESPONDENT",
      status: "EXPLANATION_REQUESTED",
      admin_note: "Lütfen gerekçenizi yazın",
      attachments: [{ id: "f1", filename: "kanit.pdf" }],
    });
    vi.mocked(submitExplanation).mockResolvedValue({ ...base });
    renderPage();
    expect(await screen.findByText("Lütfen gerekçenizi yazın")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "kanit.pdf" })).toBeNull();
    fireEvent.change(screen.getByLabelText("Gerekçeniz"), { target: { value: "Başvuru gözden kaçmış, hemen işleme alındı." } });
    fireEvent.click(screen.getByRole("button", { name: "Gerekçeyi gönder" }));
    await waitFor(() =>
      expect(submitExplanation).toHaveBeenCalledWith("c1", "Başvuru gözden kaçmış, hemen işleme alındı."),
    );
  });

  it("is null-safe", async () => {
    vi.mocked(getComplaint).mockResolvedValue({ ...base, created_at: null, description: null, attachments: null });
    const { container } = renderPage();
    await screen.findByText(/İşleminiz inceleniyor/);
    expect(container.textContent).not.toMatch(/null|Invalid Date|undefined/);
  });
});
