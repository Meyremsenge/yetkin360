import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import YeniSikayetPage from "@/app/sikayetlerim/yeni/page";
import { createComplaint, uploadAttachment } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";

const push = vi.fn();
let search = "subject_type=ENGAGEMENT&subject_id=eng-1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("@/components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@/lib/api/complaints", () => ({ createComplaint: vi.fn(), uploadAttachment: vi.fn() }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <YeniSikayetPage />
    </QueryClientProvider>,
  );
}

const LONG = "Başvurum üç haftadır yanıtsız bekliyor.";

describe("YeniSikayetPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    search = "subject_type=ENGAGEMENT&subject_id=eng-1";
  });
  afterEach(() => cleanup());

  it("explains when the subject is missing and renders no form", () => {
    search = "";
    renderPage();
    expect(screen.getByRole("alert").textContent).toContain("belirlenemedi");
    expect(screen.queryByLabelText("Açıklama")).toBeNull();
  });

  it("validates the description before calling the API", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Açıklama"), { target: { value: "kısa" } });
    fireEvent.click(screen.getByRole("button", { name: "Şikayeti gönder" }));
    await waitFor(() => expect(screen.getByText("Açıklama en az 10 karakter olmalı.")).toBeTruthy());
    expect(createComplaint).not.toHaveBeenCalled();
  });

  it("submits only subject + description, uploads attachments, then navigates", async () => {
    vi.mocked(createComplaint).mockResolvedValue({
      id: "c1",
      status: "OPEN",
      status_label: "IN_PROGRESS",
      subject_type: "ENGAGEMENT",
      subject_id: "eng-1",
    });
    vi.mocked(uploadAttachment).mockResolvedValue({ id: "f1" });
    renderPage();
    fireEvent.change(screen.getByLabelText("Açıklama"), { target: { value: LONG } });
    const file = new File(["%PDF-1.4"], "kanit.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/Belge ekle/), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Şikayeti gönder" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/sikayetlerim/c1"));
    expect(createComplaint).toHaveBeenCalledWith({
      subject_type: "ENGAGEMENT",
      subject_id: "eng-1",
      description: LONG,
    });
    expect(uploadAttachment).toHaveBeenCalledWith("c1", file);
  });

  it("maps 409 TOO_EARLY to a clear message", async () => {
    vi.mocked(createComplaint).mockRejectedValue(
      new ApiError({ status: 409, code: "TOO_EARLY", message: "x", requestId: null }),
    );
    renderPage();
    fireEvent.change(screen.getByLabelText("Açıklama"), { target: { value: LONG } });
    fireEvent.click(screen.getByRole("button", { name: "Şikayeti gönder" }));
    await waitFor(() => expect(screen.getByText(/Bekleme süresi henüz dolmadı/)).toBeTruthy());
    expect(push).not.toHaveBeenCalled();
  });

  it("maps 429 to the rate limit message", async () => {
    vi.mocked(createComplaint).mockRejectedValue(
      new ApiError({ status: 429, code: "RATE_LIMITED", message: "x", requestId: null }),
    );
    renderPage();
    fireEvent.change(screen.getByLabelText("Açıklama"), { target: { value: LONG } });
    fireEvent.click(screen.getByRole("button", { name: "Şikayeti gönder" }));
    await waitFor(() => expect(screen.getByText(/Çok fazla şikayet/)).toBeTruthy());
  });

  it("rejects a disallowed file type client-side", async () => {
    renderPage();
    const exe = new File(["MZ"], "x.exe", { type: "application/x-msdownload" });
    fireEvent.change(screen.getByLabelText(/Belge ekle/), { target: { files: [exe] } });
    await waitFor(() => expect(screen.getByText(/Yalnızca PDF, JPG veya PNG/)).toBeTruthy());
  });
});
