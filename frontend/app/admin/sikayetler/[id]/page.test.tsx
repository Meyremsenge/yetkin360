import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminSikayetDetayPage from "@/app/admin/sikayetler/[id]/page";
import {
  adminGetComplaint,
  adminTransition,
  getAttachmentDownloadUrl,
  type AdminComplaint,
} from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "c1" }) }));
vi.mock("@/components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/lib/api/complaints", async (orig) => {
  const actual = await orig<typeof import("@/lib/api/complaints")>();
  return { ...actual, adminGetComplaint: vi.fn(), adminTransition: vi.fn(), getAttachmentDownloadUrl: vi.fn() };
});

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AdminSikayetDetayPage />
    </QueryClientProvider>,
  );
}

const make = (over: Partial<AdminComplaint> = {}): AdminComplaint => ({
  id: "c1",
  status: "UNDER_REVIEW",
  status_label: "IN_PROGRESS",
  subject_type: "ENGAGEMENT",
  subject_id: "e1",
  created_at: "2026-10-01T10:00:00Z",
  description: "Yanıt yok",
  attachments: [{ id: "f1", filename: "kanit.pdf" }],
  ...over,
});

describe("AdminSikayetDetayPage", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("opens the attachment through the signed url of the admin download route", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make());
    vi.mocked(getAttachmentDownloadUrl).mockResolvedValue("http://minio/signed");
    const tab = { opener: {}, location: { href: "" }, close: vi.fn() };
    const openSpy = vi.spyOn(window, "open").mockReturnValue(tab as unknown as Window);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "kanit.pdf" }));
    await waitFor(() => expect(tab.location.href).toBe("http://minio/signed"));
    expect(getAttachmentDownloadUrl).toHaveBeenCalledWith("c1", "f1", { admin: true });
    expect(tab.opener).toBeNull();
    openSpy.mockRestore();
  });

  it("closes the tab and shows an error when the signed url cannot be fetched", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make());
    vi.mocked(getAttachmentDownloadUrl).mockRejectedValue(new Error("boom"));
    const tab = { opener: {}, location: { href: "" }, close: vi.fn() };
    const openSpy = vi.spyOn(window, "open").mockReturnValue(tab as unknown as Window);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "kanit.pdf" }));
    expect(await screen.findByText("Belge açılamadı. Lütfen tekrar deneyin.")).toBeTruthy();
    expect(tab.close).toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it("sends the acceptance comment as `reason` for ACCEPT_EXPLANATION (backend ignores `note` there)", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make({ status: "EXPLANATION_SUBMITTED" }));
    vi.mocked(adminTransition).mockResolvedValue(make({ status: "RESOLVED" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Gerekçeyi kabul et" }));
    fireEvent.change(screen.getByLabelText("Not (isteğe bağlı)"), { target: { value: "Gerekçe makul." } });
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    await waitFor(() =>
      expect(adminTransition).toHaveBeenCalledWith("c1", { action: "ACCEPT_EXPLANATION", reason: "Gerekçe makul." }),
    );
  });

  it("sends the rejection text as `reason` for REJECT_EXPLANATION", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make({ status: "EXPLANATION_SUBMITTED" }));
    vi.mocked(adminTransition).mockResolvedValue(make({ status: "ESCALATED" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Gerekçeyi reddet ve yükselt" }));
    fireEvent.change(screen.getByLabelText("Gerekçe"), { target: { value: "Yetersiz." } });
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    await waitFor(() =>
      expect(adminTransition).toHaveBeenCalledWith("c1", { action: "REJECT_EXPLANATION", reason: "Yetersiz." }),
    );
  });

  it("sends the request text as `note` for REQUEST_EXPLANATION", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make({ status: "UNDER_REVIEW" }));
    vi.mocked(adminTransition).mockResolvedValue(make({ status: "EXPLANATION_REQUESTED" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Gerekçe iste" }));
    fireEvent.change(screen.getByLabelText("Not (yetkiliye iletilir)"), { target: { value: "Neden gecikti?" } });
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    await waitFor(() =>
      expect(adminTransition).toHaveBeenCalledWith("c1", { action: "REQUEST_EXPLANATION", note: "Neden gecikti?" }),
    );
  });

  it("sends the loaded version with a transition (optimistic lock)", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make({ status: "OPEN", version: 3 }));
    vi.mocked(adminTransition).mockResolvedValue(make({ status: "UNDER_REVIEW", version: 4 }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "İncelemeye al" }));
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    await waitFor(() =>
      expect(adminTransition).toHaveBeenCalledWith("c1", { action: "START_REVIEW", version: 3 }),
    );
  });

  it("requires a reason for DISMISS and sends reason when given", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make());
    vi.mocked(adminTransition).mockResolvedValue(make({ status: "DISMISSED" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Haksız bul ve kapat" }));
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    expect(await screen.findByText("Bu işlem için gerekçe zorunludur.")).toBeTruthy();
    expect(adminTransition).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Gerekçe"), { target: { value: "Süre dolmamış." } });
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    await waitFor(() =>
      expect(adminTransition).toHaveBeenCalledWith("c1", { action: "DISMISS", reason: "Süre dolmamış." }),
    );
  });

  it("asks for confirmation before the irreversible UPHOLD", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make({ status: "ESCALATED" }));
    vi.mocked(adminTransition).mockResolvedValue(make({ status: "UPHELD" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Haklı bul" }));
    fireEvent.change(screen.getByLabelText("Gerekçe"), { target: { value: "Yanıt yok." } });
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));

    expect(await screen.findByRole("alertdialog")).toBeTruthy();
    expect(adminTransition).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Vazgeç" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(adminTransition).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    fireEvent.click(await screen.findByRole("button", { name: "Evet, haklı bul" }));
    await waitFor(() =>
      expect(adminTransition).toHaveBeenCalledWith("c1", { action: "UPHOLD", reason: "Yanıt yok." }),
    );
  });

  it("shows a clear message on 409 INVALID_TRANSITION", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(make());
    vi.mocked(adminTransition).mockRejectedValue(
      new ApiError({ status: 409, code: "INVALID_TRANSITION", message: "x", requestId: null }),
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Haksız bul ve kapat" }));
    fireEvent.change(screen.getByLabelText("Gerekçe"), { target: { value: "Haksız." } });
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    expect(await screen.findByText(/Bu işlem şikayetin mevcut durumunda yapılamaz/)).toBeTruthy();
  });

  it("offers no actions on a terminal complaint and is null-safe", async () => {
    vi.mocked(adminGetComplaint).mockResolvedValue(
      make({ status: "UPHELD", created_at: null, description: null, attachments: null, events: null }),
    );
    const { container } = renderPage();
    expect(await screen.findByText("Bu durumda yapılabilecek işlem yok.")).toBeTruthy();
    expect(container.textContent).not.toMatch(/null|Invalid Date|undefined/);
  });
});
