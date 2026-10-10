import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CertificateChecksSection } from "@/app/calismalar/[id]/certificate-checks-section";
import { listCertificateChecksForEngagement, resolveCertificateCheck } from "@/lib/api/evidence";
import { ApiError } from "@/lib/api/errors";
import type { CertificateCheck } from "@/lib/api/evidence";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/evidence");

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const pendingDecisionCheck: CertificateCheck = {
  id: "check-1",
  evidence_id: "ev-1",
  status: "DONE",
  provider: "COURSERA",
  credential_id: "ABC123",
  verify_url: "https://coursera.org/verify/ABC123",
  qr_raw_data: "https://coursera.org/verify/ABC123",
  extracted_name: "Ahmet Yılmaz",
  name_match: false,
  page_name: null,
  page_match: null,
  extracted_course_name: null,
  page_course_name: null,
  course_match: null,
  decision: "PENDING",
  decided_by_user_id: null,
  decided_at: null,
  created_at: "2026-10-10T00:00:00Z",
};

/**
 * PLAN 3.55 — Koordinatörün sertifika kontrol kuyruğu bölümü.
 */
describe("CertificateChecksSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("kontrol yoksa hiçbir şey render etmez", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([]);

    const { container } = renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(listCertificateChecksForEngagement).toHaveBeenCalledWith("eng-1");
    });
    expect(container.querySelector("section")).toBeNull();
  });

  it("isim eşleşmediğinde kırmızı uyarıyla gösterir, karar butonları görünür", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([pendingDecisionCheck]);

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText(/ABC123/)).toBeTruthy();
    });
    expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckNameMatchNo))).toBeTruthy();
    expect(screen.getByRole("button", { name: messages.calismalar.certificateCheckConfirmButton })).toBeTruthy();
    expect(screen.getByRole("button", { name: messages.calismalar.certificateCheckRejectButton })).toBeTruthy();
  });

  it("resmi sayfa adı ve eşleşmesi varsa koordinatöre gösterilir", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
      { ...pendingDecisionCheck, page_name: "Başka Bir İsim", page_match: false },
    ]);

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckPageNameLabel))).toBeTruthy();
    });
    expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckPageMatchNo))).toBeTruthy();
  });

  it("resmi sayfadaki kurs adı ve eşleşmesi varsa koordinatöre gösterilir", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
      {
        ...pendingDecisionCheck,
        page_name: "Ahmet Yılmaz",
        page_match: true,
        extracted_course_name: "Advanced Machine Learning",
        page_course_name: "Introduction to Front-End Development",
        course_match: false,
      },
    ]);

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Introduction to Front-End Development/)).toBeTruthy();
    });
    expect(screen.getByText(/Advanced Machine Learning/)).toBeTruthy();
    expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckCourseMatchNo))).toBeTruthy();
    expect(screen.queryByText(messages.calismalar.certificateCheckManualVerifyNotice)).toBeNull();
  });

  it("resmi sayfa otomatik açılamadıysa (Udemy) elle kontrol uyarısı ve karşılaştırılacak alanlar gösterilir", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
      {
        ...pendingDecisionCheck,
        provider: "UDEMY",
        credential_id: "UC-a677fedf-70be-4a21-a039-ad09955d4e18",
        verify_url: "https://ude.my/UC-a677fedf-70be-4a21-a039-ad09955d4e18",
        extracted_course_name: "Photoshop ile Mimari illüstrasyon ve kolaj",
      },
    ]);

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText(messages.calismalar.certificateCheckManualVerifyNotice)).toBeTruthy();
    });
    expect(screen.getByText(/Photoshop ile Mimari illüstrasyon ve kolaj/)).toBeTruthy();
    expect(
      screen.getByRole("link", { name: messages.calismalar.certificateCheckVerifyLinkLabel }).getAttribute("href")
    ).toBe("https://ude.my/UC-a677fedf-70be-4a21-a039-ad09955d4e18");
  });

  it("doğrulama linki hiç yoksa bunu açıkça söyler", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
      { ...pendingDecisionCheck, verify_url: null, qr_raw_data: null },
    ]);

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText(messages.calismalar.certificateCheckNoVerifyLinkNotice)).toBeTruthy();
    });
  });

  it("Onayla tıklanınca resolveCertificateCheck CONFIRMED ile çağrılır", async () => {
    const user = userEvent.setup();
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([pendingDecisionCheck]);
    vi.mocked(resolveCertificateCheck).mockResolvedValue({ ...pendingDecisionCheck, decision: "CONFIRMED" });

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    const confirmButton = await screen.findByRole("button", {
      name: messages.calismalar.certificateCheckConfirmButton,
    });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(resolveCertificateCheck).toHaveBeenCalledWith("check-1", "CONFIRMED");
    });
  });

  it("409 hatasında 'zaten incelenmiş' mesajı gösterir", async () => {
    const user = userEvent.setup();
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([pendingDecisionCheck]);
    vi.mocked(resolveCertificateCheck).mockRejectedValue(
      new ApiError({ status: 409, code: "NOT_PENDING", message: "x", requestId: null })
    );

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    const confirmButton = await screen.findByRole("button", {
      name: messages.calismalar.certificateCheckConfirmButton,
    });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(screen.getByText(messages.calismalar.certificateCheckAlreadyResolved)).toBeTruthy();
    });
  });

  it("karar verilmiş bir kontrol için buton yerine karar metni gösterilir", async () => {
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
      { ...pendingDecisionCheck, decision: "CONFIRMED" },
    ]);

    renderWithQueryClient(<CertificateChecksSection engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText(messages.calismalar.certificateCheckDecisionConfirmed)).toBeTruthy();
    });
    expect(screen.queryByRole("button", { name: messages.calismalar.certificateCheckConfirmButton })).toBeNull();
  });
});
