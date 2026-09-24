import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EvaluationForm } from "./evaluation-form";
import { submitEvaluation } from "@/lib/api/evaluation";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/lib/api/evaluation", () => ({
  submitEvaluation: vi.fn(),
}));

/**
 * YET-100/YET-101 (PLAN 2.13): Kurum tarafı değerlendirme formu.
 */
describe("EvaluationForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("başlangıçta bir kriter satırı ve 4 eşit rating seçeneği gösterir, NOT_OBSERVED varsayılan işaretli", () => {
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={vi.fn()} />);

    expect(screen.getByLabelText("Kriter")).toBeTruthy();
    expect(screen.getByLabelText("Beklentinin Altında")).toBeTruthy();
    expect(screen.getByLabelText("Beklentiyi Karşılıyor")).toBeTruthy();
    expect(screen.getByLabelText("Beklentiyi Aşıyor")).toBeTruthy();
    expect(screen.getByLabelText("Gözlemlenmedi")).toBeTruthy();
    expect((screen.getByLabelText("Gözlemlenmedi") as HTMLInputElement).checked).toBe(true);
    // "Kaldır" tek satırdayken gösterilmez
    expect(screen.queryByText("Kaldır")).toBeNull();
  });

  it("'Kriter Ekle' ile satır eklenir, her satırda 'Kaldır' görünür ve satırı kaldırır", async () => {
    const user = userEvent.setup();
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={vi.fn()} />);

    await user.click(screen.getByText("Kriter Ekle"));
    expect(screen.getAllByLabelText("Kriter")).toHaveLength(2);
    // 2 satır varken her satırın kendi "Kaldır" butonu vardır.
    expect(screen.getAllByText("Kaldır")).toHaveLength(2);

    await user.click(screen.getAllByText("Kaldır")[0]);
    expect(screen.getAllByLabelText("Kriter")).toHaveLength(1);
    // Tek satır kalınca "Kaldır" hiç gösterilmez.
    expect(screen.queryByText("Kaldır")).toBeNull();
  });

  it("kriter boş bırakılırsa gönderilmez, doğrulama hatası gösterilir", async () => {
    const user = userEvent.setup();
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={vi.fn()} />);

    await user.click(screen.getByText("Değerlendirmeyi Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Kriter adı gereklidir")).toBeTruthy();
    });
    expect(submitEvaluation).not.toHaveBeenCalled();
  });

  it("geçerli form gönderilince submitEvaluation doğru payload ile çağrılır ve onSubmitted tetiklenir", async () => {
    vi.mocked(submitEvaluation).mockResolvedValueOnce({
      id: "mock-evaluation-1",
      engagement_id: "mock-eng-5",
      direction: "ORG_TO_TALENT",
      submitted_at: "2026-09-24T00:00:00Z",
    });
    const onSubmitted = vi.fn();

    const user = userEvent.setup();
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={onSubmitted} />);

    await user.type(screen.getByLabelText("Kriter"), "Python kullanımı");
    await user.click(screen.getByLabelText("Beklentiyi Aşıyor"));
    await user.type(screen.getByLabelText("Kurum içi not (opsiyonel)"), "Gizli not");
    await user.click(screen.getByText("Değerlendirmeyi Gönder"));

    await waitFor(() => {
      expect(submitEvaluation).toHaveBeenCalledWith("mock-eng-5", "ORG_TO_TALENT", {
        items: [{ criterion: "Python kullanımı", rating: "EXCEEDS", comment: "" }],
        private_note: "Gizli not",
      });
      expect(onSubmitted).toHaveBeenCalled();
    });
  });

  it("409 ALREADY_SUBMITTED hatasında uygun mesaj gösterilir", async () => {
    vi.mocked(submitEvaluation).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "ALREADY_SUBMITTED", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={vi.fn()} />);

    await user.type(screen.getByLabelText("Kriter"), "X");
    await user.click(screen.getByText("Değerlendirmeyi Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bu çalışma için değerlendirme zaten gönderilmiş.")).toBeTruthy();
    });
  });

  it("422 INVALID_STATUS hatasında uygun mesaj gösterilir", async () => {
    vi.mocked(submitEvaluation).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "INVALID_STATUS", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={vi.fn()} />);

    await user.type(screen.getByLabelText("Kriter"), "X");
    await user.click(screen.getByText("Değerlendirmeyi Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bu çalışma şu anda değerlendirme aşamasında değil.")).toBeTruthy();
    });
  });

  it("bilinmeyen hata durumunda genel hata mesajı gösterilir", async () => {
    vi.mocked(submitEvaluation).mockRejectedValueOnce(new Error("boom"));

    const user = userEvent.setup();
    render(<EvaluationForm engagementId="mock-eng-5" onSubmitted={vi.fn()} />);

    await user.type(screen.getByLabelText("Kriter"), "X");
    await user.click(screen.getByText("Değerlendirmeyi Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.")).toBeTruthy();
    });
  });
});
